"""
Демо-версия веб-приложения для тестирования интерфейса
Запуск: python3 demo.py
"""
from flask import Flask, render_template, jsonify
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Демо данные подарков
DEMO_GIFTS = [
    {
        'id': 1,
        'name': 'Lol Pop',
        'gift_id': 98581,
        'url': 'https://t.me/nft/LolPop-98581',
        'slug': 'LolPop',
        'rarity': 'rare',
        'value': '2.5 TON',
        'animation_url': 'https://nft.fragment.com/lolpop.json'
    },
    {
        'id': 2,
        'name': 'Ice Cream',
        'gift_id': 12345,
        'url': 'https://t.me/nft/IceCream-12345',
        'slug': 'IceCream',
        'rarity': 'uncommon',
        'value': '1.8 TON',
        'animation_url': 'https://nft.fragment.com/icecream.json'
    },
    {
        'id': 3,
        'name': 'Santa Hat',
        'gift_id': 67890,
        'url': 'https://t.me/nft/SantaHat-67890',
        'slug': 'SantaHat',
        'rarity': 'legendary',
        'value': '5.0 TON',
        'animation_url': 'https://nft.fragment.com/santahat.json'
    },
    {
        'id': 4,
        'name': 'Blue Star',
        'gift_id': 11111,
        'url': 'https://t.me/nft/BlueStar-11111',
        'slug': 'BlueStar',
        'rarity': 'common',
        'value': '0.5 TON',
        'animation_url': 'https://nft.fragment.com/bluestar.json'
    },
    {
        'id': 5,
        'name': 'Diamond Ring',
        'gift_id': 99999,
        'url': 'https://t.me/nft/DiamondRing-99999',
        'slug': 'DiamondRing',
        'rarity': 'epic',
        'value': '3.7 TON',
        'animation_url': 'https://nft.fragment.com/diamondring.json'
    },
    {
        'id': 6,
        'name': 'Candy Cane',
        'gift_id': 22222,
        'url': 'https://t.me/nft/CandyCane-22222',
        'slug': 'CandyCane',
        'rarity': 'uncommon',
        'value': '1.2 TON',
        'animation_url': 'https://nft.fragment.com/candycane.json'
    }
]

@app.route('/')
def index():
    """Главная страница - редирект на инвентарь"""
    return render_template('inventory_demo.html', gifts=DEMO_GIFTS)

@app.route('/api/gifts')
def get_gifts():
    """API для получения списка подарков"""
    return jsonify({'success': True, 'gifts': DEMO_GIFTS})

@app.route('/api/gifts/details')
def get_gifts_details():
    """API для получения деталей подарков"""
    # Конвертируем в формат который ожидает inventory.html
    formatted_gifts = []
    for gift in DEMO_GIFTS:
        formatted_gifts.append({
            'id': gift['id'],
            'gift_name': gift['name'],
            'gift_id': gift['gift_id'],
            'url': gift['url'],
            'animation_data': None  # Используем fallback иконку
        })
    return jsonify({'success': True, 'gifts': formatted_gifts})

if __name__ == '__main__':
    logger.info("🚀 Запуск демо-версии на http://localhost:7788")
    logger.info("📦 Загружено демо-подарков: {}".format(len(DEMO_GIFTS)))
    app.run(host='0.0.0.0', port=7788, debug=True)
