"""
Библиотека источников данных для арбитражного бота
Содержит все доступные источники данных с автоматической заменой неисправных
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from database import db

logger = logging.getLogger(__name__)

class SourcesLibrary:
    """Библиотека всех доступных источников данных"""
    
    def __init__(self):
        self.all_sources = {
            # Российские биржи и брокеры
            "moex": {
                "name": "MOEX ISS API",
                "url": "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json",
                "type": "official_exchange",
                "reliability": 95,
                "requires_auth": False,
                "description": "Официальный API Московской биржи"
            },
            "spbex": {
                "name": "СПБ Биржа API",
                "url": "https://api.spbexchange.ru/market-data/v1/securities",
                "type": "official_exchange", 
                "reliability": 90,
                "requires_auth": False,
                "description": "Официальный API СПБ Биржи"
            },
            "tinkoff": {
                "name": "Tinkoff Invest API",
                "url": "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService",
                "type": "broker_api",
                "reliability": 85,
                "requires_auth": True,
                "description": "API Тинькофф Инвестиции"
            },
            "sberbank": {
                "name": "Sberbank Invest API", 
                "url": "https://api.sberbank.ru/investments/v1/instruments",
                "type": "broker_api",
                "reliability": 85,
                "requires_auth": True,
                "description": "API Сбербанк Инвестиции"
            },
            "bcs": {
                "name": "БКС Брокер API",
                "url": "https://bcs-express.ru/api/v1/market/instruments",
                "type": "broker_api",
                "reliability": 80,
                "requires_auth": True,
                "description": "API БКС Брокер"
            },
            "vtb": {
                "name": "ВТБ Инвестиции API",
                "url": "https://api.vtb.ru/investments/v1/instruments",
                "type": "broker_api",
                "reliability": 80,
                "requires_auth": True,
                "description": "API ВТБ Инвестиции"
            },
            "finam": {
                "name": "Finam Trade API",
                "url": "https://trade-api.finam.ru/public/api/v1/time",
                "type": "broker_api",
                "reliability": 75,
                "requires_auth": True,
                "description": "API Финам"
            },
            "alfa": {
                "name": "Альфа-Директ API",
                "url": "https://api.alfadirect.ru/v2/instruments",
                "type": "broker_api",
                "reliability": 80,
                "requires_auth": True,
                "description": "API Альфа-Директ"
            },
            "open": {
                "name": "Открытие Брокер API",
                "url": "https://api.open-broker.ru/api/market/v1/securities",
                "type": "broker_api",
                "reliability": 75,
                "requires_auth": True,
                "description": "API Открытие Брокер"
            },
            "kit": {
                "name": "КИТ Финанс API",
                "url": "https://api.kit-invest.ru/v1/market/instruments",
                "type": "broker_api",
                "reliability": 70,
                "requires_auth": True,
                "description": "API КИТ Финанс"
            },
            
            # Международные источники данных
            "tradingview": {
                "name": "TradingView Scanner",
                "url": "https://scanner.tradingview.com/russia/scan",
                "type": "data_provider",
                "reliability": 85,
                "requires_auth": False,
                "description": "Сканер TradingView для российских инструментов"
            },
            "investing_com": {
                "name": "Investing.com",
                "url": "https://www.investing.com/equities/russia",
                "type": "data_provider",
                "reliability": 80,
                "requires_auth": False,
                "description": "Investing.com российские акции"
            },
            "yahoo_finance": {
                "name": "Yahoo Finance",
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/GAZP.ME",
                "type": "data_provider",
                "reliability": 70,
                "requires_auth": False,
                "description": "Yahoo Finance для российских инструментов"
            },
            "alpha_vantage": {
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo",
                "type": "data_provider",
                "reliability": 75,
                "requires_auth": True,
                "description": "Alpha Vantage API"
            },
            "quandl": {
                "name": "Quandl API",
                "url": "https://www.quandl.com/api/v3/datasets/MCX/",
                "type": "data_provider",
                "reliability": 75,
                "requires_auth": True,
                "description": "Quandl финансовые данные"
            },
            "iex": {
                "name": "IEX Cloud",
                "url": "https://cloud.iexapis.com/stable/stock/market/batch",
                "type": "data_provider",
                "reliability": 80,
                "requires_auth": True,
                "description": "IEX Cloud API"
            },
            
            # Криптовалютные биржи (могут иметь российские фьючерсы)
            "binance": {
                "name": "Binance API",
                "url": "https://api.binance.com/api/v3/ticker/price",
                "type": "crypto_exchange",
                "reliability": 90,
                "requires_auth": False,
                "description": "Binance API для глобальных данных"
            },
            "okx": {
                "name": "OKX API",
                "url": "https://www.okx.com/api/v5/market/ticker",
                "type": "crypto_exchange",
                "reliability": 85,
                "requires_auth": False,
                "description": "OKX API"
            },
            
            # Дополнительные российские источники
            "dohodinfo": {
                "name": "DohodInfo API",
                "url": "https://dohodinfo.ru/api/v1/quotes",
                "type": "data_provider",
                "reliability": 65,
                "requires_auth": False,
                "description": "DohodInfo финансовые данные"
            },
            "smart_lab": {
                "name": "Smart-Lab API",
                "url": "https://smart-lab.ru/q/shares_fundamental/",
                "type": "data_provider",
                "reliability": 60,
                "requires_auth": False,
                "description": "Smart-Lab данные"
            },
            "rbc_quote": {
                "name": "РБК Котировки API",
                "url": "https://quote.rbc.ru/ajax/shares/",
                "type": "data_provider",
                "reliability": 70,
                "requires_auth": False,
                "description": "РБК котировки"
            },
            "cbr": {
                "name": "ЦБ РФ API",
                "url": "https://www.cbr-xml-daily.ru/daily_json.js",
                "type": "official_data",
                "reliability": 95,
                "requires_auth": False,
                "description": "Официальные курсы ЦБ РФ"
            }
        }
        
        # Активные источники (используемые в данный момент)
        self.active_sources = []
        self.failed_attempts = {}  # source_name -> attempts count
        self.replacement_history = {}  # source_name -> replaced_by
        
    async def test_source_connection(self, source_key: str) -> Tuple[bool, Optional[str]]:
        """Тестирование подключения к источнику"""
        if source_key not in self.all_sources:
            return False, "Источник не найден в библиотеке"
            
        source = self.all_sources[source_key]
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(source["url"]) as response:
                    if response.status == 200:
                        return True, None
                    elif response.status == 403:
                        return False, "Доступ запрещен (возможно требуется API ключ)"
                    elif response.status == 429:
                        return False, "Превышен лимит запросов"
                    else:
                        return False, f"HTTP {response.status}"
                        
        except asyncio.TimeoutError:
            return False, "Таймаут подключения"
        except aiohttp.ClientConnectorError:
            return False, "Ошибка соединения"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
    
    async def find_working_sources(self, count: int = 10) -> List[str]:
        """Поиск работающих источников"""
        working_sources = []
        
        # Сортируем источники по надежности
        sorted_sources = sorted(
            self.all_sources.items(),
            key=lambda x: x[1]["reliability"],
            reverse=True
        )
        
        logger.info(f"🔍 Тестирование {len(sorted_sources)} источников данных...")
        
        # Тестируем источники параллельно группами по 5
        for i in range(0, len(sorted_sources), 5):
            batch = sorted_sources[i:i+5]
            
            # Создаем задачи для параллельного тестирования
            tasks = []
            for source_key, source_info in batch:
                task = self.test_source_connection(source_key)
                tasks.append((source_key, source_info, task))
            
            # Ждем результаты
            for source_key, source_info, task in tasks:
                try:
                    is_working, error = await task
                    
                    if is_working:
                        working_sources.append(source_key)
                        logger.info(f"✅ {source_info['name']}: работает")
                        
                        # Обновляем статус в базе данных
                        await db.update_source_status(source_key, "working")
                        
                        if len(working_sources) >= count:
                            break
                    else:
                        logger.warning(f"❌ {source_info['name']}: {error}")
                        await db.update_source_status(source_key, "error", error)
                        
                except Exception as e:
                    logger.error(f"Ошибка тестирования {source_key}: {e}")
                    await db.update_source_status(source_key, "error", str(e))
            
            if len(working_sources) >= count:
                break
            
            # Небольшая пауза между группами
            await asyncio.sleep(1)
        
        logger.info(f"🎯 Найдено {len(working_sources)} работающих источников из {count} требуемых")
        return working_sources[:count]
    
    async def replace_failed_source(self, failed_source: str) -> Optional[str]:
        """Замена неисправного источника на рабочий"""
        if failed_source not in self.active_sources:
            return None
            
        logger.info(f"🔄 Поиск замены для неисправного источника: {failed_source}")
        
        # Ищем источники, которые еще не использовались
        unused_sources = [
            key for key in self.all_sources.keys() 
            if key not in self.active_sources
        ]
        
        # Сортируем по надежности
        unused_sources.sort(
            key=lambda x: self.all_sources[x]["reliability"],
            reverse=True
        )
        
        # Тестируем источники по очереди
        for source_key in unused_sources:
            is_working, error = await self.test_source_connection(source_key)
            
            if is_working:
                # Заменяем источник
                index = self.active_sources.index(failed_source)
                self.active_sources[index] = source_key
                
                # Записываем историю замены
                self.replacement_history[failed_source] = source_key
                
                logger.info(f"✅ Источник {failed_source} заменен на {source_key}")
                logger.info(f"📝 {self.all_sources[source_key]['name']}")
                
                # Обновляем статусы в базе данных
                await db.update_source_status(failed_source, "replaced", f"Заменен на {source_key}")
                await db.update_source_status(source_key, "working")
                
                return source_key
        
        logger.warning(f"⚠️ Не найдена замена для источника {failed_source}")
        return None
    
    async def initialize_active_sources(self, count: int = 10) -> List[str]:
        """Инициализация активных источников при запуске"""
        logger.info(f"🚀 Инициализация {count} активных источников данных...")
        
        # Сбрасываем счетчики попыток
        self.failed_attempts = {}
        
        # Ищем работающие источники
        self.active_sources = await self.find_working_sources(count)
        
        if len(self.active_sources) < count:
            logger.warning(f"⚠️ Найдено только {len(self.active_sources)} источников из {count} требуемых")
        
        # Логируем активные источники
        logger.info("📋 Активные источники:")
        for i, source_key in enumerate(self.active_sources, 1):
            source_info = self.all_sources[source_key]
            logger.info(f"  {i}. {source_info['name']} ({source_info['reliability']}% надежность)")
        
        return self.active_sources
    
    async def check_and_replace_failed_sources(self) -> int:
        """Проверка и замена неисправных источников"""
        replaced_count = 0
        failed_sources = await db.get_failed_sources()
        
        if not failed_sources:
            logger.debug("Все источники работают корректно")
            return 0
        
        logger.info(f"🔧 Обнаружено {len(failed_sources)} неисправных источников")
        
        for failed_source in failed_sources:
            if failed_source in self.active_sources:
                # Увеличиваем счетчик попыток
                self.failed_attempts[failed_source] = self.failed_attempts.get(failed_source, 0) + 1
                
                # Если 3 попытки неудачны - заменяем источник
                if self.failed_attempts[failed_source] >= 3:
                    logger.info(f"🚨 Источник {failed_source} неисправен 3 попытки подряд - заменяем")
                    
                    replacement = await self.replace_failed_source(failed_source)
                    if replacement:
                        replaced_count += 1
                        # Сбрасываем счетчик для замененного источника
                        self.failed_attempts.pop(failed_source, None)
                else:
                    logger.info(f"⚠️ Источник {failed_source} - попытка {self.failed_attempts[failed_source]}/3")
        
        if replaced_count > 0:
            logger.info(f"🎯 Заменено {replaced_count} источников")
        
        return replaced_count
    
    def get_library_stats(self) -> Dict:
        """Статистика библиотеки источников"""
        total_sources = len(self.all_sources)
        active_count = len(self.active_sources)
        
        # Группировка по типам
        type_counts = {}
        for source in self.all_sources.values():
            source_type = source["type"]
            type_counts[source_type] = type_counts.get(source_type, 0) + 1
        
        # Средняя надежность активных источников
        if self.active_sources:
            avg_reliability = sum(
                self.all_sources[key]["reliability"] 
                for key in self.active_sources
            ) / len(self.active_sources)
        else:
            avg_reliability = 0
        
        return {
            "total_sources": total_sources,
            "active_sources": active_count,
            "type_distribution": type_counts,
            "average_reliability": round(avg_reliability, 1),
            "replacement_count": len(self.replacement_history),
            "failed_attempts": dict(self.failed_attempts)
        }
    
    def get_source_info(self, source_key: str) -> Optional[Dict]:
        """Получение информации об источнике"""
        return self.all_sources.get(source_key)
    
    def get_active_sources_info(self) -> List[Dict]:
        """Получение информации об активных источниках"""
        return [
            {
                "key": source_key,
                **self.all_sources[source_key]
            }
            for source_key in self.active_sources
        ]

# Глобальный экземпляр библиотеки
sources_library = SourcesLibrary()