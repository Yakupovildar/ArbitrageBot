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
        self.cache_cleared_at = 0  # Время последней очистки кеша
        
    async def __aenter__(self):
        """Асинхронный контекст менеджер - вход"""
        # Создаем сессию с агрессивными заголовками против кеширования
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'User-Agent': f'ArbitrageBot/{int(time.time())}'
        }
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT),
            headers=headers
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
        # Добавляем параметр для получения свежих данных
        if params is None:
            params = {}
        # Агрессивная борьба с кешированием
        import random
        current_time = int(time.time() * 1000)  # Миллисекунды для точности
        params.update({
            '_t': current_time,
            '_r': random.randint(10000, 99999),
            '_nocache': 1,
            'cache': 'no',
            'pragma': 'no-cache',
            '_v': random.randint(1, 999),
            '_bust': current_time % 10000
        })
        
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
            'securities.columns': 'SECID,PREVPRICE,LOTSIZE'
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
                    
                    # Используем PREVPRICE (цена закрытия предыдущего дня)
                    if 'PREVPRICE' in columns:
                        prev_index = columns.index('PREVPRICE')
                        if len(row) > prev_index and row[prev_index] is not None:
                            price_per_share = float(row[prev_index])
                            # Для арбитража нужна цена за лот (как для фьючерсов)
                            price_per_lot = price_per_share * lot_size
                            logger.debug(f"✅ Цена акции {ticker}: {price_per_share}₽/шт × {lot_size} = {price_per_lot}₽/лот")
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
            'securities.columns': 'SECID,PREVPRICE,LOTSIZE'
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
                    
                    # Получаем размер лота для фьючерса (если есть)
                    lot_size = 1
                    if 'LOTSIZE' in columns:
                        lot_index = columns.index('LOTSIZE')
                        if len(row) > lot_index and row[lot_index] is not None:
                            lot_size = int(row[lot_index])
                    
                    # Используем PREVPRICE (цена закрытия предыдущего дня)
                    if 'PREVPRICE' in columns:
                        prev_index = columns.index('PREVPRICE')
                        if len(row) > prev_index and row[prev_index] is not None:
                            price_in_points = float(row[prev_index])
                            
                            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Разные фьючерсы имеют разные коэффициенты
                            price_in_rubles = self._convert_futures_price_to_rubles(ticker, price_in_points)
                            
                            # Умножаем на размер контракта (если есть лотность)
                            price_total = price_in_rubles * lot_size
                            
                            logger.debug(f"✅ Цена фьючерса {ticker}: {price_in_points} -> {price_in_rubles}₽ × {lot_size} = {price_total}₽")
                            return price_total
                            
            return None
            
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга цены фьючерса {ticker}: {e}")
            return None
    
    def _convert_futures_price_to_rubles(self, ticker: str, price: float) -> float:
        """Конвертация цены фьючерса в рубли с учетом специфики каждого инструмента"""
        
        # По результатам тестирования MOEX API - все фьючерсы уже возвращаются в правильном масштабе
        # SBERF: 3.192 это уже цена в рублях за акцию, НЕ в пунктах
        # VBZ5: 84.51 это уже цена в рублях за акцию
        # GKZ5: 13.66 нужно умножить на 0.01, так как это в пунктах
        
        # Фьючерсы на акции, которые торгуются в рублях за акцию (как обычные акции)
        if ticker in ['SBERF']:
            return price
        
        # GAZPF торгуется с множителем 10 (нужно умножить на 10)
        elif ticker in ['GAZPF']:
            return price * 10.0
        
        # Фьючерсы которые торгуются в копейках - нужно поделить на 100
        elif ticker in ['VBZ5']:
            return price / 100.0
        
        # Фьючерсы с коэффициентом 10 - поделить на 10 
        elif ticker in ['FSZ5']:
            return price / 10.0
        
        # Фьючерсы на металлы - оставляем как есть (API уже возвращает правильную цену)
        elif ticker in ['GKZ5']:  # ГМК Норникель: оставляем без изменений (1366 → 1366)
            return price
        elif ticker in ['LKZ5']:  # Лукойл: делить на 10
            return price / 10.0
        
        # Остальные фьючерсы - торгуются в пунктах (1 пункт = 0.01₽)
        elif ticker in ['RNZ5', 'TTZ5', 'ALZ5', 'NMZ5', 'MGZ5', 'CHZ5']:
            return price * 0.01
        
        # По умолчанию считаем что это пункты
        else:
            return price * 0.01
    
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
        # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА КЕША ПЕРЕД КАЖДЫМ ЗАПРОСОМ
        await self._force_cache_clear()
        
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
        pair_results = await asyncio.gather(*[fetch_pair(stock_ticker, stock_task, futures_task) 
                                            for stock_ticker, stock_task, futures_task in tasks], 
                                          return_exceptions=True)
        
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
    
    async def _force_cache_clear(self):
        """Принудительная очистка всех кешей и перезапуск сессии"""
        logger.info("🔄 Принудительная очистка кеша MOEX API")
        
        # Закрываем текущую сессию
        if self.session:
            await self.session.close()
            await asyncio.sleep(0.1)  # Даем время на закрытие
        
        # Создаем новую сессию с уникальными заголовками
        import random
        current_time = int(time.time() * 1000)
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0',
            'If-Modified-Since': 'Mon, 01 Jan 1990 00:00:00 GMT',
            'If-None-Match': '*',
            'User-Agent': f'ArbitrageBot/{current_time}_{random.randint(1000, 9999)}',
            'Accept': 'application/json, */*',
            'Accept-Encoding': 'identity'  # Отключаем сжатие для борьбы с кешем
        }
        
        # Создаем новую сессию с отключенным кешированием
        connector = aiohttp.TCPConnector(
            force_close=True,  # Принудительно закрываем соединения
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT),
            headers=headers,
            connector=connector
        )
        
        self.cache_cleared_at = time.time()
        logger.info("✅ Кеш очищен, новая сессия создана")
