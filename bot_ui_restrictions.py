#!/usr/bin/env python3
"""
Модуль для интеграции ограничений в пользовательский интерфейс бота
"""

import logging
from typing import List, Dict
from pair_status_manager import PairStatusManager, PairStatus

logger = logging.getLogger(__name__)

class BotUIRestrictions:
    """Управление ограничениями в пользовательском интерфейсе"""
    
    def __init__(self):
        self.status_manager = PairStatusManager()
    
    def filter_available_pairs(self, all_pairs: List[tuple]) -> List[tuple]:
        """Фильтрует только доступные пары для показа пользователю"""
        available_pairs = []
        
        for stock, futures in all_pairs:
            if self.status_manager.is_pair_available(stock, futures):
                available_pairs.append((stock, futures))
            else:
                # Логируем заблокированные пары
                status_info = self.status_manager.get_pair_status_info(stock, futures)
                if status_info:
                    logger.info(f"🚫 Пара {stock}/{futures} скрыта от пользователя: {status_info.reason}")
        
        return available_pairs
    
    def get_pair_restriction_message(self, stock: str, futures: str) -> str:
        """Возвращает сообщение об ограничении для конкретной пары"""
        status_info = self.status_manager.get_pair_status_info(stock, futures)
        
        if not status_info:
            return ""
        
        if status_info.status == PairStatus.BLOCKED:
            return f"🚫 {stock}/{futures} временно заблокирована: {status_info.reason}"
        elif status_info.status == PairStatus.UNAVAILABLE:
            return f"❌ {stock}/{futures} недоступна: {status_info.reason}"
        
        return ""
    
    def format_available_pairs_message(self, available_pairs: List[tuple], blocked_count: int = 0, unavailable_count: int = 0) -> str:
        """Форматирует сообщение о доступных парах"""
        message = f"✅ Доступно пар для торговли: {len(available_pairs)}\n\n"
        
        if blocked_count > 0:
            message += f"🚫 Заблокировано пар: {blocked_count} (временно недоступны)\n"
        
        if unavailable_count > 0:
            message += f"❌ Недоступно пар: {unavailable_count} (нет данных)\n"
        
        if blocked_count > 0 or unavailable_count > 0:
            message += "\n💡 Показаны только рабочие пары для вашей безопасности"
        
        return message

# Глобальный экземпляр для использования в боте
ui_restrictions = BotUIRestrictions()