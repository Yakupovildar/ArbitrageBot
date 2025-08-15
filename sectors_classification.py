#!/usr/bin/env python3
"""
Классификация торговых пар по экономическим секторам
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum

class EconomicSector(Enum):
    """Экономические секторы российского рынка"""
    BANKS = "🏦 Банки"
    OIL_GAS = "⛽ Нефть и газ"
    METALS = "🏭 Металлургия"
    TELECOM = "📱 Телекоммуникации"
    RETAIL = "🛒 Розничная торговля"
    TECH = "💻 Технологии"
    TRANSPORT = "🚛 Транспорт и логистика"
    UTILITIES = "⚡ Энергетика"
    CHEMICALS = "🧪 Химия и удобрения"
    REAL_ESTATE = "🏢 Недвижимость"
    FOOD = "🍕 Пищевая промышленность"
    CONSUMER_GOODS = "🛍️ Потребительские товары"
    PHARMACEUTICALS = "💊 Фармацевтика"
    CONSTRUCTION = "🏗️ Строительство"
    MEDIA = "📺 Медиа и развлечения"

@dataclass
class CompanyInfo:
    """Информация о компании"""
    ticker: str
    name: str
    sector: EconomicSector
    description: str

class SectorClassification:
    """Классификация компаний по секторам"""
    
    def __init__(self):
        self.companies = {
            # БАНКИ
            "SBER": CompanyInfo("SBER", "Сбербанк", EconomicSector.BANKS, "Крупнейший банк России"),
            "VTBR": CompanyInfo("VTBR", "ВТБ", EconomicSector.BANKS, "Второй по величине банк России"),
            
            # НЕФТЬ И ГАЗ
            "GAZP": CompanyInfo("GAZP", "Газпром", EconomicSector.OIL_GAS, "Крупнейшая газовая компания"),
            "LKOH": CompanyInfo("LKOH", "Лукойл", EconomicSector.OIL_GAS, "Вертикально интегрированная нефтяная компания"),
            "ROSN": CompanyInfo("ROSN", "Роснефть", EconomicSector.OIL_GAS, "Крупнейшая нефтяная компания России"),
            "TATN": CompanyInfo("TATN", "Татнефть", EconomicSector.OIL_GAS, "Региональная нефтяная компания"),
            "SNGS": CompanyInfo("SNGS", "Сургутнефтегаз", EconomicSector.OIL_GAS, "Нефтегазовая компания"),
            
            # МЕТАЛЛУРГИЯ
            "GMKN": CompanyInfo("GMKN", "ГМК Норильский никель", EconomicSector.METALS, "Цветная металлургия, никель и палладий"),
            "ALRS": CompanyInfo("ALRS", "АЛРОСА", EconomicSector.METALS, "Алмазодобывающая компания"),
            "NLMK": CompanyInfo("NLMK", "НЛМК", EconomicSector.METALS, "Черная металлургия"),
            "CHMF": CompanyInfo("CHMF", "Северсталь", EconomicSector.METALS, "Черная металлургия"),
            "RUAL": CompanyInfo("RUAL", "РУСАЛ", EconomicSector.METALS, "Алюминиевая промышленность"),
            "MAGN": CompanyInfo("MAGN", "ММК", EconomicSector.METALS, "Магнитогорский металлургический комбинат"),
            "AKRN": CompanyInfo("AKRN", "Акрон", EconomicSector.CHEMICALS, "Минеральные удобрения"),
            "PHOR": CompanyInfo("PHOR", "ФосАгро", EconomicSector.CHEMICALS, "Фосфорные удобрения"),
            
            # ТЕЛЕКОММУНИКАЦИИ
            "MTSS": CompanyInfo("MTSS", "МТС", EconomicSector.TELECOM, "Мобильная связь"),
            "RTKM": CompanyInfo("RTKM", "Ростелеком", EconomicSector.TELECOM, "Фиксированная связь"),
            
            # ТЕХНОЛОГИИ
            "TCSG": CompanyInfo("TCSG", "TCS Group", EconomicSector.TECH, "Финтех, Тинькофф банк"),
            "OZON": CompanyInfo("OZON", "Ozon", EconomicSector.TECH, "Интернет-торговля"),
            "HHRU": CompanyInfo("HHRU", "HeadHunter", EconomicSector.TECH, "HR-технологии"),
            "MAIL": CompanyInfo("MAIL", "VK (Mail.ru)", EconomicSector.TECH, "Интернет и IT-услуги"),
            "QIWI": CompanyInfo("QIWI", "QIWI", EconomicSector.TECH, "Платежные системы"),
            
            # РОЗНИЧНАЯ ТОРГОВЛЯ
            "MGNT": CompanyInfo("MGNT", "Магнит", EconomicSector.RETAIL, "Продуктовый ритейл"),
            "FIVE": CompanyInfo("FIVE", "X5 Retail Group", EconomicSector.RETAIL, "Продуктовый ритейл (Пятерочка)"),
            "DIXY": CompanyInfo("DIXY", "Дикси", EconomicSector.RETAIL, "Продуктовый ритейл"),
            
            # ТРАНСПОРТ И ЛОГИСТИКА
            "AFLT": CompanyInfo("AFLT", "Аэрофлот", EconomicSector.TRANSPORT, "Авиаперевозки"),
            
            # ЭНЕРГЕТИКА
            "HYDR": CompanyInfo("HYDR", "РусГидро", EconomicSector.UTILITIES, "Гидроэнергетика"),
            "IRAO": CompanyInfo("IRAO", "Интер РАО", EconomicSector.UTILITIES, "Энергетика"),
            "MOEX": CompanyInfo("MOEX", "Московская Биржа", EconomicSector.UTILITIES, "Биржевые услуги"),
            
            # НЕДВИЖИМОСТЬ И СТРОИТЕЛЬСТВО
            "LSRG": CompanyInfo("LSRG", "ЛСР", EconomicSector.REAL_ESTATE, "Строительство и недвижимость"),
            "PIKK": CompanyInfo("PIKK", "ПИК", EconomicSector.REAL_ESTATE, "Жилищное строительство"),
            
            # ПОТРЕБИТЕЛЬСКИЕ ТОВАРЫ
            "FLOT": CompanyInfo("FLOT", "Совкомфлот", EconomicSector.TRANSPORT, "Морские перевозки"),
            "FEES": CompanyInfo("FEES", "ФСК ЕЭС", EconomicSector.UTILITIES, "Электросетевая компания"),
            "ETLN": CompanyInfo("ETLN", "Etalon Group", EconomicSector.REAL_ESTATE, "Недвижимость"),
            "CBOM": CompanyInfo("CBOM", "МКБ", EconomicSector.BANKS, "Московский кредитный банк"),
            
            # ОСТАЛЬНЫЕ КОМПАНИИ (требуют доисследования)
            "SGZH": CompanyInfo("SGZH", "Сегежа Групп", EconomicSector.CONSUMER_GOODS, "ЦБП и упаковка"),
            "BANE": CompanyInfo("BANE", "Башнефть обыкн", EconomicSector.OIL_GAS, "Региональная нефтяная компания"),
            "BANEP": CompanyInfo("BANEP", "Башнефть прив", EconomicSector.OIL_GAS, "Привилегированные акции Башнефти"),
            "BSPB": CompanyInfo("BSPB", "Банк Санкт-Петербург", EconomicSector.BANKS, "Региональный банк"),
            "DSKY": CompanyInfo("DSKY", "Детский мир", EconomicSector.RETAIL, "Детские товары"),
            "AFKS": CompanyInfo("AFKS", "Система", EconomicSector.TECH, "Диверсифицированный холдинг"),
            "APTK": CompanyInfo("APTK", "Аптечная сеть 36.6", EconomicSector.PHARMACEUTICALS, "Фармацевтический ритейл"),
            "NKNC": CompanyInfo("NKNC", "НКНХ", EconomicSector.CHEMICALS, "Нефтехимия"),
            "FIXP": CompanyInfo("FIXP", "Fix Price", EconomicSector.RETAIL, "Товары по фиксированным ценам"),
            "GEMC": CompanyInfo("GEMC", "ЕМС", EconomicSector.CONSUMER_GOODS, "Производство товаров"),
            "KMAZ": CompanyInfo("KMAZ", "КАМАЗ", EconomicSector.TRANSPORT, "Производство грузовиков"),
            "MSNG": CompanyInfo("MSNG", "МосЭнерго", EconomicSector.UTILITIES, "Электроэнергетика"),
            "PLZL": CompanyInfo("PLZL", "Полюс", EconomicSector.METALS, "Золотодобыча"),
            "PMSB": CompanyInfo("PMSB", "Промсвязьбанк", EconomicSector.BANKS, "Коммерческий банк"),
            "POLY": CompanyInfo("POLY", "Polymetal", EconomicSector.METALS, "Драгметаллы"),
            "PRTK": CompanyInfo("PRTK", "Протек", EconomicSector.PHARMACEUTICALS, "Фармацевтическая дистрибуция"),
            "RASP": CompanyInfo("RASP", "Распадская", EconomicSector.METALS, "Угледобыча"),
            "RENI": CompanyInfo("RENI", "Ренессанс страхование", EconomicSector.UTILITIES, "Страхование"),
            "SMLT": CompanyInfo("SMLT", "Самолет", EconomicSector.REAL_ESTATE, "Девелопмент"),
            "TRNFP": CompanyInfo("TRNFP", "Транснефть (прив)", EconomicSector.OIL_GAS, "Трубопроводный транспорт"),
            "YAKG": CompanyInfo("YAKG", "ЯТЭК", EconomicSector.UTILITIES, "Коммунальные услуги"),
            "ABIO": CompanyInfo("ABIO", "Артген", EconomicSector.PHARMACEUTICALS, "Биотехнологии")
        }
    
    def get_sectors_dict(self) -> Dict[EconomicSector, List[Tuple[str, str]]]:
        """Группировка торговых пар по секторам"""
        from config import Config
        config = Config()
        
        sectors_dict = {}
        
        # Получаем все торговые пары
        trading_pairs = config.MONITORED_INSTRUMENTS
        
        for stock_ticker, futures_ticker in trading_pairs:
            if stock_ticker in self.companies:
                company_info = self.companies[stock_ticker]
                sector = company_info.sector
                
                if sector not in sectors_dict:
                    sectors_dict[sector] = []
                
                sectors_dict[sector].append((stock_ticker, futures_ticker))
        
        return sectors_dict
    
    def get_sector_name(self, ticker: str) -> str:
        """Получение названия сектора для тикера"""
        if ticker in self.companies:
            return self.companies[ticker].sector.value
        return "🔍 Прочее"
    
    def get_company_description(self, ticker: str) -> str:
        """Получение описания компании"""
        if ticker in self.companies:
            return f"{self.companies[ticker].name} - {self.companies[ticker].description}"
        return f"Компания {ticker}"

# Глобальный экземпляр
sector_classifier = SectorClassification()