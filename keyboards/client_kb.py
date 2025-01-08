from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config import ADMIN_IDS

def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    # Общие кнопки
    builder.add(
        KeyboardButton(text="📝 Записаться на прием"),
        KeyboardButton(text="🎯 Мои упражнения"),
        KeyboardButton(text="📅 Мои записи"),
        KeyboardButton(text="ℹ️ Информация"),
        KeyboardButton(text="💬 Связаться с логопедом"),
        KeyboardButton(text="❓ Частые вопросы")
    )
    
    # Админ кнопки
    if user_id in ADMIN_IDS:
        builder.add(
            KeyboardButton(text="⚙️ Админ-панель"),
            KeyboardButton(text="🔄 Рестарт"),
            KeyboardButton(text="ℹ️ Help")
        )
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True) 