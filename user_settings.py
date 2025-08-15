"""
Система персональных настроек пользователей
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class UserSettings:
    """Персональные настройки пользователя"""
    user_id: int
    monitoring_interval: int = 300  # По умолчанию 5 минут (в секундах)
    spread_threshold: float = 1.0   # По умолчанию 1%
    max_signals: int = 3            # Максимум сигналов за раз
    source_rotation_index: int = 0  # Индекс текущего источника данных
    selected_instruments: List[str] = field(default_factory=list)  # Выбранные пользователем инструменты (макс 10)
    
    # Доступные интервалы мониторинга
    AVAILABLE_INTERVALS = {
        30: "30 секунд",
        60: "1 минута", 
        180: "3 минуты",
        300: "5 минут",
        900: "15 минут"
    }
    
    # Доступные пороги спредов
    AVAILABLE_SPREADS = {
        0.2: "0.2%",
        0.3: "0.3%",
        0.4: "0.4%",
        0.5: "0.5%",
        0.7: "0.7%", 
        0.9: "0.9%",
        1.0: "1.0%",
        1.5: "1.5%",
        2.0: "2.0%",
        3.0: "3.0%"
    }
    
    def get_interval_display(self) -> str:
        """Получить текстовое представление интервала"""
        return self.AVAILABLE_INTERVALS.get(self.monitoring_interval, f"{self.monitoring_interval} сек")
    
    def get_spread_display(self) -> str:
        """Получить текстовое представление порога спреда"""
        return self.AVAILABLE_SPREADS.get(self.spread_threshold, f"{self.spread_threshold:.2f}%")
    
    def is_fast_monitoring(self) -> bool:
        """Проверить, используется ли быстрый мониторинг (требует ротации источников)"""
        return self.monitoring_interval < 300  # Менее 5 минут
    
    def get_next_source_index(self, total_sources: int) -> int:
        """Получить следующий индекс источника для ротации"""
        self.source_rotation_index = (self.source_rotation_index + 1) % total_sources
        return self.source_rotation_index
    
    def add_instrument(self, instrument_key: str) -> bool:
        """Добавить инструмент в список выбранных (максимум 10)"""
        if len(self.selected_instruments) >= 10:
            return False
        if instrument_key not in self.selected_instruments:
            self.selected_instruments.append(instrument_key)
        return True
    
    def remove_instrument(self, instrument_key: str) -> bool:
        """Удалить инструмент из списка выбранных"""
        if instrument_key in self.selected_instruments:
            self.selected_instruments.remove(instrument_key)
            return True
        return False
    
    def get_selected_instruments_dict(self, all_instruments: Dict[str, str]) -> Dict[str, str]:
        """Получить словарь выбранных инструментов пользователя"""
        if not self.selected_instruments:
            # Если пользователь ничего не выбрал, возвращаем первые 5 инструментов по умолчанию
            default_instruments = list(all_instruments.keys())[:5]
            return {k: all_instruments[k] for k in default_instruments if k in all_instruments}
        
        return {k: all_instruments[k] for k in self.selected_instruments if k in all_instruments}
    
    def get_selected_count(self) -> int:
        """Получить количество выбранных инструментов"""
        return len(self.selected_instruments)

class UserSettingsManager:
    """Менеджер персональных настроек пользователей"""
    
    def __init__(self):
        self.user_settings: Dict[int, UserSettings] = {}
        self.data_sources = [
            "moex",
            "tradingview", 
            "investing_com",
            "alpha_vantage",
            "finam"
        ]
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """Получить настройки пользователя (создать если не существуют)"""
        if user_id not in self.user_settings:
            self.user_settings[user_id] = UserSettings(user_id=user_id)
        return self.user_settings[user_id]
    
    def update_monitoring_interval(self, user_id: int, interval: int) -> bool:
        """Обновить интервал мониторинга пользователя"""
        if interval not in UserSettings.AVAILABLE_INTERVALS:
            return False
        
        settings = self.get_user_settings(user_id)
        settings.monitoring_interval = interval
        logger.info(f"Пользователь {user_id} изменил интервал на {interval} сек")
        return True
    
    def update_spread_threshold(self, user_id: int, threshold: float) -> bool:
        """Обновить порог спреда пользователя"""
        if threshold not in UserSettings.AVAILABLE_SPREADS:
            return False
            
        settings = self.get_user_settings(user_id)
        settings.spread_threshold = threshold
        logger.info(f"Пользователь {user_id} изменил порог спреда на {threshold}%")
        return True
    
    def update_max_signals(self, user_id: int, max_signals: int) -> bool:
        """Обновить максимальное количество сигналов за раз"""
        if max_signals < 1 or max_signals > 10:
            return False
            
        settings = self.get_user_settings(user_id)
        settings.max_signals = max_signals
        logger.info(f"Пользователь {user_id} изменил макс. сигналов на {max_signals}")
        return True
    
    def get_current_source_for_user(self, user_id: int) -> str:
        """Получить текущий источник данных для пользователя (с ротацией для быстрого мониторинга)"""
        settings = self.get_user_settings(user_id)
        
        if settings.is_fast_monitoring():
            # Для быстрого мониторинга используем ротацию источников
            source_index = settings.get_next_source_index(len(self.data_sources))
            source = self.data_sources[source_index]
            logger.debug(f"Пользователь {user_id}: ротация источника -> {source}")
            return source
        else:
            # Для обычного мониторинга используем MOEX
            return "moex"
    
    def get_settings_keyboard(self, user_id: int) -> Dict:
        """Создать клавиатуру настроек для пользователя"""
        settings = self.get_user_settings(user_id)
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"⏱️ Интервал: {settings.get_interval_display()}", "callback_data": "settings_interval"},
                    {"text": f"📊 Спред: {settings.get_spread_display()}", "callback_data": "settings_spread"}
                ],
                [
                    {"text": f"🔢 Сигналов: {settings.max_signals}", "callback_data": "settings_signals"},
                    {"text": f"📈 Инструменты: {settings.get_selected_count()}/10", "callback_data": "settings_instruments"}
                ],
                [
                    {"text": "🔙 Назад", "callback_data": "settings_back"}
                ]
            ]
        }
        return keyboard
    
    def get_interval_keyboard(self) -> Dict:
        """Создать клавиатуру выбора интервала"""
        keyboard_rows = []
        
        # Создаем кнопки по 2 в ряд
        intervals = list(UserSettings.AVAILABLE_INTERVALS.items())
        for i in range(0, len(intervals), 2):
            row = []
            for j in range(2):
                if i + j < len(intervals):
                    interval, display = intervals[i + j]
                    row.append({"text": display, "callback_data": f"interval_{interval}"})
            keyboard_rows.append(row)
        
        keyboard_rows.append([{"text": "🔙 Назад", "callback_data": "settings_back"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def get_spread_keyboard(self) -> Dict:
        """Создать клавиатуру выбора порога спреда"""
        keyboard_rows = []
        
        # Создаем кнопки по 3 в ряд
        spreads = list(UserSettings.AVAILABLE_SPREADS.items())
        for i in range(0, len(spreads), 3):
            row = []
            for j in range(3):
                if i + j < len(spreads):
                    spread, display = spreads[i + j]
                    row.append({"text": display, "callback_data": f"spread_{spread}"})
            keyboard_rows.append(row)
        
        keyboard_rows.append([{"text": "🔙 Назад", "callback_data": "settings_back"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def get_signals_keyboard(self) -> Dict:
        """Создать клавиатуру выбора количества сигналов"""
        return {
            "inline_keyboard": [
                [
                    {"text": "1 сигнал", "callback_data": "signals_1"},
                    {"text": "2 сигнала", "callback_data": "signals_2"},
                    {"text": "3 сигнала", "callback_data": "signals_3"}
                ],
                [
                    {"text": "4 сигнала", "callback_data": "signals_4"},
                    {"text": "5 сигналов", "callback_data": "signals_5"},
                    {"text": "10 сигналов", "callback_data": "signals_10"}
                ],
                [
                    {"text": "🔙 Назад", "callback_data": "settings_back"}
                ]
            ]
        }
    
    def get_settings_summary(self, user_id: int) -> str:
        """Получить сводку настроек пользователя"""
        settings = self.get_user_settings(user_id)
        
        summary = f"""⚙️ Ваши персональные настройки:

⏱️ Интервал мониторинга: {settings.get_interval_display()}
📊 Порог спреда: {settings.get_spread_display()}
🔢 Максимум сигналов: {settings.max_signals} за раз
📈 Выбрано инструментов: {settings.get_selected_count()}/10

"""
        
        if settings.is_fast_monitoring():
            summary += "🔄 Быстрый мониторинг: включена ротация источников данных для избежания блокировок\n\n"
        else:
            summary += "🐌 Обычный мониторинг: стандартная скорость без ротации источников\n\n"
            
        summary += "Нажмите на настройку чтобы изменить:"
        
        return summary
    
    def add_user_instrument(self, user_id: int, instrument_key: str) -> bool:
        """Добавить инструмент для пользователя"""
        settings = self.get_user_settings(user_id)
        return settings.add_instrument(instrument_key)
    
    def remove_user_instrument(self, user_id: int, instrument_key: str) -> bool:
        """Удалить инструмент у пользователя"""
        settings = self.get_user_settings(user_id)
        return settings.remove_instrument(instrument_key)
    
    def get_user_instruments_dict(self, user_id: int, all_instruments: Dict[str, str]) -> Dict[str, str]:
        """Получить выбранные инструменты пользователя"""
        settings = self.get_user_settings(user_id)
        return settings.get_selected_instruments_dict(all_instruments)
    
    def get_instruments_keyboard(self, user_id: int, all_instruments: Dict[str, str], page: int = 0) -> Dict:
        """Создать клавиатуру выбора инструментов с разбивкой по секторам"""
        settings = self.get_user_settings(user_id)
        keyboard_rows = []
        
        # Группируем инструменты по секторам
        sectors = self._group_instruments_by_sectors(all_instruments)
        
        # Показываем меню выбора сектора
        if page == 0:
            for sector_name, instruments in sectors.items():
                selected_count = sum(1 for stock in instruments.keys() if stock in settings.selected_instruments)
                total_count = len(instruments)
                
                keyboard_rows.append([{
                    "text": f"📊 {sector_name} ({selected_count}/{total_count})", 
                    "callback_data": f"sector_{sector_name.replace(' ', '_').replace('🔵', 'blue').replace('🏦', 'banks').replace('⛽', 'oil').replace('🏭', 'metals').replace('⚡', 'energy').replace('📡', 'telecom').replace('💻', 'tech').replace('🛒', 'retail').replace('🏘️', 'realty').replace('🚛', 'transport').replace('🧪', 'chem').replace('🔧', 'industry').replace('💰', 'finance').replace('🆕', 'new')}"
                }])
            
            # Кнопки управления
            keyboard_rows.append([
                {"text": "🔄 Сбросить выбор", "callback_data": "instruments_clear"},
                {"text": "🎯 По умолчанию", "callback_data": "instruments_default"}
            ])
            keyboard_rows.append([{"text": "🔙 Назад", "callback_data": "settings_back"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def get_sector_instruments_keyboard(self, user_id: int, sector_name: str, all_instruments: Dict[str, str]) -> Dict:
        """Создать клавиатуру для выбора инструментов в конкретном секторе"""
        settings = self.get_user_settings(user_id)
        keyboard_rows = []
        
        # Получаем инструменты сектора
        sectors = self._group_instruments_by_sectors(all_instruments)
        sector_instruments = sectors.get(sector_name, {})
        
        # По 1 инструменту на строку для наглядности
        for stock, futures in sector_instruments.items():
            is_selected = stock in settings.selected_instruments
            emoji = "✅" if is_selected else "⭕"
            action = "remove" if is_selected else "add"
            
            keyboard_rows.append([{
                "text": f"{emoji} {stock} → {futures}", 
                "callback_data": f"instrument_{action}_{stock}"
            }])
        
        # Кнопки управления
        keyboard_rows.append([
            {"text": "✅ Выбрать все", "callback_data": f"sector_select_all_{hash(sector_name) % 1000}"},
            {"text": "❌ Снять все", "callback_data": f"sector_clear_all_{hash(sector_name) % 1000}"}
        ])
        keyboard_rows.append([{"text": "🔙 К секторам", "callback_data": "instruments_back_to_sectors"}])
        
        return {"inline_keyboard": keyboard_rows}
    
    def _group_instruments_by_sectors(self, all_instruments: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Группировка инструментов по секторам"""
        sectors = {
            "🔵 Голубые фишки": {},
            "🏦 Банки": {},
            "⛽ Нефть и газ": {},
            "🏭 Металлургия": {},
            "⚡ Энергетика": {},
            "📡 Телеком": {},
            "💻 Технологии": {},
            "🛒 Ритейл": {},
            "🏘️ Недвижимость": {},
            "🚛 Транспорт": {},
            "🧪 Химия": {},
            "🔧 Промышленность": {},
            "💰 Финуслуги": {},
            "🆕 Новые активы": {}
        }
        
        # Распределяем инструменты по секторам

        blue_chips = ["SBER", "GAZP", "GMKN", "FEES", "VTBR", "LKOH", "ROSN", "TATN", "ALRS"]
        banks = ["SBERP", "CBOM", "BSPB", "SVCB", "VTBR"]
        oil_gas = ["GAZP", "LKOH", "ROSN", "TATN", "TATP", "SNGS", "SNGSP", "NVTK", "SIBN", "BANE", "RNFT"]
        metals = ["GMKN", "ALRS", "NLMK", "MAGN", "CHMF", "MTLR", "PLZL", "POLY", "RUAL", "PHOR", "RASP"]
        energy = ["FEES", "IRAO", "HYDR", "RSTI", "MSNG", "TRNFP"]
        telecom = ["RTKM", "MTSS", "TCSI"]
        tech = ["YDEX", "VKCO", "OZON", "TCSG"]
        retail = ["MGNT", "FIVE", "DIXY", "LENTA", "MVID"]
        real_estate = ["PIKK", "SMLT", "LSRG", "ETALON"]
        transport = ["AFLT", "FESH", "FLOT", "KMAZ"]
        chemical = ["AKRN", "NKNC", "URKZ"]
        industrial = ["SGZH", "LEAS", "BELUGA", "KMAZ", "LIFE"]
        finance = ["MOEX", "SPBE", "SFIN"]
        international = ["SPY", "QQQ", "DAX", "HANG", "NIKKEI", "EURO50", "RUSSELL", "MSCI_EM"]
        currency = ["USDRUB", "EURRUB", "CNYRUB", "TRYRUB", "HKDRUB"]
        commodities = ["GOLD_RUB", "SILVER_RUB", "BRENT", "NATGAS", "WHEAT", "SUGAR"]
        indices = ["MOEX_IDX", "RTS_IDX", "MOEX_MINI", "RTS_MINI"]
        new_assets = ["AFKS", "AQUA", "VSMO", "KOGK", "UPRO", "ISKJ", "POSI", "ASTR", "SOFL", "WUSH", "DIAS"]
        
        for stock, futures in all_instruments.items():
            if stock in blue_chips:
                sectors["🔵 Голубые фишки"][stock] = futures
            elif stock in banks:
                sectors["🏦 Банки"][stock] = futures
            elif stock in oil_gas:
                sectors["⛽ Нефть и газ"][stock] = futures
            elif stock in metals:
                sectors["🏭 Металлургия"][stock] = futures
            elif stock in energy:
                sectors["⚡ Энергетика"][stock] = futures
            elif stock in telecom:
                sectors["📡 Телеком"][stock] = futures
            elif stock in tech:
                sectors["💻 Технологии"][stock] = futures
            elif stock in retail:
                sectors["🛒 Ритейл"][stock] = futures
            elif stock in real_estate:
                sectors["🏘️ Недвижимость"][stock] = futures
            elif stock in transport:
                sectors["🚛 Транспорт"][stock] = futures
            elif stock in chemical:
                sectors["🧪 Химия"][stock] = futures
            elif stock in industrial:
                sectors["🔧 Промышленность"][stock] = futures
            elif stock in finance:
                sectors["💰 Финуслуги"][stock] = futures
            elif stock in international:
                sectors["🌍 Международные ETF"][stock] = futures
            elif stock in currency:
                sectors["💱 Валютные пары"][stock] = futures
            elif stock in commodities:
                sectors["🥇 Товары"][stock] = futures
            elif stock in indices:
                sectors["📈 Индексы"][stock] = futures
            elif stock in new_assets:
                sectors["🆕 Новые активы"][stock] = futures
            else:
                sectors["🔧 Промышленность"][stock] = futures  # По умолчанию
        
        # Удаляем пустые секторы
        return {name: instruments for name, instruments in sectors.items() if instruments}
    
    def get_sector_name_by_hash(self, sector_hash: int, all_instruments: Dict[str, str]) -> str:
        """Получить название сектора по хешу"""
        sectors = self._group_instruments_by_sectors(all_instruments)
        for sector_name in sectors.keys():
            if hash(sector_name) % 1000 == sector_hash:
                return sector_name
        return "🔧 Промышленность"  # По умолчанию
    
    def clear_user_instruments(self, user_id: int):
        """Очистить выбранные инструменты пользователя"""
        settings = self.get_user_settings(user_id)
        settings.selected_instruments = []
        logger.info(f"Пользователь {user_id} очистил список инструментов")
    
    def set_default_instruments(self, user_id: int, all_instruments: Dict[str, str]):
        """Установить инструменты по умолчанию (первые 5)"""
        settings = self.get_user_settings(user_id)
        default_instruments = list(all_instruments.keys())[:5]
        settings.selected_instruments = default_instruments
        logger.info(f"Пользователь {user_id} выбрал инструменты по умолчанию: {default_instruments}")