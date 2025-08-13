"""
Система управления очередью сигналов с ограничениями
"""

import asyncio
import logging
from typing import List, Dict, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QueuedSignal:
    """Сигнал в очереди"""
    signal: object  # ArbitrageSignal
    target_users: List[int]
    timestamp: datetime

class SignalQueue:
    """Очередь сигналов с ограничениями"""
    
    def __init__(self, max_signals_per_batch: int = 3, signal_interval: float = 3.0):
        self.max_signals_per_batch = max_signals_per_batch
        self.signal_interval = signal_interval
        self.queue: List[QueuedSignal] = []
        self.processing = False
        self.last_batch_time = datetime.now()
        
    def add_signals_batch(self, signals: List[object], target_users: List[int]):
        """Добавление пакета сигналов в очередь"""
        now = datetime.now()
        
        # Ограничиваем количество сигналов с учетом настроек пользователей
        # Используем минимальное значение из настроек активных пользователей
        effective_limit = self._get_effective_signal_limit(target_users)
        limited_signals = signals[:effective_limit]
        
        for signal in limited_signals:
            queued_signal = QueuedSignal(
                signal=signal,
                target_users=target_users.copy(),
                timestamp=now
            )
            self.queue.append(queued_signal)
            
        logger.info(f"Добавлено {len(limited_signals)} сигналов в очередь (из {len(signals)})")
        
    async def process_queue(self, send_callback):
        """Обработка очереди сигналов"""
        if self.processing or not self.queue:
            return
            
        self.processing = True
        
        try:
            # Обрабатываем сигналы с интервалом
            while self.queue:
                queued_signal = self.queue.pop(0)
                
                # Отправляем сигнал
                await send_callback(queued_signal.signal, queued_signal.target_users)
                
                # Ждем интервал перед следующим сигналом
                if self.queue:  # Если есть еще сигналы
                    await asyncio.sleep(self.signal_interval)
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке очереди сигналов: {e}")
        finally:
            self.processing = False
            
    def get_queue_status(self) -> Dict:
        """Статус очереди"""
        return {
            "queue_size": len(self.queue),
            "processing": self.processing,
            "max_batch_size": self.max_signals_per_batch,
            "signal_interval": self.signal_interval
        }
        
    def _get_effective_signal_limit(self, target_users: List[int]) -> int:
        """Получение эффективного лимита сигналов для пользователей"""
        if not target_users:
            return self.max_signals_per_batch
        
        # Используем наименьший лимит среди всех пользователей
        return self.max_signals_per_batch  # Теперь уже 3 по умолчанию
        
    def clear_queue(self):
        """Очистка очереди"""
        self.queue.clear()
        logger.info("Очередь сигналов очищена")

class UserMonitoringScheduler:
    """Планировщик мониторинга для разных пользователей"""
    
    def __init__(self):
        # Группы пользователей по интервалам мониторинга
        self.user_groups: Dict[int, Set[int]] = {
            30: set(),    # 30 секунд
            60: set(),    # 1 минута
            180: set(),   # 3 минуты
            300: set(),   # 5 минут
            900: set()    # 15 минут
        }
        
        # Последние запуски мониторинга для каждого интервала
        self.last_monitoring: Dict[int, datetime] = {}
        
        # Счетчики источников для ротации
        self.source_counters: Dict[int, int] = {}
        
    def add_user_to_group(self, user_id: int, interval_seconds: int):
        """Добавление пользователя в группу мониторинга"""
        # Удаляем из всех групп
        for group_users in self.user_groups.values():
            group_users.discard(user_id)
            
        # Добавляем в нужную группу
        if interval_seconds in self.user_groups:
            self.user_groups[interval_seconds].add(user_id)
            logger.info(f"Пользователь {user_id} добавлен в группу {interval_seconds}с")
            
    def remove_user(self, user_id: int):
        """Удаление пользователя из всех групп"""
        for group_users in self.user_groups.values():
            group_users.discard(user_id)
        logger.info(f"Пользователь {user_id} удален из всех групп мониторинга")
        
    def get_groups_to_monitor(self) -> List[int]:
        """Получение интервалов, которые нужно мониторить сейчас"""
        now = datetime.now()
        groups_to_run = []
        
        for interval, users in self.user_groups.items():
            if not users:  # Пустая группа
                continue
                
            last_run = self.last_monitoring.get(interval, datetime.min)
            time_since_last = (now - last_run).total_seconds()
            
            if time_since_last >= interval:
                groups_to_run.append(interval)
                self.last_monitoring[interval] = now
                
        return groups_to_run
        
    def get_users_for_interval(self, interval_seconds: int) -> Set[int]:
        """Получение пользователей для интервала"""
        return self.user_groups.get(interval_seconds, set()).copy()
        
    def get_next_source_for_interval(self, interval_seconds: int, total_sources: int) -> tuple[int, bool]:
        """Получение следующего источника для ротации"""
        if interval_seconds not in self.source_counters:
            self.source_counters[interval_seconds] = 0
            
        source_index = self.source_counters[interval_seconds] % total_sources
        self.source_counters[interval_seconds] += 1
        
        # Проверяем, прошли ли полный цикл источников
        completed_cycle = self.source_counters[interval_seconds] % total_sources == 0 and self.source_counters[interval_seconds] > 0
        
        return source_index, completed_cycle
        
    def get_monitoring_stats(self) -> Dict:
        """Статистика мониторинга"""
        stats = {}
        for interval, users in self.user_groups.items():
            if users:
                last_run = self.last_monitoring.get(interval)
                stats[f"{interval}s"] = {
                    "users_count": len(users),
                    "last_run": last_run.strftime("%H:%M:%S") if last_run else "Never",
                    "source_rotation": self.source_counters.get(interval, 0)
                }
        return stats