import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, time, timezone, timedelta

# Версия бота  
BOT_VERSION = "0.1.2"

@dataclass
class Config:
    """Конфигурация бота"""
    
    # API настройки
    MOEX_API_BASE_URL: str = "https://iss.moex.com/iss"
    REQUEST_TIMEOUT: int = 30
    RATE_LIMIT_DELAY: float = 5.0  # Задержка между запросами к MOEX API (увеличена)
    
    # Правила MOEX API для избежания блокировок (ультраконсервативные)
    MAX_REQUESTS_PER_MINUTE: int = 15  # Максимум запросов в минуту (еще больше снижено)
    MAX_CONCURRENT_REQUESTS: int = 1   # Только 1 одновременный запрос
    RETRY_ATTEMPTS: int = 1            # Минимум попыток
    RETRY_DELAY: float = 8.0           # Увеличенная задержка
    BACKOFF_MULTIPLIER: float = 4.0    # Максимальный множитель задержки
    
    # Настройки для работы с основными инструментами (ультраконсервативная версия)
    MAX_PAIRS_PER_BATCH: int = 5       # 5 пар за цикл для минимальной нагрузки
    BATCH_DELAY: float = 5.0           # Увеличенная задержка между батчами
    SMART_ROTATION_ENABLED: bool = True # Умная ротация без повторов
    FULL_SCAN_CYCLES: int = 6          # Больше циклов для 30 основных пар (30/5)
    MIN_REQUEST_INTERVAL: float = 5.0  # Увеличенный интервал между запросами
    
    # Настройки мониторинга
    MONITORING_INTERVAL_MIN: int = 300  # 5 минут в секундах
    MONITORING_INTERVAL_MAX: int = 420  # 7 минут в секундах
    MIN_SPREAD_THRESHOLD: float = 1.0  # Минимальный спред для сигнала (%)
    SPREAD_LEVEL_2: float = 2.0  # Уровень для зеленого выделения (%)
    SPREAD_LEVEL_3: float = 3.0  # Уровень для ярко-зеленого выделения (%)
    CLOSE_SPREAD_MIN: float = 0.0  # Минимальный спред для закрытия (%)
    CLOSE_SPREAD_MAX: float = 0.5  # Максимальный спред для закрытия (%)
    
    # Настройки истории спредов
    MAX_SPREAD_HISTORY: int = 10  # Максимум записей в истории спредов
    
    # Настройки администратора и поддержки
    ADMIN_USERNAME: str = "@Ildaryakupovv"
    SUPPORT_MESSAGE: str = "Для связи с технической поддержкой напишите @Ildaryakupovv"
    
    # Резервные источники данных при блокировке MOEX API
    BACKUP_DATA_SOURCES: List[str] = field(default_factory=lambda: [
        "tradingview",
        "investing_com", 
        "yahoo_finance"
    ])
    
    # Рабочие часы биржи (московское время)
    # Акции с 8:00, фьючерсы с 9:00, арбитражный мониторинг с 9:00
    TRADING_START_TIME: time = time(9, 0)     # 09:00 МСК (фьючерсы)
    TRADING_END_TIME: time = time(18, 45)     # 18:45 МСК
    TRADING_DAYS: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Пн-Пт (0=Понедельник)
    
    # Инструменты для мониторинга
    MONITORED_INSTRUMENTS: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        if not self.MONITORED_INSTRUMENTS:
            self.MONITORED_INSTRUMENTS = {
                # ===== ГОЛУБЫЕ ФИШКИ (проверенные пары) =====
                "SBER": "SBERF",  # Сбербанк - дневной фьючерс ✅ 
                "GAZP": "GAZPF",  # Газпром - дневной фьючерс ✅
                "LKOH": "LKZ5",   # Лукойл - декабрь 2025 ✅ 
                "GMKN": "GKZ5",   # ГМК Норильский никель - декабрь 2025 ✅
                "VTBR": "VBZ5",   # ВТБ - декабрь 2025 ✅  
                "ROSN": "RNZ5",   # Роснефть - декабрь 2025 ✅
                "TATN": "TNZ5",   # Татнефть - декабрь 2025 ✅
                "ALRS": "ALZ5",   # АЛРОСА - декабрь 2025 ✅
                
                # ===== ВСЕ ПАРЫ (с исправленной логикой конверсии) =====
                "ABIO": "ISZ5",   # АВТОВАЗ
                "AFKS": "AKZ5",   # АФК Система  
                "AFLT": "AFZ5",   # Аэрофлот
                "AKRN": "ANZ5",   # Акрон
                "APTK": "APZ5",   # Аптеки 36.6
                "BANE": "BNZ5",   # Башнефть
                "BANEP": "BEZ5",  # Башнефть-П
                "BSPB": "BSZ5",   # Банк СПБ
                "CBOM": "CMZ5",   # МКБ
                "CHMF": "CHZ5",   # Северсталь
                "DIXY": "DXZ5",   # Дикси
                "DSKY": "DSZ5",   # Детский мир
                "ETLN": "ETZ5",   # Etalon Group
                "FEES": "FSZ5",   # ФСК ЕЭС
                "FIVE": "FVZ5",   # X5 Retail
                "FIXP": "FXZ5",   # Fix Price
                "FLOT": "FLZ5",   # Совкомфлот
                "GEMC": "GEZ5",   # Генетико
                "HHRU": "HRZ5",   # HeadHunter
                "HYDR": "HYZ5",   # РусГидро
                "IRAO": "IRZ5",   # Интер РАО
                "KMAZ": "KMZ5",   # КАМАЗ
                "LSRG": "LSZ5",   # ЛСР
                "MAGN": "MAZ5",   # ММК
                "MAIL": "MLZ5",   # Mail.ru
                "MGNT": "MGZ5",   # Магнит
                "MOEX": "MEZ5",   # Московская биржа
                "MSNG": "MSZ5",   # Мосэнерго
                "MTSS": "MTZ5",   # МТС
                "NKNC": "NKZ5",   # Нижнекамскнефтехим
                "OZON": "OZZ5",   # Ozon
                "PHOR": "PHZ5",   # ФосАгро
                "PIKK": "PKZ5",   # ПИК
                "PLZL": "PLZ5",   # Полюс
                "PMSB": "PMZ5",   # Промсвязьбанк
                "POLY": "POZ5",   # Полиметалл
                "PRTK": "PRZ5",   # ПРОТЕК
                "QIWI": "QIZ5",   # QIWI
                "RASP": "RAZ5",   # Распадская
                "RENI": "REZ5",   # Ренессанс Страхование
                "RTKM": "RTZ5",   # Ростелеком
                "RUAL": "RUZ5",   # РУСАЛ
                "SGZH": "SZZ5",   # Сегежа
                "SMLT": "SMZ5",   # Самолет
                "SNGS": "SNZ5",   # Сургутнефтегаз
                "TCSG": "TCZ5",   # TCS Group
                "TRNFP": "TRZ5",  # Транснефть-П
                "YAKG": "YAZ5"    # Якутскэнерго
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
            # Акции - размер лота (количество акций в одном лоте)
            "SBER": 100,    # Сбербанк - 100 акций в лоте
            "GAZP": 100,    # Газпром - 100 акций в лоте
            "GMKN": 1,      # ГМК Норильский никель - 1 акция в лоте
            "FEES": 1000,   # ФСК ЕЭС - 1000 акций в лоте  
            "VTBR": 1000,   # ВТБ - 1000 акций в лоте
            "LKOH": 1,      # Лукойл - 1 акция в лоте
            "ROSN": 1,      # Роснефть - 1 акция в лоте
            "TATN": 1,      # Татнефть - 1 акция в лоте
            "NLMK": 100,    # НЛМК - 100 акций в лоте
            "ALRS": 100,    # Алроса - 100 акций в лоте
        }
    
    def get_futures_lot_value(self, ticker: str) -> float:
        """УСТАРЕВШИЙ МЕТОД - оставлен для совместимости, но больше не используется в конверсии цен.
        
        Новая логика конверсии основана на том факте, что все фьючерсы MOEX торгуются в пунктах:
        1 пункт = 1 копейка = 0.01 рубля
        
        Исключения только для SBERF и GAZPF, которые уже торгуются в рублях.
        """
        # Этот метод больше НЕ используется для конверсии цен фьючерсов
        # Оставлен только для совместимости с другими частями кода
        return 1
    
    def get_random_monitoring_interval(self) -> int:
        """Получение случайного интервала мониторинга в допустимых пределах"""
        return random.randint(self.MONITORING_INTERVAL_MIN, self.MONITORING_INTERVAL_MAX)
    
    def is_trading_hours(self, current_time: datetime = None) -> bool:
        """Проверка, находимся ли мы в торговых часах"""
        if current_time is None:
            # Используем московское время
            moscow_tz = timezone(timedelta(hours=3))
            current_time = datetime.now(moscow_tz)
        
        # Проверяем день недели (0=понедельник, 6=воскресенье)
        weekday = current_time.weekday()
        if weekday not in self.TRADING_DAYS:
            return False
        
        # Проверяем время
        current_time_only = current_time.time()
        return self.TRADING_START_TIME <= current_time_only <= self.TRADING_END_TIME
    
    def get_trading_status_message(self) -> str:
        """Получение сообщения о статусе торгов"""
        moscow_tz = timezone(timedelta(hours=3))
        now = datetime.now(moscow_tz)
        
        if self.is_trading_hours(now):
            return f"🟢 Биржа работает\n📅 Торги до {self.TRADING_END_TIME.strftime('%H:%M')} МСК"
        
        # Если биржа закрыта
        current_time = now.time()
        weekday = now.weekday()
        
        if weekday in self.TRADING_DAYS:
            if current_time < self.TRADING_START_TIME:
                return f"🔴 Биржа закрыта\n📅 Откроется сегодня в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
            else:
                return f"🔴 Биржа закрыта\n📅 Откроется завтра в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
        
        # Выходные
        days = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
        next_trading_day = min(self.TRADING_DAYS)
        return f"🔴 Биржа закрыта (выходной)\n📅 Откроется в {days[next_trading_day]} в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
    
    def get_trading_schedule_info(self) -> str:
        """Получение информации о расписании торгов"""
        return f"""📊 Расписание торгов MOEX:
📈 Акции: 08:00 - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
📊 Фьючерсы: {self.TRADING_START_TIME.strftime('%H:%M')} - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
🤖 Арбитражный мониторинг: {self.TRADING_START_TIME.strftime('%H:%M')} - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
📅 Рабочие дни: Понедельник - Пятница"""

    def get_futures_specs(self) -> Dict[str, Dict]:
        """Спецификации фьючерсных контрактов"""
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
        }