#!/usr/bin/env python3
"""
Исследование и исправление логики конверсии цен фьючерсов
"""

import asyncio
import logging
from moex_api import MOEXAPIClient
from config import Config

logging.basicConfig(level=logging.INFO)

async def investigate_conversion_logic():
    """Полное исследование проблемы с конверсией"""
    print("🔬 ИССЛЕДОВАНИЕ ЛОГИКИ КОНВЕРСИИ ЦЕН ФЬЮЧЕРСОВ")
    print("=" * 60)
    
    config = Config()
    
    # Тестовые пары с известными проблемами
    problematic_pairs = [
        ("SGZH", "SZZ5"),  # 1.609₽ / 16.85₽
        ("AFKS", "AKZ5"),  # 16.595₽ / 174.62₽
        ("ABIO", "ISZ5"),  # 78.46₽ / 8.38₽
        ("NKNC", "NKZ5"),  # 88.05₽ / 1293.73₽
    ]
    
    async with MOEXAPIClient() as api:
        for stock_ticker, futures_ticker in problematic_pairs:
            print(f"\n🧪 АНАЛИЗ ПАРЫ {stock_ticker}/{futures_ticker}:")
            print("-" * 40)
            
            # Получаем реальные данные
            stock_price = await api.get_stock_price(stock_ticker)
            futures_price = await api.get_futures_price(futures_ticker)
            
            if stock_price and futures_price:
                # Текущий коэффициент из конфигурации
                current_coeff = config.get_futures_lot_value(futures_ticker)
                
                # Рассчитываем правильный коэффициент
                correct_coeff = stock_price / futures_price if futures_price != 0 else 1
                
                print(f"📈 Акция {stock_ticker}: {stock_price:.3f}₽")
                print(f"📉 Фьючерс {futures_ticker}: {futures_price:.3f}₽")
                print(f"⚙️ Текущий коэффициент: {current_coeff}")
                print(f"✅ Правильный коэффициент: {correct_coeff:.6f}")
                print(f"❌ Разница в коэффициентах: {abs(current_coeff - correct_coeff):.6f}")
                
                # Тестируем оба варианта
                wrong_converted = futures_price * current_coeff
                right_converted = futures_price * correct_coeff
                
                wrong_spread = ((wrong_converted - stock_price) / stock_price) * 100
                right_spread = ((right_converted - stock_price) / stock_price) * 100
                
                print(f"🔴 С текущим коэффициентом: {wrong_converted:.2f}₽ (спред: {wrong_spread:.2f}%)")
                print(f"🟢 С правильным коэффициентом: {right_converted:.2f}₽ (спред: {right_spread:.2f}%)")
                
                # Проверяем другие возможные формулы
                alt1 = futures_price / current_coeff  # Деление вместо умножения
                alt1_spread = ((alt1 - stock_price) / stock_price) * 100
                print(f"🔵 Альтернатива (деление): {alt1:.2f}₽ (спред: {alt1_spread:.2f}%)")
                
            else:
                print(f"❌ Не удалось получить цены для {stock_ticker}/{futures_ticker}")

if __name__ == "__main__":
    asyncio.run(investigate_conversion_logic())