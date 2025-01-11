from aiogram import Router
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from database import Database

router = Router()
db = Database()

@router.message(lambda m: m.text == "📝 Мои задания")
async def show_user_tasks(message: Message):
    user_id = message.from_user.id
    
    # Получаем личные и назначенные задания
    own_tasks = db.get_user_tasks(user_id)
    assigned_tasks = db.get_assigned_tasks(user_id)
    
    if not own_tasks and not assigned_tasks:
        await message.answer("У вас пока нет заданий")
        return
        
    text = ""
    keyboard = []
    
    if assigned_tasks:
        text += "📋 Назначенные задания:\n\n"
        for task in assigned_tasks:
            task_id, name, description, created_at, completed = task
            status = "✅" if completed else "⏳"
            text += f"{status} {name}\n"
            text += f"📝 {description}\n\n"
            
            if not completed:
                keyboard.append([
                InlineKeyboardButton(
                    text="▶️ Старт",
                    callback_data=f"start_assigned_{task_id}"
                ),
                InlineKeyboardButton(
                    text="⏹ Стоп",  # Была обрезана
                    callback_data=f"stop_assigned_{task_id}"
                )
            ])
            
    if own_tasks:
        text += "\n📝 Личные задания:\n\n"
        for task in own_tasks:
            task_id, name, description, created_at = task
            text += f"📌 {name}\n"
            text += f"📝 {description}\n\n"
    
    await message.answer(text) 