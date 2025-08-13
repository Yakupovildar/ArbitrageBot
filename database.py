import os
import logging
import asyncpg
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class UserSettings:
    """Настройки пользователя"""
    user_id: int
    monitoring_interval: int = 60  # секунды
    spread_threshold: float = 1.0  # процент
    max_signals: int = 3  # максимум сигналов за раз
    is_monitoring: bool = False
    selected_instruments: str = "[]"  # JSON строка с выбранными инструментами
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL")
        
    async def init_connection(self):
        """Инициализация подключения к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Создаем таблицы если не существуют
            await self.create_tables()
            logger.info("✅ Подключение к базе данных установлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            raise
    
    async def close_connection(self):
        """Закрытие подключения к базе данных"""
        if self.pool:
            await self.pool.close()
            logger.info("Подключение к базе данных закрыто")
    
    async def create_tables(self):
        """Создание таблиц в базе данных"""
        async with self.pool.acquire() as conn:
            # Таблица настроек пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id BIGINT PRIMARY KEY,
                    monitoring_interval INTEGER DEFAULT 60,
                    spread_threshold REAL DEFAULT 1.0,
                    max_signals INTEGER DEFAULT 3,
                    is_monitoring BOOLEAN DEFAULT FALSE,
                    selected_instruments TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем колонку selected_instruments к существующей таблице если её нет
            try:
                await conn.execute("""
                    ALTER TABLE user_settings 
                    ADD COLUMN selected_instruments TEXT DEFAULT '[]'
                """)
                logger.info("✅ Добавлена колонка selected_instruments")
            except Exception:
                # Колонка уже существует
                pass
            
            # Таблица состояния источников данных
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS data_sources_status (
                    source_name VARCHAR(100) PRIMARY KEY,
                    status VARCHAR(50) DEFAULT 'unknown',
                    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT NULL
                )
            """)
            
            # Таблица истории мониторинга
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    total_signals INTEGER DEFAULT 0,
                    session_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            logger.info("✅ Таблицы базы данных созданы/проверены")
    
    async def save_user_settings(self, settings: UserSettings) -> bool:
        """Сохранение настроек пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_settings 
                    (user_id, monitoring_interval, spread_threshold, max_signals, is_monitoring, selected_instruments, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        monitoring_interval = EXCLUDED.monitoring_interval,
                        spread_threshold = EXCLUDED.spread_threshold,
                        max_signals = EXCLUDED.max_signals,
                        is_monitoring = EXCLUDED.is_monitoring,
                        selected_instruments = EXCLUDED.selected_instruments,
                        updated_at = CURRENT_TIMESTAMP
                """, settings.user_id, settings.monitoring_interval, 
                    settings.spread_threshold, settings.max_signals, settings.is_monitoring, settings.selected_instruments)
                
                logger.info(f"💾 Настройки пользователя {settings.user_id} сохранены")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек: {e}")
            return False
    
    async def load_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Загрузка настроек пользователя"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM user_settings WHERE user_id = $1", user_id
                )
                
                if row:
                    return UserSettings(
                        user_id=row['user_id'],
                        monitoring_interval=row['monitoring_interval'],
                        spread_threshold=row['spread_threshold'],
                        max_signals=row['max_signals'],
                        is_monitoring=row['is_monitoring'],
                        selected_instruments=row.get('selected_instruments', '[]'),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                else:
                    # Создаем настройки по умолчанию
                    default_settings = UserSettings(user_id=user_id)
                    await self.save_user_settings(default_settings)
                    return default_settings
                    
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки настроек: {e}")
            return None
    
    async def get_all_monitoring_users(self) -> List[UserSettings]:
        """Получение всех пользователей с активным мониторингом"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM user_settings WHERE is_monitoring = TRUE"
                )
                
                users = []
                for row in rows:
                    users.append(UserSettings(
                        user_id=row['user_id'],
                        monitoring_interval=row['monitoring_interval'],
                        spread_threshold=row['spread_threshold'],
                        max_signals=row['max_signals'],
                        is_monitoring=row['is_monitoring'],
                        selected_instruments=row.get('selected_instruments', '[]'),
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    ))
                
                return users
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения активных пользователей: {e}")
            return []
    
    async def update_source_status(self, source_name: str, status: str, error: str = None):
        """Обновление статуса источника данных"""
        try:
            async with self.pool.acquire() as conn:
                error_text = error if error is not None else None
                await conn.execute("""
                    INSERT INTO data_sources_status 
                    (source_name, status, last_check, error_count, last_error)
                    VALUES ($1, $2, CURRENT_TIMESTAMP, 
                            CASE WHEN $2 = 'error' THEN 1 ELSE 0 END, $3)
                    ON CONFLICT (source_name) 
                    DO UPDATE SET 
                        status = EXCLUDED.status,
                        last_check = CURRENT_TIMESTAMP,
                        error_count = CASE 
                            WHEN EXCLUDED.status = 'error' THEN data_sources_status.error_count + 1
                            ELSE 0
                        END,
                        last_error = EXCLUDED.last_error
                """, source_name, status, error_text)
                
        except Exception as e:
            logger.debug(f"❌ Ошибка обновления статуса источника: {e}")
    
    async def get_failed_sources(self) -> List[str]:
        """Получение списка неисправных источников"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT source_name FROM data_sources_status WHERE status = 'error'"
                )
                return [row['source_name'] for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения неисправных источников: {e}")
            return []

# Глобальный экземпляр базы данных
db = Database()