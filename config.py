import os
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Config:
    """Конфигурация бота"""
    
    # API настройки
    MOEX_API_BASE_URL: str = "https://iss.moex.com/iss"
    REQUEST_TIMEOUT: int = 30
    RATE_LIMIT_DELAY: float = 1.0  # Задержка между запросами к MOEX API
    
    # Настройки мониторинга
    MONITORING_INTERVAL: int = 300  # 5 минут в секундах
    MIN_SPREAD_THRESHOLD: float = 1.0  # Минимальный спред для сигнала (%)
    SPREAD_LEVEL_2: float = 2.0  # Уровень для зеленого выделения (%)
    SPREAD_LEVEL_3: float = 3.0  # Уровень для ярко-зеленого выделения (%)
    CLOSE_SPREAD_MIN: float = 0.0  # Минимальный спред для закрытия (%)
    CLOSE_SPREAD_MAX: float = 0.5  # Максимальный спред для закрытия (%)
    
    # Инструменты для мониторинга
    MONITORED_INSTRUMENTS: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        if not self.MONITORED_INSTRUMENTS:
            self.MONITORED_INSTRUMENTS = {
                # Акции и соответствующие фьючерсы
                "SBER": "SiM5",  # Сбербанк
                "GAZP": "GZM5",  # Газпром
                "LKOH": "LKM5",  # Лукойл
                "NVTK": "NVM5",  # Новатэк
                "YNDX": "YNM5",  # Яндекс
                "TCSG": "TCM5",  # TCS Group
                "ROSN": "RSM5",  # Роснефть
                "GMKN": "GMM5",  # ГМК Норильский никель
                "PLZL": "PLM5",  # Полюс
                "MGNT": "MGM5",  # Магнит
                "SNGS": "SGM5",  # Сургутнефтегаз
                "VTBR": "VTM5",  # ВТБ
                "ALRS": "ALM5",  # Алроса
                "TATN": "TTM5",  # Татнефть
                "MTSS": "MTM5",  # МТС
            }
    
    @classmethod
    def get_admin_users(cls) -> List[int]:
        """Получение списка администраторов из переменных окружения"""
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        if not admin_ids_str:
            return []
        
        try:
            return [int(user_id.strip()) for user_id in admin_ids_str.split(",") if user_id.strip()]
        except ValueError:
            return []
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in cls.get_admin_users()
    
    def get_lot_multipliers(self) -> Dict[str, int]:
        """Получение мультипликаторов лотов для различных инструментов"""
        return {
            # Стандартные мультипликаторы для фьючерсов MOEX
            "Si": 1000,   # Доллар США - рубль (1000 долларов)
            "RTS": 1,     # Индекс РТС
            "MIX": 1,     # Индекс МосБиржи
            "BR": 10,     # Нефть Brent (10 баррелей)
            "GOLD": 1,    # Золото (1 кг)
            "SILV": 1,    # Серебро (1 кг)
            # Для акций обычно 1 лот = 1 акция, но могут быть исключения
        }
    
    def get_futures_specs(self) -> Dict[str, Dict]:
        """Получение спецификаций фьючерсов"""
        return {
            "SiM5": {"underlying": "USD/RUB", "lot_size": 1000, "tick_size": 0.0001},
            "GZM5": {"underlying": "GAZP", "lot_size": 100, "tick_size": 0.001},
            "LKM5": {"underlying": "LKOH", "lot_size": 10, "tick_size": 0.01},
            "NVM5": {"underlying": "NVTK", "lot_size": 10, "tick_size": 0.01},
            "YNM5": {"underlying": "YNDX", "lot_size": 1, "tick_size": 0.01},
            "TCM5": {"underlying": "TCSG", "lot_size": 1, "tick_size": 0.01},
            "RSM5": {"underlying": "ROSN", "lot_size": 10, "tick_size": 0.01},
            "GMM5": {"underlying": "GMKN", "lot_size": 1, "tick_size": 0.01},
            "PLM5": {"underlying": "PLZL", "lot_size": 1, "tick_size": 0.01},
            "MGM5": {"underlying": "MGNT", "lot_size": 1, "tick_size": 0.01},
            "SGM5": {"underlying": "SNGS", "lot_size": 100, "tick_size": 0.001},
            "VTM5": {"underlying": "VTBR", "lot_size": 1000, "tick_size": 0.0001},
            "ALM5": {"underlying": "ALRS", "lot_size": 10, "tick_size": 0.001},
            "TTM5": {"underlying": "TATN", "lot_size": 10, "tick_size": 0.01},
            "MTM5": {"underlying": "MTSS", "lot_size": 10, "tick_size": 0.01},
        }
