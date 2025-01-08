import sqlite3
from typing import List, Dict

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('logoped_bot.db')
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            video_path TEXT NOT NULL,
            description TEXT,
            is_url BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.conn.commit() 

    def get_exercise_by_id(self, exercise_id: int) -> dict:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM exercises WHERE id = ?',
            (exercise_id,)
        )
        result = cursor.fetchone()
        if result:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, result))
        return None

    def get_exercises_by_category(self, category: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM exercises WHERE category = ? ORDER BY title',
            (category,)
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()] 

    def add_exercise(self, category: str, title: str, video_source: str, description: str, is_url: bool = False) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO exercises (category, title, video_path, description, is_url) VALUES (?, ?, ?, ?, ?)',
            (category, title, video_source, description, is_url)
        )
        self.conn.commit()
        return cursor.lastrowid 