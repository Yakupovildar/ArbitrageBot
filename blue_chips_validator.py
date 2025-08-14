"""
Система валидации только голубых фишек MOEX
Фокус на проверенных торговых парах
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Только проверенные голубые фишки
BLUE_CHIPS_CORE = {
    'SBER': 'SBERF',  # Сбербанк - самая ликвидная пара
    'GAZP': 'GAZPF',  # Газпром - вторая по объемам  
    'LKOH': 'LKZ5',   # Лукойл - нефтяная
    'GMKN': 'GKZ5',   # Норникель - металлургическая
    'VTBR': 'VBZ5',   # ВТБ - банковская
    'ROSN': 'RNZ5',   # Роснефть - нефтяная
    'TATN': 'TNZ5',   # Татнефть - нефтяная  
    'ALRS': 'ALZ5',   # Алроса - алмазная
}

async def validate_blue_chips_only():
    """Валидация только проверенных голубых фишек"""
    
    print('🔵 ВАЛИДАЦИЯ ГОЛУБЫХ ФИШЕК MOEX:')
    print()
    
    valid_pairs = []
    problem_pairs = []
    
    async with aiohttp.ClientSession() as session:
        for stock, futures in BLUE_CHIPS_CORE.items():
            print(f'🔍 Проверяем {stock}/{futures}...')
            
            try:
                # Проверка акции с множественными полями
                stock_url = f'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{stock}.json?iss.meta=off'
                async with session.get(stock_url) as response:
                    if response.status != 200:
                        problem_pairs.append((stock, futures, f"Акция HTTP {response.status}"))
                        continue
                        
                    stock_data = await response.json()
                    
                    if 'securities' not in stock_data or not stock_data['securities'].get('data'):
                        problem_pairs.append((stock, futures, "Акция не найдена"))
                        continue
                
                # Проверка фьючерса
                futures_url = f'https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities/{futures}.json?iss.meta=off'
                async with session.get(futures_url) as response:
                    if response.status != 200:
                        problem_pairs.append((stock, futures, f"Фьючерс HTTP {response.status}"))
                        continue
                        
                    futures_data = await response.json()
                    
                    if 'securities' not in futures_data or not futures_data['securities'].get('data'):
                        problem_pairs.append((stock, futures, "Фьючерс не найден"))
                        continue
                
                # Извлекаем цены с fallback логикой
                stock_price = extract_price(stock_data)
                futures_price = extract_price(futures_data)
                
                if stock_price and futures_price:
                    spread = ((futures_price - stock_price) / stock_price) * 100
                    valid_pairs.append((stock, futures, stock_price, futures_price, spread))
                    print(f'✅ {stock}/{futures}: {stock_price:.2f}₽ / {futures_price:.2f}₽ (спред: {spread:.2f}%)')
                elif stock_price or futures_price:
                    # Частичные данные
                    problem_pairs.append((stock, futures, f"Частичные данные: акция={stock_price}, фьючерс={futures_price}"))
                    print(f'⚠️ {stock}/{futures}: частичные данные')
                else:
                    problem_pairs.append((stock, futures, "Нет котировок"))
                    print(f'❌ {stock}/{futures}: нет котировок')
                    
            except Exception as e:
                problem_pairs.append((stock, futures, f"Ошибка: {str(e)}"))
                print(f'❌ {stock}/{futures}: ошибка - {e}')
    
    print()
    print(f'📊 РЕЗУЛЬТАТ:')
    print(f'✅ Работающих пар: {len(valid_pairs)}')
    print(f'❌ Проблемных пар: {len(problem_pairs)}')
    
    if valid_pairs:
        print()
        print('🎯 РАБОЧИЕ ПАРЫ ДЛЯ АРБИТРАЖА:')
        for stock, futures, stock_price, futures_price, spread in valid_pairs:
            urgency = "🟢🟢" if abs(spread) > 2 else "🟢" if abs(spread) > 1 else "⚪"
            print(f'   {urgency} {stock}/{futures}: {spread:+.2f}%')
    
    if problem_pairs:
        print()
        print('🚨 ПРОБЛЕМНЫЕ ПАРЫ:')
        for stock, futures, error in problem_pairs:
            print(f'   • {stock}/{futures}: {error}')
    
    return valid_pairs, problem_pairs

def extract_price(api_data):
    """Извлечение цены из данных MOEX API с fallback логикой"""
    try:
        if 'securities' not in api_data or not api_data['securities'].get('data'):
            return None
            
        row = api_data['securities']['data'][0]
        columns = api_data['securities']['columns']
        
        # Приоритет полей для извлечения цены
        price_fields = ['LAST', 'PREVPRICE', 'MARKETPRICE', 'WAPRICE', 'OPEN']
        
        for field in price_fields:
            if field in columns:
                idx = columns.index(field)
                if len(row) > idx and row[idx] is not None:
                    price = row[idx]
                    if isinstance(price, (int, float)) and price > 0:
                        return float(price)
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка извлечения цены: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(validate_blue_chips_only())