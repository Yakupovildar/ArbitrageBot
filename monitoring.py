import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from telegram.constants import ParseMode
from telegram.error import TelegramError
from config import Config
from moex_api import MOEXAPIClient
from arbitrage_calculator import ArbitrageCalculator, ArbitrageSignal

logger = logging.getLogger(__name__)

class ArbitrageMonitor:
    """Монитор арбитражных возможностей"""
    
    def __init__(self):
        self.config = Config()
        self.calculator = ArbitrageCalculator()
        self.application = None
        self.subscribers = set()
        self.is_running = False
        
    def set_application(self, application):
        """Установка экземпляра Application"""
        self.application = application
    
    def set_subscribers(self, subscribers: set):
        """Установка списка подписчиков"""
        self.subscribers = subscribers
    
    async def start_monitoring(self):
        """Запуск мониторинга"""
        self.is_running = True
        logger.info("Запуск мониторинга арбитражных возможностей...")
        
        while self.is_running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config.MONITORING_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Мониторинг остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _monitoring_cycle(self):
        """Один цикл мониторинга"""
        logger.info("Начало цикла мониторинга...")
        
        try:
            # Получаем котировки
            async with MOEXAPIClient() as moex_client:
                quotes = await moex_client.get_multiple_quotes(
                    self.config.MONITORED_INSTRUMENTS
                )
            
            if not quotes:
                logger.warning("Не удалось получить котировки")
                return
            
            # Анализируем сигналы
            signals = await self._analyze_quotes(quotes)
            
            # Отправляем уведомления
            if signals:
                await self._send_signals(signals)
            
            logger.info(f"Цикл мониторинга завершен. Найдено сигналов: {len(signals)}")
            
        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {e}")
    
    async def _analyze_quotes(self, quotes: Dict) -> List[ArbitrageSignal]:
        """Анализ котировок и поиск сигналов"""
        signals = []
        current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
        
        for stock_ticker, (stock_price, futures_price) in quotes.items():
            try:
                if stock_price is None or futures_price is None:
                    logger.warning(f"Отсутствуют котировки для {stock_ticker}")
                    continue
                
                futures_ticker = self.config.MONITORED_INSTRUMENTS[stock_ticker]
                
                # Анализируем арбитражную возможность
                signal = self.calculator.analyze_arbitrage_opportunity(
                    stock_ticker=stock_ticker,
                    futures_ticker=futures_ticker,
                    stock_price=stock_price,
                    futures_price=futures_price,
                    timestamp=current_time
                )
                
                if signal:
                    signals.append(signal)
                    
                    # Регистрируем или закрываем позицию
                    if signal.action == "OPEN":
                        self.calculator.register_position(signal)
                    elif signal.action == "CLOSE":
                        self.calculator.close_position(signal)
                
            except Exception as e:
                logger.error(f"Ошибка анализа {stock_ticker}: {e}")
        
        return signals
    
    async def _send_signals(self, signals: List[ArbitrageSignal]):
        """Отправка сигналов подписчикам"""
        if not self.application or not self.subscribers:
            logger.warning("Нет подписчиков или application не установлен")
            return
        
        # Получаем актуальный список подписчиков из bot_handlers
        from bot_handlers import BotHandlers
        # Предполагаем, что у нас есть доступ к экземпляру BotHandlers
        # В реальной реализации это должно быть передано через dependency injection
        
        for signal in signals:
            message = self._format_signal_message(signal)
            
            # Отправляем сообщение всем подписчикам
            failed_subscribers = []
            
            for subscriber_id in self.subscribers.copy():
                try:
                    await self.application.bot.send_message(
                        chat_id=subscriber_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                except TelegramError as e:
                    logger.error(f"Ошибка отправки сообщения пользователю {subscriber_id}: {e}")
                    failed_subscribers.append(subscriber_id)
                except Exception as e:
                    logger.error(f"Неожиданная ошибка при отправке сообщения {subscriber_id}: {e}")
                    failed_subscribers.append(subscriber_id)
            
            # Удаляем неактивных подписчиков
            for failed_id in failed_subscribers:
                self.subscribers.discard(failed_id)
                logger.info(f"Удален неактивный подписчик: {failed_id}")
    
    def _format_signal_message(self, signal: ArbitrageSignal) -> str:
        """Форматирование сигнала для отправки"""
        
        if signal.action == "OPEN":
            return self._format_open_signal(signal)
        elif signal.action == "CLOSE":
            return self._format_close_signal(signal)
        
        return "Неизвестный тип сигнала"
    
    def _format_open_signal(self, signal: ArbitrageSignal) -> str:
        """Форматирование сигнала на открытие"""
        
        # Определяем эмодзи и форматирование по уровню срочности
        if signal.urgency_level == 3:  # Ярко-зеленый
            emoji = "🟢🟢"
            format_start = "*"
            format_end = "*"
        elif signal.urgency_level == 2:  # Зеленый
            emoji = "🟢"
            format_start = "*"
            format_end = "*"
        else:  # Обычный
            emoji = "📈"
            format_start = ""
            format_end = ""
        
        # Определяем направление стрелок
        stock_arrow = "📈" if signal.stock_position == "BUY" else "📉"
        futures_arrow = "📈" if signal.futures_position == "BUY" else "📉"
        
        message = f"{emoji} {format_start}АРБИТРАЖ СИГНАЛ{format_end}\n\n"
        message += f"🎯 *{signal.stock_ticker}/{signal.futures_ticker}*\n"
        message += f"📊 Спред: *{signal.spread_percent:.2f}%*\n\n"
        
        message += f"💼 *Позиции:*\n"
        message += f"{stock_arrow} Акции {signal.stock_ticker}: *{signal.stock_position}* {signal.stock_lots} лотов\n"
        message += f"{futures_arrow} Фьючерс {signal.futures_ticker}: *{signal.futures_position}* {signal.futures_lots} лотов\n\n"
        
        message += f"💰 *Цены:*\n"
        message += f"📈 {signal.stock_ticker}: {signal.stock_price:.2f} ₽\n"
        message += f"📊 {signal.futures_ticker}: {signal.futures_price:.2f} ₽\n\n"
        
        # Расчет потенциальной прибыли
        potential_profit = self.calculator.calculate_potential_profit(signal)
        if potential_profit > 0:
            message += f"💵 Потенциальная прибыль: ~{potential_profit:.0f} ₽\n\n"
        
        message += f"⏰ Время: {signal.timestamp}"
        
        return message
    
    def _format_close_signal(self, signal: ArbitrageSignal) -> str:
        """Форматирование сигнала на закрытие"""
        
        message = "🔄 *СИГНАЛ НА ЗАКРЫТИЕ*\n\n"
        message += f"👋 Дружище, пора закрывать позицию по *{signal.stock_ticker}/{signal.futures_ticker}*!\n\n"
        
        message += f"📉 Спред снизился до: *{signal.spread_percent:.2f}%*\n\n"
        
        message += f"🔚 *Закрываем позицию:*\n"
        message += f"• Акции {signal.stock_ticker}: *{signal.stock_position}* {signal.stock_lots} лотов\n"
        message += f"• Фьючерс {signal.futures_ticker}: *{signal.futures_position}* {signal.futures_lots} лотов\n\n"
        
        message += f"⏰ Время: {signal.timestamp}"
        
        return message
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        logger.info("Получен сигнал остановки мониторинга")
    
    def get_monitoring_stats(self) -> Dict:
        """Получение статистики мониторинга"""
        return {
            "is_running": self.is_running,
            "open_positions": len(self.calculator.open_positions),
            "monitored_instruments": len(self.config.MONITORED_INSTRUMENTS),
            "subscribers_count": len(self.subscribers)
        }
