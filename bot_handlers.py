import logging
from datetime import datetime
from typing import List, Dict
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import Config
from arbitrage_calculator import ArbitrageCalculator
from moex_api import MOEXAPIClient

logger = logging.getLogger(__name__)

class BotHandlers:
    """Обработчики команд Telegram бота"""
    
    def __init__(self):
        self.config = Config()
        self.calculator = ArbitrageCalculator()
        self.subscribers: set = set()
        self.application = None
        
    def set_application(self, application):
        """Установка экземпляра Application"""
        self.application = application
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        
        welcome_message = """
🤖 *Добро пожаловать в бота арбитража MOEX!*

Этот бот мониторит спреды между акциями и фьючерсами на Московской бирже и предоставляет сигналы для арбитражной торговли.

📊 *Основные функции:*
• Мониторинг спредов каждые 5 минут
• Сигналы при спреде > 1%
• Цветовое выделение по уровням спреда
• Сигналы на закрытие позиций
• Расчет пропорций для арбитража

🎯 *Цветовая схема:*
• Обычный текст: спред 1-2%
• 🟢 Зеленый: спред 2-3%
• 🟢🟢 Ярко-зеленый: спред > 3%

📝 *Доступные команды:*
/help - справка по командам
/status - статус мониторинга и рынка
/positions - открытые позиции
/instruments - отслеживаемые инструменты
/history - история найденных спредов
/schedule - расписание торгов биржи
/subscribe - подписаться на уведомления
/unsubscribe - отписаться от уведомлений
/test - тестовый мониторинг спредов каждые 5-7 минут

⚠️ *Важно:* Сигналы носят информационный характер. Торговля на финансовых рынках связана с рисками.
        """
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 *Справка по командам:*

/start - Запуск бота и приветствие
/help - Эта справка
/status - Текущий статус мониторинга и рынка
/positions - Список открытых арбитражных позиций
/instruments - Список отслеживаемых инструментов
/history - История найденных спредов (последние 10)
/schedule - Расписание торгов и статус биржи
/subscribe - Подписаться на уведомления о сигналах
/unsubscribe - Отписаться от уведомлений
/test - Тестовый мониторинг спредов каждые 5-7 минут

🔍 *Как читать сигналы:*

*Сигнал на открытие:*
📈 SBER/SiM5 | Спред: 2.5%
💰 Акции: КУПИТЬ 100 лотов
📊 Фьючерс: ПРОДАТЬ 1 лот
⏰ 12:34:56

*Сигнал на закрытие:*
🔄 Дружище, пора закрывать позицию по SBER/SiM5
📉 Спред снизился до 0.3%

⚡ *Автоматический мониторинг каждые 5-7 минут (рандомизированный)*
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        try:
            # Проверяем статус рынка
            market_status = self.config.get_market_status_message()
            
            # Проверяем статус API
            async with MOEXAPIClient() as moex_client:
                trading_status = await moex_client.get_trading_status()
            
            # Формируем сообщение о статусе
            status_message = "📊 *Статус системы мониторинга:*\n\n"
            
            # Статус рынка
            status_message += f"{market_status}\n\n"
            
            # Статус API
            api_status = "✅ Доступен" if trading_status["api_available"] else "❌ Недоступен"
            status_message += f"🔌 MOEX API: {api_status}\n"
            
            # Статус рынков
            stock_status = "🟢 Открыт" if trading_status["stock_market"] else "🔴 Закрыт"
            futures_status = "🟢 Открыт" if trading_status["futures_market"] else "🔴 Закрыт"
            
            status_message += f"📈 Фондовый рынок: {stock_status}\n"
            status_message += f"📊 Срочный рынок: {futures_status}\n\n"
            
            # Статус подписки
            user_id = update.effective_user.id
            subscription_status = "✅ Активна" if user_id in self.subscribers else "❌ Отключена"
            status_message += f"🔔 Ваша подписка: {subscription_status}\n"
            
            # Открытые позиции
            open_positions_count = len(self.calculator.open_positions)
            status_message += f"📋 Открытых позиций: {open_positions_count}\n"
            
            # Количество подписчиков (для админов)
            if self.config.is_admin(user_id):
                status_message += f"👥 Всего подписчиков: {len(self.subscribers)}\n"
            
            status_message += f"\n⏰ Интервал мониторинга: 5-7 мин (рандомизированный)"
            
            await update.message.reply_text(
                status_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде status: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении статуса системы"
            )
    
    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /positions"""
        try:
            positions = self.calculator.get_open_positions_summary()
            
            if not positions:
                await update.message.reply_text(
                    "📋 *Открытые позиции:*\n\nНет открытых арбитражных позиций",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            message = "📋 *Открытые арбитражные позиции:*\n\n"
            
            for i, position in enumerate(positions, 1):
                entry_time = position["entry_timestamp"]
                
                message += f"*{i}. {position['stock_ticker']}/{position['futures_ticker']}*\n"
                message += f"📈 Акции: {position['stock_position']} {position['stock_lots']} лотов\n"
                message += f"📊 Фьючерс: {position['futures_position']} {position['futures_lots']} лотов\n"
                message += f"📊 Входной спред: {position['entry_spread']:.2f}%\n"
                message += f"⏰ Время входа: {entry_time}\n\n"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде positions: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении списка позиций"
            )
    
    async def instruments_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /instruments"""
        try:
            message = "📊 *Отслеживаемые инструменты:*\n\n"
            
            for stock, futures in self.config.MONITORED_INSTRUMENTS.items():
                message += f"• {stock} ↔️ {futures}\n"
            
            message += f"\n📈 Всего пар: {len(self.config.MONITORED_INSTRUMENTS)}"
            message += f"\n⚡ Минимальный спред для сигнала: {self.config.MIN_SPREAD_THRESHOLD}%"
            message += f"\n🟢 Зеленое выделение: > {self.config.SPREAD_LEVEL_2}%"
            message += f"\n🟢🟢 Ярко-зеленое: > {self.config.SPREAD_LEVEL_3}%"
            
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде instruments: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении списка инструментов"
            )
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /subscribe"""
        user_id = update.effective_user.id
        
        # Проверяем статус рынка при подписке
        if not self.config.is_trading_hours():
            market_status = self.config.get_trading_status_message()
            await update.message.reply_text(
                f"{market_status}\n\n⚠️ Мониторинг будет активен только в торговые часы.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        if user_id in self.subscribers:
            await update.message.reply_text(
                "✅ Вы уже подписаны на уведомления о сигналах арбитража"
            )
        else:
            self.subscribers.add(user_id)
            await update.message.reply_text(
                "🔔 Вы успешно подписались на уведомления!\n\n"
                "Теперь вы будете получать сигналы об арбитражных возможностях каждые 5-7 минут.\n\n"
                "Для отписки используйте /unsubscribe"
            )
        
        logger.info(f"Пользователь {user_id} подписался на уведомления")
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /unsubscribe"""
        user_id = update.effective_user.id
        
        if user_id in self.subscribers:
            self.subscribers.remove(user_id)
            await update.message.reply_text(
                "🔕 Вы отписались от уведомлений о сигналах арбитража"
            )
        else:
            await update.message.reply_text(
                "❌ Вы не были подписаны на уведомления"
            )
        
        logger.info(f"Пользователь {user_id} отписался от уведомлений")
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /history - показать историю найденных спредов"""
        try:
            # Получаем историю спредов от монитора
            from monitoring import ArbitrageMonitor
            # В реальном коде это должно быть передано через dependency injection
            # Здесь используем заглушку для демонстрации
            
            history_message = "📊 История найденных спредов:\n\n"
            history_message += "⚠️ История доступна только во время работы бота\n"
            history_message += "Используйте /status для проверки состояния системы"
            
            await update.message.reply_text(
                history_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде history: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении истории спредов"
            )
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /schedule - расписание торгов"""
        try:
            schedule_info = self.config.get_trading_schedule_info()
            market_status = self.config.get_market_status_message()
            
            full_message = f"{market_status}\n\n{schedule_info}"
            
            await update.message.reply_text(
                full_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде schedule: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении расписания торгов"
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обычных сообщений"""
        await update.message.reply_text(
            "🤖 Я понимаю только команды. Используйте /help для получения списка доступных команд."
        )
    
    def get_subscribers(self) -> set:
        """Получение списка подписчиков"""
        return self.subscribers.copy()
