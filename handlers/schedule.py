from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from config import ADMIN_IDS
from database import Database
from keyboards.schedule_kb import (
    get_schedule_admin_kb,
    get_month_calendar,
    get_time_slots_kb,
    get_confirm_schedule_kb
)
from states.schedule_states import ScheduleStates

router = Router()
db = Database()

# Админ-панель управления расписанием
@router.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "📅 Календарь")
async def schedule_admin_panel(message: Message):
    try:
        print("Открываем панель управления расписанием")  # Отладка
        await message.answer(
            "📅 Управление расписанием:",
            reply_markup=get_schedule_admin_kb()
        )
    except Exception as e:
        print(f"Ошибка в schedule_admin_panel: {e}")  # Отладка
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

# Обработчик всех callback-запросов для отладки
@router.callback_query()
async def process_callback(callback: CallbackQuery, state: FSMContext):
    print(f"Получен callback: {callback.data}")  # Отладка
    
    try:
        if callback.data == "add_work_hours":
            await start_add_work_hours(callback, state)
        
        elif callback.data == "view_appointments":
            await view_appointments(callback)
        
        elif callback.data == "cancel_appointment":
            await start_cancel_appointment(callback, state)
        
        elif callback.data.startswith("cancel_slot_"):
            await cancel_specific_appointment(callback, state)
        
        elif callback.data.startswith("date_"):
            await process_selected_date(callback, state)
        
        elif callback.data.startswith("time_"):
            await process_selected_time(callback, state)
        
        elif callback.data == "confirm_schedule":
            await confirm_schedule(callback, state)
        
        elif callback.data == "cancel_schedule":
            await cancel_schedule(callback, state)
        
        elif callback.data == "back_to_schedule":
            await back_to_schedule(callback)
        
        else:
            print(f"Неизвестный callback: {callback.data}")  # Отладка
            await callback.answer("Неизвестная команда")
    
    except Exception as e:
        print(f"Ошибка в process_callback: {e}")  # Отладка
        await callback.message.answer(
            f"❌ Произошла ошибка: {str(e)}\n"
            "Попробуйте еще раз или обратитесь к администратору."
        )

async def start_add_work_hours(callback: CallbackQuery, state: FSMContext):
    try:
        print("Начинаем добавление рабочих часов")  # Отладка
        await state.set_state(ScheduleStates.selecting_date)
        await callback.message.edit_text(
            "📅 Выберите дату для добавления рабочих часов:",
            reply_markup=get_month_calendar()
        )
    except Exception as e:
        print(f"Ошибка в start_add_work_hours: {e}")  # Отладка
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        await callback.answer()

async def view_appointments(callback: CallbackQuery):
    try:
        print("Просмотр записей")  # Отладка
        await callback.message.edit_text("🔄 Загрузка записей...")
        
        appointments = db.get_all_appointments()
        print(f"Получены записи: {appointments}")  # Отладка
        
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_schedule"
        ))
        
        if not appointments:
            await callback.message.edit_text(
                "📅 Нет активных записей на ближайшие дни",
                reply_markup=kb.as_markup()
            )
            return
        
        text = "📅 Активные записи:\n\n"
        for app in appointments:
            text += (f"Дата: {app['date']}\n"
                    f"Время: {app['time']}\n"
                    f"Статус: {app['status']}\n"
                    f"------------------------\n")
        
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
    
    except Exception as e:
        print(f"Ошибка в view_appointments: {e}")  # Отладка
        await callback.message.edit_text(
            f"❌ Произошла ошибка при загрузке записей: {str(e)}",
            reply_markup=get_schedule_admin_kb()
        )
    finally:
        await callback.answer()

# Выбор даты
@router.callback_query(lambda c: c.data.startswith("date_"))
async def process_selected_date(callback: CallbackQuery, state: FSMContext):
    try:
        date = callback.data.replace("date_", "")
        await state.update_data(selected_date=date)
        
        # Показываем временные слоты
        await callback.message.edit_text(
            f"🕒 Выберите рабочие часы на {date}:",
            reply_markup=get_time_slots_kb()
        )
        await state.set_state(ScheduleStates.selecting_hours)
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
    await callback.answer()

# Выбор времени
@router.callback_query(lambda c: c.data.startswith("time_"))
async def process_selected_time(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        selected_slots = data.get("selected_slots", [])
        time_slot = callback.data.replace("time_", "")
        
        if time_slot in selected_slots:
            selected_slots.remove(time_slot)
        else:
            selected_slots.append(time_slot)
        
        await state.update_data(selected_slots=selected_slots)
        
        # Показываем выбранные слоты
        slots_text = "\n".join(sorted(selected_slots)) if selected_slots else "Нет выбранных слотов"
        await callback.message.edit_text(
            f"📅 Дата: {data['selected_date']}\n\n"
            f"Выбранные слоты:\n{slots_text}\n\n"
            f"Выберите дополнительные слоты или подтвердите выбор:",
            reply_markup=get_time_slots_kb()
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
    await callback.answer()

# Подтверждение выбора
@router.callback_query(lambda c: c.data == "confirm_schedule")
async def confirm_schedule(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        date = data.get('selected_date')
        slots = data.get('selected_slots', [])
        
        if not slots:
            await callback.message.edit_text(
                "❌ Не выбрано ни одного временного слота!",
                reply_markup=get_time_slots_kb()
            )
            return
        
        # Сохраняем слоты в базу
        for slot in slots:
            db.add_work_slot(date, slot)
        
        await callback.message.edit_text(
            f"✅ Рабочие часы на {date} добавлены:\n"
            f"{', '.join(sorted(slots))}",
            reply_markup=get_schedule_admin_kb()
        )
        await state.clear()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при сохранении: {str(e)}")
    await callback.answer()

# Отмена выбора
@router.callback_query(lambda c: c.data == "cancel_schedule")
async def cancel_schedule(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Добавление рабочих часов отменено",
        reply_markup=get_schedule_admin_kb()
    )
    await callback.answer()

# Обработчик для возврата в меню расписания
@router.callback_query(lambda c: c.data == "back_to_schedule")
async def back_to_schedule(callback: CallbackQuery):
    try:
        try:
            await callback.message.edit_text(
                "📅 Управление расписанием:",
                reply_markup=get_schedule_admin_kb()
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                "📅 Управление расписанием:",
                reply_markup=get_schedule_admin_kb()
            )
    except Exception as e:
        print(f"Ошибка в back_to_schedule: {e}")
        await callback.message.answer(
            "📅 Управление расписанием:",
            reply_markup=get_schedule_admin_kb()
        )
    await callback.answer()

# Добавляем новые функции для отмены записей
async def start_cancel_appointment(callback: CallbackQuery, state: FSMContext):
    try:
        # Получаем все активные записи
        appointments = db.get_all_appointments()
        
        if not appointments:
            try:
                await callback.message.edit_text(
                    "📅 Нет активных записей для отмены",
                    reply_markup=get_schedule_admin_kb()
                )
            except Exception:
                # Если не удалось отредактировать, отправляем новое сообщение
                await callback.message.answer(
                    "📅 Нет активных записей для отмены",
                    reply_markup=get_schedule_admin_kb()
                )
            return

        # Создаем клавиатуру с записями
        kb = InlineKeyboardBuilder()
        
        for app in appointments:
            date = datetime.strptime(app['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
            button_text = f"{date} {app['time']}"
            if app['status'] == 'booked':
                button_text += f" (Занято: ID {app['user_id']})"
            kb.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"cancel_slot_{app['date']}_{app['time']}"
            ))
        
        # Добавляем кнопку возврата
        kb.add(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_schedule"
        ))
        
        kb.adjust(1)  # По одной кнопке в ряд
        
        try:
            await callback.message.edit_text(
                "🗑 Выберите запись для отмены:",
                reply_markup=kb.as_markup()
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                "🗑 Выберите запись для отмены:",
                reply_markup=kb.as_markup()
            )
        
    except Exception as e:
        print(f"Ошибка в start_cancel_appointment: {e}")
        await callback.message.answer(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_schedule_admin_kb()
        )
    finally:
        await callback.answer()

async def cancel_specific_appointment(callback: CallbackQuery, state: FSMContext):
    try:
        # Получаем дату и время из callback_data
        _, date, time = callback.data.split('_', 2)
        
        # Отменяем запись в базе
        db.cancel_appointment(date, time)
        
        await callback.message.edit_text(
            f"✅ Запись на {date} {time} успешно отменена",
            reply_markup=get_schedule_admin_kb()
        )
        
    except Exception as e:
        print(f"Ошибка в cancel_specific_appointment: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при отмене записи: {str(e)}",
            reply_markup=get_schedule_admin_kb()
        )
    finally:
        await callback.answer() 