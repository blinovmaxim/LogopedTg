import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_IDS
from handlers import admin, client, exercises, schedule, access, tasks
from aiogram.types import BotCommand
from handlers.access import access_middleware
import socket
import sys
import json
from datetime import datetime
import os
import signal
from database import Database

    # Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Регистрируем роутеры в правильном порядке
dp.include_router(access.router)
dp.include_router(admin.router)  # Сначала админский роутер
dp.include_router(client.router)
dp.include_router(exercises.router)
dp.include_router(schedule.router)
dp.include_router(tasks.router)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands)


def cleanup_socket():
    """Очищаем сокет если он остался от предыдущего запуска"""
    try:
        os.remove("bot_lock.sock")
    except FileNotFoundError:
        pass

def is_bot_running():
    """Проверяет, запущен ли уже бот"""
    try:
        # Пытаемся занять порт. Если порт занят - значит бот уже запущен
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 47200))  # Используем случайный свободный порт
        return False
    except socket.error:
        return True
    finally:
        sock.close()

async def shutdown(dispatcher: Dispatcher, bot: Bot):
    """Корректное завершение работы бота"""
    print('Останавливаю бота...')
    
    # Отменяем все задачи
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Закрываем хранилище состояний
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
    
    # Закрываем сессию бота
    await bot.session.close()
    
    # Очищаем сокет
    cleanup_socket()
    
    print('Бот остановлен')

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print(f'Получен сигнал {signum}')
    cleanup_socket()
    sys.exit(0)




# Middleware для проверки доступа
class AccessMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            # Проверяем, является ли команда из раздела упражнений
            if event.text and event.text.startswith(('🎯 Упражнения', '/exercise')):
                if not await access_middleware(event, data['bot']):
                    return
            # Для остальных команд пропускаем проверку
        elif isinstance(event, types.CallbackQuery):
            # Проверяем callback-запросы для упражнений
            if event.data and event.data.startswith(('ex_', 'video:')):
                if not await access_middleware(event.message, data['bot']):
                    await event.answer("⚠️ Для доступа к упражнениям необходимо подписаться на канал и получить доступ", show_alert=True)
                    return
        return await handler(event, data)

# Регистрируем middleware
dp.message.middleware(AccessMiddleware())

def save_restart_status(status: str, error: str = None):
    """Сохраняет статус перезапуска в файл"""
    data = {
        'status': status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'error': error
    }
    with open('restart_status.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    try:
        # Проверяем, был ли это рестарт
        if os.path.exists('restart_chat.txt'):
            with open('restart_chat.txt', 'r') as f:
                chat_id = int(f.read().strip())
            
            # Отправляем уведомление
            await bot.send_message(
                chat_id,
                "✅ Бот успешно перезапущен!"
            )
            
            # Удаляем файл
            os.remove('restart_chat.txt')
            
        # Обновляем статус
        save_restart_status('success')
        
    except Exception as e:
        print(f"Ошибка при отправке уведомления о рестарте: {e}")

# Добавляем on_startup в диспетчер
dp.startup.register(on_startup)

async def main():
    try:
        # Отмечаем успешный запуск
        save_restart_status('success')
        
        await set_commands(bot)
        
        # Инициализация базы данных (только один раз)
        db = Database()
        
        # Удаляем все обновления, которые произошли после последнего завершения работы бота
        await bot.delete_webhook(drop_pending_updates=True)
        
        await dp.start_polling(bot)
    except Exception as e:
        save_restart_status('error', str(e))
        print(f'Ошибка: {e}')
    finally:
        await bot.session.close()

if __name__ == '__main__':
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if is_bot_running():
        print("❌ Бот уже запущен! Закройте другой экземпляр.")
        sys.exit(1)
    
    # Настраиваем логирование
    logging.basicConfig(level=logging.INFO)
    

    
    try:
        # Запускаем бота
        asyncio.run(main())
    except KeyboardInterrupt:
        # Корректно завершаем при Ctrl+C
        print('\nПолучен сигнал на завершение')
        asyncio.run(shutdown(dp, bot))
    except Exception as e:
        print(f'Критическая ошибка: {e}')
        asyncio.run(shutdown(dp, bot))
    finally:
        # В любом случае очищаем сокет
        cleanup_socket()


