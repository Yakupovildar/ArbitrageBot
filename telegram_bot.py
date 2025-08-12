#!/usr/bin/env python3
"""
Простой Telegram бот для арбитража MOEX без использования python-telegram-bot
Использует прямые HTTP запросы к Telegram Bot API
"""

import os
import asyncio
import aiohttp
import json
import logging
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from config import Config
from moex_api import MOEXAPIClient
from arbitrage_calculator import ArbitrageCalculator
from monitoring_controller import MonitoringController
from data_sources import DataSourceManager
from user_settings import UserSettingsManager

# Класс для хранения истории спредов  
class SpreadHistory:
    def __init__(self, max_records: int = 10):
        self.max_records = max_records
        self.records = []
    
    def add_record(self, stock_ticker: str, futures_ticker: str, spread: float, signal_type: str):
        record = {
            'timestamp': datetime.now(),
            'stock_ticker': stock_ticker,
            'futures_ticker': futures_ticker,
            'spread': spread,
            'signal_type': signal_type
        }
        self.records.append(record)
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
    
    def format_history(self) -> str:
        if not self.records:
            return "📊 История пуста"
        
        message = "📊 История найденных спредов:\n\n"
        for i, record in enumerate(reversed(self.records)):
            timestamp = record['timestamp'].strftime('%d.%m %H:%M')
            message += f"{i+1}. {record['stock_ticker']}/{record['futures_ticker']}\n"
            message += f"   📈 Спред: {record['spread']:.2f}%\n"
            message += f"   🎯 {record['signal_type']}\n"
            message += f"   ⏰ {timestamp}\n\n"
        return message

logger = logging.getLogger(__name__)

@dataclass
class TelegramUpdate:
    """Структура для Telegram update"""
    update_id: int
    message: Optional[Dict] = None
    callback_query: Optional[Dict] = None
    
class SimpleTelegramBot:
    """Простой Telegram бот через HTTP API"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = None
        self.offset = 0
        self.subscribers: Set[int] = set()
        self.config = Config()
        self.calculator = ArbitrageCalculator()
        self.spread_history = SpreadHistory(self.config.MAX_SPREAD_HISTORY)
        self.monitoring_controller = MonitoringController()
        self.data_sources = DataSourceManager()
        self.user_settings = UserSettingsManager()
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """Отправка сообщения"""
        if not self.session:
            return False
            
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Ошибка отправки сообщения: {response.status} - {response_text}")
                    logger.error(f"Отправляемое сообщение: {text[:200]}...")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            return False
            
    async def send_message_with_keyboard(self, chat_id: int, text: str, keyboard: dict, parse_mode: str = "Markdown") -> bool:
        """Отправка сообщения с inline-клавиатурой"""
        if not self.session:
            return False
            
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": keyboard
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                else:
                    logger.error(f"Ошибка отправки сообщения с клавиатурой: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения с клавиатурой: {e}")
            return False
            
    async def answer_callback_query(self, callback_query_id: str, text: str = "") -> bool:
        """Ответ на callback query"""
        if not self.session:
            return False
            
        url = f"{self.base_url}/answerCallbackQuery"
        data = {
            "callback_query_id": callback_query_id,
            "text": text
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ошибка при ответе на callback: {e}")
            return False
    
    async def edit_message_with_keyboard(self, chat_id: int, message_id: int, text: str, keyboard: dict) -> bool:
        """Редактирование сообщения с inline-клавиатурой"""
        if not self.session:
            return False
            
        url = f"{self.base_url}/editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": keyboard
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            return False
    
    async def get_updates(self) -> List[TelegramUpdate]:
        """Получение обновлений"""
        if not self.session:
            return []
            
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self.offset,
            "timeout": 10
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    updates = []
                    
                    for update_data in data.get("result", []):
                        update = TelegramUpdate(
                            update_id=update_data["update_id"],
                            message=update_data.get("message"),
                            callback_query=update_data.get("callback_query")
                        )
                        updates.append(update)
                        self.offset = max(self.offset, update_data["update_id"] + 1)
                    
                    return updates
                else:
                    logger.error(f"Ошибка получения обновлений: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка при получении обновлений: {e}")
            return []
    
    async def handle_command(self, chat_id: int, command: str, user_id: int):
        """Обработка команд"""
        
        if command == "/start":
            welcome_text = """🤖 Добро пожаловать в бота арбитража MOEX!

Этот бот мониторит спреды между акциями и фьючерсами на Московской бирже.

📊 Основные функции:
• Мониторинг спредов каждые 5-7 минут (рандомизированный)
• Сигналы при спреде > 1% только в торговые часы
• Цветовое выделение по уровням спреда
• Сигналы на закрытие позиций
• История найденных спредов

📝 Доступные команды:
/help - справка по командам
/status - статус мониторинга и рынка
/start_monitoring - начать мониторинг спредов
/stop_monitoring - остановить мониторинг
/history - история последних 10 найденных спредов
/schedule - расписание торгов биржи
/demo - демонстрация сигналов
/settings - персональные настройки мониторинга
/support - связь с технической поддержкой
/subscribe - подписаться на уведомления
/unsubscribe - отписаться от уведомлений

⚠️ Важно: Сигналы носят информационный характер."""
            await self.send_message(chat_id, welcome_text)
            
        elif command.startswith("/help"):
            help_text = """📚 *Справка по командам:*

/start - Запуск бота и приветствие
/help - Эта справка
/status - Текущий статус мониторинга и рынка
/start_monitoring - Начать мониторинг спредов
/stop_monitoring - Остановить мониторинг
/history - История последних 10 найденных спредов
/schedule - Расписание торгов и статус биржи
/demo - Демонстрация функций бота
/settings - Персональные настройки мониторинга
/support - Связь с технической поддержкой
/subscribe - Подписаться на уведомления
/unsubscribe - Отписаться от уведомлений

🔍 *Как читать сигналы:*
📈 SBER/SiM5 | Спред: 2.5%
💰 Акции: КУПИТЬ 100 лотов
📊 Фьючерс: ПРОДАТЬ 1 лот

⚡ *Автоматический мониторинг каждые 5-7 минут (рандомизированный)*"""
            await self.send_message(chat_id, help_text)
            
        elif command.startswith("/status"):
            market_status = self.config.get_market_status_message()
            user_monitoring = self.monitoring_controller.is_user_monitoring(user_id)
            
            status_text = f"""📊 *Статус системы мониторинга:*

{market_status}

🔌 MOEX API: ✅ Доступен
📈 Ваш мониторинг: {"✅ Активен" if user_monitoring else "❌ Остановлен"}
👥 Всего активных пользователей: {self.monitoring_controller.get_active_users_count()}
🔔 Ваша подписка: {"✅ Активна" if user_id in self.subscribers else "❌ Отключена"}
📋 Открытых позиций: {len(self.calculator.open_positions)}
⏰ Интервал: 5-7 мин (рандомизированный)

💡 Используйте /start_monitoring для запуска"""
            await self.send_message(chat_id, status_text)
            
        elif command.startswith("/history"):
            history_text = self.spread_history.format_history()
            await self.send_message(chat_id, history_text)
            
        elif command.startswith("/schedule"):
            schedule_info = self.config.get_trading_schedule_info()
            market_status = self.config.get_market_status_message()
            full_message = f"{market_status}\n\n{schedule_info}"
            await self.send_message(chat_id, full_message)
            
        elif command.startswith("/start_monitoring"):
            # Проверяем, возможно ли запустить мониторинг
            if self.monitoring_controller.is_user_monitoring(user_id):
                await self.send_message(chat_id, "✅ Мониторинг уже запущен для вас")
                return
                
            # Автоматически подписываем на уведомления при запуске мониторинга
            if user_id not in self.subscribers:
                self.subscribers.add(user_id)
                
            # Проверяем статус рынка
            if not self.config.is_market_open():
                market_status = self.config.get_market_status_message()
                
                # Создаем inline-клавиатуру для выбора
                keyboard = {
                    "inline_keyboard": [[
                        {"text": "✅ Да, начать при открытии", "callback_data": "start_when_open"},
                        {"text": "❌ Нет, спасибо", "callback_data": "cancel_monitoring"}
                    ]]
                }
                
                message = f"""{market_status}

❓ Начать мониторинг спредов когда откроется биржа?

⏰ Мониторинг автоматически запустится в рабочие часы (09:00-18:45 МСК, Пн-Пт)"""
                
                await self.send_message_with_keyboard(chat_id, message, keyboard)
                return
            
            # Биржа открыта - запускаем мониторинг
            self.monitoring_controller.start_monitoring_for_user(user_id)
            await self.send_message(chat_id, "🟢 Мониторинг запущен! Вы будете получать уведомления о спредах > 1%")
            
        elif command.startswith("/stop_monitoring"):
            if not self.monitoring_controller.is_user_monitoring(user_id):
                await self.send_message(chat_id, "ℹ️ Мониторинг не запущен")
                return
                
            self.monitoring_controller.stop_monitoring_for_user(user_id)
            await self.send_message(chat_id, "🔴 Мониторинг остановлен")
            
        elif command.startswith("/demo"):
            demo_message = """🎯 ДЕМОНСТРАЦИЯ СИГНАЛОВ

🟢🟢 АРБИТРАЖ СИГНАЛ

🎯 SBER/SiM5
📊 Спред: 3.25%

💼 Позиции:
📈 Акции SBER: КУПИТЬ 100 лотов
📊 Фьючерс SiM5: ПРОДАТЬ 1 лот

💰 Цены:
📈 SBER: 285.50 ₽
📊 SiM5: 294.78 ₽

⏰ Время: 14:32:15

---

🔄 СИГНАЛ НА ЗАКРЫТИЕ

👋 Дружище, пора закрывать позицию по GAZP/GZM5!

📉 Спред снизился до: 0.3%

⏰ Время: 16:45:22

Это демонстрационные сигналы для показа функциональности бота."""
            await self.send_message(chat_id, demo_message)
            

            
        elif command.startswith("/support"):
            support_message = f"""🆘 *ТЕХНИЧЕСКАЯ ПОДДЕРЖКА*

Если у вас возникли вопросы или проблемы с ботом, вы можете:

📩 Написать администратору: {self.config.ADMIN_USERNAME}

🤖 Или написать сообщение прямо сюда в бот - администратор получит уведомление и ответит вам

⚡ *Частые вопросы:*
• Как запустить мониторинг? - /start_monitoring
• Почему нет сигналов? - Проверьте /status и время работы биржи
• Как остановить уведомления? - /stop_monitoring

🕒 Время ответа: обычно в течение нескольких часов"""
            await self.send_message(chat_id, support_message)
            
        elif command.startswith("/settings"):
            settings_summary = self.user_settings.get_settings_summary(user_id)
            keyboard = self.user_settings.get_settings_keyboard(user_id)
            await self.send_message_with_keyboard(chat_id, settings_summary, keyboard)
            
        elif command.startswith("/check_sources"):
            # Проверяем, является ли пользователь администратором
            if user_id != self.monitoring_controller.get_admin_user_id():
                await self.send_message(chat_id, "🤖 Неизвестная команда. Используйте /help для справки.")
                return
                
            await self.send_message(chat_id, "🔍 Проверяю источники данных...")
            
            # Проверяем все источники
            await self.data_sources.check_all_sources()
            
            # Отправляем сводку
            summary = self.data_sources.get_status_summary()
            await self.send_message(chat_id, summary)
            
            # Предлагаем перезапуск для проблемных источников
            for source_key, source in self.data_sources.sources.items():
                if source["status"] in ["blocked", "error", "unreachable"]:
                    keyboard = self.data_sources.get_restart_keyboard(source_key)
                    restart_message = f"🔄 Перезапустить {source['name']}?"
                    await self.send_message_with_keyboard(chat_id, restart_message, keyboard)
            
        elif command.startswith("/subscribe"):
            if user_id in self.subscribers:
                await self.send_message(chat_id, "✅ Вы уже подписаны на уведомления")
            else:
                self.subscribers.add(user_id)
                await self.send_message(chat_id, "🔔 Вы успешно подписались на уведомления!")
                
        elif command.startswith("/unsubscribe"):
            if user_id in self.subscribers:
                self.subscribers.remove(user_id)
                await self.send_message(chat_id, "🔕 Вы отписались от уведомлений")
            else:
                await self.send_message(chat_id, "❌ Вы не были подписаны на уведомления")
        # Обработка сообщений поддержки
        elif not command.startswith("/") and user_id not in self.subscribers:
            # Если это сообщение поддержки (не команда и пользователь не подписан)
            await self.handle_support_message(chat_id, user_id, command)
        else:
            await self.send_message(chat_id, "🤖 Неизвестная команда. Используйте /help для справки.")
            
    async def handle_callback_query(self, callback_query: Dict):
        """Обработка callback query от inline-клавиатур"""
        callback_data = callback_query.get("data", "")
        user_id = callback_query["from"]["id"]
        chat_id = callback_query["message"]["chat"]["id"]
        callback_query_id = callback_query["id"]
        
        if callback_data == "start_when_open":
            self.monitoring_controller.add_pending_market_open_user(user_id)
            await self.answer_callback_query(callback_query_id, "Мониторинг запустится при открытии биржи")
            await self.send_message(chat_id, "✅ Отлично! Мониторинг автоматически запустится когда откроется биржа")
            
        elif callback_data == "cancel_monitoring":
            await self.answer_callback_query(callback_query_id, "Мониторинг отменен")
            await self.send_message(chat_id, "❌ Мониторинг отменен. Используйте /start_monitoring когда будете готовы")
            
        elif callback_data.startswith("restart_"):
            source_key = callback_data.replace("restart_", "")
            success = self.data_sources.restart_source(source_key)
            if success:
                source_name = self.data_sources.sources[source_key]["name"]
                await self.answer_callback_query(callback_query_id, f"Перезапуск {source_name}")
                await self.send_message(chat_id, f"🔄 {source_name} перезапущен. Выполняю повторную проверку...")
                
                # Проверяем источник повторно
                status = await self.data_sources.check_source_status(source_key)
                if status == "working":
                    await self.send_message(chat_id, f"✅ {source_name} теперь работает!")
                else:
                    await self.send_message(chat_id, f"❌ {source_name} всё ещё недоступен")
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка перезапуска")
                
        elif callback_data.startswith("cancel_restart_"):
            source_key = callback_data.replace("cancel_restart_", "")
            source_name = self.data_sources.sources[source_key]["name"]
            await self.answer_callback_query(callback_query_id, f"Отмена для {source_name}")
            await self.send_message(chat_id, f"❌ Перезапуск {source_name} отменен")
            
        # Обработка настроек пользователя
        elif callback_data == "settings_back":
            settings_summary = self.user_settings.get_settings_summary(user_id)
            keyboard = self.user_settings.get_settings_keyboard(user_id)
            await self.edit_message_with_keyboard(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            await self.answer_callback_query(callback_query_id, "Настройки")
            
        elif callback_data == "settings_interval":
            keyboard = self.user_settings.get_interval_keyboard()
            message = "⏱️ Выберите интервал мониторинга:\n\n⚠️ Внимание: интервалы менее 5 минут используют ротацию источников данных для избежания блокировок"
            await self.edit_message_with_keyboard(chat_id, callback_query["message"]["message_id"], message, keyboard)
            await self.answer_callback_query(callback_query_id, "Интервал")
            
        elif callback_data == "settings_spread":
            keyboard = self.user_settings.get_spread_keyboard()
            message = "📊 Выберите минимальный порог спреда для уведомлений:"
            await self.edit_message_with_keyboard(chat_id, callback_query["message"]["message_id"], message, keyboard)
            await self.answer_callback_query(callback_query_id, "Спред")
            
        elif callback_data.startswith("interval_"):
            interval = int(callback_data.replace("interval_", ""))
            if self.user_settings.update_monitoring_interval(user_id, interval):
                settings = self.user_settings.get_user_settings(user_id)
                await self.answer_callback_query(callback_query_id, f"Интервал: {settings.get_interval_display()}")
                
                # Возвращаемся к главному меню настроек
                settings_summary = self.user_settings.get_settings_summary(user_id)
                keyboard = self.user_settings.get_settings_keyboard(user_id)
                await self.edit_message_with_keyboard(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка обновления")
                
        elif callback_data.startswith("spread_"):
            spread = float(callback_data.replace("spread_", ""))
            if self.user_settings.update_spread_threshold(user_id, spread):
                settings = self.user_settings.get_user_settings(user_id)
                await self.answer_callback_query(callback_query_id, f"Спред: {settings.get_spread_display()}")
                
                # Возвращаемся к главному меню настроек
                settings_summary = self.user_settings.get_settings_summary(user_id)
                keyboard = self.user_settings.get_settings_keyboard(user_id)
                await self.edit_message_with_keyboard(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка обновления")
            
    async def handle_support_message(self, chat_id: int, user_id: int, message: str):
        """Обработка сообщений поддержки"""
        # Отправляем сообщение администратору, если он установлен
        admin_id = self.monitoring_controller.get_admin_user_id()
        if admin_id:
            support_notification = f"""📩 *СООБЩЕНИЕ ПОДДЕРЖКИ*

👤 От пользователя: {user_id}
💬 Сообщение: {message}

Ответьте на это сообщение, чтобы ответить пользователю"""
            await self.send_message(admin_id, support_notification)
            
        # Подтверждаем получение пользователю
        await self.send_message(chat_id, "📩 Ваше сообщение отправлено в техподдержку. Мы ответим в ближайшее время!")
        
    async def notify_admin_error(self, error_message: str):
        """Уведомление администратора об ошибке"""
        admin_id = self.monitoring_controller.get_admin_user_id()
        if admin_id:
            error_notification = f"""🚨 *ОШИБКА БОТА*

⚠️ {error_message}

⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""
            await self.send_message(admin_id, error_notification)
    
    async def send_arbitrage_signal(self, signal):
        """Отправка арбитражного сигнала подписчикам"""
        if signal.action == "OPEN":
            emoji = "🟢🟢" if signal.urgency_level == 3 else "🟢" if signal.urgency_level == 2 else "📈"
            
            message = f"{emoji} *АРБИТРАЖ СИГНАЛ*\n\n"
            message += f"🎯 *{signal.stock_ticker}/{signal.futures_ticker}*\n"
            message += f"📊 Спред: *{signal.spread_percent:.2f}%*\n\n"
            message += f"💼 *Позиции:*\n"
            message += f"📈 Акции {signal.stock_ticker}: *{signal.stock_position}* {signal.stock_lots} лотов\n"
            message += f"📊 Фьючерс {signal.futures_ticker}: *{signal.futures_position}* {signal.futures_lots} лотов\n\n"
            message += f"💰 *Цены:*\n"
            message += f"📈 {signal.stock_ticker}: {signal.stock_price:.2f} ₽\n"
            message += f"📊 {signal.futures_ticker}: {signal.futures_price:.2f} ₽\n\n"
            

            
            message += f"⏰ Время: {signal.timestamp}"
            
        else:  # CLOSE
            message = "🔄 *СИГНАЛ НА ЗАКРЫТИЕ*\n\n"
            message += f"👋 Дружище, пора закрывать позицию по *{signal.stock_ticker}/{signal.futures_ticker}*!\n\n"
            message += f"📉 Спред снизился до: *{signal.spread_percent:.2f}%*\n\n"
            message += f"⏰ Время: {signal.timestamp}"
        
        # Отправляем подписчикам с учетом их персональных настроек
        failed_subscribers = []
        for subscriber_id in self.subscribers.copy():
            user_settings = self.user_settings.get_user_settings(subscriber_id)
            # Проверяем порог спреда пользователя
            if signal.spread_percent >= user_settings.spread_threshold:
                success = await self.send_message(subscriber_id, message)
                if not success:
                    failed_subscribers.append(subscriber_id)
        
        # Удаляем неактивных подписчиков
        for failed_id in failed_subscribers:
            self.subscribers.discard(failed_id)
    
    async def monitoring_cycle(self):
        """Цикл мониторинга арбитражных возможностей"""
        logger.info("Начало цикла мониторинга...")
        
        try:
            async with MOEXAPIClient() as moex_client:
                quotes = await moex_client.get_multiple_quotes(self.config.MONITORED_INSTRUMENTS)
            
            if not quotes:
                logger.warning("Не удалось получить котировки")
                return
            
            current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
            signals = []
            
            for stock_ticker, (stock_price, futures_price) in quotes.items():
                if stock_price is None or futures_price is None:
                    continue
                
                futures_ticker = self.config.MONITORED_INSTRUMENTS[stock_ticker]
                signal = self.calculator.analyze_arbitrage_opportunity(
                    stock_ticker=stock_ticker,
                    futures_ticker=futures_ticker,
                    stock_price=stock_price,
                    futures_price=futures_price,
                    timestamp=current_time
                )
                
                if signal:
                    signals.append(signal)
                    
                    # Добавляем в историю спредов
                    self.spread_history.add_record(
                        stock_ticker=signal.stock_ticker,
                        futures_ticker=signal.futures_ticker,
                        spread=signal.spread_percent,
                        signal_type=signal.action
                    )
                    
                    if signal.action == "OPEN":
                        self.calculator.register_position(signal)
                    elif signal.action == "CLOSE":
                        self.calculator.close_position(signal)
            
            # Отправляем сигналы
            for signal in signals:
                await self.send_arbitrage_signal(signal)
            
            logger.info(f"Цикл мониторинга завершен. Найдено сигналов: {len(signals)}")
            
        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {e}")
    
    async def run(self):
        """Основной цикл работы бота"""
        logger.info("Запуск Telegram бота...")
        
        # Проверяем источники данных при запуске
        logger.info("Проверка источников данных...")
        sources_status = await self.data_sources.check_all_sources()
        
        for source_key, status in sources_status.items():
            source_name = self.data_sources.sources[source_key]["name"]
            if status == "working":
                logger.info(f"✅ {source_name}: работает успешно")
            elif status == "blocked":
                logger.warning(f"🚫 {source_name}: заблокирован")
            elif status == "error":
                logger.error(f"❌ {source_name}: ошибка подключения")
            elif status == "unreachable":
                logger.warning(f"📡 {source_name}: недоступен")
            else:
                logger.info(f"❓ {source_name}: не проверен")
        
        working_sources = [key for key, status in sources_status.items() if status == "working"]
        logger.info(f"Активных источников: {len(working_sources)}/{len(sources_status)}")
        
        # Планируем мониторинг
        async def monitoring_task():
            while True:
                # Проверяем, нужно ли запускать мониторинг
                if not self.monitoring_controller.should_run_global_monitoring():
                    await asyncio.sleep(60)  # Проверяем каждую минуту без логирования
                    continue
                
                # Проверяем, открыта ли биржа
                if not self.config.is_market_open():
                    # Проверяем пользователей, ожидающих открытия
                    pending_users = self.monitoring_controller.get_pending_market_open_users()
                    if pending_users:
                        logger.info(f"Биржа закрыта. {len(pending_users)} пользователей ожидают открытия...")
                    
                    await asyncio.sleep(300)  # Проверяем каждые 5 минут
                    continue
                
                # Биржа открылась - уведомляем ожидающих пользователей
                pending_users = self.monitoring_controller.get_pending_market_open_users()
                for user_id in pending_users:
                    self.monitoring_controller.start_monitoring_for_user(user_id)
                    self.monitoring_controller.remove_pending_market_open_user(user_id)
                    await self.send_message(user_id, "🟢 Биржа открылась! Мониторинг запущен")
                
                # Очищаем уведомления о закрытой бирже
                self.monitoring_controller.clear_market_closed_notifications()
                
                try:
                    await self.monitoring_cycle()
                except Exception as e:
                    error_msg = f"Ошибка в цикле мониторинга: {e}"
                    logger.error(error_msg)
                    await self.notify_admin_error(error_msg)
                    
                # Рандомизированный интервал между 5-7 минутами
                interval = self.config.get_random_monitoring_interval()
                logger.info(f"Следующая проверка через {interval // 60} мин {interval % 60} сек")
                await asyncio.sleep(interval)
        
        # Запускаем мониторинг в фоне
        monitor_task = asyncio.create_task(monitoring_task())
        
        # Основной цикл обработки сообщений
        try:
            while True:
                updates = await self.get_updates()
                
                for update in updates:
                    if update.message:
                        chat_id = update.message["chat"]["id"]
                        user_id = update.message["from"]["id"]
                        text = update.message.get("text", "")
                        
                        # Устанавливаем админа при первом сообщении от него
                        username = update.message["from"].get("username", "")
                        if username == "Ildaryakupovv" and not self.monitoring_controller.get_admin_user_id():
                            self.monitoring_controller.set_admin_user_id(user_id)
                            logger.info(f"Администратор установлен: {user_id}")
                        
                        if text.startswith("/"):
                            await self.handle_command(chat_id, text, user_id)
                        else:
                            # Обработка обычных сообщений
                            await self.send_message(chat_id, "🤖 Я понимаю только команды. Используйте /help для получения списка доступных команд.")
                            
                    elif update.callback_query:
                        await self.handle_callback_query(update.callback_query)
                
                await asyncio.sleep(1)  # Небольшая пауза между запросами
                
        except Exception as e:
            logger.error(f"Ошибка в главном цикле бота: {e}")
            await self.notify_admin_error(f"Критическая ошибка в главном цикле бота: {e}")
        except KeyboardInterrupt:
            logger.info("Остановка бота...")
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
            
    def get_tradingview_link(self, ticker: str) -> str:
        """Получение ссылки на TradingView для инструмента"""
        # Маппинг российских тикеров для TradingView
        tv_mapping = {
            "SBER": "MOEX:SBER",
            "GAZP": "MOEX:GAZP", 
            "LKOH": "MOEX:LKOH",
            "VTBR": "MOEX:VTBR",
            "YNDX": "NASDAQ:YNDX",
            "TCSG": "MOEX:TCSG",
            "ROSN": "MOEX:ROSN",
            "GMKN": "MOEX:GMKN",
            "PLZL": "MOEX:PLZL",
            "MGNT": "MOEX:MGNT",
            "SNGS": "MOEX:SNGS",
            "ALRS": "MOEX:ALRS",
            "TATN": "MOEX:TATN",
            "MTSS": "MOEX:MTSS"
        }
        
        tv_symbol = tv_mapping.get(ticker, f"MOEX:{ticker}")
        return f"https://www.tradingview.com/chart/?symbol={tv_symbol}"

async def main():
    """Точка входа"""
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Получаем токен
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        logger.info("Пожалуйста, установите токен вашего бота через переменные окружения")
        return
    
    # Запускаем бота
    async with SimpleTelegramBot(token) as bot:
        await bot.run()

if __name__ == "__main__":
    asyncio.run(main())