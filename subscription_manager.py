"""
Система управления подписками пользователей
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from database import db, UserSettings

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Менеджер подписок пользователей"""
    
    # Ограничения бесплатного тарифа
    FREE_TIER_SIGNAL_LIMIT = 50
    
    # Настройки подписки
    SUBSCRIPTION_PRICE_USDT = 10
    SUBSCRIPTION_DURATION_DAYS = 30
    CRYPTO_ADDRESS = "TRBpnm6z8UNGXaMfLa6ZPWZ7RXUAkHCxWQ"  # USDT TRC-20 адрес
    
    def __init__(self):
        self.subscription_cache = {}  # Кеш состояния подписок
    
    async def check_signal_limit(self, user_id: int) -> bool:
        """Проверить, может ли пользователь получить еще сигналы"""
        try:
            # Получаем данные из базы
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                return True  # Новый пользователь
            
            # Если подписка активна - лимита нет
            if await self.is_subscription_active(user_id):
                return True
            
            # Проверяем лимит бесплатного тарифа
            return user_settings.signals_sent < self.FREE_TIER_SIGNAL_LIMIT
            
        except Exception as e:
            logger.error(f"Ошибка проверки лимита сигналов для {user_id}: {e}")
            return True  # В случае ошибки разрешаем
    
    async def increment_signal_count(self, user_id: int) -> int:
        """Увеличить счетчик отправленных сигналов"""
        try:
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                # Создаем новую запись
                user_settings = UserSettings(user_id=user_id, signals_sent=1)
            else:
                user_settings.signals_sent += 1
            
            await db.save_user_settings(user_settings)
            return user_settings.signals_sent
            
        except Exception as e:
            logger.error(f"Ошибка обновления счетчика сигналов для {user_id}: {e}")
            return 0
    
    async def is_subscription_active(self, user_id: int) -> bool:
        """Проверить активность подписки"""
        try:
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                return False
            
            # Проверяем флаг и срок действия
            if not user_settings.subscription_active:
                return False
            
            if not user_settings.subscription_end:
                return False
            
            # Проверяем срок действия
            return datetime.now() < user_settings.subscription_end
            
        except Exception as e:
            logger.error(f"Ошибка проверки подписки для {user_id}: {e}")
            return False
    
    async def get_remaining_signals(self, user_id: int) -> Optional[int]:
        """Получить количество оставшихся бесплатных сигналов"""
        try:
            if await self.is_subscription_active(user_id):
                return None  # Без ограничений
            
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                return self.FREE_TIER_SIGNAL_LIMIT
            
            remaining = self.FREE_TIER_SIGNAL_LIMIT - user_settings.signals_sent
            return max(0, remaining)
            
        except Exception as e:
            logger.error(f"Ошибка получения оставшихся сигналов для {user_id}: {e}")
            return self.FREE_TIER_SIGNAL_LIMIT
    
    async def activate_subscription(self, user_id: int, duration_days: int = None) -> bool:
        """Активировать подписку для пользователя"""
        try:
            if duration_days is None:
                duration_days = self.SUBSCRIPTION_DURATION_DAYS
            
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                user_settings = UserSettings(user_id=user_id)
            
            # Устанавливаем даты подписки
            start_date = datetime.now()
            end_date = start_date + timedelta(days=duration_days)
            
            user_settings.subscription_active = True
            user_settings.subscription_start = start_date
            user_settings.subscription_end = end_date
            
            await db.save_user_settings(user_settings)
            
            logger.info(f"Подписка активирована для пользователя {user_id} до {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка активации подписки для {user_id}: {e}")
            return False
    
    async def deactivate_subscription(self, user_id: int) -> bool:
        """Деактивировать подписку"""
        try:
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                return True
            
            user_settings.subscription_active = False
            await db.save_user_settings(user_settings)
            
            logger.info(f"Подписка деактивирована для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка деактивации подписки для {user_id}: {e}")
            return False
    
    def get_subscription_offer_message(self) -> str:
        """Получить сообщение с предложением подписки"""
        return f"""🔒 **Бесплатные сигналы закончились!**

Вы получили максимум {self.FREE_TIER_SIGNAL_LIMIT} бесплатных сигналов. 

💎 **Премиум подписка:**
• Безлимитные сигналы арбитража  
• Приоритетный доступ к данным
• Расширенная аналитика
• Персональная поддержка

💰 **Стоимость:** {self.SUBSCRIPTION_PRICE_USDT} USDT
⏱ **Срок действия:** {self.SUBSCRIPTION_DURATION_DAYS} дней

Активировать премиум подписку?"""
    
    def get_payment_instructions(self) -> str:
        """Получить инструкции по оплате"""
        return f"""💳 **Инструкции по оплате:**

🏦 **Адрес кошелька:** 
`{self.CRYPTO_ADDRESS}`
🌐 **Сеть:** TRC-20 (TRON)
💰 **Сумма:** {self.SUBSCRIPTION_PRICE_USDT} USDT

📋 **Как оплатить:**
1. Скопируйте адрес кошелька
2. Отправьте точно {self.SUBSCRIPTION_PRICE_USDT} USDT в сети TRC-20
3. Пришлите скриншот транзакции в чат

⚠️ **Важно:**
• Используйте только сеть TRC-20
• Сумма должна быть точной
• Сохраните скриншот подтверждения

После получения платежа подписка будет активирована в течение 1 часа."""

# Глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager()