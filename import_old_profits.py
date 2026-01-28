import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db
from portals_api import portals_api

# Данные старых профитов
old_profits = [
    {"victim": "villk18", "worker": "musa_koromusya", "gifts": ["CandyCane-188116", "JellyBunny-96686"]},
    {"victim": "w1akz0", "worker": "roxnal", "gifts": ["SnoopDogg-393074", "SnakeBox-27180"]},
    {"victim": "alenas_yo", "worker": "mashwqkk", "gifts": ["SnoopDogg-152411"]},
    {"victim": "wocrf", "worker": "none", "gifts": ["FaithAmulet-94054", "IceCream-258945"]},
    {"victim": "Georgie_aa", "worker": "usdtbuster", "gifts": ["IceCream-91085"]},
    {"victim": "Kleanov", "worker": "villsca", "gifts": ["LunarSnake-86888"]},
    {"victim": "Eeeeee_eeer", "worker": "NAMNEERDLEGIT", "gifts": ["CandyCane-189489", "JingleBells-78870"]},
    {"victim": "Privetpups_ik", "worker": "musa_koromusya", "gifts": ["IceCream-47463"]},
    {"victim": "ppprsr", "worker": "roxnal", "gifts": ["CandyCane-166900", "PetSnake-137028"]},
    {"victim": "Zevs_andreevich", "worker": "milankiisss", "gifts": ["FreshSocks-11396"]},
    {"victim": "pozser", "worker": "sonlise", "gifts": ["InstantRamen-26459", "GingerCookie-129413", "GingerCookie-129268", "PartySparkler-158207"]},
    {"victim": "usdtbuster", "worker": "usdtbuster", "gifts": ["InstantRamen-339730"]},
    {"victim": "babooshka228", "worker": "musa_koromusya", "gifts": ["InstantRamen-36333"]},
    {"victim": "ynv1dMVP", "worker": "villsca", "gifts": ["LolPop-26662", "HappyBrownie-62084"]},
    {"victim": "avj_16", "worker": "Vika8393", "gifts": ["LushBouquet-29074", "LolPop-8983", "LolPop-155242", "LolPop-228364"]},
    {"victim": "darkness_run", "worker": "chokopaika362", "gifts": ["CookieHeart-142500"]},
    {"victim": "Lover_loverliv", "worker": "villsca", "gifts": ["LolPop-52707"]},
    {"victim": "Cool_DRAGONS", "worker": "Leonardov_Guarantor", "gifts": ["GingerCookie-131255", "SpicedWine-79790"]},
    {"victim": "FR4NKL3", "worker": "Vadvoksel", "gifts": ["XmasStocking-89964", "WitchHat-41130", "HolidayDrink-47952", "CookieHeart-97112"]},
    {"victim": "Melix30", "worker": "kotakwww", "gifts": ["CookieHeart-36209"]},
    {"victim": "Vadvoksel", "worker": "flickTXF", "gifts": ["InstantRamen-190926"]},
    {"victim": "AmP0111", "worker": "Vadvoksel", "gifts": ["FlyingBroom-8998"]},
    {"victim": "sqeios918", "worker": "kkyrokx", "gifts": ["GingerCookie-103552"]},
    {"victim": "kusok_negra1337", "worker": "villsca", "gifts": ["GingerCookie-73410", "DeskCalendar-176334", "BDayCandle-250966"]},
    {"victim": "kusok_negra1337", "worker": "villsca", "gifts": ["CookieHeart-30563"]},
    {"victim": "olux28", "worker": "musa_koromusya", "gifts": ["JellyBunny-90744"]},
    {"victim": "palmorxx", "worker": "musa_koromusya", "gifts": ["JellyBunny-65265", "JellyBunny-78230", "FlyingBroom-23444"]},
    {"victim": "dnmvvy", "worker": "Vika8393", "gifts": ["FaithAmulet-39390", "XmasStocking-86173"]},
    {"victim": "imptss", "worker": "kkyrokx", "gifts": ["SwagBag-206809", "TamaGadget-14097"]},
    {"victim": "nasqw1", "worker": "villsca", "gifts": ["SnakeBox-129507"]},
    {"victim": "Katan_by", "worker": "Vika8393", "gifts": ["BDayCandle-224770"]},
]

async def import_profits():
    """Импортирует старые профиты в БД"""
    print(f"📊 Начинаю импорт {len(old_profits)} профитов...")
    
    success_count = 0
    error_count = 0
    
    for idx, profit in enumerate(old_profits, 1):
        try:
            victim_username = profit["victim"]
            worker_username = profit["worker"]
            gift_names = profit["gifts"]
            
            print(f"\n[{idx}/{len(old_profits)}] Обработка профита: {victim_username} -> {worker_username}")
            
            # Получаем telegram_id жертвы из БД по username
            victim_telegram_id = db.get_telegram_id_by_username(victim_username)
            if not victim_telegram_id:
                print(f"⚠️  Жертва @{victim_username} не найдена в БД, пропускаю...")
                error_count += 1
                continue
            
            # Получаем telegram_id воркера из БД по username
            worker_telegram_id = db.get_telegram_id_by_username(worker_username)
            if not worker_telegram_id:
                print(f"⚠️  Воркер @{worker_username} не найден в БД, пропускаю...")
                error_count += 1
                continue
            
            # Формируем ссылки на подарки
            gift_links = [f"https://t.me/nft/{name}" for name in gift_names]
            
            # Получаем floor price через Portals API
            print(f"   🔍 Получаю цены для {len(gift_links)} подарков...")
            price_info = await portals_api.calculate_total_floor_price(gift_links)
            
            total_price = price_info['total']
            print(f"   💰 Общая сумма: {total_price} TON")
            
            # Сохраняем профит в БД
            db.add_profit(
                worker_telegram_id=worker_telegram_id,
                victim_telegram_id=victim_telegram_id,
                profit_sum=total_price,
                gifts_count=len(gift_links),
                gift_links=gift_links
            )
            
            print(f"   ✅ Профит сохранен: {victim_username} [{victim_telegram_id}] -> {worker_username} [{worker_telegram_id}]")
            success_count += 1
            
            # Небольшая задержка между запросами к API
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Ошибка обработки профита: {e}")
            error_count += 1
    
    print(f"\n\n📊 ИТОГИ ИМПОРТА:")
    print(f"   ✅ Успешно: {success_count}")
    print(f"   ❌ Ошибок: {error_count}")
    print(f"   📦 Всего: {len(old_profits)}")

if __name__ == "__main__":
    asyncio.run(import_profits())
