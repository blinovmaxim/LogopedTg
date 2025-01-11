from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    buttons = [
        "👥 Пользователи",
        "📊 Статистика",
        "🔄 Рестарт",
        "ℹ️ Help",
        "↩️ Назад"
    ]
    
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    
    builder.adjust(2)  # По 2 кнопки в ряд
    
    return builder.as_markup(resize_keyboard=True) 