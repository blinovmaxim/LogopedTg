from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from config import ADMIN_IDS

def get_main_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    # Основные кнопки для всех пользователей
    buttons = [
        "📝 Записаться на прием",
        "📅 Мои записи",
        "🎯 Мои упражнения",
        "ℹ️ Информация",
        "💬 Связаться с логопедом",
        "❓ Частые вопросы"
    ]
    
    # Добавляем основные кнопки
    for button in buttons:
        builder.add(KeyboardButton(text=button))
    
    # Добавляем кнопку админ-панели ТОЛЬКО для админов
    if user_id and isinstance(user_id, int) and user_id in ADMIN_IDS:
        builder.add(KeyboardButton(text="⚙️ Админ-панель"))
    
    builder.adjust(2)  # По 2 кнопки в ряд
    
    return builder.as_markup(resize_keyboard=True) 