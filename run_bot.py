#!/usr/bin/env python3
"""
Запуск бота через кастомный telegram_bot.py (без telegram.ext)
"""
import asyncio
import logging
import os
from telegram_bot import SimpleTelegramBot
from config import Config
from monitoring_controller import MonitoringController
from subscription_manager import SubscriptionManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    try:
        logger.info("🚀 Запуск MOEX Arbitrage Bot v0.1.9")
        
        # Инициализация компонентов
        config = Config()
        subscription_manager = SubscriptionManager()
        monitoring_controller = MonitoringController()
        
        # Создание и запуск бота  
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        async with SimpleTelegramBot(bot_token) as bot:
            logger.info("✅ Бот успешно запущен и готов к работе")
            
            # Основной цикл работы
            while True:
                try:
                    updates = await bot.get_updates()
                    
                    for update in updates:
                        # Обработка сообщений
                        if update.message:
                            message = update.message
                            chat_id = message["chat"]["id"]
                            user_id = message["from"]["id"]
                            text = message.get("text", "")
                            
                            # Сохранение username пользователя
                            username = message["from"].get("username", "")
                            if username and user_id:
                                await monitoring_controller.update_user_username(user_id, username)
                            
                            # Обработка команд
                            await bot.handle_command(chat_id, text, user_id)
                        
                        # Обработка callback query (кнопки)  
                        if update.callback_query:
                            await bot.handle_callback_query(update.callback_query)
                
                except Exception as e:
                    logger.error(f"Ошибка в основном цикле: {e}")
                    await asyncio.sleep(1)
                
                # Небольшая пауза между циклами
                await asyncio.sleep(0.1)
                
    except KeyboardInterrupt:
        logger.info("👋 Остановка бота по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())