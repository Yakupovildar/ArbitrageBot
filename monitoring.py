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

class SpreadHistory:
    """Класс для хранения истории спредов"""
    
    def __init__(self, max_records: int = 10):
        self.max_records = max_records
        self.records = []  # Список записей [{timestamp, stock_ticker, futures_ticker, spread, signal_type}]
    
    def add_record(self, stock_ticker: str, futures_ticker: str, spread: float, signal_type: str):
        """Добавление записи в историю"""
        record = {
            'timestamp': datetime.now(),
            'stock_ticker': stock_ticker,
            'futures_ticker': futures_ticker,
            'spread': spread,
            'signal_type': signal_type
        }
        
        self.records.append(record)
        
        # Ограничиваем количество записей
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
    
    def get_recent_records(self, limit: int = None) -> List[Dict]:
        """Получение последних записей"""
        if limit is None:
            return self.records.copy()
        return self.records[-limit:] if self.records else []
    
    def format_history(self) -> str:
        """Форматирование истории для вывода"""
        if not self.records:
            return "📊 История пуста"
        
        message = "📊 История найденных спредов:\n\n"
        
        for i, record in enumerate(reversed(self.records)):
            timestamp = record['timestamp'].strftime('%d.%m %H:%M')
            message += f"{i+1}. {record['stock_ticker']}/{record['futures_ticker']}\n"
            message += f"   📈 Спред: {record['spread']:.2f}%\n"
            message += f"   🎯 Тип: {record['signal_type']}\n"
            message += f"   ⏰ {timestamp}\n\n"
        
        return message

class ArbitrageMonitor:
    """Монитор арбитражных возможностей"""
    
    def __init__(self):
        self.config = Config()
        self.calculator = ArbitrageCalculator()
        self.application = None
        self.subscribers = set()
        self.is_running = False
        self.spread_history = SpreadHistory(self.config.MAX_SPREAD_HISTORY)
        
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
                # Проверяем, открыта ли биржа
                if not self.config.is_market_open():
                    logger.info("Биржа закрыта. Ожидание открытия...")
                    await asyncio.sleep(300)  # Проверяем каждые 5 минут
                    continue
                
                await self._monitoring_cycle()
                
                # Рандомизированный интервал между 5-7 минутами
                interval = self.config.get_random_monitoring_interval()
                logger.info(f"Следующая проверка через {interval // 60} мин {interval % 60} сек")
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("Мониторинг остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    def __init__(self):
        self.config = Config()
        self.calculator = ArbitrageCalculator()
        self.application = None
        self.subscribers = set()
        self.is_running = False
        self.spread_history = SpreadHistory(self.config.MAX_SPREAD_HISTORY)
        # Добавляем трекер для умной ротации
        self.current_batch_index = 0
        self.instruments_processed_in_cycle = set()

    async def _monitoring_cycle(self):
        """Интеллектуальный цикл мониторинга с равномерным покрытием"""
        logger.info("Начало интеллектуального цикла мониторинга...")
        
        try:
            all_instruments = self.config.MONITORED_INSTRUMENTS
            max_pairs_per_batch = self.config.MAX_PAIRS_PER_BATCH
            instruments_list = list(all_instruments.items())
            total_batches = (len(instruments_list) + max_pairs_per_batch - 1) // max_pairs_per_batch
            
            # Умная ротация: последовательно проходим все батчи без повторов
            if self.config.SMART_ROTATION_ENABLED:
                batch_index = self.current_batch_index
                self.current_batch_index = (self.current_batch_index + 1) % total_batches
                
                # Если прошли полный цикл, сбрасываем счетчик обработанных инструментов
                if self.current_batch_index == 0:
                    self.instruments_processed_in_cycle.clear()
                    logger.info(f"🔄 Завершен полный цикл сканирования всех {len(all_instruments)} пар")
            else:
                # Случайный выбор (старая логика)
                import random
                batch_index = random.randint(0, total_batches - 1)
            
            start_idx = batch_index * max_pairs_per_batch
            end_idx = min(start_idx + max_pairs_per_batch, len(instruments_list))
            
            # Создаем словарь инструментов для текущего батча
            batch_instruments = dict(instruments_list[start_idx:end_idx])
            
            # Отслеживаем обработанные инструменты
            for stock in batch_instruments.keys():
                self.instruments_processed_in_cycle.add(stock)
            
            progress_percent = (len(self.instruments_processed_in_cycle) / len(all_instruments)) * 100
            
            logger.info(f"📦 Умный батч {batch_index + 1}/{total_batches}: {len(batch_instruments)} пар | Покрытие: {progress_percent:.1f}%")
            
            # Получаем котировки только для текущего батча
            async with MOEXAPIClient() as moex_client:
                quotes = await moex_client.get_multiple_quotes(batch_instruments)
            
            if not quotes:
                logger.warning("Не удалось получить котировки")
                return
            
            # Анализируем сигналы
            signals = await self._analyze_quotes(quotes)
            
            # Отправляем уведомления
            if signals:
                await self._send_signals(signals)
            
            logger.info(f"Цикл завершен. Сигналов: {len(signals)} | Обработано пар: {len(self.instruments_processed_in_cycle)}/{len(all_instruments)}")
            
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
                # Получаем минимальный порог спреда от всех активных пользователей
                min_threshold = self._get_minimum_spread_threshold()
                
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
            "market_open": self.config.is_market_open(),
            "open_positions": len(self.calculator.open_positions),
            "monitored_instruments": len(self.config.MONITORED_INSTRUMENTS),
            "subscribers_count": len(self.subscribers),
            "spread_history_count": len(self.spread_history.records)
        }
    
    def get_spread_history(self) -> str:
        """Получение форматированной истории спредов"""
        return self.spread_history.format_history()
    
    async def check_market_status_and_notify(self, subscriber_id: int):
        """Проверка статуса рынка и отправка уведомления"""
        if not self.application:
            return
        
        try:
            status_message = self.config.get_market_status_message()
            schedule_info = self.config.get_trading_schedule_info()
            
            full_message = f"{status_message}\n\n{schedule_info}"
            
            await self.application.bot.send_message(
                chat_id=subscriber_id,
                text=full_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки статуса рынка пользователю {subscriber_id}: {e}")
    
    def _get_minimum_spread_threshold(self) -> float:
        """Получает минимальный порог спреда среди всех активных пользователей"""
        if not hasattr(self, '_user_settings_manager') or not self._user_settings_manager:
            return 0.2  # Возвращаем минимально возможный порог по умолчанию
        
        min_threshold = float('inf')
        for user_settings in self._user_settings_manager.user_settings.values():
            if user_settings.spread_threshold < min_threshold:
                min_threshold = user_settings.spread_threshold
        
        return min_threshold if min_threshold != float('inf') else 0.2
    
    def set_user_settings_manager(self, user_settings_manager):
        """Устанавливает ссылку на менеджер настроек пользователей"""
        self._user_settings_manager = user_settings_manager
