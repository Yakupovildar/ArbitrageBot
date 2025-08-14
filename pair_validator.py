"""
Система валидации торговых пар MOEX
Проверяет актуальность тикеров и доступность данных
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class PairValidationResult:
    """Результат валидации торговой пары"""
    stock_ticker: str
    futures_ticker: str
    is_valid: bool
    stock_price: Optional[float] = None
    futures_price: Optional[float] = None
    error_message: str = ""
    last_trade_time: Optional[str] = None
    checked_at: datetime = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now()

class PairValidator:
    """Валидатор торговых пар MOEX"""
    
    def __init__(self):
        self.session = None
        self.last_validation = None
        self.validation_results: Dict[str, PairValidationResult] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def validate_stock(self, ticker: str) -> Tuple[bool, Optional[float], str]:
        """Валидация акции на MOEX"""
        try:
            url = f'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json?iss.meta=off&iss.only=securities&securities.columns=SECID,PREVPRICE'
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return False, None, f"HTTP {response.status}"
                
                data = await response.json()
                
                if 'securities' not in data or not data['securities'].get('data'):
                    return False, None, "Тикер не найден в TQBR"
                
                # Извлекаем цену
                row = data['securities']['data'][0]
                columns = data['securities']['columns']
                
                if 'PREVPRICE' in columns:
                    prev_idx = columns.index('PREVPRICE')
                    price = row[prev_idx] if len(row) > prev_idx else None
                    
                    if price and price > 0:
                        return True, float(price), ""
                    else:
                        return False, None, "Нет данных о ценах"
                else:
                    return False, None, "Нет данных о ценах"
                    
        except Exception as e:
            return False, None, f"Ошибка запроса: {str(e)}"
    
    async def validate_futures(self, ticker: str) -> Tuple[bool, Optional[float], str]:
        """Валидация фьючерса на MOEX"""
        try:
            url = f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{ticker}.json?iss.meta=off&iss.only=securities&securities.columns=SECID,PREVPRICE'
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return False, None, f"HTTP {response.status}"
                
                data = await response.json()
                
                if 'securities' not in data or not data['securities'].get('data'):
                    return False, None, "Тикер не найден в RFUD"
                
                # Извлекаем цену
                row = data['securities']['data'][0]
                columns = data['securities']['columns']
                
                if 'PREVPRICE' in columns:
                    prev_idx = columns.index('PREVPRICE')
                    price = row[prev_idx] if len(row) > prev_idx else None
                    
                    if price and price > 0:
                        return True, float(price), ""
                    else:
                        return False, None, "Нет данных о ценах"
                else:
                    return False, None, "Нет данных о ценах"
                    
        except Exception as e:
            return False, None, f"Ошибка запроса: {str(e)}"
    
    async def validate_pair(self, stock_ticker: str, futures_ticker: str) -> PairValidationResult:
        """Валидация пары акция-фьючерс"""
        
        # Проверяем акцию
        stock_valid, stock_price, stock_error = await self.validate_stock(stock_ticker)
        
        # Проверяем фьючерс
        futures_valid, futures_price, futures_error = await self.validate_futures(futures_ticker)
        
        # Определяем общий результат
        is_valid = stock_valid and futures_valid
        error_message = ""
        
        if not stock_valid:
            error_message += f"Акция {stock_ticker}: {stock_error}. "
        if not futures_valid:
            error_message += f"Фьючерс {futures_ticker}: {futures_error}. "
            
        return PairValidationResult(
            stock_ticker=stock_ticker,
            futures_ticker=futures_ticker,
            is_valid=is_valid,
            stock_price=stock_price,
            futures_price=futures_price,
            error_message=error_message.strip()
        )
    
    async def validate_all_pairs(self, pairs: Dict[str, str]) -> Dict[str, PairValidationResult]:
        """Валидация всех торговых пар"""
        results = {}
        
        logger.info(f"🔍 Начинаем валидацию {len(pairs)} торговых пар")
        
        for stock, futures in pairs.items():
            try:
                result = await self.validate_pair(stock, futures)
                results[f"{stock}_{futures}"] = result
                
                if result.is_valid:
                    logger.info(f"✅ {stock}/{futures}: {result.stock_price}₽ / {result.futures_price}₽")
                else:
                    logger.error(f"❌ {stock}/{futures}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка валидации {stock}/{futures}: {e}")
                results[f"{stock}_{futures}"] = PairValidationResult(
                    stock_ticker=stock,
                    futures_ticker=futures,
                    is_valid=False,
                    error_message=f"Критическая ошибка: {str(e)}"
                )
        
        self.validation_results = results
        self.last_validation = datetime.now()
        
        # Статистика
        valid_count = sum(1 for r in results.values() if r.is_valid)
        invalid_count = len(results) - valid_count
        
        logger.info(f"📊 Валидация завершена: {valid_count} валидных, {invalid_count} проблемных пар")
        
        return results
    
    def get_validation_summary(self) -> str:
        """Получить сводку последней валидации"""
        if not self.validation_results:
            return "❌ Валидация не проводилась"
        
        valid_pairs = [r for r in self.validation_results.values() if r.is_valid]
        invalid_pairs = [r for r in self.validation_results.values() if not r.is_valid]
        
        summary = f"""📊 ОТЧЕТ ВАЛИДАЦИИ ТОРГОВЫХ ПАР
        
⏰ Время проверки: {self.last_validation.strftime('%H:%M %d.%m.%Y')}
✅ Валидных пар: {len(valid_pairs)}
❌ Проблемных пар: {len(invalid_pairs)}

"""
        
        if invalid_pairs:
            summary += "🚨 ПРОБЛЕМНЫЕ ПАРЫ:\n"
            for result in invalid_pairs:
                summary += f"   • {result.stock_ticker}/{result.futures_ticker}: {result.error_message}\n"
            summary += "\n"
        
        if valid_pairs:
            summary += "✅ РАБОТАЮЩИЕ ПАРЫ:\n"
            for result in valid_pairs[:10]:  # Показываем первые 10
                spread = 0
                if result.stock_price and result.futures_price:
                    spread = ((result.futures_price - result.stock_price) / result.stock_price) * 100
                summary += f"   • {result.stock_ticker}/{result.futures_ticker}: спред {spread:.2f}%\n"
            
            if len(valid_pairs) > 10:
                summary += f"   ... и еще {len(valid_pairs) - 10} пар\n"
        
        return summary
    
    def needs_validation(self, hours: int = 24) -> bool:
        """Проверить, нужна ли валидация"""
        if not self.last_validation:
            return True
        
        time_since_validation = datetime.now() - self.last_validation
        return time_since_validation > timedelta(hours=hours)

async def run_daily_validation():
    """Запуск ежедневной валидации всех пар"""
    from config import Config
    
    config = Config()
    
    async with PairValidator() as validator:
        results = await validator.validate_all_pairs(config.MONITORED_INSTRUMENTS)
        
        # Логируем результаты
        summary = validator.get_validation_summary()
        print(summary)
        
        # Сохраняем результаты в файл
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'validation_report_{timestamp}.json', 'w', encoding='utf-8') as f:
            results_dict = {}
            for key, result in results.items():
                results_dict[key] = {
                    'stock_ticker': result.stock_ticker,
                    'futures_ticker': result.futures_ticker,
                    'is_valid': result.is_valid,
                    'stock_price': result.stock_price,
                    'futures_price': result.futures_price,
                    'error_message': result.error_message,
                    'checked_at': result.checked_at.isoformat()
                }
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        
        return results

if __name__ == "__main__":
    asyncio.run(run_daily_validation())