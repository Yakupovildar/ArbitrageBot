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
    signals_sent: int = 0  # количество отправленных сигналов
    subscription_active: bool = False  # активна ли подписка
    subscription_start: Optional[datetime] = None  # начало подписки
    subscription_end: Optional[datetime] = None  # конец подписки
    subscription_crypto_address: str = ""
    trial_start: Optional[datetime] = None  # начало пробного периода
    trial_end: Optional[datetime] = None  # конец пробного периода
    username: str = ""  # username телеграм

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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signals_sent INTEGER DEFAULT 0,
                    subscription_active BOOLEAN DEFAULT FALSE,
                    subscription_start TIMESTAMP NULL,
                    subscription_end TIMESTAMP NULL,
                    subscription_crypto_address TEXT DEFAULT '',
                    trial_start TIMESTAMP NULL,
                    trial_end TIMESTAMP NULL,
                    username VARCHAR(100) DEFAULT ''
                )
            """)
            
            # Добавляем новые колонки к существующей таблице если их нет
            columns_to_add = [
                ("selected_instruments", "TEXT DEFAULT '[]'"),
                ("signals_sent", "INTEGER DEFAULT 0"),
                ("subscription_active", "BOOLEAN DEFAULT FALSE"),
                ("subscription_start", "TIMESTAMP NULL"),
                ("subscription_end", "TIMESTAMP NULL"),
                ("subscription_crypto_address", "TEXT DEFAULT ''"),
                ("trial_start", "TIMESTAMP NULL"),
                ("trial_end", "TIMESTAMP NULL"),
                ("username", "VARCHAR(100) DEFAULT ''")
            ]
            
            for column_name, column_definition in columns_to_add:
                try:
                    await conn.execute(f"""
                        ALTER TABLE user_settings 
                        ADD COLUMN {column_name} {column_definition}
                    """)
                    logger.info(f"✅ Добавлена колонка {column_name}")
                except Exception:
                    # Колонка уже существует
                    pass
            
            # Таблица истории подписок
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS subscription_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username VARCHAR(100),
                    action VARCHAR(50) NOT NULL, -- 'activate' или 'deactivate'
                    duration_months INTEGER,
                    admin_id BIGINT NOT NULL,
                    admin_username VARCHAR(100),
                    comment TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
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
                    (user_id, monitoring_interval, spread_threshold, max_signals, is_monitoring, selected_instruments, 
                     signals_sent, subscription_active, subscription_start, subscription_end, 
                     subscription_crypto_address, trial_start, trial_end, username, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        monitoring_interval = EXCLUDED.monitoring_interval,
                        spread_threshold = EXCLUDED.spread_threshold,
                        max_signals = EXCLUDED.max_signals,
                        is_monitoring = EXCLUDED.is_monitoring,
                        selected_instruments = EXCLUDED.selected_instruments,
                        signals_sent = EXCLUDED.signals_sent,
                        subscription_active = EXCLUDED.subscription_active,
                        subscription_start = EXCLUDED.subscription_start,
                        subscription_end = EXCLUDED.subscription_end,
                        subscription_crypto_address = EXCLUDED.subscription_crypto_address,
                        trial_start = EXCLUDED.trial_start,
                        trial_end = EXCLUDED.trial_end,
                        username = EXCLUDED.username,
                        updated_at = CURRENT_TIMESTAMP
                """, settings.user_id, settings.monitoring_interval, 
                    settings.spread_threshold, settings.max_signals, settings.is_monitoring, settings.selected_instruments,
                    settings.signals_sent, settings.subscription_active, settings.subscription_start, 
                    settings.subscription_end, settings.subscription_crypto_address, settings.trial_start, settings.trial_end, settings.username)
                
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
                        updated_at=row['updated_at'],
                        signals_sent=row.get('signals_sent', 0),
                        subscription_active=row.get('subscription_active', False),
                        subscription_start=row.get('subscription_start'),
                        subscription_end=row.get('subscription_end'),
                        subscription_crypto_address=row.get('subscription_crypto_address', ''),
                        trial_start=row.get('trial_start'),
                        trial_end=row.get('trial_end'),
                        username=row.get('username', '')
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
    
    async def get_all_users(self) -> List[UserSettings]:
        """Получение всех пользователей (независимо от статуса мониторинга)"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM user_settings")
                
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
            logger.error(f"❌ Ошибка получения всех пользователей: {e}")
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

    async def find_user_by_username(self, username: str) -> Optional[int]:
        """Найти пользователя по username"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id FROM user_settings WHERE username = $1", 
                    username.replace('@', '')
                )
                return row['user_id'] if row else None
        except Exception as e:
            logger.error(f"❌ Ошибка поиска пользователя по username {username}: {e}")
            return None
    
    async def add_subscription_history(self, user_id: int, username: str, action: str, 
                                     duration_months: Optional[int], admin_id: int, 
                                     admin_username: str, comment: str = "") -> bool:
        """Добавить запись в историю подписок"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO subscription_history 
                    (user_id, username, action, duration_months, admin_id, admin_username, comment)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, user_id, username, action, duration_months, admin_id, admin_username, comment)
                
                logger.info(f"История подписки добавлена: {action} для @{username} от @{admin_username}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления истории подписки: {e}")
            return False
    
    async def get_subscription_history(self, limit: int = 10) -> List[Dict]:
        """Получить историю подписок"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM subscription_history 
                    ORDER BY created_at DESC 
                    LIMIT $1
                """, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории подписок: {e}")
            return []

    async def update_user_username(self, user_id: int, username: str) -> bool:
        """Обновить username пользователя"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE user_settings 
                    SET username = $2, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = $1
                """, user_id, username.replace('@', ''))
                
                logger.info(f"Username обновлен для пользователя {user_id}: @{username}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления username: {e}")
            return False

# Глобальный экземпляр базы данных
db = Database()