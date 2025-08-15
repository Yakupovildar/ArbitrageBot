import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, time, timezone, timedelta

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
                # ===== РЕКОМЕНДОВАННЫЕ =====
                "ABIO": "IS-9.25",  # АВТОВАЗ
                "AFKS": "AK-9.25",  # АФК СИСТЕМА  
                "AFLT": "AF-9.25",  # Аэрофлот
                "ALRS": "AL-9.25",  # АЛРОСА
                "ASTR": "AS-9.25",  # Астра Групп
                "BANE": "BN-9.25",  # Башнефт
                "BSPB": "BS-9.25",  # Банк СПб
                "CBOM": "CM-9.25",  # МКБ
                "CHMF": "CH-9.25",  # Северсталь
                "FEES": "FS-9.25",  # Дальэнерго
                "FESH": "FE-9.25",  # ДВМП
                "FLOT": "FL-9.25",  # Совкомфлот
                "GAZP": "GZ-9.25",  # Газпром
                "GLDRUBF": "GL-9.25", # Золото
                "GMKN": "GK-9.25",  # ГМК Норникель
                "HYDR": "HY-9.25",  # РусГидро
                "IRAO": "IR-9.25",  # Интер РАО
                "KMAZ": "KM-9.25",  # КАМАЗ
                "LEAS": "LE-9.25",  # Европлан
                "LKOH": "LK-9.25",  # Лукойл
                "MAGN": "MG-9.25",  # ММК
                "MGNT": "MN-9.25",  # Магнит
                "MOEX": "ME-9.25",  # Московская биржа
                "MTLR": "MC-9.25",  # Мечел
                "MTSS": "MT-9.25",  # МТС
                "MVID": "MV-9.25",  # М.Видео
                "NLMK": "NM-9.25",  # НЛМК
                "NVTK": "NK-9.25",  # НОВАТЭК
                "PHOR": "PH-9.25",  # ФосАгро
                "PIKK": "PI-9.25",  # ПИК
                "PLZL": "PZ-9.25",  # Полюс
                "POSI": "PS-9.25",  # Группа Позитив
                "RASP": "RA-9.25",  # Распадская
                "RNFT": "RU-9.25",  # Русснефт
                "ROSN": "RN-9.25",  # Роснефть
                "RTKM": "RT-9.25",  # Ростелеком
                "RUAL": "RL-9.25",  # РУСАЛ
                "SBER": "SR-9.25",  # Сбербанк
                "SBERP": "SP-9.25", # Сбербанк П
                "SFIN": "SH-9.25",  # СФИ
                "SGZH": "SZ-9.25",  # Сегежа
                "SIBN": "SO-9.25",  # Газпром нефть
                "SMLT": "SS-9.25",  # Самолет
                "SNGS": "SN-9.25",  # Сургутнефтегаз
                "SNGSP": "SG-9.25", # Сургутнефтегаз П
                "SOFL": "S0-9.25",  # Софтлайн
                "SPBE": "SE-9.25",  # СПБ Биржа
                "SVCB": "SC-9.25",  # Совкомбанк
                "TATN": "TT-9.25",  # Татнефть
                "TATNP": "TP-9.25", # Татнефть П
                "TRNFP": "TN-9.25", # Транснефть П
                "VKCO": "VK-9.25",  # VK
                "VTBR": "VB-9.25",  # ВТБ
                "WUSH": "WU-9.25",  # WHOOSH
                
                # ===== ПРОВЕРЕННЫЕ ГОЛУБЫЕ ФИШКИ (валидировано 14.08.2025) =====
                "SBER": "SBERF",  # Сбербанк - дневной фьючерс ✅ 
                "GAZP": "GAZPF",  # Газпром - дневной фьючерс ✅
                "LKOH": "LKZ5",   # Лукойл - декабрь 2025 ✅ 
                "GMKN": "GKZ5",   # ГМК Норильский никель - декабрь 2025 ✅
                "VTBR": "VBZ5",   # ВТБ - декабрь 2025 ✅  
                "ROSN": "RNZ5",   # Роснефть - декабрь 2025 ✅
                "TATN": "TNZ5",   # Татнефть - декабрь 2025 ✅
                "ALRS": "ALZ5",   # АЛРОСА - декабрь 2025 ✅
                
                # ===== БАНКОВСКИЙ СЕКТОР =====
                "SBERP": "SPZ5",  # Сбербанк (привилегированные) - декабрь 2025
                "CBOM": "CMZ5",   # Московский кредитный банк - декабрь 2025
                "BSPB": "BSZ5",   # Банк Санкт-Петербург - декабрь 2025
                "SVCB": "SCZ5",   # Совкомбанк - декабрь 2025
                
                # ===== НЕФТЕГАЗ =====
                "LKOH": "LKZ5",   # Лукойл - декабрь 2025
                "ROSN": "RNZ5",   # Роснефть - декабрь 2025
                "TATN": "TNZ5",   # Татнефть - декабрь 2025
                "TATP": "TPZ5",   # Татнефть (прив.) - декабрь 2025
                "SNGS": "SNZ5",   # Сургутнефтегаз - декабрь 2025
                "SNGSP": "SGZ5",  # Сургутнефтегаз (прив.) - декабрь 2025
                "NVTK": "NKZ5",   # НОВАТЭК - декабрь 2025
                "SIBN": "SOZ5",   # Газпром нефть - декабрь 2025
                "BANE": "BNZ5",   # Башнефт - декабрь 2025
                "RNFT": "RUZ5",   # Русснефт - декабрь 2025
                
                # ===== МЕТАЛЛУРГИЯ =====
                "NLMK": "NMZ5",   # НЛМК - декабрь 2025
                "MAGN": "MGZ5",   # ММК - декабрь 2025
                "CHMF": "CHZ5",   # Северсталь - декабрь 2025
                "MTLR": "MCZ5",   # Мечел - декабрь 2025
                "PLZL": "PZZ5",   # Полюс - декабрь 2025
                "POLY": "POZ5",   # Полиметалл - декабрь 2025
                "RUAL": "RLZ5",   # РУСАЛ - декабрь 2025
                "PHOR": "PHZ5",   # ФосАгро - декабрь 2025
                "RASP": "RAZ5",   # Распадская - декабрь 2025
                
                # ===== ЭЛЕКТРОЭНЕРГЕТИКА =====
                "IRAO": "IRZ5",   # Интер РАО - декабрь 2025
                "HYDR": "HYZ5",   # РусГидро - декабрь 2025
                "RSTI": "REZ5",   # Россети - декабрь 2025
                "MSNG": "MOZ5",   # Мосэнерго - декабрь 2025
                "TRNFP": "TNZ5",  # Транснефть (прив.) - декабрь 2025
                
                # ===== ТЕЛЕКОММУНИКАЦИИ =====
                "RTKM": "RTZ5",   # Ростелеком - декабрь 2025
                "MTSS": "MTZ5",   # МТС - декабрь 2025
                "TCSI": "TIZ5",   # ТКС Холдинг - декабрь 2025
                
                # ===== ТЕХНОЛОГИИ =====
                "YDEX": "YDZ5",   # Яндекс - декабрь 2025
                "VKCO": "VKZ5",   # VK - декабрь 2025
                "OZON": "OZZ5",   # Ozon - декабрь 2025 (если есть)
                "TCSG": "TCZ5",   # TCS Group - декабрь 2025 (если есть)
                
                # ===== РИТЕЙЛ И ПОТРЕБИТЕЛЬСКИЕ ТОВАРЫ =====
                "MGNT": "MNZ5",   # Магнит - декабрь 2025
                "FIVE": "FVZ5",   # X5 Retail Group - декабрь 2025 (если есть)
                "DIXY": "DIZ5",   # Дикси - декабрь 2025 (если есть)
                "LENTA": "LTZ5",  # Лента - декабрь 2025 (если есть)
                "MVID": "MVZ5",   # М.Видео - декабрь 2025
                
                # ===== ДЕВЕЛОПМЕНТ И НЕДВИЖИМОСТЬ =====
                "PIKK": "PIZ5",   # ПИК - декабрь 2025
                "SMLT": "SSZ5",   # Самолет - декабрь 2025
                "LSRG": "LSZ5",   # ЛСР - декабрь 2025 (если есть)
                "ETALON": "ETZ5", # Эталон - декабрь 2025 (если есть)
                
                # ===== ТРАНСПОРТ =====
                "AFLT": "AFZ5",   # Аэрофлот - декабрь 2025
                "FESH": "FEZ5",   # ДВМП - декабрь 2025
                "FLOT": "FLZ5",   # Совкомфлот - декабрь 2025
                "KMAZ": "KMZ5",   # КАМАЗ - декабрь 2025
                
                # ===== ФАРМАЦЕВТИКА И ЗДРАВООХРАНЕНИЕ =====
                "PHST": "PSZ5",   # ФармСтандарт - декабрь 2025 (если есть)
                "GEMC": "GEZ5",   # Генетико - декабрь 2025 (если есть)
                
                # ===== ХИМИЯ И НЕФТЕХИМИЯ =====
                "AKRN": "AKZ5",   # Акрон - декабрь 2025 (если есть)
                "NKNC": "NKZ5",   # Нижнекамскнефтехим - декабрь 2025 (если есть)
                "URKZ": "URZ5",   # Уралкалий - декабрь 2025 (если есть)
                
                # ===== МАШИНОСТРОЕНИЕ =====
                "KMAZ": "KMZ5",   # КАМАЗ - декабрь 2025
                "LIFE": "LFZ5",   # Фармсинтез - декабрь 2025 (если есть)
                
                # ===== IT И СОФТ =====
                "ISKJ": "ISZ5",   # Искра - декабрь 2025
                "POSI": "PSZ5",   # Группа Позитив - декабрь 2025
                "ASTR": "ASZ5",   # Астра Групп - декабрь 2025
                "SOFL": "S0Z5",   # Софтлайн - декабрь 2025
                "WUSH": "WUZ5",   # WHOOSH - декабрь 2025
                "DIAS": "DIZ5",   # Диасофт - декабрь 2025 (если есть)
                
                # ===== БИРЖИ И ФИНУСЛУГИ =====
                "MOEX": "MEZ5",   # Московская биржа - декабрь 2025
                "SPBE": "SEZ5",   # СПБ Биржа - декабрь 2025
                "SFIN": "SHZ5",   # СФИ - декабрь 2025 (если есть)
                
                # ===== ПРОМЫШЛЕННОСТЬ =====
                "SGZH": "SZZ5",   # Сегежа Групп - декабрь 2025
                "LEAS": "LEZ5",   # Европлан - декабрь 2025
                "BELUGA": "NBZ5", # НоваБев - декабрь 2025 (если есть)
                
                # ===== МЕЖДУНАРОДНЫЕ ETF И ДЕРИВАТИВЫ =====
                "SPY": "SFZ5",    # SPY ETF - декабрь 2025 (если есть)
                "QQQ": "NAZ5",    # NASDAQ QQQ ETF - декабрь 2025 (если есть)
                "DAX": "DXZ5",    # DAX ETF - декабрь 2025 (если есть)
                "HANG": "HSZ5",   # Hang Seng ETF - декабрь 2025 (если есть)
                "NIKKEI": "N2Z5", # Nikkei ETF - декабрь 2025 (если есть)
                "EURO50": "SXZ5", # Euro Stoxx 50 ETF - декабрь 2025 (если есть)
                "RUSSELL": "R2Z5", # Russell 2000 ETF - декабрь 2025 (если есть)
                "MSCI_EM": "EMZ5", # MSCI Emerging Markets ETF - декабрь 2025 (если есть)
                
                # ===== ВАЛЮТНЫЕ ПАРЫ (ФЬЮЧЕРСЫ) =====
                "USDRUB": "SIZ5", # USD/RUB - декабрь 2025
                "EURRUB": "EuZ5", # EUR/RUB - декабрь 2025  
                "CNYRUB": "CRZ5", # CNY/RUB - декабрь 2025
                "TRYRUB": "TYZ5", # TRY/RUB - декабрь 2025 (если есть)
                "HKDRUB": "HKZ5", # HKD/RUB - декабрь 2025 (если есть)
                
                # ===== ТОВАРНЫЕ ФЬЮЧЕРСЫ =====
                "GOLD_RUB": "GLZ5",   # Золото в рублях - декабрь 2025
                "SILVER_RUB": "SLZ5", # Серебро в рублях - декабрь 2025 (если есть)
                "BRENT": "BRZ5",      # Нефть Brent - декабрь 2025
                "NATGAS": "NGZ5",     # Природный газ - декабрь 2025 (если есть)
                "WHEAT": "WHZ5",      # Пшеница - декабрь 2025 (если есть)
                "SUGAR": "SUZ5",      # Сахар - декабрь 2025 (если есть)
                
                # ===== ИНДЕКСНЫЕ ФЬЮЧЕРСЫ =====
                "MOEX_IDX": "MXZ5",   # Индекс MOEX - декабрь 2025
                "RTS_IDX": "RIZ5",    # Индекс RTS - декабрь 2025
                "MOEX_MINI": "MMZ5",  # Мини MOEX - декабрь 2025
                "RTS_MINI": "RMZ5",   # Мини RTS - декабрь 2025 (если есть)
                
                # ===== НОВЫЕ И ПЕРСПЕКТИВНЫЕ АКТИВЫ =====
                "AFKS": "AKZ5",   # АФК Система - декабрь 2025
                "AQUA": "AQZ5",   # ИНАРКТИКА - декабрь 2025 (если есть)
                "VSMO": "VSZ5",   # ВСМПО-АВИСМА - декабрь 2025 (если есть)
                "KOGK": "KOZ5",   # Колэнерго - декабрь 2025 (если есть)
                "UPRO": "UPZ5",   # Юнипро - декабрь 2025 (если есть)
                "KOGK": "KOZ5",   # Колэнерго - декабрь 2025 (если есть)
                "UPRO": "UPZ5",   # Юнипро - декабрь 2025 (если есть)
                "TATN": "TNZ5",   # Татнефть - декабрь 2025 (если существует)
                "NLMK": "NLZ5",   # НЛМК - декабрь 2025 (если существует)
                "ALRS": "ALZ5",   # Алроса - декабрь 2025 (если существует)
                
                # В будущем здесь будет 300+ пар для выбора пользователями
                # Металлургия, химия, энергетика, технологии, ритейл, телеком, транспорт
                
                # ВРЕМЕННО ОТКЛЮЧЕНЫ ДЛЯ СТАБИЛЬНОСТИ:
                # Металлургия: 40+ пар
                # Химия и нефтехимия: 35+ пар  
                # Энергетика: 50+ инструментов
                # Технологии: 25+ пар
                # Ритейл и потребительские товары: 30+ пар
                # Телеком: 15+ инструментов
                # Транспорт: 20+ пар
                # Дополнительные ликвидные активы: 50+ пар
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
        """Получение стоимости одного лота фьючерса в рублях"""
        # Фьючерсы имеют разные размеры контрактов
        futures_multipliers = {
            "SBERF": 100,    # 1 контракт = 100 акций Сбербанка
            "GAZPF": 100,    # 1 контракт = 100 акций Газпрома
            "GKZ5": 10,      # 1 контракт = 10 акций ГМКНа
            "FSZ5": 1000,    # 1 контракт = 1000 акций ФСК ЕЭС
            "VBZ5": 1000,    # 1 контракт = 1000 акций ВТБ
            "LKZ5": 10,      # 1 контракт = 10 акций Лукойла
            "RNZ5": 10,      # 1 контракт = 10 акций Роснефти
            "TNZ5": 10,      # 1 контракт = 10 акций Татнефти
            "NLZ5": 100,     # 1 контракт = 100 акций НЛМК
            "ALZ5": 100,     # 1 контракт = 100 акций Алросы
        }
        return futures_multipliers.get(ticker, 1)
    
    def get_random_monitoring_interval(self) -> int:
        """Получение случайного интервала мониторинга между 5-7 минутами"""
        return random.randint(self.MONITORING_INTERVAL_MIN, self.MONITORING_INTERVAL_MAX)
    
    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """Проверка, открыта ли биржа в указанное время"""
        if dt is None:
            # Используем московское время - UTC + 3 часа сейчас зимой
            import pytz
            moscow_tz = pytz.timezone('Europe/Moscow')
            dt = datetime.now(moscow_tz)
        
        # Проверяем день недели (0=Понедельник, 6=Воскресенье)
        if dt.weekday() not in self.TRADING_DAYS:
            return False
        
        # Проверяем время торгов
        current_time = dt.time()
        return self.TRADING_START_TIME <= current_time <= self.TRADING_END_TIME
    
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
