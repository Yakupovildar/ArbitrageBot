import os
import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import Config
from bot_handlers import BotHandlers
from monitoring import ArbitrageMonitor

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ArbitrageBotApp:
    def __init__(self):
        self.config = Config()
        self.handlers = BotHandlers()
        self.monitor = ArbitrageMonitor()
        self.application = None
        
    async def setup_application(self):
        """Настройка Telegram бота"""
        # Получаем токен из переменных окружения
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
            
        # Создаем приложение
        self.application = Application.builder().token(bot_token).build()
        
        # Передаем application в handlers и monitor
        self.handlers.set_application(self.application)
        self.monitor.set_application(self.application)
        
        # Регистрируем команды
        self.application.add_handler(CommandHandler("start", self.handlers.start_command))
        self.application.add_handler(CommandHandler("help", self.handlers.help_command))
        self.application.add_handler(CommandHandler("status", self.handlers.status_command))
        self.application.add_handler(CommandHandler("positions", self.handlers.positions_command))
        self.application.add_handler(CommandHandler("instruments", self.handlers.instruments_command))
        self.application.add_handler(CommandHandler("subscribe", self.handlers.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.handlers.unsubscribe_command))
        
        # Обработчик сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message)
        )
        
    async def start_monitoring(self):
        """Запуск мониторинга арбитражных возможностей"""
        logger.info("Запуск мониторинга арбитража...")
        await self.monitor.start_monitoring()
        
    async def run(self):
        """Основной метод запуска бота"""
        try:
            logger.info("Инициализация Telegram бота для арбитража MOEX...")
            
            # Настройка приложения
            await self.setup_application()
            
            # Запуск мониторинга в фоновом режиме
            monitor_task = asyncio.create_task(self.start_monitoring())
            
            # Запуск бота
            logger.info("Запуск Telegram бота...")
            if self.application:
                await self.application.initialize()
                await self.application.start()
                if self.application.updater:
                    await self.application.updater.start_polling()
            
                    # Ожидание завершения
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        logger.info("Мониторинг остановлен")
                
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            raise
        finally:
            if self.application:
                if self.application.updater:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

async def main():
    """Точка входа приложения"""
    bot_app = ArbitrageBotApp()
    
    try:
        await bot_app.run()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
