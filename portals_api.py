"""
Модуль для работы с Portals API - получение floor price подарков
"""
import asyncio
import re
from typing import Optional, Dict, List
from aportalsmp import auth, gifts
from config import Config


class PortalsAPI:
    """Класс для работы с Portals Marketplace API"""
    
    def __init__(self):
        self.token = None
        self.token_expiry = None
        
    async def get_auth_token(self) -> str:
        """Получает токен авторизации для Portals API"""
        try:
            print("🔐 PORTALS: Получение токена авторизации...")
            
            # Получаем токен через pyrogram используя update_auth
            self.token = await auth.update_auth(
                api_id=Config.TELEGRAM_API_ID,
                api_hash=Config.TELEGRAM_API_HASH,
                session_name='portals_session'
            )
            
            print(f"✅ PORTALS: Токен получен успешно")
            return self.token
            
        except Exception as e:
            print(f"❌ PORTALS: Ошибка получения токена: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def ensure_token(self):
        """Проверяет наличие токена и получает новый если нужно"""
        if not self.token:
            await self.get_auth_token()
    
    def extract_gift_info_from_link(self, gift_link: str) -> Optional[Dict[str, str]]:
        """
        Извлекает название модели и номер из ссылки на подарок
        Например: https://t.me/nft/JellyBunny-65265 -> {'model': 'Jelly Bunny', 'number': '65265'}
        
        Конвертирует CamelCase в "Title Case" для поиска в Portals
        """
        try:
            # Паттерн: https://t.me/nft/ModelName-12345
            match = re.search(r'/nft/([A-Za-z]+)-(\d+)', gift_link)
            if match:
                camel_case_name = match.group(1)
                # Конвертируем CamelCase в "Title Case" (например, JellyBunny -> Jelly Bunny)
                # Добавляем пробел перед заглавными буквами
                model_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', camel_case_name)
                
                return {
                    'model': model_name,
                    'number': match.group(2)
                }
            return None
        except Exception as e:
            print(f"❌ PORTALS: Ошибка парсинга ссылки {gift_link}: {e}")
            return None
    
    async def get_gift_floor_price(self, model_name: str) -> Optional[float]:
        """
        Получает floor price (минимальную цену) для модели подарка
        
        Args:
            model_name: Название модели (например, 'JellyBunny')
            
        Returns:
            Floor price в TON или None если не найдено
        """
        try:
            await self.ensure_token()
            
            if not self.token:
                print(f"⚠️ PORTALS: Нет токена авторизации для {model_name}")
                return None
            
            print(f"🔍 PORTALS: Поиск floor price для {model_name}...")
            
            # Ищем подарки по имени модели, сортируем по возрастанию цены
            from aportalsmp import search
            
            results = await search(
                authData=self.token,
                gift_name=model_name,  # Используем gift_name вместо model
                sort='price_asc',  # По возрастанию цены
                limit=1,  # Только первый (самый дешевый)
                min_price=1  # Только с ценой > 0
            )
            
            if results and len(results) > 0:
                # price уже в TON
                floor_price = results[0].price
                print(f"💰 PORTALS: Floor price для {model_name}: {floor_price} TON")
                return floor_price
            else:
                print(f"⚠️ PORTALS: Нет предложений на продажу для {model_name}")
                return None
                
        except Exception as e:
            print(f"❌ PORTALS: Ошибка получения floor price для {model_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def calculate_total_floor_price(self, gift_links: List[str]) -> Dict[str, any]:
        """
        Вычисляет общую сумму floor price для списка подарков
        
        Args:
            gift_links: Список ссылок на подарки
            
        Returns:
            Dict с информацией: {'total': float, 'details': List[Dict], 'not_found': int}
        """
        try:
            print(f"\n💰 PORTALS: Расчет общей стоимости для {len(gift_links)} подарков...")
            
            total_price = 0.0
            details = []
            not_found_count = 0
            
            for gift_link in gift_links:
                gift_info = self.extract_gift_info_from_link(gift_link)
                
                if not gift_info:
                    print(f"⚠️ PORTALS: Не удалось распарсить ссылку {gift_link}")
                    not_found_count += 1
                    continue
                
                model_name = gift_info['model']
                floor_price = await self.get_gift_floor_price(model_name)
                
                if floor_price:
                    total_price += floor_price
                    details.append({
                        'model': model_name,
                        'number': gift_info['number'],
                        'floor_price': floor_price,
                        'link': gift_link
                    })
                else:
                    not_found_count += 1
                
                # Задержка между запросами чтобы избежать rate limit
                await asyncio.sleep(0.5)
            
            result = {
                'total': round(total_price, 2),
                'details': details,
                'not_found': not_found_count,
                'count': len(gift_links)
            }
            
            print(f"✅ PORTALS: Общая стоимость: {result['total']} TON ({len(details)}/{len(gift_links)} подарков)")
            
            return result
            
        except Exception as e:
            print(f"❌ PORTALS: Ошибка расчета общей стоимости: {e}")
            import traceback
            traceback.print_exc()
            return {
                'total': 0.0,
                'details': [],
                'not_found': len(gift_links),
                'count': len(gift_links)
            }


# Глобальный экземпляр API
portals_api = PortalsAPI()
