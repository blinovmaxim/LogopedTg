from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.client_kb import get_main_keyboard
from states.exercise_states import ExerciseStates
from config import EXERCISE_CATEGORIES
from utils.youtube import search_youtube_video
from datetime import datetime, timedelta
import json
import os

router = Router()
CACHE_FILE = 'cache/youtube_cache.json'
CACHE_DURATION = timedelta(hours=24)  # Кэш хранится 24 часа

def load_cache():
    if not os.path.exists('cache'):
        os.makedirs('cache')
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            # Проверяем срок действия кэша
            if datetime.fromisoformat(cache['timestamp']) + CACHE_DURATION > datetime.now():
                return cache['data']
    return {}

def save_cache(data):
    cache = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)

@router.message(F.text == "🎯 Мои упражнения")
async def show_exercise_categories(message: Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=name,
            callback_data=f"category_{code}"
        )] for code, name in EXERCISE_CATEGORIES.items()
    ])
    
    await message.answer(
        "Выберите категорию упражнений:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith('category_'))
async def show_category_exercises(callback: CallbackQuery, state: FSMContext, force_update=False):
    category_code = callback.data.replace('category_', '')
    category_name = EXERCISE_CATEGORIES[category_code]
    
    # Всегда показываем сообщение о поиске
    await callback.message.answer(f"🔍 Ищу упражнения для {category_name}...")
    
    # Принудительно ищем новые видео при обновлении
    search_query = category_code  # Передаем код категории для точного поиска
    videos = search_youtube_video(search_query)
    
    if not videos:
        await callback.message.answer(f"К сожалению, не удалось найти упражнения для категории {category_name}")
        await callback.answer()
        return

    # Создаем клавиатуру с найденными видео
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"📺 {video['title'][:40]}...",
            callback_data=f"video_{video['video_id']}"
        )] for video in videos
    ])
    
    # Добавляем кнопки управления
    keyboard.inline_keyboard.extend([
        [types.InlineKeyboardButton(
            text="🔄 Обновить результаты",
            callback_data=f"refresh_{category_code}"
        )],
        [types.InlineKeyboardButton(
            text="↩️ Назад к категориям",
            callback_data="back_to_categories"
        )]
    ])
    
    await callback.message.answer(
        f"🎯 Найденные упражнения для {category_name}:\n"
        f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Выберите видео для просмотра:",
        reply_markup=keyboard
    )
    await state.update_data(videos={v['video_id']: v for v in videos})
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('refresh_'))
async def refresh_videos(callback: CallbackQuery, state: FSMContext):
    category_code = callback.data.replace('refresh_', '')
    await callback.message.answer("🔄 Обновляю список видео...")
    await show_category_exercises(callback, state, force_update=True)

@router.callback_query(lambda c: c.data.startswith('video_'))
async def show_video(callback: CallbackQuery, state: FSMContext):
    video_id = callback.data.replace('video_', '')
    
    # Получаем данные о видео
    data = await state.get_data()
    video = data['videos'].get(video_id)
    
    if not video:
        await callback.message.answer("Видео не найдено")
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="▶️ Смотреть на YouTube",
            url=f"https://www.youtube.com/watch?v={video_id}"
        )],
        [types.InlineKeyboardButton(
            text="↩️ Назад к списку",
            callback_data=callback.message.reply_markup.inline_keyboard[-1][0].callback_data
        )]
    ])
    
    await callback.message.answer(
        f"📺 {video['title']}\n\n"
        f"Нажмите кнопку ниже, чтобы посмотреть видео на YouTube:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    await show_exercise_categories(callback.message)
    await callback.answer() 