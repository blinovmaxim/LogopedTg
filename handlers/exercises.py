from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from keyboards.client_kb import get_main_keyboard
from states.exercise_states import ExerciseStates
from config import EXERCISE_CATEGORIES, EXERCISE_SEARCH_QUERIES
from utils.youtube import search_youtube_video

router = Router()

# Изменяем обработчик для кнопки "Мои упражнения"
@router.message(F.text == "🎯 Мои упражнения")
async def show_exercise_categories(message: Message):
    keyboard = []
    for code, name in EXERCISE_CATEGORIES.items():
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"➤ {name}",
                callback_data=f"ex_{code}"
            )
        ])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(
        "<b>🎯 Видео-упражнения</b>\n\n"
        "<i>Выберите категорию упражнений:</i>\n\n"
        "• Каждая категория содержит специально подобранные видео\n"
        "• Выполняйте упражнения регулярно\n"
        "• Следите за техникой выполнения\n",
        reply_markup=markup,
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data.startswith('ex_'))
async def process_exercise_category(callback: CallbackQuery):
    category_code = callback.data.replace('ex_', '')
    if category_code in EXERCISE_CATEGORIES:
        category_name = EXERCISE_CATEGORIES[category_code]
        
        videos = search_youtube_video(EXERCISE_SEARCH_QUERIES[category_code], max_results=5, force_update=True)
        
        if videos:
            keyboard = []
            for i, video in enumerate(videos, 1):
                title = video['title']
                if len(title) > 40:
                    title = title[:37] + "..."
                
                keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"📺 {title}",
                        callback_data=f"video:{category_code}:{i-1}"
                    )
                ])
            
            # Добавляем кнопки обновления и возврата
            keyboard.extend([
                [
                    types.InlineKeyboardButton(
                        text="🔄 Обновить список",
                        callback_data=f"refresh:{category_code}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="◀️ Вернуться к категориям",
                        callback_data="back_to_categories"
                    )
                ]
            ])
            
            markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            if not hasattr(callback.bot, 'videos'):
                callback.bot.videos = {}
            callback.bot.videos[category_code] = videos
            
            await callback.message.edit_text(
                f"<b>🎯 {category_name}</b>\n\n"
                f"<i>Выберите видео для просмотра:</i>\n",
                reply_markup=markup,
                parse_mode="HTML"
            )

@router.callback_query(lambda c: c.data.startswith('refresh:'))
async def refresh_videos(callback: CallbackQuery):
    try:
        _, category_code = callback.data.split(':')
        if category_code in EXERCISE_CATEGORIES:
            # Показываем уведомление о начале обновления
            await callback.answer("🔄 Обновляем список видео...")
            
            # Получаем новые видео с принудительным обновлением
            videos = search_youtube_video(
                EXERCISE_SEARCH_QUERIES[category_code], 
                max_results=5, 
                force_update=True
            )
            
            if videos:
                # Перенаправляем на показ обновленного списка
                callback.data = f"ex_{category_code}"
                await process_exercise_category(callback)
            else:
                await callback.answer("❌ Не удалось загрузить видео")
    except Exception as e:
        print(f"Ошибка при обновлении видео: {e}")
        await callback.answer("❌ Ошибка обновления")

@router.callback_query(lambda c: c.data.startswith('video:'))  # Изменили разделитель на :
async def confirm_watch_video(callback: CallbackQuery):
    try:
        _, category_code, video_idx = callback.data.split(':')  # Используем : вместо _
        video_idx = int(video_idx)
        
        videos = getattr(callback.bot, 'videos', {}).get(category_code, [])
        
        if videos and video_idx < len(videos):
            video = videos[video_idx]
            keyboard = [
                [
                    types.InlineKeyboardButton(
                        text="▶️ Смотреть видео",
                        url=video['url']
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="◀️ Назад к списку",
                        callback_data=f"ex_{category_code}"
                    )
                ]
            ]
            
            markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback.message.edit_text(
                f"<b>📺 {video['title']}</b>\n\n"
                "Нажмите <b>▶️ Смотреть видео</b>, чтобы начать просмотр\n\n"
                "<i>💡 Совет: Выполняйте упражнение вместе с видео</i>",
                reply_markup=markup,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Ошибка при обработке callback: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз.")

@router.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    await show_exercise_categories(callback.message)
    await callback.answer()