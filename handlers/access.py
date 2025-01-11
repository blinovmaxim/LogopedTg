from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_ID, ADMIN_IDS, CHANNEL_URL, ADMIN_USERNAME
from database import Database
from aiogram import Bot

router = Router()
db = Database()

async def check_subscription(user_id: int, bot) -> bool:
    """Проверка подписки на канал"""
    try:
        if not CHANNEL_ID:
            print("CHANNEL_ID не установлен")
            return False
            
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID, 
            user_id=user_id
        )
        return member.status in ['member', 'administrator', 'creator']
        
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

async def check_admin_approval(user_id: int, username: str = None, message: Message = None) -> bool:
    """Проверка одобрения администратором"""
    try:
        # Проверяем по user_id
        if db.is_user_allowed(user_id):
            return True
            
        # Проверяем по username
        if username and db.is_username_allowed(f"@{username}"):
            # Если username разрешен, добавляем пользователя в allowed_users
            if db.add_allowed_user(user_id, None):
                # Удаляем username из списка разрешенных
                db.execute_query(
                    'DELETE FROM allowed_usernames WHERE username = ?',
                    (f"@{username}",)
                )
                if message:
                    await message.answer("✅ Доступ к боту предоставлен!")
                return True
                
        return False
    except Exception as e:
        print(f"Ошибка проверки доступа: {e}")
        return False

async def access_middleware(message: Message, bot: Bot) -> bool:
    """Проверяет, имеет ли пользователь доступ к боту"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Админы всегда имеют доступ
    if user_id in ADMIN_IDS:
        return True
    
    # Проверяем подписку на канал
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['left', 'kicked', 'banned']:
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
                "❗️ Для использования бота необходимо:\n\n"
                f"1. Подписаться на канал: {CHANNEL_URL}\n"
                "2. Нажать кнопку «Проверить подписку»\n"
                "3. Дождаться одобрения администратора",
                reply_markup=keyboard
            )
            return False
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False
    
    # Проверяем одобрение администратора
    is_approved = await check_admin_approval(user_id, username, message)
    if not is_approved:
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="✅ Выдать доступ",
                                callback_data=f"grant_{user_id}"
                            )
                        ]
                    ]
                )
                
                # Отправляем сообщение
                await bot.send_message(
                    admin_id,
                    f"👤 Новый пользователь ожидает подтверждения:\n"
                    f"• Username: @{username or 'нет'}\n"
                    f"• Имя: {message.from_user.full_name}\n"
                    f"• ID: {user_id}",
                    reply_markup=keyboard
                )
                
                # Отправляем всплывающее уведомление
                await bot.send_message(
                    admin_id,
                    "❗️ Новый запрос на доступ",
                    disable_notification=False  # Включаем уведомление
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления админу {admin_id}: {e}")
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать администратору",
                        url=f"https://t.me/{ADMIN_USERNAME}"
                    )
                ]
            ]
        )
        
        await message.answer(
            "✅ Вы подписаны на канал\n\n"
            "⏳ Ожидайте одобрения администратора\n"
            f"Для ускорения процесса напишите администратору: @{ADMIN_USERNAME}",
            reply_markup=keyboard
        )
        return False
    
    return True

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id, callback.bot)
    
    if is_subscribed:
        # Добавляем пользователя в список ожидающих
        db.add_pending_user(
            user_id=user_id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💬 Написать администратору",
                        url=f"https://t.me/{ADMIN_USERNAME}"
                    )
                ]
            ]
        )
        
        await callback.message.edit_text(
            "✅ Подписка подтверждена!\n\n"
            "⏳ Теперь необходимо получить доступ у администратора\n"
            f"Напишите администратору: @{ADMIN_USERNAME}",
            reply_markup=keyboard
        )
    else:
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
        
        await callback.answer(
            "❌ Вы не подписаны на канал. Подпишитесь и попробуйте снова.",
            show_alert=True
        ) 