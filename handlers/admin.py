import sys
import os
import asyncio
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_IDS
from keyboards.admin_kb import get_admin_keyboard
from keyboards.client_kb import get_main_keyboard
from database import db
import json
from datetime import datetime
from aiogram.fsm.context import FSMContext
from states.admin_states import AdminStates
from aiogram.methods import GetChat
from aiogram.fsm.state import StatesGroup, State

router = Router()

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
    # Создаем таблицу для ожидающих доступ
    db.execute_query('''
    CREATE TABLE IF NOT EXISTS pending_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Создаем таблицу для пользователей с доступом
    db.execute_query('''
    CREATE TABLE IF NOT EXISTS allowed_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        granted_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
async def view_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        user_id = int(callback.data.split('_')[2])
        
        # Получаем информацию о пользователе
        user = db.execute_query(
            'SELECT user_id, username, full_name, request_time FROM pending_users WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        
        if not user:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        text = "👤 Заявка на доступ\n\n"
        text += f"• ID: {user[0]}\n"
        text += f"Username: @{user[1]}\n" if user[1] and user[1] != "Нет username" else "Username: не указан\n"
        text += f"Имя: {user[2]}\n" if user[2] and user[2] != "Нет имени" else "Имя: не указано\n"
        text += f"• Время запроса: {user[3]}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Ошибка при просмотре заявки: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

# Обработчик для админ-панели
@router.message(lambda m: m.text == "⚙️ Админ-панель" and m.from_user.id in ADMIN_IDS)
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    await message.answer(
        "⚙️ Панель администратора\n\n"
        "Выберите нужный раздел:",
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
    
    allowed_users = db.execute_query('''
        SELECT user_id, username, full_name
        FROM allowed_users 
        WHERE user_id NOT IN ({})
    '''.format(','.join(map(str, ADMIN_IDS)))).fetchall()

    if not allowed_users:
        await message.answer("📊 Список пользователей с доступом пуст")
        return

    text = "📊 Пользователи с доступом:\n\n"
    keyboard = []
    
    for user in allowed_users:
        user_id, username, full_name = user
        # Делаем текст пользователя в одну строку и добавляем пробелы для ширины
        user_info = f"ID: {user_id} | @{username} | {full_name}                    "
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{user_info}❌ Отозвать",
                callback_data=f"revoke_{user_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_allowed"
        )
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

# Добавляем обработчик обновления списка
@router.callback_query(lambda c: c.data == "refresh_list")
async def refresh_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await list_access(callback.message)
    await callback.answer("Список обновлен")

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
@router.message(lambda m: m.text == "👥 Ожидают доступ")
async def show_pending_users(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    # Получаем список ожидающих
    pending_users = db.execute_query(
        'SELECT user_id, username, full_name, request_time FROM pending_users'
    ).fetchall()
    
    text = "📊 Ожидают доступа:\n\n"
    keyboard = []
    
    if pending_users:
        for user_id, username, full_name, req_time in pending_users:
            text += f"• ID: {user_id}\n"
            text += f"Username: @{username}\n" if username and username != "Нет username" else "Username: не указан\n"
            text += f"Имя: {full_name}\n" if full_name and full_name != "Нет имени" else "Имя: не указано\n"
            text += f"Запрос: {req_time}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text="✅ Выдать доступ",
                    callback_data=f"grant_{user_id}"
                )
            ])
    else:
        text = "👥 Нет ожидающих доступа"
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_pending"
        )
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

@router.message(lambda m: m.text == "✅ Пользователи с доступом" and m.from_user.id in ADMIN_IDS)
async def show_allowed_users(message: Message):
    if not is_admin(message.from_user.id):
        return
        
    # Получаем пользователей с доступом
    allowed_users = db.execute_query('''
        SELECT user_id, username, full_name
        FROM allowed_users 
        WHERE user_id NOT IN ({})
    '''.format(','.join(map(str, ADMIN_IDS)))).fetchall()
    
    if not allowed_users:
        text = "📊 Список пользователей с доступом пуст"
        await message.answer(text)
        return

    text = "📊 Пользователи с доступом:"
    keyboard = []
    
    for user in allowed_users:
        user_id, username, full_name = user
        # Форматируем информацию о пользователе в одну строку с отступами
        user_text = f"ID: {user_id} | @{username} | {full_name}                              "
        
        # Добавляем одну кнопку на строку с информацией и кнопкой отзыва
        keyboard.append([
            InlineKeyboardButton(
                text=user_text,
                callback_data=f"info_{user_id}"
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"revoke_{user_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_allowed"
        )
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

# Обработчики callback-кнопок
@router.callback_query(lambda c: c.data.startswith(("grant_", "deny_")))
async def process_access_action(callback: CallbackQuery):
    try:
        action, user_id = callback.data.split('_')
        user_id = int(user_id)
        
        bot = callback.bot
        
        if action == "grant":
            # Получаем информацию о пользователе из pending_users
            user_info = db.execute_query(
                'SELECT username, full_name FROM pending_users WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            
            if user_info:
                username, full_name = user_info
                # Добавляем пользователя в список разрешенных с сохранением username
                db.execute_query(
                    'INSERT OR REPLACE INTO allowed_users (user_id, username, full_name) VALUES (?, ?, ?)',
                    (user_id, username, full_name)
                )
            else:
                # Если нет в pending_users, получаем через API
                chat_member = await bot.get_chat_member(user_id, user_id)
                username = chat_member.user.username
                full_name = chat_member.user.full_name
                db.execute_query(
                    'INSERT OR REPLACE INTO allowed_users (user_id, username, full_name) VALUES (?, ?, ?)',
                    (user_id, username, full_name)
                )
            
            try:
                await bot.send_message(
                    user_id,
                    "✅ Администратор одобрил ваш доступ к боту!\n"
                    "Теперь вы можете пользоваться всеми функциями."
                )
                db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
                await callback.message.edit_text(f"✅ Доступ выдан пользователю {username or user_id}")
                await callback.answer("✅ Доступ выдан", show_alert=True)
                
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                await callback.answer("❌ Ошибка отправки уведомления", show_alert=True)
            
        elif action == "deny":
            try:
                # Отправляем уведомление об отказе
                await bot.send_message(
                    user_id,
                    "❌ К сожалению, ваш запрос на доступ отклонен."
                )
                # Удаляем из списка ожидающих
                db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
                # Обновляем сообщение
                await callback.message.edit_text(f"❌ Запрос пользователя {user_id} отклонен")
                await callback.answer("❌ Запрос отклонен", show_alert=True)
                
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
                await callback.answer("❌ Ошибка отправки уведомления", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка при обработке действия: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

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
    pending_users = db.execute_query(
        'SELECT user_id, username, full_name, request_time FROM pending_users'
    ).fetchall()
    
    text = "📊 Статистика пользователей:\n\n"
    keyboard = []
    
    if pending_users:
        text += "👥 Ожидают доступа:\n"
        for user_id, username, full_name, req_time in pending_users:
            text += f"• ID: {user_id}\n"
            text += f"Username: @{username}\n" if username and username != "Нет username" else "Username: не указан\n"
            text += f"Имя: {full_name}\n" if full_name and full_name != "Нет имени" else "Имя: не указано\n"
            text += f"Запрос: {req_time}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text="✅ Выдать доступ",
                    callback_data=f"grant_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"deny_{user_id}"
                )
            ])
    else:
        text += "👥 Нет ожидающих доступа\n"
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 Обновить список",
            callback_data="refresh_list"
        )
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

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
    await list_access(callback.message)
    await callback.answer("✅ Список обновлен")

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
        try:
            # Получаем всех ожидающих пользователей
            pending_users = db.execute_query('SELECT user_id FROM pending_users').fetchall()
            
            for (user_id,) in pending_users:
                try:
                    await callback.bot.send_message(
                        user_id,
                        "❌ К сожалению, ваш запрос на доступ отклонен."
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            # Очищаем список ожидающих
            db.execute_query('DELETE FROM pending_users')
            
            await callback.message.edit_text("✅ Все запросы отклонены")
            await callback.answer("✅ Все запросы отклонены", show_alert=True)
            
        except Exception as e:
            print(f"Ошибка при отклонении всех запросов: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

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
async def add_user_start(callback: CallbackQuery):
    await callback.message.answer("👤 Введите username пользователя\n❗️ Username должен начинаться с @\n\nНапример: @test_user")
    await callback.message.edit_reply_markup(reply_markup=None)

@router.message(lambda m: m.text and m.text.startswith('@') and is_admin(m.from_user.id))
async def add_user_finish(message: Message):
    try:
        username = message.text[1:] if message.text.startswith('@') else message.text
        
        try:
            # Используем прямой запрос к API Telegram
            result = await message.bot(GetChat(chat_id=username))
            user_id = result.id
            
            # Добавляем пользователя в список разрешенных
            db.execute_query(
                'INSERT OR REPLACE INTO allowed_users (user_id, username, full_name) VALUES (?, ?, ?)',
                (user_id, username or "Нет username", "Нет имени")
            )
            db.conn.commit()
            
            # Отправляем уведомление пользователю
            try:
                await message.bot.send_message(
                    user_id,
                    "✅ Администратор выдал вам доступ к боту!\n"
                    "Теперь вы можете пользоваться всеми функциями."
                )
                print(f"✅ Уведомление отправлено пользователю {user_id}")
            except Exception as e:
                print(f"❌ Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            await message.answer(
                f"✅ Пользователь {username} добавлен в список разрешенных!\n"
                "Пользователь получит доступ при следующем обращении к боту."
            )
            
        except Exception as e:
            await message.answer(
                f"❌ Ошибка: не удалось найти пользователя {username}\n"
                "Убедитесь, что:\n"
                "1. Пользователь существует\n"
                "2. Username указан правильно (с @)\n"
                "3. Пользователь должен начать диалог с ботом"
            )
            print(f"Ошибка поиска пользователя: {e}")
            
    except Exception as e:
        await message.answer("❌ Произошла ошибка при добавлении пользователя")
        print(f"Ошибка добавления пользователя: {e}")

# Добавляем кнопку отмены
@router.message(lambda m: m.text == "❌ Отмена" and is_admin(m.from_user.id))
async def cancel_add_user(message: Message):
    await message.answer("❌ Добавление пользователя отменено")

# Добавляем обработчик для кнопки открытия панели пользователей
@router.callback_query(lambda c: c.data == "open_users_panel")
async def open_users_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    await users_menu(callback.message)
    await callback.answer() 

@router.callback_query(lambda c: c.data.startswith('grant_'))
async def grant_access(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        user_id = int(callback.data.split('_')[1])
        
        # Получаем информацию о пользователе через Telegram API
        chat_member = await callback.bot.get_chat_member(user_id, user_id)
        username = chat_member.user.username  # Получаем актуальный username
        full_name = chat_member.user.full_name
        
        # Добавляем пользователя в список разрешенных с актуальным username
        if db.add_allowed_user(user_id, username, full_name):
            try:
                # Отправляем уведомление пользователю
                await callback.bot.send_message(
                    user_id,
                    "✅ Администратор одобрил ваш доступ к боту!\n"
                    "Теперь вы можете пользоваться всеми функциями."
                )
                
                # Удаляем из списка ожидающих
                db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
                
                # Обновляем список
                await list_access(callback.message)
                await callback.answer("✅ Доступ успешно выдан", show_alert=True)
                
            except Exception as e:
                print(f"Ошибка отправки уведомления: {e}")
                await callback.answer("❌ Ошибка отправки уведомления", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при выдаче доступа", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка при выдаче доступа: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)

@router.callback_query(lambda c: c.data == "deny_all")
async def deny_all_users(callback: CallbackQuery):
    try:
        # Получаем всех ожидающих пользователей
        pending_users = db.execute_query('SELECT user_id FROM pending_users').fetchall()
        
        for (user_id,) in pending_users:
            try:
                await callback.bot.send_message(
                    user_id,
                    "❌ К сожалению, ваш запрос на доступ отклонен."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        
        # Очищаем список ожидающих
        db.execute_query('DELETE FROM pending_users')
        
        await callback.message.edit_text("✅ Все запросы отклонены")
        await callback.answer("✅ Все запросы отклонены", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка при отклонении всех запросов: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True) 

@router.callback_query(lambda c: c.data.startswith('revoke_'))
async def revoke_access(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        user_id = int(callback.data.split('_')[1])
        
        # Удаляем пользователя из списка разрешенных
        if db.remove_allowed_user(user_id):  # Используем метод из класса Database
            try:
                # Уведомляем пользователя
                await callback.bot.send_message(
                    user_id,
                    "❌ Ваш доступ к боту был отозван администратором."
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            
            await callback.message.edit_text(f"🚫 Доступ пользователя {user_id} отозван")
            await callback.answer("✅ Доступ отозван", show_alert=True)
        else:
            await callback.answer("❌ Пользователь не найден или уже не имеет доступа", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка при отзыве доступа: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True) 

@router.callback_query(lambda c: c.data == "refresh_pending")
async def refresh_pending_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await show_pending_users(callback.message)
    await callback.answer("Список обновлен")

@router.callback_query(lambda c: c.data == "refresh_allowed")
async def refresh_allowed_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await show_allowed_users(callback.message)
    await callback.answer("Список обновлен") 

@router.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    
    try:
        user_id = int(callback.data.split("_")[1])
        
        # Получаем информацию о пользователе
        user = await callback.bot.get_chat_member(user_id, user_id)
        username = user.user.username
        full_name = user.user.full_name
        
        # Добавляем пользователя с его реальным username
        db.add_allowed_user(user_id, username, full_name)
        
        try:
            # Отправляем уведомление пользователю
            await callback.bot.send_message(
                user_id,
                "✅ Администратор одобрил ваш доступ к боту!\n"
                "Теперь вы можете пользоваться всеми функциями."
            )
            
            # Удаляем из списка ожидающих
            db.execute_query('DELETE FROM pending_users WHERE user_id = ?', (user_id,))
            db.conn.commit()
            
            # Обновляем список
            await list_access(callback.message)
            await callback.answer("✅ Доступ успешно выдан", show_alert=True)
            
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
            await callback.answer("❌ Ошибка отправки уведомления", show_alert=True)
            
    except Exception as e:
        print(f"Ошибка при выдаче доступа: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        # Закрываем соединение с базой данных
        if hasattr(db, 'conn') and db.conn:
            db.conn.close()

class AssignTaskStates(StatesGroup):
    waiting_for_user = State()
    waiting_for_task_name = State()
    waiting_for_description = State()

@router.message(Command("assign_task"))
async def start_assign_task(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
        
    # Получаем список пользователей с доступом
    users = db.execute_query('''
        SELECT user_id, username, full_name
        FROM allowed_users 
        WHERE user_id NOT IN ({})
    '''.format(','.join(map(str, ADMIN_IDS)))).fetchall()
    
    keyboard = []
    for user_id, username, full_name in users:
        user_text = f"@{username}" if username else f"{full_name}"
        keyboard.append([
            InlineKeyboardButton(
                text=user_text,
                callback_data=f"select_user_{user_id}"
            )
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите пользователя для назначения задания:", reply_markup=markup)
    await state.set_state(AssignTaskStates.waiting_for_user)

@router.callback_query(lambda c: c.data.startswith("select_user_"))
async def process_selected_user(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
        
    user_id = int(callback.data.split("_")[2])
    await state.update_data(assigned_to=user_id)
    
    await callback.message.answer("Введите название задания:")
    await state.set_state(AssignTaskStates.waiting_for_task_name)

@router.message(AssignTaskStates.waiting_for_task_name)
async def process_task_name(message: Message, state: FSMContext):
    await state.update_data(task_name=message.text)
    await message.answer("Введите описание задания:")
    await state.set_state(AssignTaskStates.waiting_for_description)

@router.message(AssignTaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    data = await state.get_data()
    
    task_id = db.assign_task(
        admin_id=message.from_user.id,
        user_id=data['assigned_to'],
        task_name=data['task_name'],
        description=message.text
    )
    
    if task_id:
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                data['assigned_to'],
                f"📝 Вам назначено новое задание!\n\n"
                f"📌 {data['task_name']}\n"
                f"📝 {message.text}"
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")
            
        await message.answer("✅ Задание успешно назначено!")
    else:
        await message.answer("❌ Ошибка при назначении задания")
    
    await state.clear()

