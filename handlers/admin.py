from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_IDS
from keyboards.admin_kb import get_admin_keyboard
import os
import sys

# Создаем роутер
router = Router()

# Обработчик для админ-панели
@router.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    await message.answer(
        "🔧 Панель администратора",
        reply_markup=get_admin_keyboard()
    )

# Обработчик для рестарта бота
@router.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "🔄 Рестарт")
async def restart_bot(message: Message):
    await message.answer("🔄 Перезапуск бота...")
    os.execv(sys.executable, ['python'] + sys.argv)

# Обработчик для админ-помощи
@router.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "ℹ️ Help")
async def admin_help(message: Message):
    await message.answer(
        "👨‍💼 Админ-команды:\n\n"
        "/restart - Перезапуск бота\n"
        "/stats - Статистика использования\n"
        "/add_exercise - Добавить упражнение\n"
        "/edit_exercise - Редактировать упражнение\n"
        "/delete_exercise - Удалить упражнение\n"
    )

# Обработчики callback-кнопок админ-панели
@router.callback_query(lambda c: c.data == "admin_stats")
async def process_admin_stats(callback: types.CallbackQuery):
    await callback.message.answer("📊 Статистика бота:\nВ разработке...")
    await callback.answer()

@router.callback_query(lambda c: c.data == "send_broadcast")
async def process_broadcast(callback: types.CallbackQuery):
    await callback.message.answer("📨 Рассылка сообщений:\nВ разработке...")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_settings")
async def process_settings(callback: types.CallbackQuery):
    await callback.message.answer("⚙️ Настройки:\nВ разработке...")
    await callback.answer() 