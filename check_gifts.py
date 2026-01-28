import asyncio
import os
from pyrogram import Client
from config import Config

async def check_and_process_gifts():
    phone = "+959766096218"
    session_file = f"sessions/{phone.replace('+', '').replace(' ', '')}.session"
    
    print(f"🔍 Проверка подарков для аккаунта: {phone}")
    print(f"📁 Сессия: {session_file}")
    
    if not os.path.exists(session_file):
        print("❌ Файл сессии не найден!")
        return
    
    # Конвертируем Telethon сессию в Pyrogram
    print("\n🔄 Конвертация сессии в Pyrogram...")
    from utils import convert_telethon_to_pyrogram
    
    try:
        pyrogram_session = await convert_telethon_to_pyrogram(session_file)
        print(f"✅ Сессия сконвертирована!")
        print(f"📝 Session string (первые 50 символов): {pyrogram_session[:50]}...")
        
        # Создаем клиент Pyrogram
        print("\n🚀 Подключение к Telegram...")
        client = Client(
            name="gift_checker",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            session_string=pyrogram_session
        )
        
        await client.start()
        print("✅ Подключено!")
        
        # Получаем информацию о себе
        me = await client.get_me()
        print(f"\n👤 Авторизован как:")
        print(f"   ID: {me.id}")
        print(f"   Username: @{me.username if me.username else 'нет'}")
        print(f"   First Name: {me.first_name}")
        
        # Получаем подарки
        print(f"\n🎁 Получение списка подарков...")
        gifts_count = 0
        
        async for gift in client.get_chat_gifts("me"):
            gifts_count += 1
            print(f"\n🎁 Подарок #{gifts_count}:")
            print(f"   ID: {gift.id}")
            if hasattr(gift, 'link'):
                print(f"   Link: {gift.link}")
            if hasattr(gift, 'gift'):
                print(f"   Gift Info: {gift.gift}")
        
        if gifts_count == 0:
            print("📭 Подарков не найдено")
        else:
            print(f"\n✅ Всего найдено подарков: {gifts_count}")
        
        await client.stop()
        print("\n✅ Проверка завершена!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_and_process_gifts())
