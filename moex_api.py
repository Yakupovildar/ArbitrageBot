import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from config import Config

logger = logging.getLogger(__name__)

class MOEXAPIClient:
    """Клиент для работы с MOEX ISS API с соблюдением всех правил"""
    
    def __init__(self):
        self.config = Config()
        self.session = None
        self.last_request_time = 0
        self.request_times = []  # История времен запросов для контроля частоты
        self.failed_requests = {}  # Счетчик неудачных запросов по URL
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер - вход"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекст менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Правило 1: Контроль частоты запросов - не более 60 в минуту"""
        current_time = time.time()
        
        # Очищаем старые записи (старше 1 минуты)
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        # Проверяем лимит запросов в минуту
        if len(self.request_times) >= self.config.MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Превышен лимит запросов в минуту. Ожидание {sleep_time:.1f} сек")
                await asyncio.sleep(sleep_time)
                current_time = time.time()
        
        # Минимальная задержка между запросами
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.config.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.config.RATE_LIMIT_DELAY - time_since_last)
            current_time = time.time()
        
        # Записываем время запроса
        self.request_times.append(current_time)
        self.last_request_time = current_time
    
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Правила 3,4,5: Выполнение HTTP запроса с retry логикой и обработкой ошибок"""
        if not self.session:
            raise RuntimeError("Сессия не инициализирована")
        
        # Правило 5: Избегаем дублирующих запросов
        request_key = f"{url}:{str(params)}"
        
        for attempt in range(self.config.RETRY_ATTEMPTS):
            try:
                await self._rate_limit()
                
                logger.debug(f"Запрос к MOEX API (попытка {attempt + 1}): {url}")
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Сбрасываем счетчик неудачных попыток при успехе
                        self.failed_requests.pop(request_key, None)
                        return data
                    
                    elif response.status in [401, 403]:
                        # Правило 2: Ошибки авторизации - не повторяем
                        logger.error(f"Ошибка авторизации MOEX API: HTTP {response.status}")
                        return None
                    
                    elif response.status == 429:
                        # Слишком много запросов - увеличиваем задержку
                        retry_delay = self.config.RETRY_DELAY * (self.config.BACKOFF_MULTIPLIER ** attempt)
                        logger.warning(f"MOEX API rate limit: HTTP 429. Ожидание {retry_delay:.1f} сек")
                        await asyncio.sleep(retry_delay)
                        continue
                    
                    elif response.status >= 500:
                        # Серверная ошибка - повторяем с задержкой
                        retry_delay = self.config.RETRY_DELAY * (self.config.BACKOFF_MULTIPLIER ** attempt)
                        logger.warning(f"Серверная ошибка MOEX API: HTTP {response.status}. Повтор через {retry_delay:.1f} сек")
                        await asyncio.sleep(retry_delay)
                        continue
                    
                    else:
                        # Правило 6: Избегаем повторных неправильных запросов
                        logger.error(f"Ошибка MOEX API: HTTP {response.status}")
                        self.failed_requests[request_key] = self.failed_requests.get(request_key, 0) + 1
                        
                        # После 3 неудачных попыток одного запроса - прекращаем
                        if self.failed_requests[request_key] >= 3:
                            logger.error(f"Слишком много неудачных попыток для {url}")
                            return None
                        
                        return None
                        
            except asyncio.TimeoutError:
                retry_delay = self.config.RETRY_DELAY * (self.config.BACKOFF_MULTIPLIER ** attempt)
                logger.warning(f"Таймаут MOEX API (попытка {attempt + 1}). Повтор через {retry_delay:.1f} сек")
                if attempt < self.config.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(retry_delay)
                    
            except Exception as e:
                retry_delay = self.config.RETRY_DELAY * (self.config.BACKOFF_MULTIPLIER ** attempt)
                logger.error(f"Ошибка запроса к MOEX API (попытка {attempt + 1}): {e}")
                if attempt < self.config.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(retry_delay)
        
        logger.error(f"Не удалось выполнить запрос после {self.config.RETRY_ATTEMPTS} попыток: {url}")
        return None
    
    async def get_stock_price(self, ticker: str) -> Optional[float]:
        """Получение цены акции"""
        url = f"{self.config.MOEX_API_BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        params = {
            'iss.meta': 'off',
            'iss.only': 'securities',
            'securities.columns': 'SECID,LAST,PREVPRICE,LOTSIZE'
        }
        
        data = await self._make_request(url, params)
        if not data:
            return None
        
        try:
            securities = data.get('securities', {})
            if 'data' in securities and securities['data']:
                columns = securities.get('columns', [])
                
                for row in securities['data']:
                    if not row or row[0] != ticker:
                        continue
                    
                    # Получаем размер лота
                    lot_size = 1
                    if 'LOTSIZE' in columns:
                        lot_index = columns.index('LOTSIZE')
                        if len(row) > lot_index and row[lot_index] is not None:
                            lot_size = int(row[lot_index])
                    
                    # Сначала пробуем LAST (цена последней сделки)
                    if 'LAST' in columns:
                        last_index = columns.index('LAST')
                        if len(row) > last_index and row[last_index] is not None:
                            price_per_share = float(row[last_index])
                            # Для арбитража нужна цена за лот (как для фьючерсов)
                            price_per_lot = price_per_share * lot_size
                            logger.debug(f"Цена акции {ticker} (LAST): {price_per_share}₽/шт × {lot_size} = {price_per_lot}₽/лот")
                            return price_per_lot
                    
                    # Если LAST нет, используем PREVPRICE (цена предыдущего дня)
                    if 'PREVPRICE' in columns:
                        prev_index = columns.index('PREVPRICE')
                        if len(row) > prev_index and row[prev_index] is not None:
                            price_per_share = float(row[prev_index])
                            # Для арбитража нужна цена за лот (как для фьючерсов)
                            price_per_lot = price_per_share * lot_size
                            logger.debug(f"Цена акции {ticker} (PREVPRICE): {price_per_share}₽/шт × {lot_size} = {price_per_lot}₽/лот")
                            return price_per_lot
                            
            return None
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга цены акции {ticker}: {e}")
            return None
    
    async def get_futures_price(self, ticker: str) -> Optional[float]:
        """Получение цены фьючерса"""
        url = f"{self.config.MOEX_API_BASE_URL}/engines/futures/markets/forts/boards/RFUD/securities/{ticker}.json"
        params = {
            'iss.meta': 'off',
            'iss.only': 'securities', 
            'securities.columns': 'SECID,LAST,PREVPRICE'
        }
        
        data = await self._make_request(url, params)
        if not data:
            return None
        
        try:
            securities = data.get('securities', {})
            if 'data' in securities and securities['data']:
                columns = securities.get('columns', [])
                
                for row in securities['data']:
                    if not row or row[0] != ticker:
                        continue
                    
                    # Сначала пробуем LAST (цена последней сделки)
                    if 'LAST' in columns:
                        last_index = columns.index('LAST')
                        if len(row) > last_index and row[last_index] is not None:
                            price = float(row[last_index])
                            logger.debug(f"Цена фьючерса {ticker} (LAST): {price}")
                            return price
                    
                    # Если LAST нет, используем PREVPRICE (цена предыдущего дня)
                    if 'PREVPRICE' in columns:
                        prev_index = columns.index('PREVPRICE')
                        if len(row) > prev_index and row[prev_index] is not None:
                            price = float(row[prev_index])
                            logger.debug(f"Цена фьючерса {ticker} (PREVPRICE): {price}")
                            return price
                            
            return None
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга цены фьючерса {ticker}: {e}")
            return None
    
    async def get_instrument_info(self, ticker: str, instrument_type: str) -> Optional[Dict]:
        """Получение информации об инструменте"""
        if instrument_type == "stock":
            url = f"{self.config.MOEX_API_BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        else:  # futures
            url = f"{self.config.MOEX_API_BASE_URL}/engines/futures/markets/forts/boards/RFUD/securities/{ticker}.json"
        
        data = await self._make_request(url)
        if not data:
            return None
        
        try:
            securities = data.get('securities', {})
            if 'data' in securities and securities['data']:
                columns = securities.get('columns', [])
                row_data = securities['data'][0] if securities['data'] else []
                
                info = {}
                for i, column in enumerate(columns):
                    if i < len(row_data):
                        info[column] = row_data[i]
                
                return info
                
        except (KeyError, IndexError) as e:
            logger.error(f"Ошибка получения информации об инструменте {ticker}: {e}")
            return None
        
        return None
    
    async def get_multiple_quotes(self, instruments: Dict[str, str]) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        """Получение котировок для множества инструментов"""
        results = {}
        
        # Группируем запросы для оптимизации
        tasks = []
        for stock_ticker, futures_ticker in instruments.items():
            stock_task = self.get_stock_price(stock_ticker)
            futures_task = self.get_futures_price(futures_ticker)
            tasks.append((stock_ticker, stock_task, futures_task))
        
        # Правило 7: Ограничиваем количество одновременных запросов (ужесточено)
        semaphore = asyncio.Semaphore(1)  # Только 1 одновременный запрос
        
        async def fetch_pair(stock_ticker, stock_task, futures_task):
            async with semaphore:
                # Добавляем максимальную задержку перед каждой парой
                await asyncio.sleep(self.config.MIN_REQUEST_INTERVAL)
                
                # Получаем цены последовательно с максимальными задержками
                stock_price = await stock_task
                await asyncio.sleep(2.0)  # Увеличенная задержка между запросами
                futures_price = await futures_task
                
                # Дополнительная задержка после обработки пары
                await asyncio.sleep(1.0)
                
                # Обработка исключений
                if isinstance(stock_price, Exception):
                    logger.error(f"Ошибка получения цены акции {stock_ticker}: {stock_price}")
                    stock_price = None
                    
                if isinstance(futures_price, Exception):
                    futures_ticker = instruments[stock_ticker]
                    logger.error(f"Ошибка получения цены фьючерса {futures_ticker}: {futures_price}")
                    futures_price = None
                
                return stock_ticker, (stock_price, futures_price)
        
        # Выполняем все задачи
        pair_tasks = [fetch_pair(stock_ticker, stock_task, futures_task) 
                     for stock_ticker, stock_task, futures_task in tasks]
        
        pair_results = await asyncio.gather(*pair_tasks, return_exceptions=True)
        
        # Собираем результаты
        for result in pair_results:
            if isinstance(result, Exception):
                logger.error(f"Ошибка при получении котировок: {result}")
                continue
            
            if result is not None:
                stock_ticker, prices = result
                results[stock_ticker] = prices
        
        return results
    
    async def get_trading_status(self) -> Dict[str, bool]:
        """Получение статуса торгов на различных рынках"""
        try:
            # Проверяем статус торгов на фондовом рынке
            stock_url = f"{self.config.MOEX_API_BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities.json"
            futures_url = f"{self.config.MOEX_API_BASE_URL}/engines/futures/markets/forts/boards/RFUD/securities.json"
            
            stock_data, futures_data = await asyncio.gather(
                self._make_request(stock_url),
                self._make_request(futures_url),
                return_exceptions=True
            )
            
            status = {
                "stock_market": stock_data is not None and not isinstance(stock_data, Exception),
                "futures_market": futures_data is not None and not isinstance(futures_data, Exception),
                "api_available": True
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Ошибка проверки статуса торгов: {e}")
            return {
                "stock_market": False,
                "futures_market": False,
                "api_available": False
            }
