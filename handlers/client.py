from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
from keyboards.client_kb import get_main_keyboard

router = Router()

# Обработчик команды /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.answer(
        "Здравствуйте! Я бот-помощник логопедического центра.\n"
        "Чем могу помочь?",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

# Обработчик команды /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
    )

# Обработчики основных кнопок меню
@router.message(F.text == "📝 Записаться на прием")
async def make_appointment(message: Message):
    await message.answer("Функция записи на прием в разработке...")

@router.message(F.text == "🎯 Мои упражнения")
async def show_exercises(message: Message):
    await message.answer("Функция просмотра упражнений в разработке...")

@router.message(F.text == "📅 Мои записи")
async def show_appointments(message: Message):
    await message.answer("Функция просмотра записей в разработке...")

@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    await message.answer(
        "🏥 О нашем центре:\n\n"
        "- Квалифицированные специалисты\n"
        "- Современные методики\n"
        "- Индивидуальный подход\n\n"
        "📍 Адрес: [Ваш адрес]\n"
        "📞 Телефон: [Ваш телефон]\n"
        "🌐 Сайт: [Ваш сайт]"
    )

@router.message(F.text == "💬 Связаться с логопедом")
async def contact_specialist(message: Message):
    await message.answer("Функция связи со специалистом в разработке...")

@router.message(F.text == "❓ Частые вопросы")
async def show_faq(message: Message):
    await message.answer(
        "Частые вопросы:\n\n"
        "1. С какого возраста можно обращаться к логопеду?\n"
        "2. Сколько длится занятие?\n"
        "3. Как часто нужно заниматься?\n"
        "4. Что взять с собой на первый прием?"
    )

# Обработчик неизвестных сообщений
@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "Извините, я не понимаю эту команду.\n"
        "Используйте кнопки меню или команду /help"
    )

# ... остальные обработчики клиента ... 