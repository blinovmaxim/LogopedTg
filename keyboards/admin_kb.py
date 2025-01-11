from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_keyboard():
    buttons = [
        [
            KeyboardButton(text="👥 Ожидают доступ"),
            KeyboardButton(text="✅ Пользователи с доступом")
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="🔄 Рестарт")
        ],
        [
            KeyboardButton(text="↩️ Назад")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    ) 