from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY') 
ADMIN_IDS = [515716689, 474177687]
  # Замените на свои ID

EXERCISE_CATEGORIES = {
    "sounds_r": "Звук Р",
    "sounds_l": "Звук Л",
    "sounds_sh": "Звук Ш",
    "sounds_s": "Звук С",
    "articulation": "Артикуляционная гимнастика"
} 