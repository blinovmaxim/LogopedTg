from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import time

from database import db
from config import ADMIN_IDS
from handlers.user import show_user_tasks

router = Router()

class TaskStates(StatesGroup):
    waiting_for_task_name = State()
    waiting_for_description = State()

# Показать список заданий пользователя
@router.message(Command("my_tasks"))
async def show_my_tasks(message: Message):
    user_id = message.from_user.id
    
    tasks = db.execute_query('''
        SELECT task_id, task_name, description 
        FROM tasks 
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    if not tasks:
        await message.answer("У вас пока нет заданий. Создать новое: /new_task")
        return
    
    text = "📝 Ваши задания:\n\n"
    keyboard = []
    
    for task_id, name, description in tasks:
        # Получаем общее время выполнения задания
        total_time = db.execute_query('''
            SELECT SUM(duration) 
            FROM task_timers 
            WHERE task_id = ?
        ''', (task_id,)).fetchone()[0] or 0
        
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        
        text += f"📌 {name}\n"
        text += f"📝 {description}\n"
        text += f"⏱ Затрачено: {hours}ч {minutes}мин\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                text="▶️ Старт",
                callback_data=f"start_task_{task_id}"
            ),
            InlineKeyboardButton(
                text="⏹ Стоп",
                callback_data=f"stop_task_{task_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Новое задание",
            callback_data="new_task"
        )
    ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup)

# Создание нового задания
@router.message(Command("new_task"))
async def create_task(message: Message, state: FSMContext):
    await message.answer("Введите название задания:")
    await state.set_state(TaskStates.waiting_for_task_name)

@router.message(TaskStates.waiting_for_task_name)
async def process_task_name(message: Message, state: FSMContext):
    await state.update_data(task_name=message.text)
    await message.answer("Введите описание задания:")
    await state.set_state(TaskStates.waiting_for_description)

@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    user_data = await state.get_data()
    task_name = user_data['task_name']
    
    db.execute_query('''
        INSERT INTO tasks (user_id, task_name, description)
        VALUES (?, ?, ?)
    ''', (message.from_user.id, task_name, message.text))
    
    await message.answer(
        f"✅ Задание создано!\n\n"
        f"📌 {task_name}\n"
        f"📝 {message.text}"
    )
    await state.clear()

# Обработчики таймера
@router.callback_query(lambda c: c.data.startswith("start_task_"))
async def start_timer(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])
    
    # Проверяем, нет ли уже запущенного таймера
    active_timer = db.execute_query('''
        SELECT timer_id FROM task_timers 
        WHERE task_id = ? AND end_time IS NULL
    ''', (task_id,)).fetchone()
    
    if active_timer:
        await callback.answer("⚠️ Таймер уже запущен!", show_alert=True)
        return
    
    # Создаем новый таймер
    db.execute_query('''
        INSERT INTO task_timers (task_id, user_id, start_time)
        VALUES (?, ?, datetime('now'))
    ''', (task_id, callback.from_user.id))
    
    await callback.answer("⏱ Таймер запущен!")

@router.callback_query(lambda c: c.data.startswith("stop_task_"))
async def stop_timer(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])
    
    # Находим активный таймер
    timer = db.execute_query('''
        SELECT timer_id, start_time 
        FROM task_timers 
        WHERE task_id = ? AND end_time IS NULL
    ''', (task_id,)).fetchone()
    
    if not timer:
        await callback.answer("⚠️ Нет активного таймера!", show_alert=True)
        return
    
    # Останавливаем таймер
    db.stop_timer(task_id, callback.from_user.id)
    await callback.answer("⏱ Таймер остановлен!")
    # Обновляем список заданий
    await show_user_tasks(callback.message)

@router.callback_query(lambda c: c.data.startswith("start_assigned_"))
async def start_assigned_timer(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])
    
    # Проверяем, нет ли уже запущенного таймера
    active_timer = db.execute_query('''
        SELECT timer_id FROM task_timers 
        WHERE task_id = ? AND end_time IS NULL
    ''', (task_id,)).fetchone()
    
    if active_timer:
        await callback.answer("⚠️ Таймер уже запущен!", show_alert=True)
        return
    
    # Создаем новый таймер
    db.execute_query('''
        INSERT INTO task_timers (task_id, user_id, start_time)
        VALUES (?, ?, datetime('now'))
    ''', (task_id, callback.from_user.id))
    
    await callback.answer("⏱ Таймер запущен!")

@router.callback_query(lambda c: c.data.startswith("stop_assigned_"))
async def stop_assigned_timer(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])
    
    # Находим активный таймер
    timer = db.execute_query('''
        SELECT timer_id, start_time 
        FROM task_timers 
        WHERE task_id = ? AND end_time IS NULL
    ''', (task_id,)).fetchone()
    
    if not timer:
        await callback.answer("⚠️ Нет активного таймера!", show_alert=True)
        return
    
    # Останавливаем таймер и отмечаем задание как выполненное
    db.stop_timer(task_id, callback.from_user.id)
    db.complete_assigned_task(task_id, callback.from_user.id)
    
    await callback.answer("⏱ Таймер остановлен!")
    await show_user_tasks(callback.message)

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
                        text="⏹ Стоп",
                        callback_data=f"stop_assigned_{task_id}"
                    )
                ])
    
    if own_tasks:
        text += "\n📝 Личные задания:\n\n"
        for task in own_tasks:
            task_id, name, description, created_at = task
            text += f"📌 {name}\n"
            text += f"📝 {description}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text="▶️ Старт",
                    callback_data=f"start_task_{task_id}"
                ),
                InlineKeyboardButton(
                    text="⏹ Стоп",
                    callback_data=f"stop_task_{task_id}"
                )
            ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup) 