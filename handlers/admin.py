import sys
import os
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS
from keyboards.admin_kb import get_admin_keyboard
from keyboards.client_kb import get_main_keyboard
from database import Database
import json
from datetime import datetime
from aiogram.fsm.context import FSMContext
from states.admin_states import AdminStates

router = Router()
db = Database()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def save_restart_status(status: str, error: str = None):
    """Сохраняет статус перезапуска бота"""
    try:
        status_data = {
            'status': status,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': error
        }
        
        with open('restart_status.json', 'w') as f:
            json.dump(status_data, f)
            
    except Exception as e:
        print(f"Ошибка при сохранении статуса: {e}")

def get_restart_status() -> dict:
    """Получает информацию о последнем перезапуске"""
    try:
        with open('restart_status.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Ошибка при чтении статуса: {e}")
        return None
# Добавляем в базу данных таблицу для ожидающих доступ
async def init_db():
    db.execute_query('''
    CREATE TABLE IF NOT EXISTS pending_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

# Функция для добавления пользователя в список ожидающих
async def add_pending_user(bot: Bot, user_id: int, username: str = None, full_name: str = None):
    # Добавляем пользователя в список ожидающих
    db.execute_query(
        'INSERT OR REPLACE INTO pending_users (user_id, username, full_name) VALUES (?, ?, ?)',
        (user_id, username, full_name)
    )
    
    # Уведомляем всех админов
    for admin_id in ADMIN_IDS:
        try:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👥 Просмотреть заявку",
                            callback_data=f"view_request_{user_id}"
                        )
                    ]
                ]
            )
            
            # Отправляем краткое уведомление
            await bot.send_message(
                admin_id,
                f"❗️ Новая заявка на доступ от пользователя @{username or 'без username'}",
                reply_markup=keyboard
            )
            
            # Отправляем всплывающее уведомление
            await bot.send_message(
                admin_id,
                "❗️ Новый пользователь ожидает подтверждения",
                disable_notification=False  # Включаем звук уведомления
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления админу {admin_id}: {e}")

# Добавляем обработчик для просмотра заявки
@router.callback_query(lambda c: c.data.startswith('view_request_'))
async def view_user_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.split('_')[2])
    
    # Получаем информацию о пользователе
    user_info = db.execute_query(
        'SELECT user_id, username, full_name, request_time FROM pending_users WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if user_info:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Выдать доступ",
                        callback_data=f"grant_{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"deny_{user_id}"
                    )
                ]
            ]
        )
        
        await callback.message.edit_text(
            f"👤 <b>Заявка на доступ</b>\n\n"
            f"• ID: <code>{user_info[0]}</code>\n"
            f"• Username: @{user_info[1] or 'нет'}\n"
            f"• Имя: {user_info[2] or 'не указано'}\n"
            f"• Время запроса: {user_info[3]}\n\n"
            f"ℹ️ Выберите действие:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Заявка не найдена или уже обработана")

# Обработчик для админ-панели
@router.message(lambda m: m.text == "⚙️ Админ-панель" and m.from_user.id in ADMIN_IDS)
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем статус последнего перезапуска
    restart_status = get_restart_status()
    status_text = ""
    
    if restart_status:
        if restart_status['status'] == 'success':
            status_text = (
                "\n\n✅ Статус бота: работает\n"
                f"🕒 Последний перезапуск: {restart_status['timestamp']}"
            )
        elif restart_status['status'] == 'error':
            status_text = (
                "\n\n❌ Ошибка при последнем перезапуске\n"
                f"🕒 Время: {restart_status['timestamp']}\n"
                f"⚠️ Ошибка: {restart_status['error']}"
            )
        elif restart_status['status'] == 'stopped':
            status_text = (
                "\n\n⛔️ Бот был остановлен\n"
                f"🕒 Время: {restart_status['timestamp']}\n"
                f"📝 Причина: {restart_status['error']}"
            )
    
    await message.answer(
        f"🔧 Панель администратора{status_text}",
        reply_markup=get_admin_keyboard()
    )

# Обработчик для рестарта бота
@router.message(lambda m: m.text == "🔄 Рестарт" and m.from_user.id in ADMIN_IDS)
async def restart_bot(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        await message.answer("🔄 Перезапуск бота...")
        save_restart_status('restarting')
        
        # Сохраняем chat_id для уведомления после рестарта
        with open('restart_chat.txt', 'w') as f:
            f.write(str(message.chat.id))
        
        # Перезапускаем процесс
        os.execv(sys.executable, ['python'] + sys.argv)
        
    except Exception as e:
        save_restart_status('error', str(e))
        await message.answer(f"❌ Ошибка при перезапуске: {e}")

# Обработчик для проверки статуса после рестарта
@router.message(lambda m: m.text == "📊 Статус" and m.from_user.id in ADMIN_IDS)
async def check_status(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    restart_status = get_restart_status()
    if restart_status:
        status_text = (
            "📊 Статус бота:\n\n"
            f"▫️ Состояние: {'✅ Работает' if restart_status['status'] == 'success' else '❌ Ошибка'}\n"
            f"▫️ Последний рестарт: {restart_status['timestamp']}\n"
        )
        if restart_status.get('error'):
            status_text += f"▫️ Ошибка: {restart_status['error']}\n"
    else:
        status_text = "❌ Информация о статусе недоступна"
    
    await message.answer(status_text, reply_markup=get_admin_keyboard())

# Обработчик для кнопки "Назад"
@router.message(F.text == "↩️ Назад")
async def back_to_main(message: Message):
    user_id = message.from_user.id
    if is_admin(user_id):
        await message.answer(
            "Вы вернулись в главное меню администратора",
            reply_markup=get_main_keyboard(user_id)
        )
    else:
        await message.answer(
            "Вы вернулись в главное меню",
            reply_markup=get_main_keyboard(user_id)
        )

# Обработчик для неизвестных команд админ-панели
@router.message(lambda m: m.text in ["🔄 Рестарт", "⚙️ Админ-панель"] and m.from_user.id not in ADMIN_IDS)
async def unauthorized_admin_access(message: Message):
    await message.answer(
        "⚠️ У вас нет доступа к этой функции",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

# Добавляем команду для выдачи доступа
@router.message(lambda m: m.text.startswith('/grant_access'))
async def grant_access(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Получаем ID пользователя из сообщения
        user_id = int(message.text.split()[1])
        
        # Добавляем пользователя в базу данных
        if db.add_allowed_user(user_id, message.from_user.id):
            await message.answer(f"✅ Доступ выдан пользователю {user_id}")
        else:
            await message.answer("❌ Ошибка при выдаче доступа")
            
    except (IndexError, ValueError):
        await message.answer(
            "❌ Неверный формат команды\n"
            "Используйте: /grant_access USER_ID"
        )

# Добавляем команду для отзыва доступа
@router.message(lambda m: m.text.startswith('/revoke_access'))
async def revoke_access(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Получаем ID пользователя из сообщения
        user_id = int(message.text.split()[1])
        
        # Удаляем пользователя из базы данных
        if db.remove_allowed_user(user_id):
            await message.answer(f"✅ Доступ отозван у пользователя {user_id}")
        else:
            await message.answer("❌ Ошибка при отзыве доступа")
            
    except (IndexError, ValueError):
        await message.answer(
            "❌ Неверный формат команды\n"
            "Используйте: /revoke_access USER_ID"
        )

# Добавляем команду для просмотра списка пользователей с доступом
@router.message(lambda m: m.text == '/list_access')
async def list_access(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    users = db.get_allowed_users()
    if users:
        text = "📋 Пользователи с доступом:\n\n"
        for user_id in users:
            text += f"• {user_id}\n"
    else:
        text = "📋 Список пользователей с доступом пуст"
    
    await message.answer(text)

# Добавляем справку по командам доступа
@router.message(lambda m: m.text == '/access_help')
async def access_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    help_text = (
        "📝 Команды управления доступом:\n\n"
        "/grant_access USER_ID - выдать доступ\n"
        "/revoke_access USER_ID - отозвать доступ\n"
        "/list_access - список пользователей с доступом\n"
        "/access_help - эта справка"
    )
    
    await message.answer(help_text)

# Обработчик кнопки "Ожидают доступ" в админ-панели
@router.message(lambda m: m.text == "👥 Ожидают доступ" and m.from_user.id in ADMIN_IDS)
async def show_pending_users(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    # Получаем список ожидающих
    pending = db.execute_query(
        'SELECT user_id, username, full_name, request_time FROM pending_users'
    ).fetchall()
    
    if not pending:
        await message.answer(
            "📝 Нет пользователей, ожидающих доступ",
            reply_markup=get_admin_keyboard()
        )
        return
        
    text = "📝 Пользователи, ожидающие доступ:\n\n"
    for user in pending:
        text += (
            f"👤 ID: {user[0]}\n"
            f"Username: @{user[1]}\n"
            f"Имя: {user[2]}\n"
            f"Запрос от: {user[3]}\n"
            "➖➖➖➖➖➖➖➖➖\n"
        )
        
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Выдать доступ всем",
                    callback_data="grant_all"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить всех",
                    callback_data="deny_all"
                )
            ]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard)

# Обработчики callback-кнопок
@router.callback_query(lambda c: c.data.startswith(("grant_", "deny_")))
async def process_access_action(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
        
    action, user_id = callback.data.split('_')
    bot = callback.bot
    
    if user_id == "all":
        if action == "grant":
            # Выдаем доступ всем ожидающим
            pending = db.execute_query('SELECT user_id FROM pending_users').fetchall()
            for user in pending:
                db.add_allowed_user(user[0])
                try:
                    await bot.send_message(
                        user[0],
                        "✅ Администратор одобрил ваш доступ к боту!\n"
                        "Теперь вы можете пользоваться всеми функциями."
                    )
                except:
                    pass
            db.execute_query('DELETE FROM pending_users')
            await callback.message.edit_text("✅ Доступ выдан всем пользователям")
        else:
            # Отклоняем всех
            pending = db.execute_query('SELECT user_id FROM pending_users').fetchall()
            for user in pending:
                try:
                    await bot.send_message(
                        user[0],
                        "❌ К сожалению, ваш запрос на доступ отклонен."
                    )
                except:
                    pass
            db.execute_query('DELETE FROM pending_users')
            await callback.message.edit_text("❌ Все запросы отклонены")
    else:
        user_id = int(user_id)
        if action == "grant":
            db.add_allowed_user(user_id)
            try:
                await bot.send_message(
                    user_id,
                    "✅ Администратор одобрил ваш доступ к боту!\n"
                    "Теперь вы можете пользоваться всеми функциями."
                )
            except:
                pass
            db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
            await callback.message.edit_text(f"✅ Доступ выдан пользователю {user_id}")
        else:
            try:
                await bot.send_message(
                    user_id,
                    "❌ К сожалению, ваш запрос на доступ отклонен."
                )
            except:
                pass
            db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
            await callback.message.edit_text(f"❌ Запрос пользователя {user_id} отклонен") 

# Обработчик команды /admin
@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🔧 Панель администратора",
        reply_markup=get_admin_keyboard()
    )

# Обработчик для кнопки "👥 Пользователи"
@router.message(lambda m: m.text == "👥 Пользователи" and m.from_user.id in ADMIN_IDS)
async def users_menu(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    # Получаем списки пользователей
    allowed_users = db.execute_query('''
        SELECT au.user_id, au.added_at, au.added_by 
        FROM allowed_users au
        ORDER BY au.added_at DESC
    ''').fetchall()
    
    # Получаем список ожидающих
    pending_users = db.get_pending_users()
    
    text = "<b>👥 Управление пользователями</b>\n\n"
    
    # Список пользователей с доступом
    if allowed_users:
        text += "<b>✅ Пользователи с доступом:</b>\n"
        for user in allowed_users:
            user_id, added_at, added_by = user
            text += f"• ID: {user_id} | Добавлен: {added_at[:16]}\n"
    else:
        text += "❌ Нет пользователей с доступом\n"
    
    keyboard = []
    
    # Кнопки удаления для пользователей с доступом
    for user in allowed_users:
        user_id = user[0]
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"❌ Удалить {user_id}",
                callback_data=f"remove_user:{user_id}"
            )
        ])
    
    # Список и кнопки для ожидающих доступ
    if pending_users:
        text += "\n<b>⏳ Ожидают доступа:</b>\n"
        for user in pending_users:
            user_id, username, full_name, req_time = user
            text += (
                f"• ID: {user_id}\n"
                f"  └ Имя: {full_name or 'не указано'}\n"
                f"  └ @{username or 'нет username'}\n"
                f"  └ Запрос: {req_time[:16]}\n"
            )
            # Добавляем кнопки одобрения/отклонения для каждого ожидающего
            keyboard.append([
                types.InlineKeyboardButton(
                    text=f"✅ Одобрить {user_id}",
                    callback_data=f"approve_user:{user_id}"
                ),
                types.InlineKeyboardButton(
                    text=f"❌ Отклонить",
                    callback_data=f"deny_user:{user_id}"
                )
            ])
        
        # Кнопки для массовых действий
        keyboard.append([
            types.InlineKeyboardButton(
                text="✅ Одобрить всех",
                callback_data="approve_all"
            ),
            types.InlineKeyboardButton(
                text="❌ Отклонить всех",
                callback_data="deny_all"
            )
        ])
    else:
        text += "\n⏳ Нет ожидающих доступа"
    
    # Добавляем кнопку для добавления пользователя
    keyboard.append([
        types.InlineKeyboardButton(
            text="➕ Добавить пользователя",
            callback_data="add_user"
        )
    ])
    
    keyboard.append([
        types.InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_users"
        )
    ])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup, parse_mode="HTML")

# Добавляем обработчики для одобрения/отклонения отдельных пользователей
@router.callback_query(lambda c: c.data.startswith('approve_user:'))
async def approve_single_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        _, user_id = callback.data.split(':')
        user_id = int(user_id)
        
        # Добавляем пользователя в список разрешенных
        if db.add_allowed_user(user_id, callback.from_user.id):
            # Удаляем из списка ожидающих
            db.remove_pending_user(user_id)
            
            try:
                # Уведомляем пользователя
                await callback.bot.send_message(
                    user_id,
                    "✅ Ваш запрос на доступ к боту одобрен!"
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            await callback.answer("✅ Пользователь одобрен")
            await users_menu(callback.message)
        else:
            await callback.answer("❌ Ошибка при одобрении пользователя")
            
    except Exception as e:
        print(f"Ошибка при одобрении пользователя: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data.startswith('deny_user:'))
async def deny_single_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        _, user_id = callback.data.split(':')
        user_id = int(user_id)
        
        # Удаляем из списка ожидающих
        if db.remove_pending_user(user_id):
            try:
                # Уведомляем пользователя
                await callback.bot.send_message(
                    user_id,
                    "❌ Ваш запрос на доступ к боту отклонен."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            await callback.answer("✅ Пользователь отклонен")
            await users_menu(callback.message)
        else:
            await callback.answer("❌ Ошибка при отклонении пользователя")
            
    except Exception as e:
        print(f"Ошибка при отклонении пользователя: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data == "refresh_users")
async def refresh_users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await callback.answer("🔄 Список обновлен")
    await users_menu(callback.message)

# Обработчик для одобрения/отклонения пользователей
@router.callback_query(lambda c: c.data in ["approve_all", "deny_all"])
async def process_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    action = callback.data
    bot = callback.bot
    
    if action == "approve_all":
        # Получаем всех ожидающих пользователей
        pending_users = db.execute_query('SELECT user_id FROM pending_users').fetchall()
        
        # Одобряем каждого пользователя
        for user in pending_users:
            user_id = user[0]
            db.add_allowed_user(user_id)
            try:
                await bot.send_message(
                    user_id,
                    "✅ Ваш доступ к боту одобрен администратором!\n"
                    "Теперь вы можете пользоваться всеми функциями бота."
                )
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        
        # Очищаем список ожидающих
        db.execute_query('DELETE FROM pending_users')
        
        await callback.message.edit_text(
            f"✅ Одобрено {len(pending_users)} пользователей"
        )
    
    elif action == "deny_all":
        # Получаем всех ожидающих пользователей
        pending_users = db.execute_query('SELECT user_id FROM pending_users').fetchall()
        
        # Отправляем уведомления об отказе
        for user in pending_users:
            try:
                await bot.send_message(
                    user[0],
                    "❌ К сожалению, ваш запрос на доступ к боту был отклонен."
                )
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
        
        # Очищаем список ожидающих
        db.execute_query('DELETE FROM pending_users')
        
        await callback.message.edit_text(
            f"❌ Отклонено {len(pending_users)} запросов"
        )

# Обработчик для выдачи доступа конкретному пользователю
@router.message(Command("grant"))
async def grant_access(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Используйте: /grant USER_ID"
        )
        return
    
    try:
        user_id = int(args[1])
        db.add_allowed_user(user_id)
        db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
        
        try:
            await message.bot.send_message(
                user_id,
                "✅ Ваш доступ к боту одобрен администратором!\n"
                "Теперь вы можете пользоваться всеми функциями бота."
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        
        await message.answer(f"✅ Доступ выдан пользователю {user_id}")
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}") 

@router.callback_query(lambda c: c.data.startswith('remove_user:'))
async def remove_user_access(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора")
        return
    
    try:
        # Получаем user_id из callback_data
        user_id = int(callback.data.split(':')[1])
        
        # Проверяем существование пользователя в базе
        if db.is_user_allowed(user_id):
            # Удаляем пользователя
            if db.remove_allowed_user(user_id):
                try:
                    # Уведомляем пользователя об удалении доступа
                    await callback.bot.send_message(
                        user_id,
                        "❌ Ваш доступ к боту был отозван администратором."
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
                
                await callback.answer("✅ Пользователь успешно удален")
                # Обновляем список пользователей
                await users_menu(callback.message)
            else:
                await callback.answer("❌ Ошибка при удалении из базы данных")
        else:
            await callback.answer("❌ Пользователь не найден в базе")
            await users_menu(callback.message)
            
    except ValueError as e:
        print(f"Ошибка преобразования user_id: {e}")
        await callback.answer("❌ Некорректный ID пользователя")
    except Exception as e:
        print(f"Неожиданная ошибка при удалении пользователя: {e}")
        await callback.answer("❌ Произошла ошибка при удалении") 

@router.callback_query(lambda c: c.data == "add_user")
async def add_user_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    keyboard = [
        [
            types.InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_add_user"
            )
        ]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.answer(
        "👤 Введите username пользователя\n"
        "❗️ Username должен начинаться с @\n\n"
        "<i>Например: @test_user</i>",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_username)
    await callback.answer()

@router.message(AdminStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    
    username = message.text.strip()
    
    if not username.startswith('@'):
        await message.answer(
            "❌ Username должен начинаться с @\n"
            "Попробуйте еще раз или нажмите кнопку отмены"
        )
        return
    
    try:
        # Создаем клавиатуру для подтверждения
        keyboard = [
            [
                types.InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"confirm_add:{username}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_add_user"
                )
            ]
        ]
        markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await message.answer(
            f"📝 Добавить пользователя {username}?",
            reply_markup=markup
        )
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка: {e}")
        await state.clear()

@router.callback_query(lambda c: c.data.startswith('confirm_add:'))
async def confirm_add_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    
    username = callback.data.split(':')[1]
    
    try:
        # Добавляем username в список разрешенных
        if db.add_allowed_username(username):
            # Получаем информацию о пользователе из списка ожидающих
            pending_users = db.get_pending_users()
            user_id = None
            
            # Ищем пользователя по username среди ожидающих
            for pending_user in pending_users:
                if f"@{pending_user[1]}" == username:  # pending_user[1] - это username
                    user_id = pending_user[0]  # pending_user[0] - это user_id
                    break
            
            if user_id:
                try:
                    # Отправляем уведомление пользователю
                    await callback.bot.send_message(
                        user_id,
                        "✅ Администратор одобрил ваш запрос!\n"
                        "Теперь вы можете пользоваться ботом."
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление пользователю: {e}")
            
            await callback.message.edit_text(
                f"✅ Username {username} добавлен в список разрешенных!\n"
                "Пользователь получит доступ при следующем обращении к боту."
            )
            
            await users_menu(callback.message)
        else:
            await callback.message.edit_text("❌ Ошибка при добавлении пользователя")
    
    except Exception as e:
        await callback.message.edit_text(f"❌ Произошла ошибка: {e}")
    
    finally:
        await state.clear()

@router.callback_query(lambda c: c.data == "cancel_add_user")
async def cancel_add_user(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Добавление пользователя отменено")
    await callback.answer() 

# Добавляем обработчик для кнопки открытия панели пользователей
@router.callback_query(lambda c: c.data == "open_users_panel")
async def open_users_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await users_menu(callback.message)
    await callback.answer() 

@router.callback_query(lambda c: c.data.startswith('grant_'))
async def process_grant_access(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        user_id = int(callback.data.split('_')[1])
        
        if db.add_allowed_user(user_id, callback.from_user.id):
            try:
                await callback.bot.send_message(
                    user_id,
                    "✅ Администратор одобрил ваш запрос!\n"
                    "Теперь вы можете пользоваться ботом."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            db.remove_pending_user(user_id)
            await callback.message.edit_text(f"✅ Доступ выдан пользователю {user_id}")
        else:
            await callback.message.edit_text("❌ Ошибка при выдаче доступа")
            
    except Exception as e:
        await callback.answer(f"❌ Произошла ошибка: {e}") 