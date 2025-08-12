"""
Контроллер мониторинга для управления состоянием мониторинга пользователей
"""

import logging
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MonitoringController:
    """Контроллер для управления состоянием мониторинга"""
    
    def __init__(self):
        # Пользователи, которые включили мониторинг
        self.active_monitoring_users: Set[int] = set()
        
        # Пользователи, которых уведомили о закрытой бирже
        self.notified_market_closed: Set[int] = set()
        
        # Пользователи, ожидающие решения о мониторинге после открытия биржи
        self.pending_market_open_users: Set[int] = set()
        
        # Последние уведомления об ошибках API
        self.last_api_error_notification: Dict[str, datetime] = {}
        
        # Флаг глобального мониторинга (запускается только если есть активные пользователи)
        self.global_monitoring_active = False
        
        # ID администратора для уведомлений об ошибках
        self.admin_user_id: Optional[int] = None
        
    def start_monitoring_for_user(self, user_id: int) -> bool:
        """Запуск мониторинга для пользователя"""
        self.active_monitoring_users.add(user_id)
        if not self.global_monitoring_active:
            self.global_monitoring_active = True
            logger.info(f"Глобальный мониторинг запущен для пользователя {user_id}")
        return True
        
    def stop_monitoring_for_user(self, user_id: int) -> bool:
        """Остановка мониторинга для пользователя"""
        self.active_monitoring_users.discard(user_id)
        self.notified_market_closed.discard(user_id)
        self.pending_market_open_users.discard(user_id)
        
        # Если больше нет активных пользователей - останавливаем глобальный мониторинг
        if not self.active_monitoring_users and self.global_monitoring_active:
            self.global_monitoring_active = False
            logger.info("Глобальный мониторинг остановлен - нет активных пользователей")
        return True
        
    def is_user_monitoring(self, user_id: int) -> bool:
        """Проверка, включен ли мониторинг для пользователя"""
        return user_id in self.active_monitoring_users
        
    def should_run_global_monitoring(self) -> bool:
        """Нужно ли запускать глобальный мониторинг"""
        return self.global_monitoring_active and len(self.active_monitoring_users) > 0
        
    def get_active_users_count(self) -> int:
        """Количество активных пользователей мониторинга"""
        return len(self.active_monitoring_users)
        
    def notify_market_closed(self, user_id: int):
        """Отметить, что пользователь уведомлен о закрытой бирже"""
        self.notified_market_closed.add(user_id)
        
    def is_user_notified_market_closed(self, user_id: int) -> bool:
        """Был ли пользователь уведомлен о закрытой бирже"""
        return user_id in self.notified_market_closed
        
    def add_pending_market_open_user(self, user_id: int):
        """Добавить пользователя в очередь на запуск при открытии биржи"""
        self.pending_market_open_users.add(user_id)
        
    def remove_pending_market_open_user(self, user_id: int):
        """Убрать пользователя из очереди на запуск при открытии биржи"""
        self.pending_market_open_users.discard(user_id)
        
    def get_pending_market_open_users(self) -> Set[int]:
        """Получить список пользователей, ожидающих открытия биржи"""
        return self.pending_market_open_users.copy()
        
    def clear_market_closed_notifications(self):
        """Очистить уведомления о закрытой бирже (при открытии биржи)"""
        self.notified_market_closed.clear()
        
    def set_admin_user_id(self, admin_id: int):
        """Установить ID администратора"""
        self.admin_user_id = admin_id
        logger.info(f"Установлен ID администратора: {admin_id}")
        
    def get_admin_user_id(self) -> Optional[int]:
        """Получить ID администратора"""
        return self.admin_user_id
        
    def get_status_summary(self) -> str:
        """Получить сводку состояния мониторинга"""
        return f"""📊 Состояние мониторинга:
        
🔍 Глобальный мониторинг: {"✅ Активен" if self.global_monitoring_active else "❌ Остановлен"}
👥 Активных пользователей: {len(self.active_monitoring_users)}
📝 Уведомлено о закрытой бирже: {len(self.notified_market_closed)}
⏳ Ожидают открытия биржи: {len(self.pending_market_open_users)}
👨‍💼 Админ установлен: {"✅" if self.admin_user_id else "❌"}"""