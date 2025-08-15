#!/usr/bin/env python3
"""
Модуль секторного пользовательского интерфейса для выбора торговых пар
"""

import logging
from typing import Dict, List, Tuple
from sectors_classification import sector_classifier, EconomicSector
from bot_ui_restrictions import ui_restrictions

logger = logging.getLogger(__name__)

class SectorUI:
    """Секторный интерфейс для торговых пар"""
    
    def __init__(self):
        self.classifier = sector_classifier
        self.restrictions = ui_restrictions
    
    def get_sectors_menu_keyboard(self) -> Dict:
        """Главное меню выбора секторов"""
        sectors_dict = self.classifier.get_sectors_dict()
        
        # Фильтруем только доступные пары
        available_sectors = {}
        for sector, pairs in sectors_dict.items():
            available_pairs = []
            for stock, futures in pairs:
                if self.restrictions.status_manager.is_pair_available(stock, futures):
                    available_pairs.append((stock, futures))
            
            if available_pairs:  # Показываем только секторы с доступными парами
                available_sectors[sector] = available_pairs
        
        # Создаем кнопки по секторам
        keyboard = []
        
        # Группируем кнопки по 2 в ряд
        sector_buttons = []
        for sector in available_sectors.keys():
            pairs_count = len(available_sectors[sector])
            button_text = f"{sector.value} ({pairs_count})"
            callback_data = f"sector_{sector.name.lower()}"
            
            sector_buttons.append({"text": button_text, "callback_data": callback_data})
            
            # По 2 кнопки в ряд
            if len(sector_buttons) == 2:
                keyboard.append(sector_buttons)
                sector_buttons = []
        
        # Добавляем оставшуюся кнопку
        if sector_buttons:
            keyboard.append(sector_buttons)
        
        # Добавляем кнопки управления
        keyboard.append([
            {"text": "🔍 Показать все доступные", "callback_data": "sector_all_available"},
            {"text": "🚫 Показать заблокированные", "callback_data": "sector_blocked"}
        ])
        
        keyboard.append([
            {"text": "🔙 Назад в настройки", "callback_data": "settings"}
        ])
        
        return {"inline_keyboard": keyboard}
    
    def get_sector_pairs_keyboard(self, sector_name: str) -> Dict:
        """Клавиатура с парами конкретного сектора"""
        try:
            sector_enum = EconomicSector[sector_name.upper()]
        except KeyError:
            return self.get_sectors_menu_keyboard()
        
        sectors_dict = self.classifier.get_sectors_dict()
        
        if sector_enum not in sectors_dict:
            return self.get_sectors_menu_keyboard()
        
        pairs = sectors_dict[sector_enum]
        keyboard = []
        
        # Фильтруем доступные пары и создаем кнопки
        row = []
        for stock, futures in pairs:
            if self.restrictions.status_manager.is_pair_available(stock, futures):
                company_name = self.classifier.companies.get(stock, {}).name if hasattr(self.classifier.companies.get(stock, {}), 'name') else stock
                button_text = f"{stock}/{futures}"
                callback_data = f"pair_{stock}_{futures}"
                
                row.append({"text": button_text, "callback_data": callback_data})
                
                # По 2 пары в ряд
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        # Добавляем оставшуюся кнопку
        if row:
            keyboard.append(row)
        
        # Кнопки управления
        keyboard.append([
            {"text": "✅ Выбрать все пары сектора", "callback_data": f"sector_select_all_{sector_name.lower()}"},
            {"text": "❌ Отменить все", "callback_data": f"sector_deselect_all_{sector_name.lower()}"}
        ])
        
        keyboard.append([
            {"text": "🔙 К выбору секторов", "callback_data": "sectors_menu"}
        ])
        
        return {"inline_keyboard": keyboard}
    
    def get_sectors_summary_message(self) -> str:
        """Сводное сообщение о доступности пар по секторам"""
        sectors_dict = self.classifier.get_sectors_dict()
        
        message = "📊 **ТОРГОВЫЕ ПАРЫ ПО СЕКТОРАМ**\n\n"
        
        total_available = 0
        total_blocked = 0
        total_unavailable = 0
        
        for sector, pairs in sectors_dict.items():
            available_pairs = []
            blocked_pairs = []
            unavailable_pairs = []
            
            for stock, futures in pairs:
                if self.restrictions.status_manager.is_pair_available(stock, futures):
                    available_pairs.append((stock, futures))
                    total_available += 1
                else:
                    status_info = self.restrictions.status_manager.get_pair_status_info(stock, futures)
                    if status_info and hasattr(status_info, 'status'):
                        from pair_status_manager import PairStatus
                        if status_info.status == PairStatus.BLOCKED:
                            blocked_pairs.append((stock, futures))
                            total_blocked += 1
                        else:
                            unavailable_pairs.append((stock, futures))
                            total_unavailable += 1
            
            if available_pairs or blocked_pairs or unavailable_pairs:
                message += f"**{sector.value}**\n"
                
                if available_pairs:
                    message += f"✅ Доступно: {len(available_pairs)} пар\n"
                if blocked_pairs:
                    message += f"🚫 Заблокировано: {len(blocked_pairs)} пар\n"  
                if unavailable_pairs:
                    message += f"❌ Недоступно: {len(unavailable_pairs)} пар\n"
                
                message += "\n"
        
        message += f"**📈 ОБЩАЯ СТАТИСТИКА:**\n"
        message += f"✅ Всего доступных пар: {total_available}\n"
        message += f"🚫 Заблокированных пар: {total_blocked}\n"
        message += f"❌ Недоступных пар: {total_unavailable}\n\n"
        
        message += "💡 *Выберите сектор для просмотра конкретных торговых пар*"
        
        return message
    
    def get_sector_description(self, sector_name: str) -> str:
        """Получение описания сектора"""
        try:
            sector_enum = EconomicSector[sector_name.upper()]
            sectors_dict = self.classifier.get_sectors_dict()
            
            if sector_enum not in sectors_dict:
                return "Сектор не найден"
            
            pairs = sectors_dict[sector_enum]
            available_pairs = [
                (stock, futures) for stock, futures in pairs 
                if self.restrictions.status_manager.is_pair_available(stock, futures)
            ]
            
            message = f"**{sector_enum.value}**\n\n"
            message += f"📊 Доступно пар для торговли: {len(available_pairs)}\n\n"
            
            # Показываем компании в секторе
            if available_pairs:
                message += "**🏢 Компании в секторе:**\n"
                for stock, futures in available_pairs[:10]:  # Показываем первые 10
                    company_info = self.classifier.companies.get(stock)
                    if company_info:
                        message += f"• {stock} - {company_info.name}\n"
                    else:
                        message += f"• {stock}\n"
                
                if len(available_pairs) > 10:
                    message += f"• ... и еще {len(available_pairs) - 10} компаний\n"
            
            return message
            
        except KeyError:
            return "Неизвестный сектор"

# Глобальный экземпляр
sector_ui = SectorUI()