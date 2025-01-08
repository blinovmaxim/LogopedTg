from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import EXERCISE_CATEGORIES

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📝 Добавить упражнение", callback_data="add_exercise"),
        InlineKeyboardButton(text="✏️ Редактировать упражнения", callback_data="edit_exercises"),
        InlineKeyboardButton(text="📨 Рассылка", callback_data="send_broadcast"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    builder.adjust(2)
    return builder.as_markup()

def get_exercise_categories_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, name in EXERCISE_CATEGORIES.items():
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"add_ex_{code}"
        ))
    builder.add(InlineKeyboardButton(
        text="↩️ Назад",
        callback_data="back_to_admin"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
    )
    return builder.as_markup() 