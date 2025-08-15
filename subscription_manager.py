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
    
    # Настройки пробного периода
    FREE_TRIAL_DAYS = 7
    
    # Настройки подписки
    SUBSCRIPTION_PRICE_USDT = 10
    SUBSCRIPTION_DURATION_DAYS = 30
    CRYPTO_ADDRESS = ""  # Адрес будет указан позже
    
    def __init__(self):
        self.subscription_cache = {}  # Кеш состояния подписок
    
    async def check_signal_limit(self, user_id: int) -> bool:
        """Проверить, может ли пользователь получить еще сигналы"""
        try:
            # Получаем данные из базы
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                # Новый пользователь - активируем 7-дневный пробный период
                await self.activate_trial_period(user_id)
                return True
            
            # Если подписка активна - лимита нет
            if await self.is_subscription_active(user_id):
                return True
            
            # Проверяем пробный период
            if await self.is_trial_active(user_id):
                return True
            
            # Пробный период истек, подписки нет
            return False
            
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
    
    async def get_remaining_trial_days(self, user_id: int) -> Optional[int]:
        """Получить количество оставшихся дней пробного периода"""
        try:
            if await self.is_subscription_active(user_id):
                return None  # Безлимитно
            
            user_settings = await db.load_user_settings(user_id)
            if not user_settings or not user_settings.trial_end:
                return self.FREE_TRIAL_DAYS  # Новый пользователь
            
            # Вычисляем оставшиеся дни
            remaining = (user_settings.trial_end - datetime.now()).days
            return max(0, remaining)
            
        except Exception as e:
            logger.error(f"Ошибка получения оставшихся дней пробного периода для {user_id}: {e}")
            return self.FREE_TRIAL_DAYS
    
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

    async def activate_subscription_by_username(self, username: str, duration_months: int, admin_id: int, admin_username: str, comment: str = "") -> tuple[bool, str]:
        """Активировать подписку по username"""
        try:
            # Ищем пользователя по username
            user_id = await db.find_user_by_username(username)
            if not user_id:
                return False, f"Пользователь @{username} не найден в базе данных"
            
            duration_days = duration_months * 30  # Приблизительно
            
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
            
            # Записываем в историю
            await db.add_subscription_history(
                user_id=user_id,
                username=username,
                action="activate",
                duration_months=duration_months,
                admin_id=admin_id,
                admin_username=admin_username,
                comment=comment
            )
            
            logger.info(f"Подписка активирована для @{username} (ID: {user_id}) на {duration_months} мес. до {end_date}")
            return True, f"✅ Подписка активирована для @{username} на {duration_months} мес."
            
        except Exception as e:
            logger.error(f"Ошибка активации подписки для @{username}: {e}")
            return False, f"Ошибка: {str(e)}"

    async def deactivate_subscription_by_username(self, username: str, admin_id: int, admin_username: str, comment: str = "") -> tuple[bool, str]:
        """Деактивировать подписку по username"""
        try:
            # Ищем пользователя по username
            user_id = await db.find_user_by_username(username)
            if not user_id:
                return False, f"Пользователь @{username} не найден в базе данных"
            
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                return False, f"Настройки пользователя @{username} не найдены"
            
            user_settings.subscription_active = False
            user_settings.subscription_end = datetime.now()  # Завершаем подписку сейчас
            
            await db.save_user_settings(user_settings)
            
            # Записываем в историю
            await db.add_subscription_history(
                user_id=user_id,
                username=username,
                action="deactivate",
                duration_months=None,
                admin_id=admin_id,
                admin_username=admin_username,
                comment=comment
            )
            
            logger.info(f"Подписка деактивирована для @{username} (ID: {user_id})")
            return True, f"✅ Подписка деактивирована для @{username}"
            
        except Exception as e:
            logger.error(f"Ошибка деактивации подписки для @{username}: {e}")
            return False, f"Ошибка: {str(e)}"
    
    async def activate_trial_period(self, user_id: int) -> bool:
        """Активировать пробный период для нового пользователя"""
        try:
            user_settings = await db.load_user_settings(user_id)
            if not user_settings:
                user_settings = UserSettings(user_id=user_id)
            
            # Проверяем, не был ли пробный период уже активирован
            if user_settings.trial_end:
                return False  # Пробный период уже был
            
            # Устанавливаем даты пробного периода
            start_date = datetime.now()
            end_date = start_date + timedelta(days=self.FREE_TRIAL_DAYS)
            
            user_settings.trial_start = start_date
            user_settings.trial_end = end_date
            
            await db.save_user_settings(user_settings)
            
            logger.info(f"Пробный период активирован для пользователя {user_id} до {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка активации пробного периода для {user_id}: {e}")
            return False
    
    async def is_trial_active(self, user_id: int) -> bool:
        """Проверить активность пробного периода"""
        try:
            user_settings = await db.load_user_settings(user_id)
            if not user_settings or not user_settings.trial_end:
                return False
            
            # Проверяем срок действия пробного периода
            return datetime.now() < user_settings.trial_end
            
        except Exception as e:
            logger.error(f"Ошибка проверки пробного периода для {user_id}: {e}")
            return False
    
    def get_subscription_offer_message(self) -> str:
        """Сообщение с предложением подписки"""
        return f"""💎 **ПРЕМИУМ ПОДПИСКА**

⏰ **Ваш пробный период истек**

🚀 **Преимущества Premium:**
• Безлимитные сигналы арбитража
• Приоритетная поддержка
• Эксклюзивная аналитика
• Персональные настройки

💰 **Стоимость:** {self.SUBSCRIPTION_PRICE_USDT} USDT/месяц

🎯 **Интересно?** Мы расскажем как оплатить"""
    
    def get_payment_instructions(self) -> str:
        """Инструкции по оплате подписки"""
        return f"""💳 **ИНСТРУКЦИИ ПО ОПЛАТЕ**

💰 **Сумма:** {self.SUBSCRIPTION_PRICE_USDT} USDT
📋 **Сеть:** TRC-20 (Tron)
🏦 **Адрес:** `{self.CRYPTO_ADDRESS or 'Будет предоставлен'}`

📱 **Как оплатить:**
1. Откройте кошелек (Trust Wallet, Binance и др.)
2. Выберите USDT (TRC-20)
3. Отправьте {self.SUBSCRIPTION_PRICE_USDT} USDT на указанный адрес
4. Сделайте скриншот транзакции
5. Нажмите кнопку ниже

⚡ **Активация:** До 2 часов после подтверждения
🔔 **Поддержка:** Администратор ответит в Telegram

💡 Подписка активируется автоматически после проверки платежа"""
    
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
    


# Глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager()