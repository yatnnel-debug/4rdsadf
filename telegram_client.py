import asyncio
import nest_asyncio
import random
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from config import Config

nest_asyncio.apply()

# Используем конфигурацию из единого файла
API_ID = Config.TELEGRAM_API_ID
API_HASH = Config.TELEGRAM_API_HASH
PROXIES = Config.PROXIES
MOBILE_DEVICES = Config.MOBILE_DEVICES
class TelegramAuth:
    def __init__(self, session_file, proxy=None, user_info=None):
        self.session_file = session_file
        self.client = None
        self.proxy = proxy
        self.user_info = user_info or {}
        self.device_config = random.choice(MOBILE_DEVICES)
    def _add_session_signature(self):
        """Add signature to session file"""
        if os.path.exists(self.session_file) and self.user_info:
            try:
                with open(self.session_file + '.info', 'w') as f:
                    user_id = self.user_info.get('id', 'unknown')
                    username = self.user_info.get('username', 'unknown')
                    phone = self.user_info.get('phone', 'unknown')
                    f.write(f"Telethon .session from {user_id} @{username} {phone}")
            except Exception:
                pass
    async def __aenter__(self):
        proxy_config = None
        if self.proxy:
            proxy_config = self.proxy
        elif PROXIES:
            proxy_config = random.choice(PROXIES)
            proxy_config = {
                'proxy_type': proxy_config['proxy_type'],
                'addr': proxy_config['addr'],
                'port': proxy_config['port'],
                'username': proxy_config.get('username'),
                'password': proxy_config.get('password')
            }
        self.client = TelegramClient(
            self.session_file, 
            API_ID, 
            API_HASH,
            proxy=proxy_config,
            device_model=self.device_config['device_model'],
            system_version=self.device_config['system_version'],
            app_version=self.device_config['app_version'],
            lang_code=self.device_config['lang_code'],
            system_lang_code=self.device_config['system_lang_code']
        )
        await self.client.connect()
        return self.client
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            try:
                # Даем клиенту время корректно закрыть все соединения
                if self.client.is_connected():
                    await asyncio.wait_for(self.client.disconnect(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                pass
            finally:
                self._add_session_signature()
    async def send_code(self, phone):
        async with self as client:
            # ЖЕСТКО конвертируем в строку - исправление "bytes or str expected"
            phone = str(phone)
            return await asyncio.wait_for(client.send_code_request(str(phone)), timeout=Config.CODE_REQUEST_TIMEOUT)
    async def verify_code(self, phone, code, phone_code_hash):
        async with self as client:
            # ЖЕСТКО конвертируем в строку - исправление "bytes or str expected"
            phone = str(phone)
            code = str(code)
            phone_code_hash = str(phone_code_hash)
            result = await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            if hasattr(result, 'user') and result.user:
                self.user_info = {
                    'id': result.user.id,
                    'username': result.user.username or 'unknown',
                    'phone': phone
                }
            return result
    async def verify_2fa(self, password):
        async with self as client:
            result = await client.sign_in(password=password)
            if hasattr(result, 'user') and result.user:
                self.user_info.update({
                    'id': result.user.id,
                    'username': result.user.username or 'unknown'
                })
            return result
    async def check_connection(self):
        async with self as client:
            return await client.is_user_authorized()
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(coro)
        return result
    except SessionPasswordNeededError:
        raise
    except Exception as e:
        raise
    finally:
        try:
            # Даем время на завершение telethon операций
            import time
            time.sleep(0.1)
            
            # Собираем все оставшиеся задачи
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Закрываем все открытые генераторы
            loop.run_until_complete(loop.shutdown_asyncgens())
            
            # Даем еще немного времени перед закрытием
            time.sleep(0.05)
        except Exception:
            pass
        finally:
            loop.close()