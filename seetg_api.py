"""
Модуль для работы с see.tg API
API документация: https://see.tg/api/docs
"""

import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
from config import Config


class SeeTgAPI:
    """Класс для работы с see.tg API"""
    
    def __init__(self, app_token: str = None):
        self.app_token = app_token or Config.SEE_TG_APP_TOKEN
        self.base_url = Config.SEE_TG_BASE_URL
        self.session = None
    
    async def _ensure_session(self):
        """Создает aiohttp сессию если её нет"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None) -> Optional[Dict]:
        """Базовый метод для HTTP запросов"""
        await self._ensure_session()
        
        url = f"{self.base_url}{endpoint}"
        
        # Добавляем app_token ко всем запросам
        if params is None:
            params = {}
        params['app_token'] = self.app_token
        
        try:
            async with self.session.request(method, url, params=params, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    print(f"❌ SEE.TG API Error {response.status}: {error_text}")
                    return None
        except Exception as e:
            print(f"❌ SEE.TG API Request failed: {e}")
            return None
    
    async def search_gifts(
        self,
        gift_id: str = None,
        title: str = None,
        slug: str = None,
        num: int = None,
        model_name: str = None,
        pattern_name: str = None,
        backdrop_name: str = None,
        url: str = None,
        market_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        order: str = "desc"
    ) -> Optional[Dict]:
        """
        Поиск подарков с фильтрами
        
        Args:
            url: Telegram URL (например, https://t.me/nft/IonGem-1)
            model_name: Название модели (например, "Jelly Bunny")
            num: Номер подарка
            market_only: Только подарки на продаже
            limit: Количество результатов (1-50)
            
        Returns:
            {
                "gifts": [gift_objects],
                "total": int,
                "limit": int,
                "offset": int
            }
        """
        params = {
            'limit': limit,
            'offset': offset,
            'sort_by': sort_by,
            'order': order
        }
        
        if gift_id:
            params['gift_id'] = gift_id
        if title:
            params['title'] = title
        if slug:
            params['slug'] = slug
        if num is not None:
            params['num'] = num
        if model_name:
            params['model_name'] = model_name
        if pattern_name:
            params['pattern_name'] = pattern_name
        if backdrop_name:
            params['backdrop_name'] = backdrop_name
        if url:
            params['url'] = url
        if market_only:
            params['market_only'] = 'true'
        
        return await self._request('GET', '/api/gifts', params=params)
    
    async def get_owner_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """
        Получает информацию о владельце по Telegram ID
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            {
                "id": str,
                "telegram_id": int,
                "username": str,
                "name": str,
                "gifts_count": int,
                ...
            }
        """
        params = {'telegram_id': str(telegram_id)}
        return await self._request('GET', '/api/owner', params=params)
    
    async def get_owner_by_username(self, username: str) -> Optional[Dict]:
        """
        Получает информацию о владельце по username
        
        Args:
            username: Username пользователя (с @ или без)
        """
        clean_username = username.lstrip('@')
        params = {'username': clean_username}
        return await self._request('GET', '/api/owner', params=params)


# Глобальный экземпляр API
seetg_api = SeeTgAPI()
