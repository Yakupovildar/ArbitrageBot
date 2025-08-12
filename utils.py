import logging
import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import functools

logger = logging.getLogger(__name__)

def format_number(value: float, decimal_places: int = 2) -> str:
    """Форматирование числа с заданным количеством знаков после запятой"""
    try:
        return f"{value:.{decimal_places}f}"
    except (ValueError, TypeError):
        return "N/A"

def format_currency(value: float, currency: str = "₽") -> str:
    """Форматирование валютного значения"""
    try:
        return f"{value:.2f} {currency}"
    except (ValueError, TypeError):
        return f"N/A {currency}"

def format_percentage(value: float, decimal_places: int = 2) -> str:
    """Форматирование процентного значения"""
    try:
        return f"{value:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "N/A%"

def format_timestamp(timestamp: Optional[datetime] = None, 
                    format_string: str = "%H:%M:%S") -> str:
    """Форматирование временной метки"""
    try:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        return timestamp.strftime(format_string)
    except Exception:
        return "N/A"

def safe_division(numerator: float, denominator: float, 
                 default: float = 0.0) -> float:
    """Безопасное деление с обработкой деления на ноль"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default

def validate_ticker(ticker: str) -> bool:
    """Валидация тикера инструмента"""
    if not ticker or not isinstance(ticker, str):
        return False
    
    # Базовая валидация тикера
    if len(ticker) < 2 or len(ticker) > 10:
        return False
    
    # Проверяем, что тикер содержит только допустимые символы
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return all(c in allowed_chars for c in ticker.upper())

def validate_price(price: Any) -> bool:
    """Валидация цены"""
    try:
        float_price = float(price)
        return float_price > 0
    except (ValueError, TypeError):
        return False

def retry_async(max_attempts: int = 3, delay: float = 1.0, 
               backoff_factor: float = 2.0):
    """Декоратор для повторных попыток асинхронных функций"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Попытка {attempt + 1}/{max_attempts} не удалась для {func.__name__}: {e}"
                    )
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
            
            logger.error(f"Все попытки исчерпаны для {func.__name__}")
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator

class RateLimiter:
    """Класс для контроля частоты запросов"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Получение разрешения на выполнение запроса"""
        now = asyncio.get_event_loop().time()
        
        # Удаляем старые вызовы
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        # Проверяем лимит
        if len(self.calls) >= self.max_calls:
            # Вычисляем время ожидания
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call)
            
            if wait_time > 0:
                logger.debug(f"Rate limit достигнут. Ожидание {wait_time:.2f} секунд")
                await asyncio.sleep(wait_time)
        
        # Записываем текущий вызов
        self.calls.append(now)

class CircuitBreaker:
    """Паттерн Circuit Breaker для защиты от каскадных ошибок"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """Выполнение функции с защитой Circuit Breaker"""
        
        if self.state == "OPEN":
            # Проверяем, можно ли попробовать снова
            if (self.last_failure_time and 
                asyncio.get_event_loop().time() - self.last_failure_time > self.recovery_timeout):
                self.state = "HALF_OPEN"
                logger.info("Circuit Breaker переведен в состояние HALF_OPEN")
            else:
                raise Exception("Circuit Breaker OPEN - сервис недоступен")
        
        try:
            result = await func(*args, **kwargs)
            
            # Успешный вызов
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit Breaker восстановлен - состояние CLOSED")
            
            return result
            
        except Exception as e:
            # Ошибка при вызове
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit Breaker ОТКРЫТ после {self.failure_count} ошибок")
            
            raise e

def create_message_chunks(text: str, max_length: int = 4096) -> list:
    """Разбивка длинного сообщения на части для Telegram"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    lines = text.split('\n')
    
    for line in lines:
        # Если добавление строки превысит лимит
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
        
        # Если сама строка слишком длинная
        if len(line) > max_length:
            # Разбиваем строку по словам
            words = line.split(' ')
            for word in words:
                if len(current_chunk) + len(word) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = word
                    else:
                        # Если даже одно слово слишком длинное
                        chunks.append(word[:max_length-3] + "...")
                        current_chunk = ""
                else:
                    current_chunk += " " + word if current_chunk else word
        else:
            current_chunk += "\n" + line if current_chunk else line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown в Telegram"""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

class AsyncTimer:
    """Асинхронный таймер для периодических задач"""
    
    def __init__(self, interval: float, callback: Callable):
        self.interval = interval
        self.callback = callback
        self.is_running = False
        self.task = None
    
    async def start(self):
        """Запуск таймера"""
        if self.is_running:
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Остановка таймера"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    async def _run(self):
        """Внутренний цикл таймера"""
        while self.is_running:
            try:
                await self.callback()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в таймере: {e}")
                await asyncio.sleep(self.interval)

def log_function_call(func: Callable):
    """Декоратор для логирования вызовов функций"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger.debug(f"Вызов {func.__name__} с args={args}, kwargs={kwargs}")
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.debug(f"{func.__name__} выполнен за {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"{func.__name__} завершен с ошибкой за {execution_time:.3f}s: {e}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger.debug(f"Вызов {func.__name__} с args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} выполнен успешно")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} завершен с ошибкой: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
