import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, time, timezone, timedelta

# Версия бота
BOT_VERSION = "0.0.1"

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
                
                # ===== РЕКОМЕНДОВАННЫЕ ПАРЫ (все Z5 контракты с конверсией) =====
                "ABIO": "ISZ5",   # АВТОВАЗ
                "AFKS": "AKZ5",   # АФК Система
                "AFLT": "AFZ5",   # Аэрофлот
                "AKRN": "ANZ5",   # Акрон
                "APTK": "APZ5",   # Аптеки 36.6
                "BANE": "BNZ5",   # Башнефть
                "BANEP": "BEZ5",  # Башнефть-П
                "BSPB": "BSZ5",   # Банк СПБ
                "CBOM": "CBZ5",   # МКБ
                "CHMF": "CHZ5",   # Северсталь
                "DIXY": "DXZ5",   # Дикси
                "DSKY": "DSZ5",   # Детский мир
                "ETLN": "ETZ5",   # Etalon Group
                "FEES": "FSZ5",   # ФСК ЕЭС
                "FIVE": "FVZ5",   # X5 Retail
                "FIXP": "FXZ5",   # Fix Price
                "FLOT": "FLZ5",   # Совкомфлот
                "GAZP": "GZZ5",   # Газпром (новый контракт)
                "GEMC": "GEZ5",   # Генетико
                "GMKN": "GKZ5",   # ГМК Норильский никель (новый контракт)
                "HHRU": "HRZ5",   # HeadHunter
                "HYDR": "HYZ5",   # РусГидро
                "IRAO": "IRZ5",   # Интер РАО
                "KMAZ": "KMZ5",   # КАМАЗ
                "LKOH": "LKZ5",   # Лукойл (новый контракт)
                "LSRG": "LSZ5",   # ЛСР
                "MAGN": "MAZ5",   # ММК
                "MAIL": "MLZ5",   # Mail.ru
                "MGNT": "MGZ5",   # Магнит
                "MOEX": "MEZ5",   # Московская биржа
                "MSNG": "MSZ5",   # Мосэнерго
                "MTSS": "MTZ5",   # МТС
                "NKNC": "NKZ5",   # Нижнекамскнефтехим
                "NLMK": "NLZ5",   # НЛМК
                "NVTK": "NVZ5",   # НОВАТЭК
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
                "ROSN": "RNZ5",   # Роснефть (новый контракт)
                "RTKM": "RTZ5",   # Ростелеком
                "RUAL": "RUZ5",   # РУСАЛ
                "SBER": "SRZ5",   # Сбербанк (новый контракт)
                "SGZH": "SZZ5",   # Сегежа
                "SMLT": "SMZ5",   # Самолет
                "SNGS": "SNZ5",   # Сургутнефтегаз
                "TATN": "TNZ5",   # Татнефть (новый контракт)
                "TCSG": "TCZ5",   # TCS Group
                "TRNFP": "TRZ5",  # Транснефть-П
                "VTBR": "VBZ5",   # ВТБ (новый контракт)
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
                "CBOM": "CMZ5",   # Московский кредитный банк - декабрь 2025
                "BSPB": "BSZ5",   # Банк Санкт-Петербург - декабрь 2025
                "SVCB": "SCZ5",   # Совкомбанк - декабрь 2025
    
    def get_market_status_message(self) -> str:
        """Получение сообщения о статусе рынка"""
        # Используем московское время
        import pytz
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz)
        
        if self.is_market_open(now):
            return "🟢 Биржа открыта"
        
        # Определяем, когда откроется биржа
        if now.weekday() in self.TRADING_DAYS:
            if now.time() < self.TRADING_START_TIME:
                return f"🔴 Биржа закрыта\n📅 Откроется сегодня в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
            else:
                return f"🔴 Биржа закрыта\n📅 Откроется завтра в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
        else:
            # Выходной день
            days = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
            next_trading_day = min(self.TRADING_DAYS)
            return f"🔴 Биржа закрыта (выходной)\n📅 Откроется в {days[next_trading_day]} в {self.TRADING_START_TIME.strftime('%H:%M')} МСК"
    
    def get_trading_schedule_info(self) -> str:
        """Получение информации о расписании торгов"""
        return f"""📊 Расписание торгов Московской биржи:

📈 Акции: 08:00 - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
📊 Фьючерсы: {self.TRADING_START_TIME.strftime('%H:%M')} - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
🤖 Арбитражный мониторинг: {self.TRADING_START_TIME.strftime('%H:%M')} - {self.TRADING_END_TIME.strftime('%H:%M')} МСК
📅 Торговые дни: Понедельник - Пятница
🚫 Выходные: Суббота, Воскресенье

⚠️ Внимание: не учитываются праздничные дни"""
    
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
