#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы статусов торговых пар
"""

import asyncio
import logging
from pair_status_manager import PairStatusManager, PairStatus

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_pair_status_system():
    """Тестирование новой системы статусов пар"""
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ СТАТУСОВ ТОРГОВЫХ ПАР")
    print("=" * 60)
    
    # Создаем менеджер статусов
    status_manager = PairStatusManager()
    
    # Запускаем полную проверку всех пар
    print("🔍 Запуск проверки всех торговых пар...")
    pair_statuses = await status_manager.check_all_pairs()
    
    # Выводим результаты
    print("\n📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    print(f"✅ Активные пары: {len(status_manager.active_pairs)}")
    print(f"🚫 Заблокированные пары: {len(status_manager.blocked_pairs)}")
    print(f"❌ Недоступные пары: {len(status_manager.unavailable_pairs)}")
    print(f"📈 Общее количество пар: {len(pair_statuses)}")
    
    # Показываем активные пары
    if status_manager.active_pairs:
        print(f"\n✅ АКТИВНЫЕ ПАРЫ ({len(status_manager.active_pairs)}):")
        for pair in status_manager.active_pairs[:10]:  # Первые 10
            info = pair_statuses[pair]
            spread_str = f" (спред: {info.spread_percent:.2f}%)" if info.spread_percent else ""
            print(f"   {pair}{spread_str}")
        if len(status_manager.active_pairs) > 10:
            print(f"   ... и еще {len(status_manager.active_pairs) - 10} пар")
    
    # Показываем заблокированные пары
    if status_manager.blocked_pairs:
        print(f"\n🚫 ЗАБЛОКИРОВАННЫЕ ПАРЫ ({len(status_manager.blocked_pairs)}):")
        for pair in status_manager.blocked_pairs:
            info = pair_statuses[pair]
            print(f"   {pair}: {info.reason}")
    
    # Показываем недоступные пары
    if status_manager.unavailable_pairs:
        print(f"\n❌ НЕДОСТУПНЫЕ ПАРЫ ({len(status_manager.unavailable_pairs)}):")
        for pair in status_manager.unavailable_pairs:
            info = pair_statuses[pair]
            print(f"   {pair}: {info.reason}")
    
    # Тестируем проверку доступности конкретных пар
    print(f"\n🧪 ТЕСТИРОВАНИЕ ДОСТУПНОСТИ КОНКРЕТНЫХ ПАР:")
    test_pairs = [
        ("SBER", "SBERF"),
        ("SGZH", "SZZ5"),  # Проблемная пара
        ("NKNC", "NKZ5"),  # Проблемная пара
        ("TCSG", "TCZ5"),  # Недоступная пара
    ]
    
    for stock, futures in test_pairs:
        is_available = status_manager.is_pair_available(stock, futures)
        status_info = status_manager.get_pair_status_info(stock, futures)
        
        if is_available:
            print(f"   ✅ {stock}/{futures}: ДОСТУПНА")
        else:
            status_text = status_info.status.value if status_info else "неизвестно"
            reason = status_info.reason if status_info else "причина неизвестна"
            print(f"   🚫 {stock}/{futures}: {status_text.upper()} - {reason}")
    
    print("\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")

if __name__ == "__main__":
    asyncio.run(test_pair_status_system())