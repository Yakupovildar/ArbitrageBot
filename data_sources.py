"""
Управление источниками данных для бота арбитража
"""

import logging
import aiohttp
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class DataSourceManager:
    """Менеджер источников данных"""
    
    def __init__(self):
        self.sources = {
            "moex": {
                "name": "MOEX ISS API",
                "url": "https://iss.moex.com",
                "status": "unknown",
                "last_check": None,
                "priority": 1,
                "active": True
            },
            "tradingview": {
                "name": "TradingView",
                "url": "https://www.tradingview.com",
                "status": "unknown", 
                "last_check": None,
                "priority": 2,
                "active": False
            },
            "investing": {
                "name": "Investing.com",
                "url": "https://api.investing.com",
                "status": "unknown",
                "last_check": None,
                "priority": 3,
                "active": False
            },
            "yahoo_finance": {
                "name": "Yahoo Finance",
                "url": "https://query1.finance.yahoo.com",
                "status": "unknown",
                "last_check": None,
                "priority": 4,
                "active": False
            },
            "alphavantage": {
                "name": "Alpha Vantage",
                "url": "https://www.alphavantage.co",
                "status": "unknown",
                "last_check": None,
                "priority": 5,
                "active": False
            },
            "finam": {
                "name": "Finam Trade API",
                "url": "https://trade-api.finam.ru",
                "status": "unknown",
                "last_check": None,
                "priority": 6,
                "active": False
            }
        }
        
    async def check_source_status(self, source_key: str) -> str:
        """Проверка статуса источника данных"""
        source = self.sources.get(source_key)
        if not source:
            return "not_found"
            
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(source["url"]) as response:
                    if response.status == 200:
                        status = "working"
                    elif response.status in [403, 429]:
                        status = "blocked"
                    else:
                        status = "error"
        except aiohttp.ClientError:
            status = "unreachable"
        except Exception:
            status = "error"
            
        # Обновляем статус
        self.sources[source_key]["status"] = status
        self.sources[source_key]["last_check"] = datetime.now()
        
        return status
        
    async def check_all_sources(self) -> Dict[str, str]:
        """Проверка всех источников данных"""
        results = {}
        
        for source_key in self.sources.keys():
            status = await self.check_source_status(source_key)
            results[source_key] = status
            
        return results
        
    def get_status_summary(self) -> str:
        """Получение сводки по всем источникам"""
        message = "🔍 *ПРОВЕРКА ИСТОЧНИКОВ ДАННЫХ*\n\n"
        
        for source_key, source in self.sources.items():
            name = source["name"]
            status = source["status"]
            last_check = source["last_check"]
            priority = source["priority"]
            active = source["active"]
            
            # Эмодзи статуса
            if status == "working":
                status_emoji = "✅"
                status_text = "работает успешно"
            elif status == "blocked":
                status_emoji = "🚫"
                status_text = "заблокирован"
            elif status == "error":
                status_emoji = "❌"
                status_text = "ошибка подключения"
            elif status == "unreachable":
                status_emoji = "📡"
                status_text = "недоступен"
            else:
                status_emoji = "❓"
                status_text = "не проверен"
                
            # Статус активности
            active_text = "🟢 активен" if active else "🔴 отключен"
            
            message += f"*{priority}. {name}*\n"
            message += f"{status_emoji} {status_text} | {active_text}\n"
            
            if last_check:
                check_time = last_check.strftime("%H:%M:%S")
                message += f"⏰ Проверено: {check_time}\n"
                
            message += "\n"
            
        return message
        
    def get_restart_keyboard(self, source_key: str) -> dict:
        """Создание клавиатуры для перезапуска источника"""
        source_name = self.sources[source_key]["name"]
        
        return {
            "inline_keyboard": [[
                {"text": "✅ Да, перезапустить", "callback_data": f"restart_{source_key}"},
                {"text": "❌ Нет", "callback_data": f"cancel_restart_{source_key}"}
            ]]
        }
        
    def restart_source(self, source_key: str) -> bool:
        """Перезапуск источника данных"""
        if source_key in self.sources:
            # Сброс статуса
            self.sources[source_key]["status"] = "unknown"
            self.sources[source_key]["last_check"] = None
            logger.info(f"Источник {source_key} перезапущен")
            return True
        return False
        
    def get_active_sources(self) -> List[str]:
        """Получение списка активных источников"""
        return [key for key, source in self.sources.items() if source["active"]]
        
    def set_source_active(self, source_key: str, active: bool):
        """Установка активности источника"""
        if source_key in self.sources:
            self.sources[source_key]["active"] = active
            
    def get_working_sources(self) -> List[str]:
        """Получение списка работающих источников"""
        return [key for key, source in self.sources.items() 
                if source["status"] == "working" and source["active"]]