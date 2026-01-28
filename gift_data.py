"""
Gift data from changes.tg CDN with local JSON caching
"""

import json
import requests
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Путь к кэш файлу
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
GIFTS_CACHE_FILE = os.path.join(CACHE_DIR, 'gifts_data.json')

# Кэш для данных в памяти
_gifts_cache = None
_patterns_cache = None
_models_cache = None
_full_cache = None  # Полный кэш всех данных подарков

def load_gifts() -> Dict[str, str]:
    """Загружает список подарков (ID -> Название)"""
    global _gifts_cache
    if _gifts_cache is None:
        try:
            resp = requests.get('https://cdn.changes.tg/gifts/id-to-name.json', timeout=5)
            _gifts_cache = resp.json()
        except:
            _gifts_cache = {}
    return _gifts_cache

def load_patterns() -> Dict[str, Tuple[str, str]]:
    """Загружает паттерны и парсит их в (Подарок, Модель)"""
    global _patterns_cache
    if _patterns_cache is None:
        try:
            resp = requests.get('https://cdn.changes.tg/gifts/patterns.json', timeout=5)
            raw_patterns = resp.json()
            # Парсим "Santa Hat/Alarm" -> ("Santa Hat", "Alarm")
            _patterns_cache = {}
            for hash_id, pattern_str in raw_patterns.items():
                if '/' in pattern_str:
                    gift, model = pattern_str.split('/', 1)
                    _patterns_cache[hash_id] = (gift.strip(), model.strip())
        except:
            _patterns_cache = {}
    return _patterns_cache

def get_unique_gifts() -> List[str]:
    """Возвращает уникальный список подарков"""
    gifts = load_gifts()
    return sorted(set(gifts.values()))

def get_unique_models() -> List[str]:
    """Возвращает уникальный список моделей (узоров)"""
    patterns = load_patterns()
    models = set()
    for gift, model in patterns.values():
        models.add(model)
    return sorted(models)

def load_full_cache() -> Dict:
    """Загружает полный кэш из JSON файла"""
    global _full_cache
    if _full_cache is None:
        if os.path.exists(GIFTS_CACHE_FILE):
            try:
                with open(GIFTS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    _full_cache = json.load(f)
                    print(f"✅ Загружен кэш подарков: {len(_full_cache.get('gifts', {}))} подарков")
            except:
                _full_cache = {}
        else:
            _full_cache = {}
    return _full_cache

def save_full_cache(cache_data: Dict):
    """Сохраняет полный кэш в JSON файл"""
    global _full_cache
    _full_cache = cache_data
    
    # Создаем директорию если её нет
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    with open(GIFTS_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Кэш сохранен: {len(cache_data.get('gifts', {}))} подарков")

def build_gifts_cache(gift_list: List[str] = None):
    """Строит кэш подарков с моделями/паттернами/фонами"""
    
    if gift_list is None:
        # Топ популярных подарков для быстрого кэширования
        gift_list = [
            "Ice Cream", "Santa Hat", "Delicious Cake", "Green Star",
            "Blue Star", "Red Star", "Plush Pepe", "Precious Peach",
            "Candy Cane", "Signet Ring", "Easter Egg", "Electric Skull",
            "Ginger Cookie", "Ion Gem", "Lol Pop", "Love Potion"
        ]
    
    print(f"🔄 Загружаю данные для {len(gift_list)} подарков...")
    
    # Загружаем существующий кэш
    cache = load_full_cache()
    if 'gifts' not in cache:
        cache['gifts'] = {}
    cache['updated_at'] = datetime.now().isoformat()
    
    total = len(gift_list)
    success_count = 0
    
    for i, gift_name in enumerate(gift_list, 1):
        print(f"  [{i}/{total}] {gift_name}...", end='', flush=True)
        
        try:
            # Загружаем модели
            url = f"https://api.changes.tg/models/{gift_name}"
            resp = requests.get(url, timeout=10)
            models = [m['name'] for m in resp.json()] if resp.status_code == 200 else []
            
            # Загружаем паттерны
            url = f"https://api.changes.tg/patterns/{gift_name}"
            resp = requests.get(url, timeout=10)
            patterns = [p['name'] for p in resp.json()] if resp.status_code == 200 else []
            
            # Загружаем фоны
            url = f"https://api.changes.tg/backdrops/{gift_name}"
            resp = requests.get(url, timeout=10)
            backdrops = [b['name'] for b in resp.json()] if resp.status_code == 200 else []
            
            cache['gifts'][gift_name] = {
                'models': models,
                'patterns': patterns,
                'backdrops': backdrops
            }
            
            print(f" ✅ M:{len(models)} P:{len(patterns)} B:{len(backdrops)}")
            success_count += 1
            
        except Exception as e:
            print(f" ❌ {str(e)[:50]}")
            # Сохраняем пустой кэш чтобы не пытаться загрузить снова
            if gift_name not in cache['gifts']:
                cache['gifts'][gift_name] = {
                    'models': [],
                    'patterns': [],
                    'backdrops': []
                }
    
    save_full_cache(cache)
    print(f"\n✅ Кэш обновлен! Успешно: {success_count}/{total}, Всего в кэше: {len(cache['gifts'])}")
    return cache

def get_models_for_gift(gift_name: str) -> List[str]:
    """Возвращает все модели для конкретного подарка (из кэша или API)"""
    cache = load_full_cache()
    
    # Проверяем кэш
    if gift_name in cache.get('gifts', {}):
        return cache['gifts'][gift_name].get('models', [])
    
    # Если нет в кэше - загружаем из API
    try:
        url = f"https://api.changes.tg/models/{gift_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            models_data = resp.json()
            models = [m['name'] for m in models_data]
            
            # Сохраняем в кэш
            if 'gifts' not in cache:
                cache['gifts'] = {}
            if gift_name not in cache['gifts']:
                cache['gifts'][gift_name] = {}
            cache['gifts'][gift_name]['models'] = models
            save_full_cache(cache)
            
            return models
        return []
    except Exception as e:
        print(f"Ошибка загрузки моделей для {gift_name}: {e}")
        return []

def get_patterns_for_gift(gift_name: str) -> List[str]:
    """Возвращает все паттерны/символы для конкретного подарка (из кэша или API)"""
    cache = load_full_cache()
    
    # Проверяем кэш
    if gift_name in cache.get('gifts', {}):
        return cache['gifts'][gift_name].get('patterns', [])
    
    # Если нет в кэше - загружаем из API
    try:
        url = f"https://api.changes.tg/patterns/{gift_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            patterns_data = resp.json()
            patterns = [p['name'] for p in patterns_data]
            
            # Сохраняем в кэш
            if 'gifts' not in cache:
                cache['gifts'] = {}
            if gift_name not in cache['gifts']:
                cache['gifts'][gift_name] = {}
            cache['gifts'][gift_name]['patterns'] = patterns
            save_full_cache(cache)
            
            return patterns
        return []
    except Exception as e:
        print(f"Ошибка загрузки паттернов для {gift_name}: {e}")
        return []

def get_backdrops_for_gift(gift_name: str) -> List[str]:
    """Возвращает все фоны для конкретного подарка (из кэша или API)"""
    cache = load_full_cache()
    
    # Проверяем кэш
    if gift_name in cache.get('gifts', {}):
        return cache['gifts'][gift_name].get('backdrops', [])
    
    # Если нет в кэше - загружаем из API
    try:
        url = f"https://api.changes.tg/backdrops/{gift_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            backdrops_data = resp.json()
            backdrops = [b['name'] for b in backdrops_data]
            
            # Сохраняем в кэш
            if 'gifts' not in cache:
                cache['gifts'] = {}
            if gift_name not in cache['gifts']:
                cache['gifts'][gift_name] = {}
            cache['gifts'][gift_name]['backdrops'] = backdrops
            save_full_cache(cache)
            
            return backdrops
        return []
    except Exception as e:
        print(f"Ошибка загрузки фонов для {gift_name}: {e}")
        return []

# Backdrops data
BACKDROPS_DATA = [
    {"name": "Black", "backdropId": 0},
    {"name": "Electric Purple", "backdropId": 1},
    {"name": "Lavender", "backdropId": 2},
    {"name": "Cyberpunk", "backdropId": 3},
    {"name": "Electric Indigo", "backdropId": 4},
    {"name": "Neon Blue", "backdropId": 5},
    {"name": "Navy Blue", "backdropId": 6},
    {"name": "Sapphire", "backdropId": 7},
    {"name": "Sky Blue", "backdropId": 8},
    {"name": "Azure Blue", "backdropId": 9},
    {"name": "Pacific Cyan", "backdropId": 10},
    {"name": "Aquamarine", "backdropId": 11},
    {"name": "Pacific Green", "backdropId": 12},
    {"name": "Emerald", "backdropId": 13},
    {"name": "Mint Green", "backdropId": 14},
    {"name": "Malachite", "backdropId": 15},
    {"name": "Shamrock Green", "backdropId": 16},
    {"name": "Lemongrass", "backdropId": 17},
    {"name": "Light Olive", "backdropId": 18},
    {"name": "Satin Gold", "backdropId": 19},
    {"name": "Pure Gold", "backdropId": 20},
    {"name": "Amber", "backdropId": 21},
    {"name": "Caramel", "backdropId": 22},
    {"name": "Orange", "backdropId": 23},
    {"name": "Carrot Juice", "backdropId": 24},
    {"name": "Coral Red", "backdropId": 25},
    {"name": "Persimmon", "backdropId": 26},
    {"name": "Strawberry", "backdropId": 27},
    {"name": "Raspberry", "backdropId": 28},
    {"name": "Mystic Pearl", "backdropId": 29},
    {"name": "Fandango", "backdropId": 30},
    {"name": "Dark Lilac", "backdropId": 31},
    {"name": "English Violet", "backdropId": 32},
    {"name": "Moonstone", "backdropId": 33},
    {"name": "Pine Green", "backdropId": 34},
    {"name": "Hunter Green", "backdropId": 35},
    {"name": "Pistachio", "backdropId": 36},
    {"name": "Khaki Green", "backdropId": 37},
    {"name": "Desert Sand", "backdropId": 38},
    {"name": "Cappuccino", "backdropId": 39},
    {"name": "Rosewood", "backdropId": 40},
    {"name": "Ivory White", "backdropId": 41},
    {"name": "Platinum", "backdropId": 42},
    {"name": "Roman Silver", "backdropId": 43},
    {"name": "Steel Grey", "backdropId": 44},
    {"name": "Silver Blue", "backdropId": 45},
    {"name": "Burgundy", "backdropId": 46},
    {"name": "Indigo Dye", "backdropId": 47},
    {"name": "Midnight Blue", "backdropId": 48},
    {"name": "Onyx Black", "backdropId": 49},
    {"name": "Battleship Grey", "backdropId": 50},
    {"name": "Purple", "backdropId": 51},
    {"name": "Grape", "backdropId": 52},
    {"name": "Cobalt Blue", "backdropId": 53},
    {"name": "French Blue", "backdropId": 54},
    {"name": "Turquoise", "backdropId": 55},
    {"name": "Jade Green", "backdropId": 56},
    {"name": "Copper", "backdropId": 57},
    {"name": "Chestnut", "backdropId": 58},
    {"name": "Chocolate", "backdropId": 59},
    {"name": "Marine Blue", "backdropId": 60},
    {"name": "Tactical Pine", "backdropId": 61},
    {"name": "Gunship Green", "backdropId": 62},
    {"name": "Dark Green", "backdropId": 63},
    {"name": "Seal Brown", "backdropId": 64},
    {"name": "Rifle Green", "backdropId": 65},
    {"name": "Ranger Green", "backdropId": 66},
    {"name": "Camo Green", "backdropId": 67},
    {"name": "Feldgrau", "backdropId": 68},
    {"name": "Gunmetal", "backdropId": 69},
    {"name": "Deep Cyan", "backdropId": 70},
    {"name": "Mexican Pink", "backdropId": 71},
    {"name": "Tomato", "backdropId": 72},
    {"name": "Fire Engine", "backdropId": 73},
    {"name": "Celtic Blue", "backdropId": 74},
    {"name": "Old Gold", "backdropId": 75},
    {"name": "Burnt Sienna", "backdropId": 76},
    {"name": "Carmine", "backdropId": 77},
    {"name": "Mustard", "backdropId": 78},
    {"name": "French Violet", "backdropId": 79},
]

def get_unique_backdrops() -> List[str]:
    """Возвращает список всех фонов"""
    return [b['name'] for b in BACKDROPS_DATA]


# Удаляем старый GIFT_MODELS - теперь используем load_gifts()
GIFT_MODELS_OLD = {
    "5983471780763796287": "Santa Hat",
    "5936085638515261992": "Signet Ring",
    "5933671725160989227": "Precious Peach",
    "5936013938331222567": "Plush Pepe",
    "5913442287462908725": "Spiced Wine",
    "5915502858152706668": "Jelly Bunny",
    "5915521180483191380": "Durov's Cap",
    "5913517067138499193": "Perfume Bottle",
    "5882125812596999035": "Eternal Rose",
    "5882252952218894938": "Berry Box",
    "5857140566201991735": "Vintage Cigar",
    "5846226946928673709": "Magic Potion",
    "5845776576658015084": "Kissed Frog",
    "5825801628657124140": "Hex Pot",
    "5825480571261813595": "Evil Eye",
    "5841689550203650524": "Sharp Tongue",
    "5841391256135008713": "Trapped Heart",
    "5839038009193792264": "Skull Flower",
    "5837059369300132790": "Scared Cat",
    "5821261908354794038": "Spy Agaric",
    "5783075783622787539": "Homemade Cake",
    "5933531623327795414": "Genie Lamp",
    "6028426950047957932": "Lunar Snake",
    "6003643167683903930": "Party Sparkler",
    "5933590374185435592": "Jester Hat",
    "5821384757304362229": "Witch Hat",
    "5915733223018594841": "Hanging Star",
    "5915550639663874519": "Love Candle",
    "6001538689543439169": "Cookie Heart",
    "5782988952268964995": "Desk Calendar",
    "6001473264306619020": "Jingle Bells",
    "5980789805615678057": "Snow Mittens",
    "5836780359634649414": "Voodoo Doll",
    "5841632504448025405": "Mad Pumpkin",
    "5825895989088617224": "Hypno Lollipop",
    "5782984811920491178": "B-Day Candle",
    "5935936766358847989": "Bunny Muffin",
    "5933629604416717361": "Astral Shard",
    "5837063436634161765": "Flying Broom",
    "5841336413697606412": "Crystal Ball",
    "5821205665758053411": "Eternal Candle",
    "5936043693864651359": "Swiss Watch",
    "5983484377902875708": "Ginger Cookie",
    "5879737836550226478": "Mini Oscar",
    "5170594532177215681": "Lol Pop",
    "5843762284240831056": "Ion Gem",
    "5936017773737018241": "Star Notepad",
    "5868659926187901653": "Loot Bag",
    "5868348541058942091": "Love Potion",
    "5868220813026526561": "Toy Bear",
    "5868503709637411929": "Diamond Ring",
    "5167939598143193218": "Sakura Flower",
    "5981026247860290310": "Sleigh Bell",
    "5897593557492957738": "Top Hat",
    "5856973938650776169": "Record Player",
    "5983259145522906006": "Winter Wreath",
    "5981132629905245483": "Snow Globe",
    "5846192273657692751": "Electric Skull",
    "6023752243218481939": "Tama Gadget",
    "6003373314888696650": "Candy Cane",
    "5933793770951673155": "Neko Helmet",
    "6005659564635063386": "Jack-in-the-Box",
    "5773668482394620318": "Easter Egg",
    "5870661333703197240": "Bonded Ring",
    "6023917088358269866": "Pet Snake",
    "6023679164349940429": "Snake Box",
    "6003767644426076664": "Xmas Stocking",
    "6028283532500009446": "Big Year",
    "6003735372041814769": "Holiday Drink",
    "5859442703032386168": "Gem Signet",
    "5897581235231785485": "Light Sword",
    "5870784783948186838": "Restless Jar",
    "5870720080265871962": "Nail Bracelet",
    "5895328365971244193": "Heroic Helmet",
    "5895544372761461960": "Bow Tie",
    "5868455043362980631": "Heart Locket",
    "5871002671934079382": "Lush Bouquet",
    "5933543975653737112": "Whip Cupcake",
    "5870862540036113469": "Joyful Bundle",
    "5868561433997870501": "Cupid Charm",
    "5868595669182186720": "Valentine Box",
    "6014591077976114307": "Snoop Dogg",
    "6012607142387778152": "Swag Bag",
    "6012435906336654262": "Snoop Cigar",
    "6014675319464657779": "Low Rider",
    "6014697240977737490": "Westside Sign",
    "6042113507581755979": "Stellar Rocket",
    "6005880141270483700": "Jolly Chimp",
    "5998981470310368313": "Moon Pendant",
    "5933937398953018107": "Ionic Dryer",
    "5870972044522291836": "Input Key",
    "5895518353849582541": "Mighty Arm",
    "6005797617768858105": "Artisan Brick",
    "5960747083030856414": "Clover Pin",
    "5870947077877400011": "Sky Stilettos",
    "5895603153683874485": "Fresh Socks",
    "6006064678835323371": "Happy Brownie",
    "5900177027566142759": "Ice Cream",
    "5773725897517433693": "Spring Basket",
    "6005564615793050414": "Instant Ramen",
    "6003456431095808759": "Faith Amulet",
    "5935877878062253519": "Mousse Cake",
    "5902339509239940491": "Bling Binky",
    "5963238670868677492": "Money Pot",
    "5933737850477478635": "Pretty Posy",
    "5839094187366024301": "Khabib's Papakha",
    "5882260270843168924": "UFC Strike",
}
