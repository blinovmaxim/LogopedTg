from config import YOUTUBE_API_KEY
from googleapiclient.discovery import build

def search_youtube_video(query: str, max_results=5, force_update=False):
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Добавляем случайное смещение при обновлении
        if force_update:
            from random import randint
            offset = randint(1, 10)
        else:
            offset = 0
            
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=max_results + offset,  # Увеличиваем количество результатов
            type='video',
            relevanceLanguage='ru',
            safeSearch='strict',
            order='relevance'  # Можно использовать 'date' для новых видео
        ).execute()

        videos = []
        # Пропускаем первые offset видео при обновлении
        items = search_response['items'][offset:offset + max_results]
        for item in items:
            video_data = {
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId'],
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            videos.append(video_data)
        
        return videos
    
    except Exception as e:
        print(f"Ошибка при поиске видео: {e}")
        return []