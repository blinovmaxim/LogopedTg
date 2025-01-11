from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS, CHANNEL_ID, CHANNEL_URL, ADMIN_USERNAME, EXERCISE_CATEGORIES
from database import db
import logging

router = Router()

async def access_middleware(message: Message, bot: Bot) -> bool:
    user_id = message.from_user.id
    
    # Проверяем доступ через базу данных (которая уже проверяет админов)
    if db.is_user_allowed(user_id):
        await show_exercises_menu(message)
        return True
        
    # Для остальных проверяем подписку на канал
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        is_subscribed = member.status not in ['left', 'kicked', 'banned']
        
        if not is_subscribed:
            # Показываем кнопку подписки
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📢 Подписаться на канал",
                            url=CHANNEL_URL
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔄 Проверить подписку",
                            callback_data="check_subscription"
                        )
                    ]
                ]
            )
            
            await message.answer(
                "❗️ Для доступа к упражнениям необходимо:\n\n"
                f"1. Подписаться на канал: {CHANNEL_URL}\n"
                "2. После подписки нажмите кнопку проверки",
                reply_markup=keyboard
            )
            return False
            
        # Проверяем ожидание подтверждения
        pending = db.execute_query(
            'SELECT 1 FROM pending_users WHERE user_id = ?', 
            (user_id,)
        ).fetchone()
        
        if pending:
            await message.answer(
                "⏳ Ваша заявка на доступ находится на рассмотрении\n"
                "Пожалуйста, ожидайте решения администратора"
            )
            return False
            
        # Если подписан, но нет доступа - показываем кнопку запроса
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Запросить доступ",
                        callback_data="request_access"
                    )
                ]
            ]
        )
        
        await message.answer(
            "❗️ Для доступа к упражнениям необходимо получить разрешение администратора\n\n"
            "Нажмите кнопку ниже, чтобы отправить запрос",
            reply_markup=keyboard
        )
        return False
        
    except Exception as e:
        logging.error(f"Ошибка при проверке доступа: {e}")
        await message.answer("❌ Произошла ошибка при проверке доступа")
        return False

@router.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    try:
        member = await callback.bot.get_chat_member(CHANNEL_ID, user_id)
        is_subscribed = member.status not in ['left', 'kicked', 'banned']
        
        if is_subscribed:
            # Если подписан - проверяем доступ
            if db.is_user_allowed(user_id):
                await show_exercises_menu(callback.message)
                return
                
            # Если нет доступа - показываем кнопку запроса
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📝 Запросить доступ",
                            callback_data="request_access"
                        )
                    ]
                ]
            )
            
            await callback.message.edit_text(
                "✅ Подписка подтверждена!\n\n"
                "⏳ Теперь необходимо получить доступ у администратора\n"
                "Нажмите кнопку ниже, чтобы отправить запрос",
                reply_markup=keyboard
            )
        else:
            await callback.answer(
                "❌ Вы не подписаны на канал. Подпишитесь и попробуйте снова.",
                show_alert=True
            )
            
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        await callback.answer(
            "❌ Произошла ошибка при проверке подписки",
            show_alert=True
        )

@router.message(lambda m: m.text == "🎯 Мои упражнения")
async def show_exercises(message: Message):
    user_id = message.from_user.id
    
    # Проверяем подписку на канал
    try:
        member = await message.bot.get_chat_member(CHANNEL_ID, user_id)
        is_subscribed = member.status not in ['left', 'kicked', 'banned']
        
        if not is_subscribed:
            # Если не подписан на канал
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📢 Подписаться на канал",
                            url=CHANNEL_URL
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔄 Проверить подписку",
                            callback_data="check_subscription"
                        )
                    ]
                ]
            )
            
            await message.answer(
                "❗️ Для доступа к упражнениям необходимо:\n\n"
                f"1. Подписаться на канал: {CHANNEL_URL}\n"
                "2. После подписки нажмите кнопку проверки",
                reply_markup=keyboard
            )
            return
            
        # Проверяем наличие доступа
        if not db.is_user_allowed(user_id):
            # Проверяем, не отправлял ли уже запрос
            pending = db.execute_query(
                'SELECT 1 FROM pending_users WHERE user_id = ?', 
                (user_id,)
            ).fetchone()
            
            if pending:
                await message.answer(
                    "⏳ Ваша заявка на доступ находится на рассмотрении\n"
                    "Пожалуйста, ожидайте решения администратора"
                )
                return
                
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📝 Запросить доступ",
                            callback_data="request_access"
                        )
                    ]
                ]
            )
            
            await message.answer(
                "❗️ Для доступа к упражнениям необходимо получить разрешение администратора\n\n"
                "Нажмите кнопку ниже, чтобы отправить запрос",
                reply_markup=keyboard
            )
            return
            
        # Если есть доступ - показываем упражнения
        await show_exercises_menu(message)
        
    except Exception as e:
        print(f"Ошибка при проверке доступа: {e}")
        await message.answer("❌ Произошла ошибка при проверке доступа") 

# Добавляем функцию для показа упражнений
async def show_exercises_menu(message: Message):
    keyboard = []
    for code, name in EXERCISE_CATEGORIES.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"➤ {name}",
                callback_data=f"ex_{code}"
            )
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        "<b>🎯 Видео-упражнения</b>\n\n"
        "<i>Выберите категорию упражнений:</i>\n\n"
        "• Каждая категория содержит специально подобранные видео\n"
        "• Выполняйте упражнения регулярно\n"
        "• Следите за техникой выполнения",
        reply_markup=markup,
        parse_mode="HTML"
    ) 

@router.callback_query(lambda c: c.data == "request_access")
async def process_access_request(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    
    try:
        # Проверяем, не отправлял ли уже запрос
        pending = db.execute_query(
            'SELECT 1 FROM pending_users WHERE user_id = ?', 
            (user_id,)
        ).fetchone()
        
        if pending:
            await callback.answer(
                "⏳ Ваша заявка уже находится на рассмотрении",
                show_alert=True
            )
            return
            
        # Добавляем пользователя в список ожидающих
        db.execute_query(
            'INSERT INTO pending_users (user_id, username, full_name) VALUES (?, ?, ?)',
            (user_id, username, full_name)
        )
        db.conn.commit()
        
        await callback.answer(
            "✅ Заявка отправлена! Ожидайте решения администратора.",
            show_alert=True
        )
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="👁 Посмотреть заявку",
                                callback_data=f"view_request_{user_id}"
                            )
                        ]
                    ]
                )
                
                await callback.bot.send_message(
                    admin_id,
                    f"📝 Новая заявка на доступ!\n\n"
                    f"От: {full_name}\n"
                    f"Username: @{username or 'нет'}\n"
                    f"ID: {user_id}",
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления админу {admin_id}: {e}")
                
    except Exception as e:
        print(f"Ошибка при обработке заявки: {e}")
        await callback.answer(
            "❌ Произошла ошибка при отправке заявки",
            show_alert=True
        ) 