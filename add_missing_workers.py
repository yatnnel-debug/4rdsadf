import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

# Воркеры, которых не было в БД
missing_workers = [
    {"username": "Vika8393", "telegram_id": 8578072689},  # Реальный username вместо user8578072689
]

# Жертвы, которых не было в БД
missing_victims = []

print("📝 Добавление отсутствующих пользователей...")

for worker in missing_workers:
    try:
        # Проверяем, есть ли уже в БД
        existing = db.get_telegram_id_by_username(worker['username'])
        if existing:
            print(f"✅ Воркер @{worker['username']} уже есть в БД (ID: {existing})")
        else:
            db.create_user(
                telegram_id=worker['telegram_id'],
                username=worker['username'],
                first_name=None,
                last_name=None
            )
            print(f"✅ Воркер @{worker['username']} добавлен (ID: {worker['telegram_id']})")
    except Exception as e:
        print(f"❌ Ошибка добавления воркера @{worker['username']}: {e}")

for victim in missing_victims:
    try:
        existing = db.get_telegram_id_by_username(victim['username'])
        if existing:
            print(f"✅ Жертва @{victim['username']} уже есть в БД (ID: {existing})")
        else:
            db.create_user(
                telegram_id=victim['telegram_id'],
                username=victim['username'],
                first_name=None,
                last_name=None
            )
            print(f"✅ Жертва @{victim['username']} добавлена (ID: {victim['telegram_id']})")
    except Exception as e:
        print(f"❌ Ошибка добавления жертвы @{victim['username']}: {e}")

print("\n📊 Готово!")
