"""
Система персональных настроек пользователей
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class UserSettings:
    """Персональные настройки пользователя"""
    user_id: int
    monitoring_interval: int = 300  # По умолчанию 5 минут (в секундах)
    spread_threshold: float = 1.0   # По умолчанию 1%
    source_rotation_index: int = 0  # Индекс текущего источника данных
    
    # Доступные интервалы мониторинга
    AVAILABLE_INTERVALS = {
        30: "30 секунд",
        60: "1 минута", 
        180: "3 минуты",
        300: "5 минут",
        900: "15 минут"
    }
    
    # Доступные пороги спредов
    AVAILABLE_SPREADS = {
        0.5: "0.5%",
        0.7: "0.7%", 
        0.9: "0.9%",
        1.0: "1.0%",
        1.5: "1.5%",
        2.0: "2.0%",
        3.0: "3.0%"
    }
    
    def get_interval_display(self) -> str:
        """Получить текстовое представление интервала"""
        return self.AVAILABLE_INTERVALS.get(self.monitoring_interval, f"{self.monitoring_interval} сек")
    
    def get_spread_display(self) -> str:
        """Получить текстовое представление порога спреда"""
        return self.AVAILABLE_SPREADS.get(self.spread_threshold, f"{self.spread_threshold}%")
    
    def is_fast_monitoring(self) -> bool:
        """Проверить, используется ли быстрый мониторинг (требует ротации источников)"""
        return self.monitoring_interval < 300  # Менее 5 минут
    
    def get_next_source_index(self, total_sources: int) -> int:
        """Получить следующий индекс источника для ротации"""
        self.source_rotation_index = (self.source_rotation_index + 1) % total_sources
        return self.source_rotation_index

class UserSettingsManager:
    """Менеджер персональных настроек пользователей"""
    
    def __init__(self):
        self.user_settings: Dict[int, UserSettings] = {}
        self.data_sources = [
            "moex",
            "tradingview", 
            "investing_com",
            "alpha_vantage",
            "finam"
        ]
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """Получить настройки пользователя (создать если не существуют)"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = UserSettings(user_id=user_id)
        return self.user_settings[user_id]
    
    def update_monitoring_interval(self, user_id: int, interval: int) -> bool:
        """Обновить интервал мониторинга пользователя"""
        if interval not in UserSettings.AVAILABLE_INTERVALS:
            return False
        
        settings = self.get_user_settings(user_id)
        settings.monitoring_interval = interval
        logger.info(f"Пользователь {user_id} изменил интервал на {interval} сек")
        return True
    
    def update_spread_threshold(self, user_id: int, threshold: float) -> bool:
        """Обновить порог спреда пользователя"""
        if threshold not in UserSettings.AVAILABLE_SPREADS:
            return False
            
        settings = self.get_user_settings(user_id)
        settings.spread_threshold = threshold
        logger.info(f"Пользователь {user_id} изменил порог спреда на {threshold}%")
        return True
    
    def get_current_source_for_user(self, user_id: int) -> str:
        """Получить текущий источник данных для пользователя (с ротацией для быстрого мониторинга)"""
        settings = self.get_user_settings(user_id)
        
        if settings.is_fast_monitoring():
            # Для быстрого мониторинга используем ротацию источников
            source_index = settings.get_next_source_index(len(self.data_sources))
            source = self.data_sources[source_index]
            logger.debug(f"Пользователь {user_id}: ротация источника -> {source}")
            return source
        else:
            # Для обычного мониторинга используем MOEX
            return "moex"
    
    def get_settings_keyboard(self, user_id: int) -> Dict:
        """Создать клавиатуру настроек для пользователя"""
        settings = self.get_user_settings(user_id)
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"⏱️ Интервал: {settings.get_interval_display()}", "callback_data": "settings_interval"},
                    {"text": f"📊 Спред: {settings.get_spread_display()}", "callback_data": "settings_spread"}
                ],
                [
                    {"text": "🔙 Назад", "callback_data": "settings_back"}
                ]
            ]
        }
        return keyboard
    
    def get_interval_keyboard(self) -> Dict:
        """Создать клавиатуру выбора интервала"""
        keyboard_rows = []
        
        # Создаем кнопки по 2 в ряд
        intervals = list(UserSettings.AVAILABLE_INTERVALS.items())
        for i in range(0, len(intervals), 2):
            row = []
            for j in range(2):
                if i + j < len(intervals):
                    interval, display = intervals[i + j]
                    row.append({"text": display, "callback_data": f"interval_{interval}"})
            keyboard_rows.append(row)
        
        keyboard_rows.append([{"text": "🔙 Назад", "callback_data": "settings_back"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def get_spread_keyboard(self) -> Dict:
        """Создать клавиатуру выбора порога спреда"""
        keyboard_rows = []
        
        # Создаем кнопки по 3 в ряд
        spreads = list(UserSettings.AVAILABLE_SPREADS.items())
        for i in range(0, len(spreads), 3):
            row = []
            for j in range(3):
                if i + j < len(spreads):
                    spread, display = spreads[i + j]
                    row.append({"text": display, "callback_data": f"spread_{spread}"})
            keyboard_rows.append(row)
        
        keyboard_rows.append([{"text": "🔙 Назад", "callback_data": "settings_back"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def get_settings_summary(self, user_id: int) -> str:
        """Получить сводку настроек пользователя"""
        settings = self.get_user_settings(user_id)
        
        summary = f"""⚙️ Ваши персональные настройки:

⏱️ Интервал мониторинга: {settings.get_interval_display()}
📊 Порог спреда: {settings.get_spread_display()}

"""
        
        if settings.is_fast_monitoring():
            summary += "🔄 Быстрый мониторинг: включена ротация источников данных для избежания блокировок\n\n"
        else:
            summary += "🐌 Обычный мониторинг: стандартная скорость без ротации источников\n\n"
            
        summary += "Нажмите на настройку чтобы изменить:"
        
        return summary