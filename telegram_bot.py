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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from config import Config
from moex_api import MOEXAPIClient
from arbitrage_calculator import ArbitrageCalculator

logger = logging.getLogger(__name__)

@dataclass
class TelegramUpdate:
    """Структура для Telegram update"""
    update_id: int
    message: Optional[Dict] = None
    
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
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
        """Отправка сообщения"""
        if not self.session:
            return False
            
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                else:
                    logger.error(f"Ошибка отправки сообщения: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
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
                            message=update_data.get("message")
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
        
        if command.startswith("/start"):
            welcome_text = """🤖 *Добро пожаловать в бота арбитража MOEX!*

Этот бот мониторит спреды между акциями и фьючерсами на Московской бирже.

📊 *Основные функции:*
• Мониторинг спредов каждые 5 минут
• Сигналы при спреде > 1%
• Цветовое выделение по уровням спреда
• Сигналы на закрытие позиций

📝 *Доступные команды:*
/help - справка по командам
/status - статус мониторинга  
/positions - открытые позиции
/subscribe - подписаться на уведомления
/unsubscribe - отписаться от уведомлений

⚠️ *Важно:* Сигналы носят информационный характер."""
            await self.send_message(chat_id, welcome_text)
            
        elif command.startswith("/help"):
            help_text = """📚 *Справка по командам:*

/start - Запуск бота и приветствие
/help - Эта справка
/status - Текущий статус мониторинга
/positions - Список открытых позиций
/subscribe - Подписаться на уведомления
/unsubscribe - Отписаться от уведомлений

🔍 *Как читать сигналы:*
📈 SBER/SiM5 | Спред: 2.5%
💰 Акции: КУПИТЬ 100 лотов
📊 Фьючерс: ПРОДАТЬ 1 лот

⚡ *Автоматический мониторинг каждые 5 минут*"""
            await self.send_message(chat_id, help_text)
            
        elif command.startswith("/status"):
            status_text = f"""📊 *Статус системы мониторинга:*

🔌 MOEX API: ✅ Доступен
📈 Мониторинг: ✅ Активен
🔔 Ваша подписка: {"✅ Активна" if user_id in self.subscribers else "❌ Отключена"}
📋 Открытых позиций: {len(self.calculator.open_positions)}
⏰ Интервал: {self.config.MONITORING_INTERVAL // 60} мин"""
            await self.send_message(chat_id, status_text)
            
        elif command.startswith("/positions"):
            positions = self.calculator.get_open_positions_summary()
            if not positions:
                await self.send_message(chat_id, "📋 *Открытые позиции:*\n\nНет открытых арбитражных позиций")
            else:
                message = "📋 *Открытые арбитражные позиции:*\n\n"
                for i, pos in enumerate(positions, 1):
                    message += f"*{i}. {pos['stock_ticker']}/{pos['futures_ticker']}*\n"
                    message += f"📈 Акции: {pos['stock_position']} {pos['stock_lots']} лотов\n"
                    message += f"📊 Фьючерс: {pos['futures_position']} {pos['futures_lots']} лотов\n"
                    message += f"📊 Входной спред: {pos['entry_spread']:.2f}%\n\n"
                await self.send_message(chat_id, message)
                
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
        else:
            await self.send_message(chat_id, "🤖 Неизвестная команда. Используйте /help для справки.")
    
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
        
        # Отправляем всем подписчикам
        failed_subscribers = []
        for subscriber_id in self.subscribers.copy():
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
        
        # Планируем мониторинг
        async def monitoring_task():
            while True:
                await self.monitoring_cycle()
                await asyncio.sleep(self.config.MONITORING_INTERVAL)
        
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
                        
                        if text.startswith("/"):
                            await self.handle_command(chat_id, text, user_id)
                        else:
                            await self.send_message(chat_id, "🤖 Я понимаю только команды. Используйте /help для справки.")
                
                await asyncio.sleep(1)  # Небольшая пауза между запросами
                
        except KeyboardInterrupt:
            logger.info("Остановка бота...")
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

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