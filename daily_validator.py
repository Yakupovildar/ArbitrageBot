"""
Система ежедневной валидации торговых пар
Автоматически проверяет пары каждые 24 часа
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pair_validator import PairValidator
from config import Config

logger = logging.getLogger(__name__)

class DailyValidator:
    """Ежедневный валидатор торговых пар"""
    
    def __init__(self):
        self.config = Config()
        self.last_validation = None
        
    async def run_validation(self):
        """Запуск валидации всех пар"""
        logger.info("🔍 Запуск ежедневной валидации торговых пар")
        
        try:
            async with PairValidator() as validator:
                # Валидируем только проверенные голубые фишки
                core_pairs = {
                    'SBER': 'SBERF',  
                    'GAZP': 'GAZPF',  
                    'LKOH': 'LKZ5',   
                    'GMKN': 'GKZ5',   
                    'VTBR': 'VBZ5',   
                    'ROSN': 'RNZ5',   
                    'TATN': 'TNZ5',   
                    'ALRS': 'ALZ5',   
                }
                
                results = await validator.validate_all_pairs(core_pairs)
                
                # Подсчет статистики
                valid_count = sum(1 for r in results.values() if r.is_valid)
                invalid_count = len(results) - valid_count
                
                # Логирование результатов
                if invalid_count > 0:
                    logger.error(f"🚨 НАЙДЕНЫ ПРОБЛЕМНЫЕ ПАРЫ: {invalid_count} из {len(results)}")
                    
                    for pair_key, result in results.items():
                        if not result.is_valid:
                            logger.error(f"❌ {result.stock_ticker}/{result.futures_ticker}: {result.error_message}")
                else:
                    logger.info(f"✅ Все {len(results)} торговых пар работают корректно")
                
                # Сохранение отчета
                self._save_validation_report(results)
                self.last_validation = datetime.now()
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка валидации: {e}")
            return {}
    
    def _save_validation_report(self, results):
        """Сохранение отчета валидации"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'validation_report_{timestamp}.json'
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_pairs': len(results),
            'valid_pairs': sum(1 for r in results.values() if r.is_valid),
            'invalid_pairs': sum(1 for r in results.values() if not r.is_valid),
            'results': {}
        }
        
        for key, result in results.items():
            report_data['results'][key] = {
                'stock_ticker': result.stock_ticker,
                'futures_ticker': result.futures_ticker,
                'is_valid': result.is_valid,
                'stock_price': result.stock_price,
                'futures_price': result.futures_price,
                'error_message': result.error_message,
                'checked_at': result.checked_at.isoformat()
            }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            logger.info(f"📄 Отчет валидации сохранен: {filename}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения отчета: {e}")
    
    def should_run_validation(self) -> bool:
        """Проверка, нужно ли запускать валидацию"""
        if not self.last_validation:
            return True
        
        time_since_last = datetime.now() - self.last_validation
        return time_since_last > timedelta(hours=24)

async def main():
    """Основная функция для запуска валидации"""
    validator = DailyValidator()
    await validator.run_validation()

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())