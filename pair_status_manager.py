import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from moex_api import MOEXAPIClient
from config import Config

logger = logging.getLogger(__name__)

class PairStatus(Enum):
    """Статус торговой пары"""
    ACTIVE = "активна"
    BLOCKED = "заблокирована"
    UNAVAILABLE = "недоступна"

@dataclass
class PairInfo:
    """Информация о торговой паре"""
    stock_ticker: str
    futures_ticker: str
    status: PairStatus
    reason: str
    stock_price: Optional[float] = None
    futures_price: Optional[float] = None
    spread_percent: Optional[float] = None
    last_check: Optional[str] = None

class PairStatusManager:
    """Менеджер статусов торговых пар"""
    
    def __init__(self):
        self.config = Config()
        self.pair_statuses: Dict[str, PairInfo] = {}
        self.blocked_pairs: List[str] = []
        self.unavailable_pairs: List[str] = []
        self.active_pairs: List[str] = []
        
    async def check_all_pairs(self) -> Dict[str, PairInfo]:
        """Проверка всех торговых пар и определение их статусов"""
        logger.info("🔍 Начинаю полную проверку всех торговых пар...")
        
        async with MOEXAPIClient() as api:
            for stock_ticker, futures_ticker in self.config.MONITORED_INSTRUMENTS.items():
                pair_key = f"{stock_ticker}/{futures_ticker}"
                logger.info(f"Проверяю пару {pair_key}...")
                
                try:
                    # Получаем цены
                    stock_price = await api.get_stock_price(stock_ticker)
                    futures_price = await api.get_futures_price(futures_ticker)
                    
                    # Проверяем доступность данных
                    if stock_price is None:
                        self._mark_unavailable(stock_ticker, futures_ticker, f"Акция {stock_ticker}: нет данных о ценах")
                        continue
                        
                    if futures_price is None:
                        self._mark_unavailable(stock_ticker, futures_ticker, f"Фьючерс {futures_ticker}: нет данных о ценах")
                        continue
                    
                    # Рассчитываем спред
                    spread_percent = self._calculate_spread(stock_price, futures_price)
                    
                    # СТРОГАЯ проверка: блокируем спреды >30%
                    if abs(spread_percent) > 30.0:
                        self._mark_blocked(stock_ticker, futures_ticker, 
                                         f"Аномальный спред: {spread_percent:.2f}% (>30%)", 
                                         stock_price, futures_price, spread_percent)
                        continue
                    
                    # Персональная проверка для известных проблемных пар
                    if self._is_personally_problematic(stock_ticker, futures_ticker, stock_price, futures_price):
                        self._mark_blocked(stock_ticker, futures_ticker,
                                         "Персональная проверка: некорректные коэффициенты",
                                         stock_price, futures_price, spread_percent)
                        continue
                    
                    # Пара активна
                    self._mark_active(stock_ticker, futures_ticker, stock_price, futures_price, spread_percent)
                    
                except Exception as e:
                    logger.error(f"Ошибка при проверке пары {pair_key}: {e}")
                    self._mark_unavailable(stock_ticker, futures_ticker, f"Ошибка проверки: {str(e)}")
                    
                # Быстрая проверка без задержек
                await asyncio.sleep(0.1)  # Минимальная задержка только для стабильности
        
        self._update_lists()
        self._log_summary()
        return self.pair_statuses
    
    async def validate_all_pairs_fast(self) -> Dict[str, PairInfo]:
        """БЫСТРАЯ валидация всех торговых пар без задержек"""
        logger.info("🚀 БЫСТРАЯ валидация торговых пар (без задержек)")
        
        async with MOEXAPIClient() as api:
            for pair_key, (stock_ticker, futures_ticker) in self.config.MONITORED_INSTRUMENTS.items():
                try:
                    logger.info(f"Проверяю пару {stock_ticker}/{futures_ticker}...")
                    
                    # Быстрое получение цен БЕЗ задержек
                    stock_price = await api.get_stock_price(stock_ticker)
                    futures_price = await api.get_futures_price(futures_ticker)
                    
                    if not stock_price:
                        self._mark_unavailable(stock_ticker, futures_ticker, f"Акция {stock_ticker}: нет данных о ценах")
                        continue
                        
                    if not futures_price:
                        self._mark_unavailable(stock_ticker, futures_ticker, f"Фьючерс {futures_ticker}: нет данных о ценах")
                        continue
                    
                    # Быстрый расчет спреда
                    spread_percent = self._calculate_spread(stock_price, futures_price)
                    
                    if abs(spread_percent) > 30:
                        self._mark_blocked(stock_ticker, futures_ticker, 
                                         f"Аномальный спред: {spread_percent:.2f}% (>30%)",
                                         stock_price, futures_price, spread_percent)
                        continue
                    
                    if self._is_personally_problematic(stock_ticker, futures_ticker, stock_price, futures_price):
                        self._mark_blocked(stock_ticker, futures_ticker, 
                                         "Персональная проверка: некорректные коэффициенты",
                                         stock_price, futures_price, spread_percent)
                        continue
                    
                    # Пара активна
                    self._mark_active(stock_ticker, futures_ticker, stock_price, futures_price, spread_percent)
                    
                except Exception as e:
                    logger.error(f"Ошибка при проверке пары {pair_key}: {e}")
                    self._mark_unavailable(stock_ticker, futures_ticker, f"Ошибка проверки: {str(e)}")
        
        self._update_lists()
        self._log_summary()
        return self.pair_statuses
    
    def _calculate_spread(self, stock_price: float, futures_price: float) -> float:
        """Расчет спреда между ценами"""
        if stock_price <= 0 or futures_price <= 0:
            return 999.0  # Аномально высокий спред
        
        return ((futures_price - stock_price) / stock_price) * 100
    
    def _is_personally_problematic(self, stock_ticker: str, futures_ticker: str, 
                                 stock_price: float, futures_price: float) -> bool:
        """Персональная проверка проблемных пар"""
        
        # SGZH/SZZ5 - известная проблемная пара
        if stock_ticker == "SGZH" and futures_ticker == "SZZ5":
            # Проверяем соотношение цен - должно быть примерно равным
            ratio = futures_price / stock_price if stock_price > 0 else 999
            if ratio > 5 or ratio < 0.2:  # Если разница больше чем в 5 раз
                logger.warning(f"SGZH/SZZ5: аномальное соотношение цен {ratio:.2f}")
                return True
        
        # NKNC/NKZ5 - проверяем большую разницу в ценах  
        if stock_ticker == "NKNC" and futures_ticker == "NKZ5":
            ratio = futures_price / stock_price if stock_price > 0 else 999
            if ratio > 10:  # Фьючерс дороже акции в 10+ раз
                logger.warning(f"NKNC/NKZ5: подозрительное соотношение цен {ratio:.2f}")
                return True
                
        # FEES/FSZ5 - проверяем обратное соотношение
        if stock_ticker == "FEES" and futures_ticker == "FSZ5":
            ratio = stock_price / futures_price if futures_price > 0 else 999
            if ratio > 500:  # Акция дороже фьючерса в 500+ раз
                logger.warning(f"FEES/FSZ5: обратное аномальное соотношение {ratio:.2f}")
                return True
        
        return False
    
    def _mark_active(self, stock_ticker: str, futures_ticker: str, 
                    stock_price: float, futures_price: float, spread_percent: float):
        """Отметить пару как активную"""
        pair_key = f"{stock_ticker}/{futures_ticker}"
        self.pair_statuses[pair_key] = PairInfo(
            stock_ticker=stock_ticker,
            futures_ticker=futures_ticker,
            status=PairStatus.ACTIVE,
            reason="Пара работает корректно",
            stock_price=stock_price,
            futures_price=futures_price,
            spread_percent=spread_percent
        )
        logger.info(f"✅ {pair_key}: активна (спред {spread_percent:.2f}%)")
    
    def _mark_blocked(self, stock_ticker: str, futures_ticker: str, reason: str,
                     stock_price: Optional[float] = None, futures_price: Optional[float] = None,
                     spread_percent: Optional[float] = None):
        """Отметить пару как заблокированную"""
        pair_key = f"{stock_ticker}/{futures_ticker}"
        self.pair_statuses[pair_key] = PairInfo(
            stock_ticker=stock_ticker,
            futures_ticker=futures_ticker,
            status=PairStatus.BLOCKED,
            reason=reason,
            stock_price=stock_price,
            futures_price=futures_price,
            spread_percent=spread_percent
        )
        logger.warning(f"🚫 {pair_key} (заблокирована): {reason}")
    
    def _mark_unavailable(self, stock_ticker: str, futures_ticker: str, reason: str):
        """Отметить пару как недоступную"""
        pair_key = f"{stock_ticker}/{futures_ticker}"
        self.pair_statuses[pair_key] = PairInfo(
            stock_ticker=stock_ticker,
            futures_ticker=futures_ticker,
            status=PairStatus.UNAVAILABLE,
            reason=reason
        )
        logger.error(f"❌ {pair_key} (недоступна): {reason}")
    
    def _update_lists(self):
        """Обновление списков пар по статусам"""
        self.active_pairs = []
        self.blocked_pairs = []
        self.unavailable_pairs = []
        
        for pair_key, info in self.pair_statuses.items():
            if info.status == PairStatus.ACTIVE:
                self.active_pairs.append(pair_key)
            elif info.status == PairStatus.BLOCKED:
                self.blocked_pairs.append(pair_key)
            elif info.status == PairStatus.UNAVAILABLE:
                self.unavailable_pairs.append(pair_key)
    
    def _log_summary(self):
        """Вывод сводки по статусам пар"""
        total = len(self.pair_statuses)
        active = len(self.active_pairs)
        blocked = len(self.blocked_pairs)
        unavailable = len(self.unavailable_pairs)
        
        logger.info(f"📊 СВОДКА ПРОВЕРКИ ТОРГОВЫХ ПАР:")
        logger.info(f"✅ Активные: {active}/{total}")
        logger.info(f"🚫 Заблокированные: {blocked}/{total}")
        logger.info(f"❌ Недоступные: {unavailable}/{total}")
        
        if blocked > 0:
            logger.info("🚫 ЗАБЛОКИРОВАННЫЕ ПАРЫ:")
            for pair in self.blocked_pairs:
                info = self.pair_statuses[pair]
                logger.info(f"   {pair}: {info.reason}")
        
        if unavailable > 0:
            logger.info("❌ НЕДОСТУПНЫЕ ПАРЫ:")
            for pair in self.unavailable_pairs:
                info = self.pair_statuses[pair]
                logger.info(f"   {pair}: {info.reason}")
    
    def is_pair_available(self, stock_ticker: str, futures_ticker: str) -> bool:
        """Проверка доступности пары для пользователя"""
        pair_key = f"{stock_ticker}/{futures_ticker}"
        return pair_key in self.active_pairs
    
    def get_available_pairs(self) -> List[str]:
        """Получение списка доступных пар"""
        return self.active_pairs.copy()
    
    def get_pair_status_info(self, stock_ticker: str, futures_ticker: str) -> Optional[PairInfo]:
        """Получение информации о статусе пары"""
        pair_key = f"{stock_ticker}/{futures_ticker}"
        return self.pair_statuses.get(pair_key)