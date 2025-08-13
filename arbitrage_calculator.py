import logging
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageSignal:
    """Сигнал для арбитража"""
    stock_ticker: str
    futures_ticker: str
    stock_price: float
    futures_price: float
    spread_percent: float
    action: str  # "OPEN" или "CLOSE"
    stock_position: str  # "BUY" или "SELL"
    futures_position: str  # "BUY" или "SELL"
    stock_lots: int
    futures_lots: int
    timestamp: str
    urgency_level: int  # 1 - обычный, 2 - зеленый, 3 - ярко-зеленый

class ArbitragePosition(NamedTuple):
    """Открытая арбитражная позиция"""
    stock_ticker: str
    futures_ticker: str
    stock_position: str
    futures_position: str
    entry_spread: float
    stock_lots: int
    futures_lots: int
    entry_timestamp: str

class ArbitrageCalculator:
    """Калькулятор арбитражных возможностей"""
    
    def __init__(self):
        self.config = Config()
        self.open_positions: Dict[str, ArbitragePosition] = {}
        
    def calculate_spread(self, stock_price: float, futures_price: float, 
                        stock_ticker: str, futures_ticker: str) -> Optional[float]:
        """Расчет спреда между спотом и фьючерсом с учетом размеров лотов
        
        Логика арбитража:
        - Лонг спот (акция) - КУПИТЬ
        - Шорт фьючерс - ПРОДАТЬ  
        - Ожидаем что фьючерс торгуется с премией к споту
        - Спред = (фьючерс_за_лот - спот_за_лот) / спот_за_лот * 100%
        """
        try:
            if stock_price <= 0 or futures_price <= 0:
                return None
            
            # ИСПРАВЛЕННЫЙ РАСЧЕТ: Сравниваем цены за одну акцию, а не за лоты
            # Спред = (цена_фьючерса - цена_акции) / цена_акции * 100%
            spread_percent = ((futures_price - stock_price) / stock_price) * 100
            
            logger.debug(f"Спред {stock_ticker}/{futures_ticker}: акция {stock_price:.2f}₽, фьючерс {futures_price:.2f}₽, спред {spread_percent:.4f}%")
            
            return spread_percent
            
        except (ZeroDivisionError, TypeError) as e:
            logger.error(f"Ошибка расчета спреда для {stock_ticker}/{futures_ticker}: {e}")
            return None
    
    def calculate_position_sizes(self, stock_ticker: str, futures_ticker: str, 
                               investment_amount: float = 100000) -> Tuple[int, int]:
        """Расчет размеров позиций для арбитража с учетом лотности"""
        try:
            # Получаем размеры лотов
            stock_lot_size = self.config.get_lot_multipliers().get(stock_ticker, 1)
            futures_lot_value = self.config.get_futures_lot_value(futures_ticker)
            
            # Рассчитываем количество лотов для сбалансированной позиции
            # Стремимся к тому, чтобы стоимость позиций была примерно равной
            if stock_lot_size == futures_lot_value:
                # Равные размеры лотов - 1 к 1
                stock_lots = 1
                futures_lots = 1
            elif stock_lot_size > futures_lot_value:
                # Лот акций больше - берем меньше лотов акций
                ratio = stock_lot_size // futures_lot_value
                stock_lots = 1
                futures_lots = ratio
            else:
                # Лот фьючерса больше - берем больше лотов акций
                ratio = futures_lot_value // stock_lot_size
                stock_lots = ratio
                futures_lots = 1
            
            logger.debug(f"Позиции {stock_ticker}/{futures_ticker}: {stock_lots} лотов акций ({stock_lot_size} акций/лот), {futures_lots} лотов фьючерса ({futures_lot_value} акций/контракт)")
            
            return int(stock_lots), int(futures_lots)
            
        except Exception as e:
            logger.error(f"Ошибка расчета размеров позиций для {stock_ticker}/{futures_ticker}: {e}")
            return 1, 1
    
    def analyze_arbitrage_opportunity(self, stock_ticker: str, futures_ticker: str,
                                    stock_price: float, futures_price: float,
                                    timestamp: str, min_spread_threshold: float = 1.0) -> Optional[ArbitrageSignal]:
        """Анализ арбитражной возможности"""
        
        spread = self.calculate_spread(stock_price, futures_price, stock_ticker, futures_ticker)
        if spread is None:
            return None
        
        position_key = f"{stock_ticker}_{futures_ticker}"
        abs_spread = abs(spread)
        
        # Проверяем существующие позиции
        if position_key in self.open_positions:
            return self._check_close_signal(position_key, spread, stock_price, 
                                          futures_price, timestamp)
        
        # Используем переданный порог или конфигурационный
        threshold = min_spread_threshold if min_spread_threshold is not None else self.config.MIN_SPREAD_THRESHOLD
        
        # Проверяем сигналы на открытие
        if abs_spread >= threshold:
            return self._generate_open_signal(stock_ticker, futures_ticker, 
                                            stock_price, futures_price, 
                                            spread, timestamp)
        
        return None
    
    def _check_close_signal(self, position_key: str, current_spread: float,
                          stock_price: float, futures_price: float,
                          timestamp: str) -> Optional[ArbitrageSignal]:
        """Проверка сигнала на закрытие позиции"""
        
        position = self.open_positions[position_key]
        abs_spread = abs(current_spread)
        
        # ИСПРАВЛЕННАЯ ЛОГИКА: Закрываем позицию только когда спред значительно уменьшился
        # Проверяем что спред сократился как минимум на 50% от входного уровня
        entry_spread_abs = abs(position.entry_spread)
        spread_reduction = entry_spread_abs - abs_spread
        spread_reduction_percent = (spread_reduction / entry_spread_abs) * 100 if entry_spread_abs > 0 else 0
        
        # Закрываем только если спред сократился минимум на 50% И стал меньше 0.5%
        if (spread_reduction_percent >= 50.0 and abs_spread <= 0.5):
            
            # Создаем сигнал на закрытие
            signal = ArbitrageSignal(
                stock_ticker=position.stock_ticker,
                futures_ticker=position.futures_ticker,
                stock_price=stock_price,
                futures_price=futures_price,
                spread_percent=current_spread,
                action="CLOSE",
                stock_position="SELL" if position.stock_position == "BUY" else "BUY",
                futures_position="SELL" if position.futures_position == "BUY" else "BUY",
                stock_lots=position.stock_lots,
                futures_lots=position.futures_lots,
                timestamp=timestamp,
                urgency_level=1
            )
            
            return signal
        
        return None
    
    def _generate_open_signal(self, stock_ticker: str, futures_ticker: str,
                            stock_price: float, futures_price: float,
                            spread: float, timestamp: str) -> ArbitrageSignal:
        """Генерация сигнала на открытие позиции"""
        
        abs_spread = abs(spread)
        
        # Определяем направление позиций
        if spread > 0:  # Фьючерс дороже спота
            stock_position = "BUY"   # Покупаем акции
            futures_position = "SELL"  # Продаем фьючерс
        else:  # Спот дороже фьючерса
            stock_position = "SELL"  # Продаем акции
            futures_position = "BUY"   # Покупаем фьючерс
        
        # Рассчитываем размеры позиций
        stock_lots, futures_lots = self.calculate_position_sizes(stock_ticker, futures_ticker)
        
        # Определяем уровень срочности
        if abs_spread >= self.config.SPREAD_LEVEL_3:
            urgency_level = 3  # Ярко-зеленый
        elif abs_spread >= self.config.SPREAD_LEVEL_2:
            urgency_level = 2  # Зеленый
        else:
            urgency_level = 1  # Обычный
        
        signal = ArbitrageSignal(
            stock_ticker=stock_ticker,
            futures_ticker=futures_ticker,
            stock_price=stock_price,
            futures_price=futures_price,
            spread_percent=spread,
            action="OPEN",
            stock_position=stock_position,
            futures_position=futures_position,
            stock_lots=stock_lots,
            futures_lots=futures_lots,
            timestamp=timestamp,
            urgency_level=urgency_level
        )
        
        return signal
    
    def register_position(self, signal: ArbitrageSignal):
        """Регистрация открытой позиции"""
        if signal.action == "OPEN":
            position_key = f"{signal.stock_ticker}_{signal.futures_ticker}"
            
            position = ArbitragePosition(
                stock_ticker=signal.stock_ticker,
                futures_ticker=signal.futures_ticker,
                stock_position=signal.stock_position,
                futures_position=signal.futures_position,
                entry_spread=signal.spread_percent,
                stock_lots=signal.stock_lots,
                futures_lots=signal.futures_lots,
                entry_timestamp=signal.timestamp
            )
            
            self.open_positions[position_key] = position
            logger.info(f"Зарегистрирована позиция: {position_key}")
    
    def close_position(self, signal: ArbitrageSignal):
        """Закрытие позиции"""
        if signal.action == "CLOSE":
            position_key = f"{signal.stock_ticker}_{signal.futures_ticker}"
            
            if position_key in self.open_positions:
                position = self.open_positions.pop(position_key)
                logger.info(f"Закрыта позиция: {position_key}")
                return position
        
        return None
    
    def get_open_positions_summary(self) -> List[Dict]:
        """Получение сводки по открытым позициям"""
        summary = []
        
        for position_key, position in self.open_positions.items():
            summary.append({
                "key": position_key,
                "stock_ticker": position.stock_ticker,
                "futures_ticker": position.futures_ticker,
                "stock_position": position.stock_position,
                "futures_position": position.futures_position,
                "entry_spread": position.entry_spread,
                "stock_lots": position.stock_lots,
                "futures_lots": position.futures_lots,
                "entry_timestamp": position.entry_timestamp
            })
        
        return summary
    
    def calculate_potential_profit(self, signal: ArbitrageSignal, 
                                 target_spread: float = 0.0) -> float:
        """Расчет потенциальной прибыли от арбитража"""
        try:
            spread_change = abs(signal.spread_percent) - abs(target_spread)
            
            # Приблизительный расчет прибыли
            stock_value = signal.stock_price * signal.stock_lots
            profit_percent = spread_change / 100
            potential_profit = stock_value * profit_percent
            
            return potential_profit
            
        except Exception as e:
            logger.error(f"Ошибка расчета потенциальной прибыли: {e}")
            return 0.0
