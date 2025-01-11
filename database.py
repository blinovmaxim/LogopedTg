import sqlite3
import logging
from typing import Optional, Dict, List
from datetime import datetime
from config import ADMIN_IDS

class Database:
    def __init__(self, db_path: str = "logoped_bot.db"):
        self.db_path = db_path
        self.conn = None
        self._tables_created = False  # Флаг для отслеживания создания таблиц
        self.create_tables()
    
    def connect(self):
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
            except Exception as e:
                logging.error(f"Ошибка подключения к БД: {e}")
                raise
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query: str, params: tuple = None) -> sqlite3.Cursor:
        try:
            self.connect()
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    def create_tables(self):
        if self._tables_created:  # Проверяем, были ли уже созданы таблицы
            return
            
        self.connect()
        try:
            self.execute_query('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES allowed_users(user_id)
            )
            ''')
            
            self.execute_query('''
            CREATE TABLE IF NOT EXISTS task_timers (
                timer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                user_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration INTEGER,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (user_id) REFERENCES allowed_users(user_id)
            )
            ''')
            
            self.execute_query('''
            CREATE TABLE IF NOT EXISTS assigned_tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                assigned_by INTEGER,
                assigned_to INTEGER,
                task_name TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed INTEGER DEFAULT 0,
                FOREIGN KEY (assigned_by) REFERENCES allowed_users(user_id),
                FOREIGN KEY (assigned_to) REFERENCES allowed_users(user_id)
            )
            ''')
            
            self.conn.commit()
            print("✅ Таблицы успешно созданы")
            
        except Exception as e:
            print(f"Ошибка создания таблиц: {e}")
            raise
        finally:
            self.close()
        
        self._tables_created = True  # Устанавливаем флаг после создания

    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, имеет ли пользователь доступ"""
        try:
            # Сначала проверяем, является ли пользователь админом
            if user_id in ADMIN_IDS:  # Добавляем импорт ADMIN_IDS из config
                return True
            
            # Если не админ, проверяем в базе данных
            result = self.execute_query(
                'SELECT 1 FROM allowed_users WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            return bool(result)
        except Exception as e:
            logging.error(f"Ошибка проверки доступа пользователя {user_id}: {e}")
            return False

    def add_allowed_user(self, user_id: int, username: str = None, full_name: str = None) -> bool:
        try:
            self.connect()
            # Получаем актуальный username пользователя из pending_users
            if username is None:
                user = self.execute_query(
                    'SELECT username FROM pending_users WHERE user_id = ?',
                    (user_id,)
                ).fetchone()
                if user and user[0]:
                    username = user[0]
            
            # Добавляем пользователя в базу
            self.execute_query(
                '''INSERT OR REPLACE INTO allowed_users 
                   (user_id, username, full_name) VALUES (?, ?, ?)''',
                (user_id, username, full_name)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка добавления пользователя {user_id}: {e}")
            return False
        finally:
            self.close()

    def remove_allowed_user(self, user_id: int) -> bool:
        try:
            self.execute_query(
                'DELETE FROM allowed_users WHERE user_id = ?',
                (user_id,)
            )
            return True
        except Exception as e:
            logging.error(f"Ошибка удаления пользователя {user_id}: {e}")
            return False

    def add_task(self, user_id: int, task_name: str, description: str) -> int:
        try:
            cursor = self.execute_query(
                '''INSERT INTO tasks (user_id, task_name, description)
                   VALUES (?, ?, ?)
                   RETURNING task_id''',
                (user_id, task_name, description)
            )
            task_id = cursor.fetchone()[0]
            self.conn.commit()
            return task_id
        except Exception as e:
            print(f"Ошибка добавления задания: {e}")
            return None

    def get_user_tasks(self, user_id: int):
        return self.execute_query(
            '''SELECT task_id, task_name, description, created_at
               FROM tasks 
               WHERE user_id = ?
               ORDER BY created_at DESC''',
            (user_id,)
        ).fetchall()

    def start_timer(self, task_id: int, user_id: int):
        self.execute_query(
            '''INSERT INTO task_timers (task_id, user_id, start_time)
               VALUES (?, ?, datetime('now'))''',
            (task_id, user_id)
        )
        self.conn.commit()

    def stop_timer(self, task_id: int, user_id: int):
        self.execute_query(
            '''UPDATE task_timers 
               SET end_time = datetime('now'),
                   duration = CAST(
                       (JULIANDAY(datetime('now')) - JULIANDAY(start_time)) * 86400 
                       AS INTEGER
                   )
               WHERE task_id = ? AND user_id = ? AND end_time IS NULL''',
            (task_id, user_id)
        )
        self.conn.commit()

    def assign_task(self, admin_id: int, user_id: int, task_name: str, description: str) -> int:
        try:
            cursor = self.execute_query(
                '''INSERT INTO assigned_tasks 
                   (assigned_by, assigned_to, task_name, description)
                   VALUES (?, ?, ?, ?)
                   RETURNING task_id''',
                (admin_id, user_id, task_name, description)
            )
            task_id = cursor.fetchone()[0]
            self.conn.commit()
            return task_id
        except Exception as e:
            print(f"Ошибка назначения задания: {e}")
            return None

    def get_assigned_tasks(self, user_id: int):
        return self.execute_query(
            '''SELECT task_id, task_name, description, created_at, completed
               FROM assigned_tasks 
               WHERE assigned_to = ?
               ORDER BY created_at DESC''',
            (user_id,)
        ).fetchall()

    def complete_assigned_task(self, task_id: int, user_id: int) -> bool:
        try:
            self.execute_query(
                '''UPDATE assigned_tasks 
                   SET completed = 1
                   WHERE task_id = ? AND assigned_to = ?''',
                (task_id, user_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка завершения задания: {e}")
            return False

# Создаем единственный экземпляр базы данных
db = Database() 