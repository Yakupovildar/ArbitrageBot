"""
Система ежедневной валидации торговых пар
Автоматически проверяет пары каждые 24 часа
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pair_validator import PairValidator
from pair_status_manager import PairStatusManager, PairStatus
from config import Config

logger = logging.getLogger(__name__)

class DailyValidator:
    """Ежедневный валидатор торговых пар с управлением статусами"""
    
    def __init__(self):
        self.config = Config()
        self.status_manager = PairStatusManager()
        self.last_validation = None
        
    async def run_validation(self):
        """Запуск валидации всех пар с проверкой спредов"""
        logger.info("🔍 Запуск усиленной валидации торговых пар")
        
        try:
            # Используем новый менеджер статусов для полной проверки
            pair_statuses = await self.status_manager.check_all_pairs()
            
            # Подсчет статистики
            active_count = len(self.status_manager.active_pairs)
            blocked_count = len(self.status_manager.blocked_pairs)
            unavailable_count = len(self.status_manager.unavailable_pairs)
            total_count = len(pair_statuses)
            
            # Логирование результатов с новой классификацией
            logger.info(f"📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ {total_count} ТОРГОВЫХ ПАР:")
            logger.info(f"✅ Активные: {active_count}")
            logger.info(f"🚫 Заблокированные: {blocked_count}") 
            logger.info(f"❌ Недоступные: {unavailable_count}")
            
            # Детальный отчет по проблемным парам
            if blocked_count > 0:
                logger.warning(f"🚫 ЗАБЛОКИРОВАННЫЕ ПАРЫ ({blocked_count}):")
                for pair_key in self.status_manager.blocked_pairs:
                    info = pair_statuses[pair_key]
                    logger.warning(f"   {pair_key} (заблокирована): {info.reason}")
                    
            if unavailable_count > 0:
                logger.error(f"❌ НЕДОСТУПНЫЕ ПАРЫ ({unavailable_count}):")
                for pair_key in self.status_manager.unavailable_pairs:
                    info = pair_statuses[pair_key]
                    logger.error(f"   {pair_key} (недоступна): {info.reason}")
                
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