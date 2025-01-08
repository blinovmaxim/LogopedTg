from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

def search_youtube_video(query: str, max_results=5):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    try:
        # Поиск видео
        search_response = youtube.search().list(
            q=query + " логопед упражнение",
            part='snippet',
            maxResults=max_results,
            type='video'
        ).execute()

        videos = []
        for item in search_response['items']:
            videos.append({
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId'],
                'thumbnail': item['snippet']['thumbnails']['default']['url'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        
        return videos
    
    except Exception as e:
        print(f"Ошибка при поиске видео: {e}")
        return [] 