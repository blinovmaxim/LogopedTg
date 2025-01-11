import sqlite3
from typing import List, Dict
import time

class Database:
    def __init__(self):
        self.database_name = 'logoped_bot.db'
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Создает новое подключение к базе данных"""
        try:
            self.conn = sqlite3.connect(self.database_name, timeout=20)
        except sqlite3.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise e
    
    def create_tables(self):
        """Создает необходимые таблицы"""
        retries = 3
        while retries > 0:
            try:
                cursor = self.conn.cursor()
                
                # Создаем таблицу allowed_users
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Создаем таблицу schedule
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    status TEXT DEFAULT 'available',
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, time)
                )
                ''')
                
                # Добавляем таблицу pending_users
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                self.conn.commit()
                break
                
            except sqlite3.OperationalError as e:
                retries -= 1
                if retries == 0:
                    raise e
                time.sleep(1)
                self.connect()  # Пересоздаем соединение
    
    def __del__(self):
        """Закрываем соединение при удалении объекта"""
        try:
            self.conn.close()
        except:
            pass
    
    def execute_query(self, query, params=None):
        """Выполняет запрос с повторными попытками"""
        retries = 3
        while retries > 0:
            try:
                cursor = self.conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                self.conn.commit()
                return cursor
            except sqlite3.OperationalError as e:
                retries -= 1
                if retries == 0:
                    raise e
                time.sleep(1)
                self.connect()
    
    def add_allowed_user(self, user_id: int, added_by: int) -> bool:
        """Добавляет пользователя в список разрешенных"""
        try:
            self.execute_query(
                'INSERT INTO allowed_users (user_id, added_by) VALUES (?, ?)',
                (user_id, added_by)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return False
    
    def remove_allowed_user(self, user_id: int) -> bool:
        """Удаляет пользователя из списка разрешенных"""
        try:
            self.execute_query(
                'DELETE FROM allowed_users WHERE user_id = ?',
                (user_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {e}")
            return False
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, есть ли пользователь в списке разрешенных"""
        try:
            cursor = self.execute_query(
                'SELECT 1 FROM allowed_users WHERE user_id = ?',
                (user_id,)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Ошибка при проверке пользователя: {e}")
            return False
    
    def add_work_slot(self, date: str, time: str):
        self.execute_query(
            'INSERT OR IGNORE INTO schedule (date, time) VALUES (?, ?)',
            (date, time)
        )
    
    def get_available_slots(self, date: str) -> List[str]:
        cursor = self.execute_query(
            'SELECT time FROM schedule WHERE date = ? AND status = "available"',
            (date,)
        )
        return [row[0] for row in cursor.fetchall()] 
    
    def get_all_appointments(self) -> List[Dict]:
        """Получает все записи из расписания"""
        cursor = self.execute_query('''
            SELECT date, time, status, user_id 
            FROM schedule 
            WHERE date >= date('now') 
            ORDER BY date, time
        ''')
        
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                'date': row[0],
                'time': row[1],
                'status': row[2],
                'user_id': row[3]
            })
        
        return appointments 
    
    def cancel_appointment(self, date: str, time: str):
        """Отменяет запись"""
        try:
            cursor = self.execute_query('''
                DELETE FROM schedule 
                WHERE date = ? AND time = ?
            ''', (date, time))
            self.conn.commit()
            print(f"Запись отменена: {date} {time}")
            return True
        except Exception as e:
            print(f"Ошибка при отмене записи: {e}")
            return False 
    
    def get_allowed_users(self) -> list:
        """Возвращает список всех разрешенных пользователей"""
        cursor = self.execute_query('SELECT user_id FROM allowed_users')
        return [row[0] for row in cursor.fetchall()] 
    
    def add_pending_user(self, user_id: int, username: str = None, full_name: str = None):
        """Добавление пользователя в список ожидающих"""
        try:
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS pending_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.execute_query(
                'INSERT OR REPLACE INTO pending_users (user_id, username, full_name) VALUES (?, ?, ?)',
                (user_id, username, full_name)
            )
            return True
        except Exception as e:
            print(f"Ошибка при добавлении ожидающего пользователя: {e}")
            return False
    
    def get_pending_users(self):
        """Получение списка ожидающих пользователей"""
        try:
            cursor = self.execute_query('''
                SELECT user_id, username, full_name, request_time 
                FROM pending_users 
                ORDER BY request_time DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка ожидающих: {e}")
            return []
    
    def remove_pending_user(self, user_id: int):
        """Удаление пользователя из списка ожидающих"""
        try:
            self.execute_query(
                'DELETE FROM pending_users WHERE user_id = ?',
                (user_id,)
            )
            return True
        except Exception as e:
            print(f"Ошибка при удалении ожидающего пользователя: {e}")
            return False 
    
    def add_allowed_username(self, username: str) -> bool:
        """Добавляет username в список разрешенных"""
        try:
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS allowed_usernames (
                    username TEXT PRIMARY KEY,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.execute_query(
                'INSERT OR REPLACE INTO allowed_usernames (username) VALUES (?)',
                (username,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении username: {e}")
            return False
    
    def is_username_allowed(self, username: str) -> bool:
        """Проверяет, есть ли username в списке разрешенных"""
        try:
            cursor = self.execute_query(
                'SELECT 1 FROM allowed_usernames WHERE username = ?',
                (username,)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Ошибка при проверке username: {e}")
            return False 