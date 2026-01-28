#!/usr/bin/env python3
"""
Тестовый скрипт для проверки Portals API
"""
import asyncio
from portals_api import portals_api


async def test_portals():
    """Тестируем получение токена и floor price"""
    
    print("=" * 60)
    print("ТЕСТ PORTALS API")
    print("=" * 60)
    
    # 1. Получаем токен авторизации
    print("\n1️⃣ Получение токена авторизации...")
    token = await portals_api.get_auth_token()
    
    if token:
        print(f"✅ Токен получен: {token[:50]}...")
    else:
        print("❌ Не удалось получить токен")
        return
    
    # 2. Тестируем получение floor price для тестовых подарков
    print("\n2️⃣ Тестирование получения floor price...")
    
    test_gifts = [
        "https://t.me/nft/JellyBunny-65265",
        "https://t.me/nft/JellyBunny-78230",
        "https://t.me/nft/FlyingBroom-23444"
    ]
    
    print(f"\nТестовые подарки:")
    for gift in test_gifts:
        print(f"  • {gift}")
    
    # 3. Получаем общую стоимость
    print("\n3️⃣ Расчет общей стоимости...")
    result = await portals_api.calculate_total_floor_price(test_gifts)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"  💰 Общая сумма: {result['total']} TON")
    print(f"  ✅ Найдено цен: {len(result['details'])}/{result['count']}")
    print(f"  ❌ Не найдено: {result['not_found']}")
    
    if result['details']:
        print(f"\n📝 Детали:")
        for detail in result['details']:
            print(f"  • {detail['model']} #{detail['number']}: {detail['floor_price']} TON")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_portals())
