from dotenv import load_dotenv
import os
import sys

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
CHANNEL_ID = os.getenv('CHANNEL_ID')  # ID вашего канала
CHANNEL_URL = os.getenv('CHANNEL_URL')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',')]
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')  # Username без @ 

if not CHANNEL_ID:
    print("❌ Ошибка: CHANNEL_ID не установлен в .env файле")
    sys.exit(1)  # Останавливаем бота, если нет ID канала
ADMIN_IDS = [
    515716689, 474177687 # Ваш ID
    # Добавьте другие ID администраторов, если нужно
]
#  474177687
# Список разрешенных пользователей
ALLOWED_USERS = set([
    # ID пользователей, которым разрешен доступ
])

# Функция для добавления нового пользователя
def add_allowed_user(user_id: int):
    ALLOWED_USERS.add(user_id)
    # Здесь можно добавить сохранение в базу данных

EXERCISE_CATEGORIES = {
    "sound_r": "🎯 Звук Р",
    "sound_l": "🎯 Звук Л",
    "sound_sh": "🎯 Звук Ш",
    "sound_zh": "🎯 Звук Ж",
    "sound_s": "🎯 Звук С",
    "sound_z": "🎯 Звук З",
    "articulation": "👄 Артикуляция",
    "tongue": "👅 Гимнастика для языка",
    "lips": "💋 Гимнастика для губ",
    "breathing": "🫁 Дыхательные упражнения"
} 

# Добавляем поисковые запросы для каждой категории
EXERCISE_SEARCH_QUERIES = {
    "sound_r": "логопед постановка звука р упражнения",
    "sound_l": "логопед постановка звука л упражнения",
    "sound_sh": "логопед постановка звука ш упражнения",
    "sound_zh": "логопед постановка звука ж упражнения",
    "sound_s": "логопед постановка звука с упражнения",
    "sound_z": "логопед постановка звука з упражнения",
    "articulation": "артикуляционная гимнастика для детей",
    "tongue": "гимнастика для языка логопед",
    "lips": "гимнастика для губ логопед",
    "breathing": "дыхательная гимнастика логопед"
}

if not YOUTUBE_API_KEY:
    print("Внимание: YOUTUBE_API_KEY не установлен в .env файле")

