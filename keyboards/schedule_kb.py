from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import calendar

def get_schedule_admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(text="➕ Добавить рабочие часы", callback_data="add_work_hours"),
        InlineKeyboardButton(text="🚫 Заблокировать время", callback_data="block_time"),
        InlineKeyboardButton(text="👥 Посмотреть записи", callback_data="view_appointments"),
        InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_appointment")
    )
    kb.adjust(1)
    return kb.as_markup()

def get_month_calendar() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    now = datetime.now()
    
    # Создаем календарь на текущий месяц
    month_calendar = calendar.monthcalendar(now.year, now.month)
    
    # Добавляем дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days:
        kb.add(InlineKeyboardButton(text=day, callback_data="ignore"))
    
    # Добавляем дни месяца
    for week in month_calendar:
        for day in week:
            if day == 0:
                kb.add(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date = datetime(now.year, now.month, day)
                if date >= now:
                    kb.add(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"date_{date.strftime('%Y-%m-%d')}"
                    ))
                else:
                    kb.add(InlineKeyboardButton(text=str(day), callback_data="ignore"))
    
    kb.adjust(7)  # 7 кнопок в ряд для дней недели
    return kb.as_markup()

def get_time_slots_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    
    # Временные слоты с интервалом в 1 час
    start_time = datetime.strptime("09:00", "%H:%M")
    end_time = datetime.strptime("19:00", "%H:%M")
    delta = timedelta(hours=1)
    
    current_time = start_time
    while current_time <= end_time:
        time_str = current_time.strftime("%H:%M")
        kb.add(InlineKeyboardButton(
            text=time_str,
            callback_data=f"time_{time_str}"
        ))
        current_time += delta
    
    kb.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_schedule"))
    kb.adjust(4)  # 4 кнопки в ряд
    return kb.as_markup()

def get_confirm_schedule_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_schedule"),
        InlineKeyboardButton(text="🔄 Выбрать другое время", callback_data="select_other_time"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_schedule")
    )
    kb.adjust(1)
    return kb.as_markup() 