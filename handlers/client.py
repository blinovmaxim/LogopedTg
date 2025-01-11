from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from keyboards.client_kb import get_main_keyboard
from keyboards.admin_kb import get_admin_keyboard
from config import ADMIN_IDS, EXERCISE_CATEGORIES

router = Router()

# Обработчик команды /start
@router.message(Command('start'))
async def start_command(message: Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    welcome_text = (
        "👋 Добро пожаловать!\n"
        "Выберите нужный пункт меню:"
    )
    
    if is_admin:
        welcome_text += "\n\n👨‍💼 Вы вошли как администратор"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user_id)
    )

# Обработчик команды /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    help_text = (
        "🔍 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n\n"
        "📌 Как пользоваться ботом:\n\n"
        "1️⃣ Подпишитесь на канал @your_channel\n"
        "2️⃣ Используйте кнопки меню для навигации\n"
        "3️⃣ Для записи на прием нажмите '📝 Записаться на прием'\n"
        "4️⃣ Чтобы посмотреть свои записи, нажмите '📅 Мои записи'\n"
        "5️⃣ Для связи с логопедом используйте '💬 Связаться с логопедом'\n\n"
        "❓ Остались вопросы? Нажмите 'Частые вопросы' или свяжитесь с администратором"
    )
    await message.answer(help_text)

# Обработчики основных кнопок меню
@router.message(F.text == "📝 Записаться на прием")
async def make_appointment(message: Message):
    await message.answer("Выберите удобную дату и время для записи...")

@router.message(F.text == "🎯 Мои упражнения")
async def show_exercises(message: Message):
    keyboard = []
    for code, name in EXERCISE_CATEGORIES.items():
        keyboard.append([
            types.InlineKeyboardButton(
                text=name,
                callback_data=f"ex_{code}"
            )
        ])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("Выберите категорию упражнений:", reply_markup=markup)

@router.message(F.text == "📅 Мои записи")
async def show_appointments(message: Message):
    await message.answer("Ваши текущие записи...")

@router.message(F.text == "ℹ️ Информация")
async def show_info(message: Message):
    info_text = (
        "🏥 *Логопедический центр*\n\n"
        "*О нас:*\n"
        "Мы специализируемся на коррекции речевых нарушений у детей "
        "Наши специалисты имеют многолетний опыт работы и используют современные методики.\n\n"
        
        "*Наши услуги:*\n"
        "• Диагностика речевых нарушений\n"
        "• Коррекция звукопроизношения\n"
        "• Развитие фонематического слуха\n"
        "• Логопедический массаж\n"
        "• Артикуляционная гимнастика\n"
        "• Развитие связной речи\n\n"
        
        "*График работы:*\n"
        "Пн-Пт: 9:00 - 19:00\n"
        "Сб: 10:00 - 15:00\n"
        "Вс: выходной\n\n"
        
        "*Контакты:*\n"
        "📞 Телефон: +7 (XXX) XXX-XX-XX\n"
        "📧 Email: info@logoped.ru\n"
        "📍 Адрес: г. Москва, ул. Примерная, д. 1\n\n"
        
        "*Как записаться:*\n"
        "1. Нажмите кнопку '📝 Записаться на прием'\n"
        "2. Выберите удобную дату и время\n"
        "3. Дождитесь подтверждения записи\n\n"
        
        "❓ Остались вопросы? Используйте кнопку '💬 Связаться с логопедом'"
    )
    
    await message.answer(
        info_text,
        parse_mode="Markdown"
    )

@router.message(F.text == "💬 Связаться с логопедом")
async def contact_specialist(message: Message):
    await message.answer("Вы можете связаться с логопедом...")

@router.message(F.text == "❓ Частые вопросы")
async def show_faq(message: Message):
    await message.answer("Ответы на частые вопросы...")

# Добавляем эти обработчики в конец файла
@router.message(F.text == "🔄 Рестарт")
async def restart_command(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        "Бот перезапущен. Выберите действие:",
        reply_markup=get_main_keyboard(is_admin)
    )

@router.message(F.text == "↩️ Назад")
async def back_command(message: Message):
    user_id = message.from_user.id
    await message.answer(
        "Вы вернулись в главное меню",
        reply_markup=get_main_keyboard(user_id)
    )

# Обновляем обработчик неизвестных сообщений
@router.message()
async def unknown_message(message: Message):
    if message.text in ["🔄 Рестарт", "↩️ Назад"]:
        return
    await message.answer(
        "Извините, я не понимаю эту команду.\n"
        "Используйте кнопки меню или команду /help"
    )

@router.message(lambda m: m.from_user.id in ADMIN_IDS and m.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    await message.answer(
        "🔧 Панель администратора\n\n"
        "📅 Календарь - управление расписанием\n"
        "👥 Пользователи - управление доступом\n"
        "📊 Статистика - просмотр статистики\n"
        "🔄 Рестарт - перезапуск бота\n"
        "ℹ️ Help - справка по командам\n"
        "↩️ Назад - вернуться в главное меню",
        reply_markup=get_admin_keyboard()
    )

# ... остальные обработчики клиента ... 