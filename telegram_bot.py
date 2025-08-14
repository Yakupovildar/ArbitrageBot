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
import pytz
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from config import Config
from moex_api import MOEXAPIClient
from arbitrage_calculator import ArbitrageCalculator
from monitoring_controller import MonitoringController
from data_sources import DataSourceManager
from user_settings import UserSettingsManager
from signal_queue import SignalQueue, UserMonitoringScheduler
from source_reconnector import SourceReconnector
from database import db
from sources_library import sources_library
from daily_validator import DailyValidator

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
        self.signal_queue = SignalQueue(max_signals_per_batch=3, signal_interval=3.0)
        self.monitoring_scheduler = UserMonitoringScheduler()
        
        # Автопереподключение к источникам
        self.source_reconnector = None
        
        # Система ежедневной валидации торговых пар
        self.daily_validator = DailyValidator()
        self.last_pair_validation = None
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер"""
        self.session = aiohttp.ClientSession()
        
        # Инициализация базы данных
        self.db = db  # Сохраняем ссылку на объект базы данных
        await db.init_connection()
        
        # Инициализация библиотеки источников (поиск лучших 10 источников)
        logger.info("🔍 Инициализация активных источников данных...")
        active_sources = await sources_library.initialize_active_sources(10)
        
        # Синхронизируем старую систему data_sources с новой библиотекой
        logger.info("🔄 Синхронизация системы источников данных...")
        self.data_sources.sync_with_library(sources_library)
        
        # Загрузка сохраненных настроек пользователей
        await self._restore_user_settings()
        
        # Запуск автопереподключения с интеграцией библиотеки источников
        self.source_reconnector = SourceReconnector(self.data_sources, self.config, sources_library)
        await self.source_reconnector.start()
        
        # Запуск ежедневной валидации пар (проверяется каждые 24 часа)
        asyncio.create_task(self.daily_validation_task())
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии"""
        # Сохранение настроек в базу
        await self._save_all_user_settings()
        
        # Остановка автопереподключения
        if self.source_reconnector:
            await self.source_reconnector.stop()
        
        # Закрытие базы данных
        await db.close_connection()
        
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
    
    async def edit_message_text(self, chat_id: int, message_id: int, text: str, keyboard: dict) -> bool:
        """Редактирование текста сообщения с inline-клавиатурой"""
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
            logger.error(f"Ошибка при редактировании текста сообщения: {e}")
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
            welcome_text = """🤖 *Добро пожаловать в бота арбитража MOEX!*

Я помогаю отслеживать арбитражные возможности между акциями и фьючерсами на Московской бирже.

🎯 *Основные функции:*
• Умный мониторинг с персональными настройками
• Уведомления о прибыльных сигналах  
• Гибкие интервалы и пороги спредов
• История и статистика

✨ *Используйте кнопки ниже для управления:*"""
            
            # Главное меню с кнопками
            main_menu_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🟢 Запустить мониторинг", "callback_data": "cmd_start_monitoring"},
                        {"text": "🔴 Остановить мониторинг", "callback_data": "cmd_stop_monitoring"}
                    ],
                    [
                        {"text": "⚙️ Настройки", "callback_data": "cmd_settings"},
                        {"text": "📊 Статус", "callback_data": "cmd_status"}
                    ],
                    [
                        {"text": "📈 История", "callback_data": "cmd_history"},
                        {"text": "🕒 Расписание", "callback_data": "cmd_schedule"}
                    ],
                    [
                        {"text": "🎯 Демо", "callback_data": "cmd_demo"},
                        {"text": "🆘 Поддержка", "callback_data": "cmd_support"}
                    ],
                    [
                        {"text": "📋 Главное меню", "callback_data": "show_main_menu"}
                    ]
                ]
            }
            
            await self.send_message_with_keyboard(chat_id, welcome_text, main_menu_keyboard)
            
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
/pairs - Список торговых пар для арбитража
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
            
            # Добавляем пользователя в планировщик мониторинга
            user_settings = self.user_settings.get_user_settings(user_id)
            self.monitoring_scheduler.add_user_to_group(user_id, user_settings.monitoring_interval)
            
            await self.send_message(chat_id, f"🟢 Мониторинг запущен! Интервал: {user_settings.get_interval_display()}, порог: {user_settings.get_spread_display()}")
            
        elif command.startswith("/stop_monitoring"):
            if not self.monitoring_controller.is_user_monitoring(user_id):
                await self.send_message(chat_id, "ℹ️ Мониторинг не запущен")
                return
                
            self.monitoring_controller.stop_monitoring_for_user(user_id)
            self.monitoring_scheduler.remove_user(user_id)
            await self.send_message(chat_id, "🔴 Мониторинг остановлен")
            
        elif command.startswith("/test"):
            # Запускаем тестовый мониторинг спредов
            if hasattr(self, 'test_monitoring_active') and self.test_monitoring_active.get(user_id, False):
                await self.send_message(chat_id, "🔴 Тестовый мониторинг остановлен")
                self.test_monitoring_active[user_id] = False
                return
            
            if not hasattr(self, 'test_monitoring_active'):
                self.test_monitoring_active = {}
            
            self.test_monitoring_active[user_id] = True
            await self.send_message(chat_id, "🧪 Запущен тестовый мониторинг спредов голубых фишек каждые 2 минуты\n💬 Для остановки: /test")
            
            # Запускаем асинхронную задачу тестового мониторинга
            asyncio.create_task(self._test_monitoring_task(user_id))
        

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

🔧 *Техническая информация:*
• /reconnect_stats - статистика источников данных
• /sources_info - информация об активных источниках

🕒 Время ответа: обычно в течение нескольких часов"""
            await self.send_message(chat_id, support_message)
            

            
        elif command.startswith("/reconnect_stats"):
            if self.source_reconnector and sources_library:
                # Статистика переподключения
                reconnect_stats = await self.source_reconnector.get_reconnect_stats()
                
                # Статистика библиотеки источников
                library_stats = sources_library.get_library_stats()
                
                message = f"""📊 Статистика источников данных:

📚 **Библиотека источников:**
🔗 Всего в библиотеке: {library_stats['total_sources']}
✅ Активных: {library_stats['active_sources']}
📈 Средняя надежность: {library_stats['average_reliability']}%
🔄 Замен выполнено: {library_stats['replacement_count']}

🔧 **Текущее состояние:**
✅ Работает: {reconnect_stats['working_sources']}
❌ Неисправно: {reconnect_stats['failed_sources']}

⏰ Последняя проверка: {reconnect_stats['last_check']}
🔄 Следующая через: {reconnect_stats['next_check_in']}

🔄 Автопереподключение каждые 30 минут во время торгов
🔀 Автозамена после 3 неудачных попыток (90 минут)

ℹ️ Система автоматически заменяет неисправные источники на рабочие из библиотеки"""
            else:
                message = "❌ Система переподключения недоступна"
                
            await self.send_message(chat_id, message)
            
        elif command.startswith("/sources_info"):
            if sources_library:
                active_sources = sources_library.get_active_sources_info()
                
                message = "📋 **Активные источники данных:**\n\n"
                
                for i, source in enumerate(active_sources, 1):
                    message += f"{i}. **{source['name']}**\n"
                    message += f"   📊 Надежность: {source['reliability']}%\n"
                    message += f"   🔒 Авторизация: {'Требуется' if source['requires_auth'] else 'Не требуется'}\n"
                    message += f"   📝 {source['description']}\n\n"
                
                message += "💡 Используйте /reconnect_stats для общей статистики"
            else:
                message = "❌ Библиотека источников недоступна"
                
            await self.send_message(chat_id, message)
            
        elif command.startswith("/settings"):
            settings_summary = self.user_settings.get_settings_summary(user_id)
            keyboard = self.user_settings.get_settings_keyboard(user_id)
            await self.send_message_with_keyboard(chat_id, settings_summary, keyboard)
            
        elif command.startswith("/menu"):
            welcome_text = """🤖 *MOEX Arbitrage Bot - Главное меню*

🎯 *Быстрое управление ботом:*"""
            
            main_menu_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🟢 Запустить мониторинг", "callback_data": "cmd_start_monitoring"},
                        {"text": "🔴 Остановить мониторинг", "callback_data": "cmd_stop_monitoring"}
                    ],
                    [
                        {"text": "⚙️ Настройки", "callback_data": "cmd_settings"},
                        {"text": "📊 Статус", "callback_data": "cmd_status"}
                    ],
                    [
                        {"text": "📈 История", "callback_data": "cmd_history"},
                        {"text": "🕒 Расписание", "callback_data": "cmd_schedule"}
                    ],
                    [
                        {"text": "🎯 Демо", "callback_data": "cmd_demo"},
                        {"text": "🆘 Поддержка", "callback_data": "cmd_support"}
                    ]
                ]
            }
            
            await self.send_message_with_keyboard(chat_id, welcome_text, main_menu_keyboard)
            
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
            # Возвращаемся к главному меню
            welcome_text = """🤖 *MOEX Arbitrage Bot - Главное меню*

🎯 *Быстрое управление ботом:*"""
            
            main_menu_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🟢 Запустить мониторинг", "callback_data": "cmd_start_monitoring"},
                        {"text": "🔴 Остановить мониторинг", "callback_data": "cmd_stop_monitoring"}
                    ],
                    [
                        {"text": "⚙️ Настройки", "callback_data": "cmd_settings"},
                        {"text": "📊 Статус", "callback_data": "cmd_status"}
                    ],
                    [
                        {"text": "📈 История", "callback_data": "cmd_history"},
                        {"text": "🕒 Расписание", "callback_data": "cmd_schedule"}
                    ],
                    [
                        {"text": "🎯 Демо", "callback_data": "cmd_demo"},
                        {"text": "🆘 Поддержка", "callback_data": "cmd_support"}
                    ]
                ]
            }
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], welcome_text, main_menu_keyboard)
            await self.answer_callback_query(callback_query_id, "Главное меню")
            
        elif callback_data == "settings_interval":
            keyboard = self.user_settings.get_interval_keyboard()
            message = "⏱️ Выберите интервал мониторинга:\n\n⚠️ Внимание: интервалы менее 5 минут используют ротацию источников данных для избежания блокировок"
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], message, keyboard)
            await self.answer_callback_query(callback_query_id, "Интервал")
            
        elif callback_data == "settings_spread":
            keyboard = self.user_settings.get_spread_keyboard()
            message = "📊 Выберите минимальный порог спреда для уведомлений:"
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], message, keyboard)
            await self.answer_callback_query(callback_query_id, "Спред")
            
        elif callback_data == "settings_signals":
            keyboard = self.user_settings.get_signals_keyboard()
            message = "🔢 Выберите максимальное количество сигналов за один раз:\n\n⏱️ Интервал между сигналами: 3 секунды"
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], message, keyboard)
            await self.answer_callback_query(callback_query_id, "Количество сигналов")
            
        elif callback_data.startswith("interval_"):
            interval = int(callback_data.replace("interval_", ""))
            if self.user_settings.update_monitoring_interval(user_id, interval):
                settings = self.user_settings.get_user_settings(user_id)
                await self.answer_callback_query(callback_query_id, f"Интервал: {settings.get_interval_display()}")
                
                # Обновляем планировщик, если пользователь активен
                if self.monitoring_controller.is_user_monitoring(user_id):
                    self.monitoring_scheduler.add_user_to_group(user_id, settings.monitoring_interval)
                
                # Сохраняем в базу данных
                await self._save_user_settings_to_db(user_id)
                
                # Возвращаемся к главному меню настроек
                settings_summary = self.user_settings.get_settings_summary(user_id)
                keyboard = self.user_settings.get_settings_keyboard(user_id)
                await self.edit_message_text(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка обновления")
                
        elif callback_data.startswith("spread_"):
            spread = float(callback_data.replace("spread_", ""))
            if self.user_settings.update_spread_threshold(user_id, spread):
                settings = self.user_settings.get_user_settings(user_id)
                await self.answer_callback_query(callback_query_id, f"Спред: {settings.get_spread_display()}")
                
                # Сохраняем в базу данных
                await self._save_user_settings_to_db(user_id)
                
                # Возвращаемся к главному меню настроек
                settings_summary = self.user_settings.get_settings_summary(user_id)
                keyboard = self.user_settings.get_settings_keyboard(user_id)
                await self.edit_message_text(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка обновления")
                
        elif callback_data.startswith("signals_"):
            max_signals = int(callback_data.replace("signals_", ""))
            if self.user_settings.update_max_signals(user_id, max_signals):
                settings = self.user_settings.get_user_settings(user_id)
                await self.answer_callback_query(callback_query_id, f"Сигналов: {settings.max_signals}")
                
                # Обновляем лимит в очереди сигналов
                user_max_signals = settings.max_signals
                self.signal_queue.max_signals_per_batch = user_max_signals
                
                # Сохраняем в базу данных
                await self._save_user_settings_to_db(user_id)
                
                # Возвращаемся к главному меню настроек
                settings_summary = self.user_settings.get_settings_summary(user_id)
                keyboard = self.user_settings.get_settings_keyboard(user_id)
                await self.edit_message_text(chat_id, callback_query["message"]["message_id"], settings_summary, keyboard)
            else:
                await self.answer_callback_query(callback_query_id, "Ошибка обновления")
                
        # Обработка команд через кнопки
        elif callback_data == "show_main_menu":
            welcome_text = """🤖 *MOEX Arbitrage Bot - Главное меню*

🎯 *Быстрое управление ботом:*"""
            
            main_menu_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🟢 Запустить мониторинг", "callback_data": "cmd_start_monitoring"},
                        {"text": "🔴 Остановить мониторинг", "callback_data": "cmd_stop_monitoring"}
                    ],
                    [
                        {"text": "⚙️ Настройки", "callback_data": "cmd_settings"},
                        {"text": "📊 Статус", "callback_data": "cmd_status"}
                    ],
                    [
                        {"text": "📈 История", "callback_data": "cmd_history"},
                        {"text": "🕒 Расписание", "callback_data": "cmd_schedule"}
                    ],
                    [
                        {"text": "🎯 Демо", "callback_data": "cmd_demo"},
                        {"text": "🆘 Поддержка", "callback_data": "cmd_support"}
                    ]
                ]
            }
            
            await self.send_message_with_keyboard(chat_id, welcome_text, main_menu_keyboard)
            await self.answer_callback_query(callback_query_id, "Главное меню")
            
        elif callback_data == "cmd_settings":
            settings_summary = self.user_settings.get_settings_summary(user_id)
            keyboard = self.user_settings.get_settings_keyboard(user_id)
            await self.send_message_with_keyboard(chat_id, settings_summary, keyboard)
            await self.answer_callback_query(callback_query_id, "Настройки")
            
        elif callback_data == "cmd_start_monitoring":
            await self.handle_command(chat_id, "/start_monitoring", user_id)
            await self.answer_callback_query(callback_query_id, "Запуск мониторинга")
            
        elif callback_data == "cmd_stop_monitoring":
            await self.handle_command(chat_id, "/stop_monitoring", user_id)
            await self.answer_callback_query(callback_query_id, "Остановка мониторинга")
            
        elif callback_data == "cmd_status":
            await self.handle_command(chat_id, "/status", user_id)
            await self.answer_callback_query(callback_query_id, "Статус")
            
        elif callback_data == "cmd_history":
            await self.handle_command(chat_id, "/history", user_id)
            await self.answer_callback_query(callback_query_id, "История")
            
        elif callback_data == "cmd_schedule":
            await self.handle_command(chat_id, "/schedule", user_id)
            await self.answer_callback_query(callback_query_id, "Расписание")
            
        elif callback_data == "cmd_demo":
            await self.handle_command(chat_id, "/demo", user_id)
            await self.answer_callback_query(callback_query_id, "Демо")
            
        elif callback_data == "cmd_support":
            await self.handle_command(chat_id, "/support", user_id)
            await self.answer_callback_query(callback_query_id, "Поддержка")
            
        # Обработчики для настройки инструментов
        elif callback_data == "settings_instruments":
            keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
            instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

🎯 *Всего доступно: {len(self.config.MONITORED_INSTRUMENTS)} торговых пар*

📊 *Разбивка по секторам:*
Выберите сектор для просмотра инструментов

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться  
• Снижает нагрузку на систему"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
            await self.answer_callback_query(callback_query_id, "Выбор инструментов")
            
        elif callback_data.startswith("instrument_add_"):
            # Формат: instrument_add_{sector_hash}_{instrument}
            parts = callback_data.replace("instrument_add_", "").split("_", 1)
            if len(parts) == 2:
                sector_hash, instrument = parts
                sector_hash = int(sector_hash)
                sector_name = self.user_settings.get_sector_name_by_hash(sector_hash, self.config.MONITORED_INSTRUMENTS)
                
                success = self.user_settings.add_user_instrument(user_id, instrument)
                
                if success:
                    # Сохраняем в базу
                    await self._save_user_settings_to_db(user_id)
                    
                    # Остаемся в том же секторе - обновляем клавиатуру сектора
                    keyboard = self.user_settings.get_sector_instruments_keyboard(user_id, sector_name, self.config.MONITORED_INSTRUMENTS)
                    sector_text = f"""📊 *{sector_name}*

Выберите инструменты для мониторинга:

✅ = выбрано, ⭕ = не выбрано
Лимит: максимум 10 пар на пользователя"""
                    
                    await self.edit_message_text(chat_id, callback_query["message"]["message_id"], sector_text, keyboard)
                    await self.answer_callback_query(callback_query_id, f"✅ {instrument} добавлен")
                else:
                    await self.answer_callback_query(callback_query_id, "❌ Максимум 10 инструментов")
            else:
                # Старый формат - вернуться к общему списку
                instrument = callback_data.replace("instrument_add_", "")
                success = self.user_settings.add_user_instrument(user_id, instrument)
                
                if success:
                    await self._save_user_settings_to_db(user_id)
                    keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
                    instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться
• Снижает нагрузку на систему

✅ = выбрано, ⭕ = не выбрано"""
                    
                    await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
                    await self.answer_callback_query(callback_query_id, f"✅ {instrument} добавлен")
                else:
                    await self.answer_callback_query(callback_query_id, "❌ Максимум 10 инструментов")
                
        elif callback_data.startswith("instrument_remove_"):
            # Формат: instrument_remove_{sector_hash}_{instrument}
            parts = callback_data.replace("instrument_remove_", "").split("_", 1)
            if len(parts) == 2:
                sector_hash, instrument = parts
                sector_hash = int(sector_hash)
                sector_name = self.user_settings.get_sector_name_by_hash(sector_hash, self.config.MONITORED_INSTRUMENTS)
                
                success = self.user_settings.remove_user_instrument(user_id, instrument)
                
                if success:
                    # Сохраняем в базу
                    await self._save_user_settings_to_db(user_id)
                    
                    # Остаемся в том же секторе - обновляем клавиатуру сектора
                    keyboard = self.user_settings.get_sector_instruments_keyboard(user_id, sector_name, self.config.MONITORED_INSTRUMENTS)
                    sector_text = f"""📊 *{sector_name}*

Выберите инструменты для мониторинга:

✅ = выбрано, ⭕ = не выбрано
Лимит: максимум 10 пар на пользователя"""
                    
                    await self.edit_message_text(chat_id, callback_query["message"]["message_id"], sector_text, keyboard)
                    await self.answer_callback_query(callback_query_id, f"❌ {instrument} удален")
                else:
                    await self.answer_callback_query(callback_query_id, "Ошибка удаления")
            else:
                # Старый формат
                instrument = callback_data.replace("instrument_remove_", "")
                success = self.user_settings.remove_user_instrument(user_id, instrument)
                
                if success:
                    await self._save_user_settings_to_db(user_id)
                    keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
                    instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться
• Снижает нагрузку на систему

✅ = выбрано, ⭕ = не выбрано"""
                    
                    await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
                    await self.answer_callback_query(callback_query_id, f"❌ {instrument} удален")
                else:
                    await self.answer_callback_query(callback_query_id, "Ошибка удаления")
                
        elif callback_data == "instruments_clear":
            self.user_settings.clear_user_instruments(user_id)
            await self._save_user_settings_to_db(user_id)
            
            # Обновляем клавиатуру
            keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
            instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться
• Снижает нагрузку на систему

✅ = выбрано, ⭕ = не выбрано"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
            await self.answer_callback_query(callback_query_id, "🔄 Выбор очищен")
            
        elif callback_data == "instruments_default":
            self.user_settings.set_default_instruments(user_id, self.config.MONITORED_INSTRUMENTS)
            await self._save_user_settings_to_db(user_id)
            
            # Обновляем клавиатуру
            keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
            instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться
• Снижает нагрузку на систему

✅ = выбрано, ⭕ = не выбрано"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
            await self.answer_callback_query(callback_query_id, "🎯 Выбраны по умолчанию")
            
        # Обработчики для выбора секторов
        elif callback_data.startswith("sector_"):
            sector_hash = int(callback_data.replace("sector_", ""))
            sector_name = self.user_settings.get_sector_name_by_hash(sector_hash, self.config.MONITORED_INSTRUMENTS)
            
            keyboard = self.user_settings.get_sector_instruments_keyboard(user_id, sector_name, self.config.MONITORED_INSTRUMENTS)
            sector_text = f"""📊 *{sector_name}*

Выберите инструменты для мониторинга:

✅ = выбрано, ⭕ = не выбрано
Лимит: максимум 10 пар на пользователя"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], sector_text, keyboard)
            await self.answer_callback_query(callback_query_id, f"Сектор: {sector_name}")
            
        elif callback_data == "instruments_back_to_sectors":
            keyboard = self.user_settings.get_instruments_keyboard(user_id, self.config.MONITORED_INSTRUMENTS)
            instruments_text = f"""📈 *Выберите торговые пары для мониторинга*

🎯 *Всего доступно: {len(self.config.MONITORED_INSTRUMENTS)} торговых пар*

📊 *Разбивка по секторам:*
Выберите сектор для просмотра инструментов

⚠️ *Ограничения:*
• Максимум 10 пар на пользователя
• Только выбранные пары будут мониториться  
• Снижает нагрузку на систему"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], instruments_text, keyboard)
            await self.answer_callback_query(callback_query_id, "К секторам")
            
        elif callback_data.startswith("sector_select_all_"):
            sector_hash = int(callback_data.replace("sector_select_all_", ""))
            sector_name = self.user_settings.get_sector_name_by_hash(sector_hash, self.config.MONITORED_INSTRUMENTS)
            
            # Добавляем все инструменты сектора (с учетом лимита)
            sectors = self.user_settings._group_instruments_by_sectors(self.config.MONITORED_INSTRUMENTS)
            sector_instruments = sectors.get(sector_name, {})
            
            added_count = 0
            for stock in sector_instruments.keys():
                if self.user_settings.add_user_instrument(user_id, stock):
                    added_count += 1
            
            if added_count > 0:
                await self._save_user_settings_to_db(user_id)
            
            # Обновляем клавиатуру
            keyboard = self.user_settings.get_sector_instruments_keyboard(user_id, sector_name, self.config.MONITORED_INSTRUMENTS)
            sector_text = f"""📊 *{sector_name}*

Выберите инструменты для мониторинга:

✅ = выбрано, ⭕ = не выбрано
Лимит: максимум 10 пар на пользователя"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], sector_text, keyboard)
            await self.answer_callback_query(callback_query_id, f"✅ Добавлено: {added_count}")
            
        elif callback_data.startswith("sector_clear_all_"):
            sector_hash = int(callback_data.replace("sector_clear_all_", ""))
            sector_name = self.user_settings.get_sector_name_by_hash(sector_hash, self.config.MONITORED_INSTRUMENTS)
            
            # Удаляем все инструменты сектора
            sectors = self.user_settings._group_instruments_by_sectors(self.config.MONITORED_INSTRUMENTS)
            sector_instruments = sectors.get(sector_name, {})
            
            removed_count = 0
            for stock in sector_instruments.keys():
                if self.user_settings.remove_user_instrument(user_id, stock):
                    removed_count += 1
            
            if removed_count > 0:
                await self._save_user_settings_to_db(user_id)
            
            # Обновляем клавиатуру
            keyboard = self.user_settings.get_sector_instruments_keyboard(user_id, sector_name, self.config.MONITORED_INSTRUMENTS)
            sector_text = f"""📊 *{sector_name}*

Выберите инструменты для мониторинга:

✅ = выбрано, ⭕ = не выбрано
Лимит: максимум 10 пар на пользователя"""
            
            await self.edit_message_text(chat_id, callback_query["message"]["message_id"], sector_text, keyboard)
            await self.answer_callback_query(callback_query_id, f"❌ Удалено: {removed_count}")
    
    async def _restore_user_settings(self):
        """Восстановление настроек пользователей из базы данных"""
        try:
            monitoring_users = await db.get_all_monitoring_users()
            logger.info(f"🔄 Восстановление настроек для {len(monitoring_users)} пользователей")
            
            for db_settings in monitoring_users:
                # Восстанавливаем настройки в менеджере
                user_settings = self.user_settings.get_user_settings(db_settings.user_id)
                user_settings.monitoring_interval = db_settings.monitoring_interval
                user_settings.spread_threshold = db_settings.spread_threshold
                user_settings.max_signals = db_settings.max_signals
                
                # Восстанавливаем выбранные инструменты если есть
                if hasattr(db_settings, 'selected_instruments') and db_settings.selected_instruments:
                    try:
                        import json
                        user_settings.selected_instruments = json.loads(db_settings.selected_instruments)
                    except Exception as e:
                        logger.warning(f"Ошибка загрузки инструментов для пользователя {db_settings.user_id}: {e}")
                        user_settings.selected_instruments = []
                
                # НЕ восстанавливаем мониторинг автоматически - пользователь должен запустить сам
                if db_settings.is_monitoring:
                    # Только записываем в БД что мониторинг был остановлен при перезапуске
                    from database import UserSettings as DBUserSettings
                    import json
                    
                    db_user_settings = DBUserSettings(
                        user_id=db_settings.user_id,
                        monitoring_interval=user_settings.monitoring_interval,
                        spread_threshold=user_settings.spread_threshold,
                        max_signals=user_settings.max_signals,
                        is_monitoring=False,  # Отключаем мониторинг
                        selected_instruments=json.dumps(user_settings.selected_instruments)
                    )
                    await db.save_user_settings(db_user_settings)
                    logger.info(f"🔄 Мониторинг пользователя {db_settings.user_id} сброшен - требуется ручной запуск")
            
            if monitoring_users:
                logger.info("🎯 Настройки пользователей восстановлены из базы данных")
                
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления настроек: {e}")
    
    async def _save_all_user_settings(self):
        """Сохранение всех настроек пользователей в базу данных"""
        try:
            for user_id, settings in self.user_settings.user_settings.items():
                from database import UserSettings as DBUserSettings
                import json
                
                db_settings = DBUserSettings(
                    user_id=user_id,
                    monitoring_interval=settings.monitoring_interval,
                    spread_threshold=settings.spread_threshold,
                    max_signals=settings.max_signals,
                    is_monitoring=self.monitoring_controller.is_user_monitoring(user_id),
                    selected_instruments=json.dumps(settings.selected_instruments)
                )
                await db.save_user_settings(db_settings)
            
            logger.info("💾 Все настройки пользователей сохранены в базу данных")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек: {e}")
    
    async def _save_user_settings_to_db(self, user_id: int):
        """Сохранение настроек конкретного пользователя"""
        try:
            settings = self.user_settings.get_user_settings(user_id)
            from database import UserSettings as DBUserSettings
            import json
            
            db_settings = DBUserSettings(
                user_id=user_id,
                monitoring_interval=settings.monitoring_interval,
                spread_threshold=settings.spread_threshold,
                max_signals=settings.max_signals,
                is_monitoring=self.monitoring_controller.is_user_monitoring(user_id),
                selected_instruments=json.dumps(settings.selected_instruments)
            )
            await db.save_user_settings(db_settings)
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек пользователя {user_id}: {e}")
            
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
    
    async def send_arbitrage_signal(self, signal, target_users=None):
        """Отправка арбитражного сигнала подписчикам"""
        if signal.action == "OPEN":
            emoji = "🟢🟢" if signal.urgency_level == 3 else "🟢" if signal.urgency_level == 2 else "📈"
            
            message = f"{emoji} *АРБИТРАЖ СИГНАЛ*\n\n"
            message += f"🎯 *{signal.stock_ticker}/{signal.futures_ticker}*\n"
            message += f"📊 Спред: *{signal.spread_percent:.2f}%*\n\n"
            message += f"💼 *Позиции:*\n"
            # Эмодзи для позиций
            stock_emoji = "🟢⬆️" if signal.stock_position == "BUY" else "🔴⬇️"
            futures_emoji = "🟢⬆️" if signal.futures_position == "BUY" else "🔴⬇️"
            
            message += f"📈 Акции {signal.stock_ticker}: *{signal.stock_position}* {stock_emoji}\n"
            message += f"📊 Фьючерс {signal.futures_ticker}: *{signal.futures_position}* {futures_emoji}\n\n"
            message += f"💰 *Цены:*\n"
            message += f"📈 {signal.stock_ticker}: {signal.stock_price:.2f} ₽\n"
            message += f"📊 {signal.futures_ticker}: {signal.futures_price:.2f} ₽\n\n"
            

            
            message += f"⏰ Время: {signal.timestamp}"
            
        else:  # CLOSE
            message = "🔄 *СИГНАЛ НА ЗАКРЫТИЕ*\n\n"
            message += f"👋 Дружище, пора закрывать позицию по *{signal.stock_ticker}/{signal.futures_ticker}*!\n\n"
            message += f"📉 Спред снизился до: *{signal.spread_percent:.2f}%*\n\n"
            message += f"⏰ Время: {signal.timestamp}"
        
        # Если target_users не указан, используем всех подписчиков с фильтрацией
        if target_users is None:
            target_users = []
            for subscriber_id in self.subscribers.copy():
                user_settings = self.user_settings.get_user_settings(subscriber_id)
                # Проверяем порог спреда пользователя
                if signal.spread_percent >= user_settings.spread_threshold:
                    target_users.append(subscriber_id)
        
        # Отправляем указанным пользователям
        failed_subscribers = []
        for subscriber_id in target_users:
            success = await self.send_message(subscriber_id, message)
            if not success:
                failed_subscribers.append(subscriber_id)
        
        # Удаляем неактивных подписчиков
        for failed_id in failed_subscribers:
            self.subscribers.discard(failed_id)
    
    async def monitoring_cycle_for_interval(self, interval_seconds: int, target_users: List[int]):
        """Цикл мониторинга для конкретного интервала"""
        logger.info(f"Мониторинг для интервала {interval_seconds}с, пользователи: {len(target_users)}")
        
        try:
            # Выбираем источник данных для ротации (для быстрых интервалов)
            if interval_seconds < 300:  # Менее 5 минут
                total_sources = len([s for s in self.data_sources.sources.values() if s["status"] == "working"])
                if total_sources > 0:
                    source_index, completed_cycle = self.monitoring_scheduler.get_next_source_for_interval(interval_seconds, total_sources)
                    logger.info(f"Используем источник #{source_index} для интервала {interval_seconds}с")
                    
                    # Если прошли полный цикл источников - делаем паузу
                    if completed_cycle:
                        import random
                        pause_seconds = random.randint(300, 420)  # 5-7 минут
                        logger.info(f"Завершен цикл источников для {interval_seconds}с. Пауза {pause_seconds}с")
                        await asyncio.sleep(pause_seconds)
                        return  # Выходим из этого цикла мониторинга
            
            # Получаем персональные инструменты всех пользователей для этого интервала
            all_user_instruments = {}
            for user_id in target_users:
                user_instruments = self.user_settings.get_user_instruments_dict(user_id, self.config.MONITORED_INSTRUMENTS)
                all_user_instruments.update(user_instruments)
            
            # Получаем котировки только для инструментов, выбранных пользователями
            instruments_to_monitor = all_user_instruments if all_user_instruments else self.config.MONITORED_INSTRUMENTS
            
            async with MOEXAPIClient() as moex_client:
                quotes = await moex_client.get_multiple_quotes(instruments_to_monitor)
            
            if not quotes:
                logger.warning("Не удалось получить котировки")
                return
            
            # Используем московское время
            import pytz
            moscow_tz = pytz.timezone('Europe/Moscow')
            moscow_time = datetime.now(moscow_tz)
            current_time = moscow_time.strftime("%H:%M:%S")
            signals = []
            
            for stock_ticker, (stock_price, futures_price) in quotes.items():
                if stock_price is None or futures_price is None:
                    continue
                
                futures_ticker = instruments_to_monitor[stock_ticker]
                # Получаем минимальный порог спреда от всех активных пользователей
                min_threshold = self._get_minimum_spread_threshold(target_users)
                
                signal = self.calculator.analyze_arbitrage_opportunity(
                    stock_ticker=stock_ticker,
                    futures_ticker=futures_ticker,
                    stock_price=stock_price,
                    futures_price=futures_price,
                    timestamp=current_time,
                    min_spread_threshold=min_threshold
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
            
            # Добавляем сигналы в очередь с ограничениями
            if signals:
                # Фильтруем пользователей по их персональным настройкам спреда
                filtered_signals = []
                for signal in signals:
                    filtered_users = []
                    for user_id in target_users:
                        user_settings = self.user_settings.get_user_settings(user_id)
                        user_instruments = self.user_settings.get_user_instruments_dict(user_id, self.config.MONITORED_INSTRUMENTS)
                        
                        # Проверяем что пользователь выбрал этот инструмент и спред превышает его порог
                        if (signal.stock_ticker in user_instruments and 
                            signal.spread_percent >= user_settings.spread_threshold):
                            filtered_users.append(user_id)
                    
                    if filtered_users:
                        filtered_signals.append((signal, filtered_users))
                
                # Добавляем отфильтрованные сигналы в очередь
                if filtered_signals:
                    for signal, users in filtered_signals[:5]:  # Максимум 5 сигналов
                        await self.send_arbitrage_signal(signal, users)
                        if len(filtered_signals) > 1:
                            await asyncio.sleep(3)  # 3 секунды между сигналами
            
            logger.info(f"Мониторинг {interval_seconds}с завершен. Найдено сигналов: {len(signals)}")
            
        except Exception as e:
            logger.error(f"Ошибка в мониторинге {interval_seconds}с: {e}")
    
    def _get_minimum_spread_threshold(self, target_users: List[int]) -> float:
        """Получает минимальный порог спреда среди целевых пользователей"""
        min_threshold = float('inf')
        
        for user_id in target_users:
            user_settings = self.user_settings.get_user_settings(user_id)
            if user_settings.spread_threshold < min_threshold:
                min_threshold = user_settings.spread_threshold
        
        return min_threshold if min_threshold != float('inf') else 0.2
            
    async def smart_monitoring_cycle(self):
        """Умный цикл мониторинга для разных групп пользователей"""
        if not self.monitoring_controller.should_run_global_monitoring():
            return
            
        # Получаем интервалы, которые нужно мониторить
        intervals_to_monitor = self.monitoring_scheduler.get_groups_to_monitor()
        
        if not intervals_to_monitor:
            return
            
        logger.info(f"Запуск мониторинга для интервалов: {intervals_to_monitor}")
        
        # Запускаем мониторинг для каждого интервала параллельно
        tasks = []
        for interval in intervals_to_monitor:
            target_users = self.monitoring_scheduler.get_users_for_interval(interval)
            if target_users:
                task = asyncio.create_task(
                    self.monitoring_cycle_for_interval(interval, list(target_users))
                )
                tasks.append(task)
        
        # Ждем завершения всех задач
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _test_monitoring_task(self, user_id: int):
        """Асинхронная задача тестового мониторинга спредов"""
        logger.info(f"Запущен тестовый мониторинг для пользователя {user_id}")
        
        # Сразу выполняем первую проверку без ожидания
        iteration = 0
        
        while self.test_monitoring_active.get(user_id, False):
            try:
                iteration += 1
                logger.info(f"Тестовый мониторинг - итерация {iteration} для пользователя {user_id}")
                
                # Получаем персональные инструменты пользователя
                user_instruments = self.user_settings.get_user_instruments_dict(user_id, self.config.MONITORED_INSTRUMENTS)
                instruments_to_test = user_instruments if user_instruments else self.config.MONITORED_INSTRUMENTS
                
                # Получаем текущие котировки через MOEX API (с правильной конвертацией)
                async with MOEXAPIClient() as moex_client:
                    quotes = await moex_client.get_multiple_quotes(instruments_to_test)
                
                logger.info(f"Получено котировок: {len(quotes) if quotes else 0}")
                
                if not quotes:
                    await self.send_message(user_id, "⚠️ Тест: Не удалось получить котировки от MOEX API")
                    await asyncio.sleep(60)  # Пауза при ошибке
                    continue
                
                # Формируем сообщение с текущими спредами
                test_message = "🧪 **ТЕСТОВЫЙ МОНИТОРИНГ СПРЕДОВ**\n\n"
                test_message += f"⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n"
                test_message += f"📊 API ответ: {len(quotes)} инструментов\n"
                test_message += f"🔄 Итерация: {iteration}\n\n"
                
                spread_found = False
                pair_count = 0
                processed_pairs = []
                
                # Обрабатываем ВСЕ пары с данными (не ограничиваем до 5)
                for stock_ticker, quote_data in quotes.items():
                    if pair_count >= 15:  # Увеличим лимит до 15 пар
                        break
                    
                    # Проверяем структуру данных
                    if not isinstance(quote_data, (list, tuple)) or len(quote_data) != 2:
                        logger.warning(f"Неправильная структура данных для {stock_ticker}: {quote_data}")
                        continue
                        
                    stock_price, futures_price = quote_data
                    
                    if stock_price is None or futures_price is None or stock_price <= 0 or futures_price <= 0:
                        logger.debug(f"Нет данных для {stock_ticker}: спот={stock_price}, фьючерс={futures_price}")
                        continue
                    
                    futures_ticker = instruments_to_test.get(stock_ticker)
                    if not futures_ticker:
                        logger.debug(f"Нет фьючерса для {stock_ticker}")
                        continue
                    
                    # Используем правильный расчет спреда через ArbitrageCalculator
                    try:
                        user_settings = self.user_settings.get_user_settings(user_id)
                        signal = self.calculator.analyze_arbitrage_opportunity(
                            stock_ticker=stock_ticker,
                            futures_ticker=futures_ticker,
                            stock_price=stock_price,
                            futures_price=futures_price,
                            timestamp=datetime.now().strftime('%H:%M:%S'),
                            min_spread_threshold=0.1  # Низкий порог для показа всех данных в тесте
                        )
                        
                        if signal:
                            # Используем правильно рассчитанный спред из сигнала
                            spread = signal.spread_percent
                            # Для отображения используем цены из сигнала (они уже правильно обработаны)
                            display_stock_price = signal.stock_price
                            display_futures_price = signal.futures_price
                        else:
                            # Прямой расчет спреда между ценами без лотности (для арбитража цены за единицу)
                            spread = ((futures_price - stock_price) / stock_price) * 100
                            display_stock_price = stock_price
                            display_futures_price = futures_price
                        
                        logger.debug(f"Спред для {stock_ticker}/{futures_ticker}: {spread:.4f}%")
                        
                        spread_found = True
                        pair_count += 1
                        processed_pairs.append(stock_ticker)
                        
                        # Определяем эмодзи для спреда
                        if abs(spread) >= 3.0:
                            emoji = "🟢🟢"
                        elif abs(spread) >= 1.5:
                            emoji = "🟢"
                        else:
                            emoji = "📊"
                        
                        test_message += f"{emoji} **{stock_ticker}/{futures_ticker}**\n"
                        test_message += f"   Спред: **{spread:.4f}%**\n"
                        test_message += f"   Акция: {display_stock_price:.2f} ₽\n"
                        test_message += f"   Фьючерс: {display_futures_price:.2f} ₽\n\n"
                        
                    except Exception as calc_error:
                        logger.error(f"Ошибка расчета спреда для {stock_ticker}: {calc_error}")
                        continue
                
                if not spread_found:
                    test_message += f"⚠️ Нет доступных данных по спредам\n"
                    test_message += f"🔍 Обработано пар: {processed_pairs}\n"
                    # Показываем сырые данные для отладки
                    sample_data = dict(list(quotes.items())[:3])
                    test_message += f"📋 Образец данных: {sample_data}\n"
                
                test_message += "💬 Для остановки: /test"
                
                await self.send_message(user_id, test_message)
                
                # Фиксированная задержка 2 минуты между итерациями для более частого обновления
                delay = 120  # 2 минуты
                logger.info(f"Следующая проверка через {delay} секунд...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                error_msg = f"⚠️ Ошибка в тестовом мониторинге: {str(e)}"
                await self.send_message(user_id, error_msg)
                logger.error(f"Ошибка в тестовом мониторинге для пользователя {user_id}: {e}")
                await asyncio.sleep(60)  # 1 минута при ошибке
        
        logger.info(f"Тестовый мониторинг остановлен для пользователя {user_id}")
    
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
                    # ИСПРАВЛЕНИЕ: Останавливаем цикл мониторинга если нет активных пользователей
                    # вместо бесконечного ожидания в цикле
                    await asyncio.sleep(10)  # Короткая проверка каждые 10 сек
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
                    
                    # Добавляем в планировщик
                    user_settings = self.user_settings.get_user_settings(user_id)
                    self.monitoring_scheduler.add_user_to_group(user_id, user_settings.monitoring_interval)
                    
                    self.monitoring_controller.remove_pending_market_open_user(user_id)
                    await self.send_message(user_id, f"🟢 Биржа открылась! Мониторинг запущен с интервалом {user_settings.get_interval_display()}")
                
                # Очищаем уведомления о закрытой бирже
                self.monitoring_controller.clear_market_closed_notifications()
                
                # ПРОВЕРЯЕМ ЕЩЕ РАЗ перед запуском мониторинга
                if not self.monitoring_controller.should_run_global_monitoring():
                    continue
                    
                try:
                    await self.smart_monitoring_cycle()
                except Exception as e:
                    error_msg = f"Ошибка в умном мониторинге: {e}"
                    logger.error(error_msg)
                    await self.notify_admin_error(error_msg)
                    
                # Умная система мониторинга проверяет каждую секунду
                await asyncio.sleep(1)
        
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
            
    async def daily_validation_task(self):
        """Фоновая задача для ежедневной валидации торговых пар"""
        while True:
            try:
                # Проверяем нужна ли валидация (раз в 24 часа)
                if self.daily_validator.should_run_validation():
                    logger.info("🔍 Запуск ежедневной валидации торговых пар")
                    
                    # Запускаем валидацию только проверенных голубых фишек
                    results = await self.daily_validator.run_validation()
                    
                    # Подсчитываем статистику
                    valid_count = sum(1 for r in results.values() if r.is_valid)
                    invalid_count = len(results) - valid_count
                    
                    # Если есть проблемные пары - уведомляем админа
                    if invalid_count > 0:
                        admin_id = self.monitoring_controller.get_admin_user_id()
                        if admin_id:
                            error_message = f"""🚨 НАЙДЕНЫ ПРОБЛЕМНЫЕ ТОРГОВЫЕ ПАРЫ
                            
⚠️ Неработающих пар: {invalid_count} из {len(results)}

🔍 Требуется проверка конфигурации MONITORED_INSTRUMENTS

⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"""
                            await self.send_message(admin_id, error_message)
                
                # Проверяем каждый час
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче валидации пар: {e}")
                await asyncio.sleep(3600)  # Пауза при ошибке

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
    # Настройка логирования для московского времени
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    class MoscowFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=moscow_tz)
            if datefmt:
                return dt.strftime(datefmt)
            else:
                return dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
    
    formatter = MoscowFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
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