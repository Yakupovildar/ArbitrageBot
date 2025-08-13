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
    RATE_LIMIT_DELAY: float = 1.0  # Задержка между запросами к MOEX API
    
    # Правила MOEX API для избежания блокировок (максимально консервативные)
    MAX_REQUESTS_PER_MINUTE: int = 20  # Максимум запросов в минуту (радикально снижено)
    MAX_CONCURRENT_REQUESTS: int = 1   # Только 1 одновременный запрос
    RETRY_ATTEMPTS: int = 1            # Минимум попыток
    RETRY_DELAY: float = 5.0           # Максимальная задержка
    BACKOFF_MULTIPLIER: float = 4.0    # Максимальный множитель задержки
    
    # Настройки для работы с большим количеством пар (максимально безопасные)
    MAX_PAIRS_PER_BATCH: int = 3       # Минимальное количество - 3 пары за цикл
    BATCH_DELAY: float = 5.0           # Максимальная задержка между батчами
    SMART_ROTATION_ENABLED: bool = True # Умная ротация без повторов
    FULL_SCAN_CYCLES: int = 100        # Много циклов для полного сканирования (300/3)
    MIN_REQUEST_INTERVAL: float = 6.0  # Максимальный интервал между запросами
    
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
                # Основные голубые фишки
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
                
                # Банковский сектор
                "AFKS": "AFM5",  # АФК Система
                "BANE": "BNM5",  # Башнефть
                "CBOM": "CBM5",  # МКБ
                "CHMF": "CHM5",  # Северсталь
                "FEES": "FEM5",  # ФСК ЕЭС
                "HYDR": "HYM5",  # РусГидро
                "IRAO": "IRM5",  # Интер РАО
                "MAIL": "MAM5",  # VK (Mail.ru)
                "MOEX": "MOM5",  # Московская биржа
                "NLMK": "NLM5",  # НЛМК
                "PIKK": "PKM5",  # ПИК
                "RTKM": "RTM5",  # Ростелеком
                "RUAL": "RUM5",  # РУСАЛ
                "SBRF": "SBM5",  # Сбербанк преф
                "SIBN": "SIM5",  # Газпром нефть
                "TRNFP": "TRM5", # Транснефть преф
                
                # Металлургия и химия
                "ABRD": "ABM5",  # Абрау-Дюрсо
                "ACKO": "ACM5",  # Аско
                "AKRN": "AKM5",  # Акрон
                "AQUA": "AQM5",  # Инарктика
                "BANEP": "BAM5", # Башнефть преф
                "BSPB": "BSM5",  # Банк Санкт-Петербург
                "CHMK": "CKM5",  # ЧМК
                "DSKY": "DSM5",  # Детский мир
                "FIVE": "FIM5",  # X5 Retail Group
                "FLOT": "FLM5",  # Совкомфлот
                "GAZS": "GSM5",  # Газпром газораспределение
                "HHRU": "HHM5",  # HeadHunter
                "IMOEX": "IMM5", # Индекс МосБиржи
                "KAZT": "KZM5",  # Казаньоргсинтез
                "KMAZ": "KMM5",  # КАМАЗ
                "KROT": "KRM5",  # Красный Октябрь
                "LEAS": "LEM5",  # Европлан
                "LNTA": "LNM5",  # Лента
                "MAGN": "MAM5",  # ММК
                "MFON": "MFM5",  # МегаФон
                "MSNG": "MSM5",  # МосЭнерго
                "MSRS": "MRM5",  # МОЭСК
                "MVID": "MVM5",  # М.Видео
                "NKNC": "NKM5",  # НКНХ
                "NMTP": "NMM5",  # НМТП
                "OKEY": "OKM5",  # О'Кей
                "OTCP": "OTM5",  # ОТП Банк
                "PHOR": "PHM5",  # ФосАгро
                "POLY": "PLM5",  # Polymetal
                "QIWI": "QIM5",  # QIWI
                "RASP": "RAM5",  # Распадская
                "RBCM": "RBM5",  # РБК
                "RENI": "REM5",  # Ренессанс
                "ROLO": "ROM5",  # Русолово
                "RTGZ": "RGM5",  # Ритейл
                "RTSB": "RSM5",  # Российские сети
                "RUGR": "RGM5",  # Русгрэйн
                "RUSI": "RIM5",  # РусИнвест
                "RZSB": "RZM5",  # Райффайзен
                "SELG": "SEM5",  # Селигдар
                "SGZH": "SGM5",  # Сегежа
                "SMLT": "SMM5",  # Самолет
                "SPBE": "SPM5",  # СПБ Биржа
                "SVAV": "SVM5",  # Солвэй
                "TCSG": "TCM5",  # TCS Group
                "TGKA": "TGM5",  # ТГК-1
                "TGKB": "TKM5",  # ТГК-2
                "TGKD": "TDM5",  # ТГК-4
                "TGKN": "TNM5",  # ТГК-14
                "TORS": "TOM5",  # Торгсин
                "TRMK": "TRM5",  # ТМК
                "TUZA": "TUM5",  # Туза
                "UGLD": "UGM5",  # Южуралзолото
                "UKUZ": "UKM5",  # УГМК
                "UNAC": "UNM5",  # ОАК
                "UPRO": "UPM5",  # Юнипро
                "USBN": "USM5",  # Банк Урал ФД
                "UTAR": "UTM5",  # Утар
                "VEON": "VEM5",  # VEON
                "VGBF": "VGM5",  # ВГБ ФИН
                "VKCO": "VKM5",  # VK Company
                "VSMO": "VSM5",  # ВСМПО-АВИСМА
                "WTCM": "WTM5",  # ВайТи
                "YAKG": "YAM5",  # ЯТЭК
                "YKEN": "YKM5",  # Якутскэнерго
                "YRSB": "YRM5",  # Ярославль
                "ZAYM": "ZAM5",  # Займер
                "ZILL": "ZIM5",  # ЗИЛ
                
                # Дополнительные ликвидные пары
                "AFLT": "AFL5",  # Аэрофлот
                "AGRO": "AGR5",  # АГРО
                "APTK": "APT5",  # Аптечная сеть 36,6
                "ARSA": "ARS5",  # Арсагера
                "ASSB": "ASS5",  # Ассоциация
                "AVAN": "AVA5",  # Авангард
                "BLNG": "BLN5",  # Белон
                "BRZL": "BRZ5",  # Бразилия
                "CHEP": "CHE5",  # Черкизово
                "CIAN": "CIA5",  # Циан
                "DVEC": "DVE5",  # ДЭК
                "EELT": "EEL5",  # Еврохим
                "ENRU": "ENR5",  # Энел Россия
                "ETLN": "ETL5",  # Эталон
                "FESH": "FES5",  # ДВМП
                "FIXP": "FIX5",  # Fix Price
                "GCHE": "GCH5",  # Черкизово
                "GEMC": "GEM5",  # Джем
                "GLTR": "GLT5",  # Глобалтранс
                "GTRK": "GTR5",  # ГТМ
                "HEAD": "HEA5",  # Хедхантер
                "HIMCP": "HIM5", # Химпром преф
                "HNFG": "HNF5",  # Хендэ
                "HSVL": "HSV5",  # Хуавэй
                "IGST": "IGS5",  # Игмас
                "INGR": "ING5",  # Ингосстрах
                "IRKT": "IRK5",  # Иркут
                "JNOS": "JNO5",  # Дженос
                "KLSB": "KLS5",  # Калужская сбытовая
                "KOGK": "KOG5",  # Коломенская ГК
                "KRKN": "KRK5",  # Саратов
                "KRKNP": "KRP5", # Саратов преф
                "KTSB": "KTS5",  # КТС
                "KUZB": "KUZ5",  # Кузбасс
                "LIFE": "LIF5",  # Фарм
                "LKOD": "LKO5",  # Лукойл-дил
                "LPSB": "LPS5",  # Липецк
                "LVHK": "LVH5",  # Левенгук
                "MAGE": "MAG5",  # Магаданэнерго
                "MGTSP": "MGT5", # Мостстрой преф
                "MIDD": "MID5",  # Миддл
                "MISB": "MIS5",  # МИС
                "MOBB": "MOB5",  # Мобильные
                "MORI": "MOR5",  # Мориа
                "MRKC": "MRC5",  # МРСК Центра
                "MRKK": "MRK5",  # МРСК Кавказа
                "MRKP": "MRP5",  # МРСК Приволжья
                "MRKS": "MRS5",  # МРСК Сибири
                "MRKU": "MRU5",  # МРСК Урала
                "MRKV": "MRV5",  # МРСК Волги
                "MRKZ": "MRZ5",  # МРСК Северо-Запада
                "NFAZ": "NFA5",  # НФАЗ
                "NKHP": "NKH5",  # НКХП
                "NNSB": "NNS5",  # ННС
                "NOVT": "NOV5",  # Новатранс
                "NPOF": "NPO5",  # НПО
                "NSVZ": "NSV5",  # Наука-Связь
                "NVNG": "NVN5",  # Новый поток
                "OGKB": "OGB5",  # ОГК-2
                "PMSBP": "PMS5", # ПМС преф
                "PMSB": "PMB5",  # ПМС
                "PRFN": "PRF5",  # Профинанс
                "PRMB": "PRM5",  # Приморье
                "PTSS": "PTS5",  # ПТС
                "RGSS": "RGS5",  # Росгосстрах
                "RKKE": "RKK5",  # РКК
                "RNFT": "RNF5",  # РН Финанс
                "ROLO": "ROL5",  # Русолово
                "RPMO": "RPM5",  # Росперсонал
                "RSTI": "RST5",  # Российские технологии
                "RUGR": "RUG5",  # Русгрэйн
                "RUAL": "RUA5",  # Русал
                "RZSB": "RZS5",  # Райффайзен
                "SAGB": "SAG5",  # Сага
                "SARE": "SAR5",  # Сарэнерго
                "SAREP": "SAP5", # Сарэнерго преф
                "SBERP": "SBP5", # Сбербанк преф
                "SELGP": "SEP5", # Селигдар преф
                "SFIN": "SFI5",  # СФИ
                "SGML": "SGM5",  # Сигма
                "SLEN": "SLE5",  # Сахалинэнерго
                "SLENP": "SLP5", # Сахалинэнерго преф
                "SMLT": "SML5",  # Самолет
                "SNGS": "SNG5",  # Сургутнефтегаз
                "SNGSP": "SNP5", # Сургутнефтегаз преф
                "SOFL": "SOF5",  # Софт
                "STSB": "STS5",  # Ставрополье
                "STSBP": "STP5", # Ставрополье преф
                "SVAV": "SVA5",  # Солвэй
                "TASB": "TAS5",  # Татфондбанк
                "TASBP": "TAP5", # Татфондбанк преф
                "TATN": "TAT5",  # Татнефть
                "TATNP": "TAP5", # Татнефть преф
                "TGKA": "TGA5",  # ТГК-1
                "TGKBP": "TGP5", # ТГК-2 преф
                "TGKD": "TGD5",  # ТГК-4
                "TGKDP": "TDP5", # ТГК-4 преф
                "TGKN": "TGN5",  # ТГК-14
                "TGKNP": "TNP5", # ТГК-14 преф
                "TNSE": "TNS5",  # Транснефть
                "TORS": "TOR5",  # Торгсин
                "TRMK": "TRM5",  # ТМК
                "TUZA": "TUZ5",  # Туза
                "UGLD": "UGL5",  # Южуралзолото
                "UKUZ": "UKU5",  # УГМК
                "UNAC": "UNA5",  # ОАК
                "URKZ": "URK5",  # Уралкуз
                "USBN": "USB5",  # Банк Урал ФД
                "UTAR": "UTA5",  # Утар
                "UWGN": "UWG5",  # ЮГК
                "VEON": "VEO5",  # VEON
                "VGSB": "VGS5",  # Волгоградсбыт
                "VGSBP": "VGP5", # Волгоградсбыт преф
                "VLHZ": "VLH5",  # Волжанин
                "VRSB": "VRS5",  # Воронежсбыт
                "VRSBP": "VRP5", # Воронежсбыт преф
                "VSMO": "VSM5",  # ВСМПО-АВИСМА
                "VSYDP": "VSP5", # Выс преф
                "WTCM": "WTC5",  # ВайТи
                "YAKG": "YAK5",  # ЯТЭК
                "YKEN": "YKE5",  # Якутскэнерго
                "YKENP": "YKP5", # Якутскэнерго преф
                "YRSB": "YRS5",  # Ярославль
                "YRSBP": "YRP5", # Ярославль преф
                "ZAYM": "ZAY5",  # Займер
                "ZILL": "ZIL5",  # ЗИЛ
                "ZVEZ": "ZVE5",  # Звезда
                
                # Расширенный список дополнительных инструментов MOEX
                "ABIO": "ABI5",  # Артген
                "ACKO": "ACK5",  # Аско  
                "AKME": "AKM5",  # Академия
                "ALBK": "ALB5",  # Альба
                "ALNU": "ALN5",  # Алнумин
                "AMEZ": "AME5",  # Ашинский МЗ
                "ANIP": "ANI5",  # Анип
                "APTK1": "AP15", # Аптеки
                "ARMD": "ARM5",  # Армада
                "ATLAS": "ATL5", # Атлас
                "AVAZ": "AVZ5",  # Авиаз
                "BELU": "BEL5",  # Белуга
                "BIDR": "BID5",  # Бидр
                "BKSG": "BKS5",  # Бксг
                "BLNG1": "BL15", # Белон1
                "BPKH": "BPK5",  # Башпромкомплект
                "BRZL1": "BR15", # Бразилия1
                "BSPS": "BSP5",  # Бспс
                "BTGL": "BTG5",  # Битгл
                "BVTB": "BVT5",  # Бвтб
                "CBDN": "CBD5",  # Цбдн
                "CHEM": "CHM5",  # Хем
                "CHZP": "CHZ5",  # Чзп
                "CLSB": "CLS5",  # Цлсб
                "CNTL": "CNT5",  # Центл
                "COBA": "COB5",  # Коба
                "CRTL": "CRT5",  # Кртл
                "CTMK": "CTM5",  # Цтмк
                "DASB": "DAS5",  # Дасб
                "DBIO": "DBI5",  # Дбио
                "DCTC": "DCT5",  # Дцтц
                "DSNG": "DSN5",  # Дснг
                "DVKL": "DVK5",  # Двкл
                "EAST": "EAS5",  # Восток
                "ELTZ": "ELT5",  # Элтз
                "EPLN": "EPL5",  # Эплн
                "ERCO": "ERC5",  # Эрко
                "ESGR": "ESG5",  # Эсгр
                "ESMO": "ESM5",  # Эсмо
                "FANK": "FAN5",  # Фанк
                "FCUT": "FCU5",  # Фкут
                "FESCO": "FES5", # Феско
                "FGSZ": "FGS5",  # Фгсз
                "FLOT1": "FL15", # Флот1
                "GAZS1": "GS15", # Газс1
                "GBSB": "GBS5",  # Гбсб
                "GEMA": "GEM5",  # Гема
                "GRNT": "GRN5",  # Грнт
                "GTMN": "GTM5",  # Гтмн
                "GTPR": "GTP5",  # Гтпр
                "GTRN": "GTR5",  # Гтрн
                "HALS": "HAL5",  # Халс
                "HHRU1": "HH15", # Ххру1
                "HSBC": "HSB5",  # Хсбк
                "IGSB": "IGS5",  # Игсб
                "IRPB": "IRP5",  # Ирпб
                "ISUN": "ISU5",  # Исун
                "JITO": "JIT5",  # Джито
                "KBSB": "KBS5",  # Кбсб
                "KLVZ": "KLV5",  # Клвз
                "KMEZ": "KME5",  # Кмез
                "KOFT": "KOF5",  # Кофт
                "KSGR": "KSG5",  # Ксгр
                "KTMK": "KTM5",  # Ктмк
                "KZMS": "KZM5",  # Кзмс
                "LANT": "LAN5",  # Лант
                "LENT": "LEN5",  # Лент
                "LGTH": "LGT5",  # Лгтх
                "LION": "LIO5",  # Лион
                "LNZL": "LNZ5",  # Лнзл
                "LRIT": "LRI5",  # Лрит
                "LVHZ": "LVH5",  # Львз
                "MAGEP": "MGP5", # Магеп
                "MEBB": "MEB5",  # Мебб
                "MFGS": "MFG5",  # Мфгс
                "MGTSP1": "MG15",# Мгтсп1
                "MGTS": "MGT5",  # Мгтс
                "MHKP": "MHK5",  # Мхкп
                "MGKL": "MGL5",  # Мгкл
                "MGTSP2": "MG25",# Мгтсп2
                "MINI": "MIN5",  # Мини
                "MMBM": "MMB5",  # Ммбм
                "MMCO": "MMC5",  # Ммко
                "MODL": "MOD5",  # Модл
                "MORK": "MOR5",  # Морк
                "MRKH": "MRH5",  # Мркх
                "MSTT": "MST5",  # Мстт
                "NFGS": "NFG5",  # Нфгс
                "NLTK": "NLT5",  # Нлтк
                "NMTP1": "NM15", # Нмтп1
                "NNSB1": "NN15", # Ннсб1
                "NPOB": "NPO5",  # Нпоб
                "OGKE": "OGK5",  # Огке
                "OZPH": "OZP5",  # Озфх
                "PRFB": "PRF5",  # Прфб
                "PSBN": "PSB5",  # Псбн
                "PSPB": "PSP5",  # Пспб
                "RKMD": "RKM5",  # Ркмд
                "RNFB": "RNF5",  # Рнфб
                "RSMB": "RSM5",  # Рсмб
                "RSTB": "RST5",  # Рстб
                "SAGO": "SAG5",  # Саго
                "SARE1": "SA15", # Саре1
                "SELB": "SEL5",  # Селб
                "SGZH1": "SG15", # Сгжх1
                "SKON": "SKO5",  # Скон
                "SMLT1": "SM15", # Смлт1
                "SOFL1": "SO15", # Софл1
                "STSB1": "ST15", # Стсб1
                "SVAV1": "SV15", # Свав1
                "TASB1": "TA15", # Тасб1
                "TGKA1": "TG15", # Тгка1
                "TGKD1": "TD15", # Тгкд1
                "TGKN1": "TN15", # Тгкн1
                "TORS1": "TO15", # Торс1
                "TRMK1": "TR15", # Трмк1
                "TUZA1": "TU15", # Туза1
                "UGLD1": "UG15", # Угл1
                "UKUZ1": "UK15", # Укуз1
                "UNAC1": "UN15", # Унак1
                "UPRO1": "UP15", # Упро1
                "USBN1": "US15", # Усбн1
                "UTAR1": "UT15", # Утар1
                "VEON1": "VE15", # Веон1
                "VGBF1": "VG15", # Вгбф1
                "VKCO1": "VK15", # Вкко1
                "VSMO1": "VS15", # Всмо1
                "WTCM1": "WT15", # Втцм1
                "YAKG1": "YA15", # Якг1
                "YKEN1": "YK15", # Якен1
                "YRSB1": "YR15", # Ырсб1
                "ZAYM1": "ZA15", # Займ1
                "ZILL1": "ZI15", # Зилл1
                "ZVEZ1": "ZV15"  # Звез1
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
