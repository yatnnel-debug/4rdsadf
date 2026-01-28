import asyncio
from telegram_client import TelegramAuth
from config import Config

API_ID=146746
API_HASH="a7ab276b0b1a3c20b4b3126"

async def authorize_account(phone):
    print(f"🔐 Начинаю авторизацию для номера: {phone}")
    print(f"📱 API ID: {Config.TELEGRAM_API_ID}")
    
    session_file = f"sessions/{phone.replace('+', '').replace(' ', '')}.session"
    print(f"💾 Файл сессии: {session_file}")
    
    auth = TelegramAuth(session_file)
    
    try:
        # Отправляем код
        print("\n📤 Отправка кода подтверждения...")
        result = await auth.send_code(phone)
        print(f"✅ Код отправлен! Phone code hash: {result.phone_code_hash}")
        
        # Ждем ввода кода
        code = input("\n🔢 Введите код из Telegram: ")
        
        print("\n🔐 Проверка кода...")
        try:
            user = await auth.verify_code(phone, code, result.phone_code_hash)
            print(f"✅ Успешная авторизация!")
            print(f"👤 User ID: {user.user.id}")
            print(f"📱 Username: @{user.user.username if user.user.username else 'нет'}")
            
        except Exception as verify_error:
            if "SessionPasswordNeededError" in str(type(verify_error).__name__):
                print("\n🔒 Требуется 2FA пароль!")
                password = input("🔑 Введите 2FA пароль: ")
                
                print("\n🔐 Проверка 2FA...")
                user = await auth.verify_2fa(password)
                print(f"✅ Успешная авторизация с 2FA!")
                print(f"👤 User ID: {user.id}")
                print(f"📱 Username: @{user.username if user.username else 'нет'}")
            else:
                raise verify_error
        
        print(f"\n✅ Сессия сохранена в: {session_file}")
        print("🎉 Авторизация завершена успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    phone = "+49 152547225077"
    asyncio.run(authorize_account(phone))
