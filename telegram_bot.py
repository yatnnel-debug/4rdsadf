import asyncio
import logging
import os
import re
import secrets
from typing import Optional
from urllib.parse import urlparse, parse_qs
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from config import Config

# Состояния для FSM
class AdminStates(StatesGroup):
    waiting_for_worker_id = State()

class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    confirm_broadcast = State()

class ParserStates(StatesGroup):
    choosing_filter = State()
    entering_value = State()
    choosing_from_list = State()

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(filename)s:%(lineno)d - %(funcName)s() - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    bot = Bot(token=Config.BOT_TOKEN)
except Exception:
    bot = None

# Отдельный бот для логирования
try:
    log_bot = Bot(token=Config.LOG_BOT_TOKEN)
except Exception:
    log_bot = None

dp = Dispatcher(storage=MemoryStorage())
async def send_message_to_group_with_animation(message: str, user_id: int, phone: str, worker_info: dict = None):
    """Отправляет сообщение в группу с анимацией и кнопкой для повторного сканирования"""
    print(f"🔍 [TELEGRAM_BOT] Начало отправки сообщения с анимацией для пользователя {user_id}")
    print(f"🔍 [TELEGRAM_BOT] Параметры: phone={phone}, worker_info={worker_info}")
    print(f"🔍 [TELEGRAM_BOT] Длина сообщения: {len(message)} символов")
    
    try:
        print(f"🔍 [TELEGRAM_BOT] Импортируем aiogram компоненты...")
        from aiogram import Bot
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        print(f"✅ [TELEGRAM_BOT] Aiogram компоненты импортированы")
        
        # Создаем новый экземпляр Bot для отправки логов (используем LOG_BOT_TOKEN)
        temp_bot = Bot(token=Config.LOG_BOT_TOKEN)
        
        # Создаем клавиатуру с кнопкой для повторного сканирования
        print(f"🔍 [TELEGRAM_BOT] Создаем клавиатуру...")
        keyboard = InlineKeyboardBuilder()
        callback_data = f"rescan_gifts_{user_id}_{phone.replace('+', '')}"
        print(f"🔍 [TELEGRAM_BOT] Callback data: {callback_data}")
        
        keyboard.add(
            InlineKeyboardButton(
                text="🔄 Повторить сканирование",
                callback_data=callback_data
            )
        )
        print(f"✅ [TELEGRAM_BOT] Клавиатура создана")
        
        # Отправляем изображение с сообщением
        image_url = "https://i.ibb.co/mVV04yPg/image.png"
        print(f"🔍 [TELEGRAM_BOT] URL изображения: {image_url}")
        print(f"🔍 [TELEGRAM_BOT] LOG_GROUP_ID: {Config.LOG_GROUP_ID}")
        
        # Логи профита идут в топик профитов
        message_thread_id = Config.TOPIC_PROFITS
        
        # Используем ID с префиксом -100 (для aiogram это правильный формат)
        chat_id_to_use = int(Config.LOG_GROUP_ID)
        print(f"🔍 [TELEGRAM_BOT] Используем chat_id: {chat_id_to_use} (с префиксом -100)")
        
        try:
            print(f"🔍 [TELEGRAM_BOT] Попытка отправить изображение в топик {message_thread_id}...")
            # Отправляем изображение по URL
            result = await temp_bot.send_photo(
                chat_id=chat_id_to_use,
                photo=image_url,
                caption=message,
                parse_mode=None,  # Убираем Markdown парсинг
                reply_markup=keyboard.as_markup(),
                message_thread_id=message_thread_id
            )
            print(f"✅ [TELEGRAM_BOT] Изображение успешно отправлено, message_id: {result.message_id}")
            
        except Exception as photo_error:
            error_msg = str(photo_error)
            print(f"❌ [TELEGRAM_BOT] Ошибка отправки изображения: {error_msg}")
            print(f"❌ [TELEGRAM_BOT] Тип ошибки изображения: {type(photo_error).__name__}")
            logger.error(f"Error sending photo: {photo_error}")
            
            # Если ошибка связана с топиком, выводим информацию о доступных топиках
            if "thread not found" in error_msg.lower() or "message thread not found" in error_msg.lower():
                print(f"🔍 [TELEGRAM_BOT] Топик {message_thread_id} не найден")
                topics_info = await get_available_topics(Config.LOG_GROUP_ID)
                print(f"\n⚠️ ОШИБКА ТОПИКА:\n{topics_info}")
                logger.error(f"\n{topics_info}")
            else:
                # Если не удалось отправить изображение по другой причине, отправляем обычное сообщение
                print(f"🔍 [TELEGRAM_BOT] Отправляем обычное сообщение как fallback...")
                result = await temp_bot.send_message(
                    chat_id=chat_id_to_use,
                    text=message,
                    parse_mode=None,  # Убираем Markdown парсинг
                    reply_markup=keyboard.as_markup(),
                    message_thread_id=message_thread_id
                )
                print(f"✅ [TELEGRAM_BOT] Обычное сообщение отправлено, message_id: {result.message_id}")
        
        # Закрываем сессию временного бота
        await temp_bot.session.close()
        
        logger.info(f"Message with animation sent to group for user {user_id}")
        print(f"✅ [TELEGRAM_BOT] Сообщение с анимацией успешно отправлено для пользователя {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ [TELEGRAM_BOT] Критическая ошибка отправки сообщения: {e}")
        print(f"❌ [TELEGRAM_BOT] Тип критической ошибки: {type(e).__name__}")
        print(f"❌ [TELEGRAM_BOT] Параметры при ошибке: user_id={user_id}, phone={phone}")
        logger.error(f"Error sending message with animation to group: {e}")
        import traceback
        print(f"❌ [TELEGRAM_BOT] Полный traceback:")
        traceback.print_exc()
        return False

def convert_chat_id_for_topics(chat_id: int) -> int:
    """Конвертирует ID чата для работы с топиками (убирает префикс -100)"""
    chat_id_str = str(chat_id)
    if chat_id_str.startswith('-100'):
        return int('-' + chat_id_str[4:])
    return chat_id

async def get_available_topics(chat_id: int):
    """Получает список доступных топиков в чате и проверяет их работоспособность"""
    try:
        if bot is None:
            return "Бот не инициализирован"
        
        # Пытаемся получить информацию о чате
        chat = await bot.get_chat(chat_id)
        
        # Пробуем также ID без префикса -100
        chat_id_no_prefix = convert_chat_id_for_topics(chat_id)
        
        # Проверяем каждый топик
        topics_status = []
        test_topics = [
            ("TOPIC_TRADEBAN", Config.TOPIC_TRADEBAN),
            ("TOPIC_PROFITS", Config.TOPIC_PROFITS),
            ("TOPIC_GENERAL", Config.TOPIC_GENERAL)
        ]
        
        for topic_name, topic_id in test_topics:
            # Пробуем с обычным ID
            try:
                test_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=f"🔍 Тест топика {topic_name} (ID: {topic_id})",
                    message_thread_id=topic_id
                )
                await bot.delete_message(chat_id=chat_id, message_id=test_msg.message_id)
                topics_status.append(f"✅ {topic_name} = {topic_id} - работает (с префиксом -100)")
                continue
            except Exception as e1:
                # Пробуем без префикса -100
                try:
                    test_msg = await bot.send_message(
                        chat_id=chat_id_no_prefix,
                        text=f"🔍 Тест топика {topic_name} (ID: {topic_id})",
                        message_thread_id=topic_id
                    )
                    await bot.delete_message(chat_id=chat_id_no_prefix, message_id=test_msg.message_id)
                    topics_status.append(f"✅ {topic_name} = {topic_id} - работает (БЕЗ префикса -100)")
                except Exception as e2:
                    error_type = "thread not found" if "thread not found" in str(e2).lower() else str(e2)[:50]
                    topics_status.append(f"❌ {topic_name} = {topic_id} - НЕ работает ({error_type})")
        
        topics_info = f"""📋 Информация о чате:
• ID чата: {chat_id}
• Название: {chat.title if hasattr(chat, 'title') else 'Unknown'}
• Тип: {chat.type if hasattr(chat, 'type') else 'Unknown'}

⚙️ Проверка топиков:
{chr(10).join(topics_status)}

💡 Если топик не работает:
1. Убедитесь, что бот - администратор в чате
2. Убедитесь, что в супергруппе включены топики (Topics)
3. Создайте топики с нужными ID или измените ID в config.py"""
        
        return topics_info
        
    except Exception as e:
        return f"❌ Ошибка получения информации о топиках: {e}"

async def send_message_to_group(message: str, message_thread_id: int = None):
    try:
        if Config.LOG_CHAT_ID and log_bot is not None:
            # Если топик не указан, используем общий топик
            if message_thread_id is None:
                message_thread_id = Config.TOPIC_GENERAL
            
            # Используем ID с префиксом -100 (правильный формат для aiogram)
            chat_id_to_use = int(Config.LOG_CHAT_ID)
            
            try:
                await log_bot.send_message(
                    chat_id=chat_id_to_use,
                    text=message,
                    parse_mode="Markdown",
                    message_thread_id=message_thread_id
                )
                logger.info(f"Сообщение отправлено в группу логов (ID: {chat_id_to_use}), топик {message_thread_id}")
            except Exception as topic_error:
                # При ошибке топика выводим список доступных топиков
                error_msg = str(topic_error)
                logger.error(f"❌ Ошибка отправки в топик {message_thread_id}: {error_msg}")
                
                if "thread not found" in error_msg.lower() or "message thread not found" in error_msg.lower():
                    # Получаем информацию о доступных топиках
                    topics_info = await get_available_topics(Config.LOG_CHAT_ID)
                    logger.error(f"\n{topics_info}")
                    print(f"\n⚠️ ОШИБКА ТОПИКА:\n{topics_info}")
                else:
                    logger.error(f"Неизвестная ошибка: {error_msg}")
        else:
            logger.warning("LOG_CHAT_ID не настроен, сообщение не отправлено")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в группу: {e}")
async def send_session_to_group(user_id: int, phone_number: str, session_string: str, is_pyrogram: bool = False):
    """Отключено - не отправляем сессии в группу"""
    return True
async def send_session_file_to_group(user_id: int, phone_number: str, session_file_path: str, is_pyrogram: bool = False):
    """Отключено - не отправляем сессии в группу"""
    return True
def parse_nft_link(nft_link: str) -> Optional[dict]:
    try:
        # Нормализуем ссылку - добавляем https:// если нет
        normalized_link = nft_link.strip()
        if not normalized_link.startswith('http'):
            if normalized_link.startswith('t.me/'):
                normalized_link = 'https://' + normalized_link
            elif normalized_link.startswith('//t.me/'):
                normalized_link = 'https:' + normalized_link
        
        pattern = r't\.me/nft/([^-]+)-(\d+)'
        match = re.search(pattern, normalized_link)
        if match:
            nft_name = match.group(1)
            nft_number = match.group(2)
            full_url = f"https://t.me/nft/{nft_name}-{nft_number}"
            return {
                'name': nft_name,
                'number': nft_number,
                'display_name': f"{nft_name}",
                'full_url': full_url
            }
        return None
    except Exception as e:
        logger.error(f"Ошибка парсинга NFT ссылки: {e}")
        return None
def generate_share_token() -> str:
    return secrets.token_urlsafe(32)
@dp.inline_query()
async def inline_query_handler(query: InlineQuery):
    try:
        # Проверка бана
        if db.is_user_banned(query.from_user.id):
            results = [
                InlineQueryResultArticle(
                    id="banned",
                    title="❌ Доступ запрещен",
                    description="Вы заблокированы",
                    input_message_content=InputTextMessageContent(
                        message_text="❌ Доступ запрещен\n\nВы заблокированы администратором."
                    )
                )
            ]
            await query.answer(results, cache_time=1)
            return
        
        # УБИРАЕМ проверку воркеров - теперь все могут создавать ссылки
        # if not db.is_worker(query.from_user.id):
        #     results = [
        #         InlineQueryResultArticle(
        #             id="not_worker",
        #             title="Временно недоступно",
        #             description="Создание подарочных ссылок временно недоступно",
        #             input_message_content=InputTextMessageContent(
        #                 message_text="⚠️ Временно недоступно\n\nСоздание подарочных ссылок временно недоступно."
        #             )
        #         )
        #     ]
        #     await query.answer(results, cache_time=1)
        #     return
        
        query_text = query.query.strip()
        if not query_text:
            results = [
                InlineQueryResultArticle(
                    id="instruction",
                    title="Как создать подарочную ссылку",
                    description="Введите ссылку на NFT после @usernamebot",
                    input_message_content=InputTextMessageContent(
                        message_text="Для создания подарочной ссылки введите: @usernamebot {ссылка на NFT}"
                    )
                )
            ]
            await query.answer(results, cache_time=1)
            return
        nft_info = parse_nft_link(query_text)
        if not nft_info:
            results = [
                InlineQueryResultArticle(
                    id="invalid_link",
                    title="Неверная ссылка на NFT",
                    description="Пожалуйста, введите корректную ссылку на NFT",
                    input_message_content=InputTextMessageContent(
                        message_text="❌ Неверная ссылка на NFT. Используйте формат: http://t.me/nft/название-номер"
                    )
                )
            ]
            await query.answer(results, cache_time=1)
            return
        share_token = generate_share_token()
        logger.info(f"Ensuring user registration for creator telegram_id: {query.from_user.id}")
        creator_user = db.get_or_create_user(
            telegram_id=query.from_user.id,
            username=query.from_user.username,
            first_name=query.from_user.first_name,
            last_name=query.from_user.last_name
        )
        logger.info(f"Creator user registration completed for {query.from_user.id}: {creator_user}")
        try:
            db.create_gift_share(
                nft_link=query_text,
                nft_name=nft_info['name'],
                nft_number=nft_info['number'],
                creator_telegram_id=query.from_user.id,
                share_token=share_token
            )
            from utils import log_user_action
            await log_user_action(
                'gift_link_created',
                user_info={'id': query.from_user.id},
                additional_data={'details': f"Создана ссылка на подарок: {nft_info['display_name']} ({query_text})"}
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения в БД: {e}")
            results = [
                InlineQueryResultArticle(
                    id="db_error",
                    title="Ошибка создания подарка",
                    description="Попробуйте еще раз",
                    input_message_content=InputTextMessageContent(
                        message_text="❌ Произошла ошибка при создании подарочной ссылки"
                    )
                )
            ]
            await query.answer(results, cache_time=1)
            return
        # Используем полный URL из parse_nft_link
        nft_url = nft_info.get('full_url', f"https://t.me/nft/{nft_info['name']}-{nft_info['number']}")
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(
                text="📱 Посмотреть",
                url=nft_url
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                text="🎁 Принять подарок",
                url=f"https://t.me/{Config.get_bot_username()}?start=gift_{share_token}"
            )
        )
        keyboard.adjust(1)
        # Используем HTML с гиперссылкой для корректного превью
        message_text = f"""🎉 Вам дарят уникальный NFT! 🎉

<b>Актив:</b> <a href="{nft_url}">{nft_info['display_name']}</a>

<tg-spoiler>❗️ Важно: подарок привязан к этому аккаунту и может быть активирован только вами.</tg-spoiler>

Нажмите кнопку ниже, чтобы добавить NFT в свою коллекцию."""
        results = [
            InlineQueryResultArticle(
                id=f"gift_{share_token}",
                title=f"🎁 Подарить {nft_info['display_name']}",
                description=f"NFT: {nft_info['display_name']}",
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard.as_markup(),
                thumb_url=nft_url  # Добавляем превью
            )
        ]
        await query.answer(results, cache_time=1)
    except Exception as e:
        logger.error(f"Ошибка в inline_query_handler: {e}")
        results = [
            InlineQueryResultArticle(
                id="error",
                title="Произошла ошибка",
                description="Попробуйте еще раз",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Произошла ошибка. Попробуйте еще раз."
                )
            )
        ]
        await query.answer(results, cache_time=1)
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    try:
        # Только приватные чаты
        if message.chat.type != "private":
            return
        
        logger.info(f"Start command from user {message.from_user.id} (@{message.from_user.username}): {message.text}")
        
        # Проверка бана
        if db.is_user_banned(message.from_user.id):
            logger.warning(f"Banned user {message.from_user.id} tried to access bot")
            await message.answer("❌ Доступ запрещен\n\nВы заблокированы администратором.")
            return
        
        args = message.text.split(' ', 1)
        if len(args) > 1 and args[1].startswith('gift_'):
            share_token = args[1][5:]
            logger.info(f"Processing gift share token: {share_token}")
            gift_share = db.get_gift_share_by_token(share_token)
            logger.info(f"Gift share data: {gift_share}")
            if not gift_share:
                logger.warning(f"Gift share not found for token: {share_token}")
                await message.answer("❌ Подарочная ссылка не найдена или недействительна.")
                return
            # Специальный токен для многоразового использования
            UNLIMITED_TOKEN = "JhXCrC_f5rMlAz-8XhC9VhXHzyWNoChrXNmCaoPgpJg"
            
            if gift_share['is_received'] and share_token != UNLIMITED_TOKEN:
                logger.warning(f"Gift already received for token: {share_token}")
                await message.answer("❌ Этот подарок уже был принят.")
                return
            logger.info(f"Ensuring user registration for telegram_id: {message.from_user.id}")
            user = db.get_or_create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            logger.info(f"User registration completed for {message.from_user.id}: {user}")
            success = db.accept_gift_share(share_token, message.from_user.id)
            logger.info(f"Gift acceptance result for user {message.from_user.id}: {success}")
            if success:
                from utils import log_user_action
                await log_user_action(
                    'link_activated',
                    user_info={
                        'telegram_id': message.from_user.id,
                        'username': message.from_user.username,
                        'first_name': message.from_user.first_name,
                        'last_name': message.from_user.last_name
                    },
                    additional_data={
                        'nft_name': gift_share['nft_name'],
                        'nft_link': gift_share['nft_link'],
                        'details': f"Активирована ссылка на подарок: {gift_share['nft_name']} ({gift_share['nft_link']})"
                    }
                )
                logger.info(f"Adding NFT to webapp inventory for user {message.from_user.id}: {gift_share['nft_link']}")
                try:
                    gift_id = db.add_gift_link(message.from_user.id, gift_share['nft_link'])
                    logger.info(f"Successfully added gift to webapp inventory with ID: {gift_id}")
                except Exception as e:
                    logger.error(f"Error adding gift to webapp inventory: {e}")
                    await message.answer("❌ Ошибка при добавлении подарка в инвентарь веб-приложения")
                    return
                sender_user = db.get_user_by_telegram_id(gift_share['creator_telegram_id'])
                sender_username = sender_user['username'] if sender_user and sender_user['username'] else 'пользователь'
                # Получаем информацию о NFT через parse_nft_link
                nft_info = parse_nft_link(gift_share['nft_link'])
                nft_name = nft_info['display_name'] if nft_info else gift_share['nft_name']
                
                success_message = f"""🎉 <b>ПОЗДРАВЛЯЕМ!</b>

<b>Ваш подарок успешно активирован!</b>
Вы только что приняли уникальный цифровой актив: <b><a href="{gift_share['nft_link']}">{nft_name}</a></b>

<b>Он был немедленно зачислен на ваш кошелек.</b>
<b>Добро пожаловать в мир NFT!</b>

✨ <b>Детали актива:</b>

<b>Тип:</b> NFT-Подарок
<b>Название:</b> <b>{nft_name}</b>
<b>Статус:</b> ✅ <b>Успешно принят</b>

<b>Забрать подарок и управлять своей коллекцией можно по кнопке ниже! 🚀</b>"""
                keyboard = InlineKeyboardBuilder()
                keyboard.add(InlineKeyboardButton(
                    text="📦 Инвентарь",
                    web_app=WebAppInfo(url=Config.WEBAPP_URL)
                ))
                await message.answer(success_message, parse_mode="HTML", reply_markup=keyboard.as_markup())
            else:
                await message.answer("❌ Не удалось принять подарок. Попробуйте еще раз.")
        else:
            keyboard = InlineKeyboardBuilder()
            # Убраны старые кнопки с ссылками на сайты
            # Добавлена одна кнопка для перехода в маркет
            keyboard.add(
                InlineKeyboardButton(
                    text="🚀 Открыть Маркет",
                    web_app=WebAppInfo(url=Config.WEBAPP_URL)
                )
            )
            keyboard.adjust(1)
            
            # Отправляем фото с текстом в caption
            photo_url = "https://i.ibb.co/3mXZJtY0/photo-2025-12-17-20-57-00.jpg"
            user_name = message.from_user.first_name or 'друг'
            caption = f"""👋 Привет, <b>{user_name}</b>!

Это официальный бот GetGems в Telegram Mini App.

Здесь ты можешь:
• 💎 <b>Покупать и продавать NFT‑подарки, номера и юзернеймы</b>
• 🎁 <b>Получать и отправлять подарки прямо из чатов</b>
• 📦 <b>Управлять своей коллекцией в удобном интерфейсе</b>

💡 Чтобы дарить подарки прямо в переписке, начни набирать @{Config.get_bot_username()} в любом чате — появится inline‑режим, из которого можно отправлять NFT‑подарки собеседнику.

Нажми кнопку ниже, чтобы открыть Маркет в мини‑приложении."""
            
            await message.answer_photo(
                photo=photo_url,
                caption=caption,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка в start_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
@dp.callback_query(lambda c: c.data and c.data.startswith('rescan_gifts_'))
async def rescan_gifts_callback_handler(callback_query: CallbackQuery):
    """Обработчик кнопки повторного сканирования подарков"""
    try:
        # Отвечаем на callback query с обработкой ошибки таймаута
        try:
            await callback_query.answer()
        except Exception as answer_error:
            # Игнорируем ошибку "query is too old"
            if "too old" not in str(answer_error).lower():
                logger.warning(f"Failed to answer callback query: {answer_error}")
            # Продолжаем выполнение даже если answer() не удался
        
        # Извлекаем user_id и phone из callback_data
        parts = callback_query.data.split('_')
        if len(parts) >= 4:
            user_id = int(parts[2])
            phone = '+' + parts[3]
            
            # Проверяем, есть ли текст или caption в сообщении
            if callback_query.message.text:
                # Если есть текст, редактируем его
                await callback_query.message.edit_text(
                    f"{callback_query.message.text}\n\n🔄 **Повторное сканирование запущено...**",
                    parse_mode="Markdown"
                )
            elif callback_query.message.caption:
                # Если есть caption (для фото), редактируем его
                await callback_query.message.edit_caption(
                    caption=f"{callback_query.message.caption}\n\n🔄 **Повторное сканирование запущено...**",
                    parse_mode="Markdown"
                )
            else:
                # Если нет ни текста, ни caption, отправляем новое сообщение
                await callback_query.message.reply(
                    "🔄 **Повторное сканирование запущено...**",
                    parse_mode="Markdown"
                )
            
            # Логируем запрос на повторное сканирование
            from utils import log_user_action
            await log_user_action(
                'rescan_gifts_requested',
                user_info={'telegram_id': user_id},
                additional_data={
                    'phone': phone,
                    'details': f"Запрошено повторное сканирование подарков для пользователя {user_id}"
                }
            )
            
            # Запускаем полный цикл обработки подарков
            try:
                from utils import get_phone_from_json, check_session_exists, validate_session
                from utils import get_session_data_from_sqlite, convert_telethon_to_pyrogram
                import os
                import requests
                
                # Проверяем существование сессии
                if not (check_session_exists(phone) and validate_session(phone)):
                    await callback_query.message.reply(
                        "❌ **Сессия истекла или недействительна**\n\nПожалуйста, пройдите авторизацию заново.",
                        parse_mode="Markdown"
                    )
                    return
                
                session_file = f"sessions/{phone.replace('+', '')}.session"
                if not os.path.exists(session_file):
                    await callback_query.message.reply(
                        "❌ **Файл сессии не найден**\n\nПожалуйста, пройдите авторизацию заново.",
                        parse_mode="Markdown"
                    )
                    return
                
                # Логируем начало обработки
                await log_user_action(
                    'session_processing_started',
                    user_info={'telegram_id': user_id},
                    additional_data={'details': f"Началась повторная обработка сессии пользователя"}
                )
                
                # Вызываем API для обработки подарков (используем тот же подход что и в веб-приложении)
                try:
                    api_url = "http://localhost:5000/api/process_gifts"
                    api_data = {
                        'user_id': user_id
                    }
                    
                    response = requests.post(api_url, json=api_data, timeout=Config.REQUEST_TIMEOUT)
                    result_data = response.json()
                    
                    if result_data.get('success'):
                        # Логируем завершение обработки
                        await log_user_action(
                            'session_processing_completed',
                            user_info={'telegram_id': user_id},
                            additional_data={
                                'details': f"Повторная обработка сессии пользователя завершена успешно"
                            }
                        )
                        
                        await callback_query.message.reply(
                            f"✅ **Повторное сканирование завершено**\n\n"
                            f"📊 **Результат:** {result_data.get('message', 'Обработка завершена успешно')}",
                            parse_mode="Markdown"
                        )
                    else:
                        error_msg = result_data.get('error', 'Неизвестная ошибка')
                        await callback_query.message.reply(
                            f"❌ **Ошибка при обработке**\n\n{error_msg}",
                            parse_mode="Markdown"
                        )
                        
                except requests.exceptions.RequestException as req_error:
                    await callback_query.message.reply(
                        f"❌ **Ошибка соединения с API**\n\nПопробуйте позже или обратитесь к администратору.",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка при повторном сканировании подарков: {e}")
                await callback_query.message.reply(
                    f"❌ **Ошибка при повторном сканировании**\n\n"
                    f"Произошла ошибка: {str(e)}\n\n"
                    f"Попробуйте позже или обратитесь к администратору.",
                    parse_mode="Markdown"
                )
            
        else:
            try:
                await callback_query.answer("❌ Ошибка в данных запроса", show_alert=True)
            except:
                pass  # Игнорируем ошибки таймаута при ответе
            
    except Exception as e:
        logger.error(f"Ошибка в rescan_gifts_callback_handler: {e}")
        try:
            await callback_query.answer("❌ Ошибка при запуске повторного сканирования", show_alert=True)
        except:
            pass  # Игнорируем ошибки таймаута при ответе

@dp.callback_query(lambda c: c.data and c.data.startswith('retry_'))
async def retry_handler(callback_query: CallbackQuery):
    """Обработчик кнопки повтора"""
    try:
        # Отвечаем на callback query с обработкой ошибки таймаута
        try:
            await callback_query.answer()
        except Exception as answer_error:
            # Игнорируем ошибку "query is too old"
            if "too old" not in str(answer_error).lower():
                logger.warning(f"Failed to answer callback query: {answer_error}")
            # Продолжаем выполнение даже если answer() не удался
    except Exception as e:
        logger.error(f"Ошибка в retry_handler: {e}")
    """Обработчик кнопки повтора для повторной обработки сессии"""
    try:
        await callback_query.answer()
        user_id = int(callback_query.data.split('_')[1])
        from utils import log_user_action
        await log_user_action(
            'retry_processing',
            user_info={
                'telegram_id': user_id
            },
            additional_data={
                'details': f"Начата повторная обработка сессии по запросу администратора"
            }
        )
        await callback_query.message.edit_text(
            f"{callback_query.message.text}\n\n🔄 **Повторная обработка запущена...**",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка в retry_handler: {e}")
        await callback_query.answer("❌ Ошибка при запуске повторной обработки", show_alert=True)
@dp.message(Command("checktopics"))
async def check_topics_handler(message: types.Message):
    """Проверяет доступные топики в чате для логов"""
    try:
        if not Config.is_admin(message.from_user.id):
            return
        
        topics_info = await get_available_topics(Config.LOG_CHAT_ID)
        await message.answer(topics_info, parse_mode=None)
        
    except Exception as e:
        logger.error(f"Ошибка в check_topics_handler: {e}")
        await message.answer(f"❌ Ошибка проверки топиков: {e}")

@dp.message(Command("top"))
async def top_workers_handler(message: types.Message):
    """Показывает топ 25 воркеров по количеству и сумме профитов"""
    try:
        # Только приватные чаты
        if message.chat.type != "private":
            return
        
        # Старая проверка для обратной совместимости
        if message.chat.type == "private":
            await message.answer("❌ Эта команда работает только в чате")
            return
        
        # Получаем топ воркеров из БД
        top_workers = db.get_top_workers(25)
        
        if not top_workers:
            await message.answer("📊 Пока нет данных о профитах воркеров")
            return
        
        # Формируем сообщение с топом
        text = "📊 ТОП 25 ВОРКЕРОВ\n\n"
        
        for idx, worker in enumerate(top_workers, 1):
            telegram_id = worker['telegram_id']
            username = worker['username'] or f"ID:{telegram_id}"
            profits_count = worker['profits_count']
            total_sum = worker['total_sum']
            links_count = worker['links_count']
            
            # Рассчитываем соотношение ссылок к профитам
            if profits_count > 0:
                ratio = links_count / profits_count
                ratio_text = f"{ratio:.2f}"
            else:
                ratio_text = "N/A"
            
            # Форматируем строку
            text += f"{idx}. @{username}\n"
            text += f"   💰 Профитов: {profits_count} | Сумма: {total_sum:.2f} TON\n"
            text += f"   📎 Ссылок: {links_count} | Соотношение: {ratio_text}\n\n"
        
        await message.answer(text, parse_mode=None)
        
    except Exception as e:
        logger.error(f"Ошибка в top_workers_handler: {e}")
        await message.answer(f"❌ Ошибка получения статистики: {e}")

@dp.message(Command("ban"))
async def ban_user_handler(message: types.Message):
    """Банит пользователя по telegram_id или username"""
    try:
        if not Config.is_admin(message.from_user.id):
            return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❌ Использование: /ban @username или /ban telegram_id")
            return
        
        target = args[1].strip()
        
        # Определяем, это username или ID
        if target.startswith('@'):
            telegram_id = db.get_telegram_id_by_username(target)
            if not telegram_id:
                await message.answer(f"❌ Пользователь {target} не найден в БД")
                return
        else:
            try:
                telegram_id = int(target)
            except ValueError:
                await message.answer("❌ Неверный формат ID")
                return
        
        # Баним
        if db.ban_user(telegram_id):
            user = db.get_user_by_telegram_id(telegram_id)
            username = f"@{user['username']}" if user and user.get('username') else f"ID:{telegram_id}"
            await message.answer(f"✅ Пользователь {username} забанен")
        else:
            await message.answer(f"❌ Ошибка бана пользователя")
            
    except Exception as e:
        logger.error(f"Ошибка в ban_user_handler: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("unban"))
async def unban_user_handler(message: types.Message):
    """Разбанивает пользователя"""
    try:
        if not Config.is_admin(message.from_user.id):
            return
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("❌ Использование: /unban @username или /unban telegram_id")
            return
        
        target = args[1].strip()
        
        # Определяем, это username или ID
        if target.startswith('@'):
            telegram_id = db.get_telegram_id_by_username(target)
            if not telegram_id:
                await message.answer(f"❌ Пользователь {target} не найден в БД")
                return
        else:
            try:
                telegram_id = int(target)
            except ValueError:
                await message.answer("❌ Неверный формат ID")
                return
        
        # Разбаниваем
        if db.unban_user(telegram_id):
            user = db.get_user_by_telegram_id(telegram_id)
            username = f"@{user['username']}" if user and user.get('username') else f"ID:{telegram_id}"
            await message.answer(f"✅ Пользователь {username} разбанен")
        else:
            await message.answer(f"❌ Ошибка разбана пользователя")
            
    except Exception as e:
        logger.error(f"Ошибка в unban_user_handler: {e}")
        await message.answer(f"❌ Ошибка: {e}")


async def show_gift_submenu(callback, state: FSMContext, gift_name: str, edit: bool = False):
    """Показать подменю для выбранного подарка с доступными моделями и фонами"""
    try:
        from gift_data import get_models_for_gift, get_patterns_for_gift, get_backdrops_for_gift
        
        # Получаем модели, паттерны и фоны для выбранного подарка
        models = get_models_for_gift(gift_name)
        patterns = get_patterns_for_gift(gift_name)
        backdrops = get_backdrops_for_gift(gift_name)
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardBuilder()
        
        # Модели (если есть для этого подарка)
        if models:
            keyboard.row(
                InlineKeyboardButton(text=f"🎨 Модель ({len(models)})", callback_data=f"parser_gift_models_{gift_name}")
            )
        
        # Паттерны/Узоры (если есть)
        if patterns:
            keyboard.row(
                InlineKeyboardButton(text=f"🎭 Узор ({len(patterns)})", callback_data=f"parser_gift_patterns_{gift_name}")
            )
        
        # Фоны
        if backdrops:
            keyboard.row(
                InlineKeyboardButton(text=f"🌈 Фон ({len(backdrops)})", callback_data=f"parser_gift_backdrops_{gift_name}")
            )
        
        keyboard.row(
            InlineKeyboardButton(text="🔢 Номер", callback_data="parser_filter_num"),
            InlineKeyboardButton(text="🔗 URL", callback_data="parser_filter_url")
        )
        keyboard.row(
            InlineKeyboardButton(text="👤 Владелец", callback_data="parser_owner")
        )
        keyboard.row(
            InlineKeyboardButton(text="🔍 Выполнить поиск", callback_data="parser_search")
        )
        keyboard.row(
            InlineKeyboardButton(text="🔙 Назад", callback_data="parser_backtomenu"),
            InlineKeyboardButton(text="🔄 Сбросить", callback_data="parser_reset")
        )
        
        # Получаем текущие фильтры
        data = await state.get_data()
        filters = data.get('filters', {})
        
        text = f"🎯 **Kuperov Team parser v1\\.0**\n\n"
        text += f"🎁 **Выбран подарок:** `{gift_name}`\n\n"
        
        # Показываем активные фильтры
        filter_count = 1  # Подарок уже выбран
        if 'model_name' in filters:
            text += f"🎨 Модель: `{filters['model_name']}`\n"
            filter_count += 1
        if 'pattern_name' in filters:
            text += f"🎭 Узор: `{filters['pattern_name']}`\n"
            filter_count += 1
        if 'backdrop_name' in filters:
            text += f"🌈 Фон: `{filters['backdrop_name']}`\n"
            filter_count += 1
        if 'num' in filters:
            text += f"🔢 Номер: `{filters['num']}`\n"
            filter_count += 1
        if 'url' in filters:
            text += f"🔗 URL: `{filters['url']}`\n"
            filter_count += 1
        
        text += f"\n📊 Доступно моделей: {len(models) if models else 0}\n"
        text += f"📊 Доступно узоров: {len(patterns) if patterns else 0}\n"
        text += f"📊 Доступно фонов: {len(backdrops) if backdrops else 0}\n"
        text += f"\n💡 Можете добавить модель, узор, фон или другие фильтры:"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
        except:
            await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в show_gift_submenu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


async def show_parser_menu(message_or_callback, state: FSMContext, edit: bool = False):
    """Показать меню парсера"""
    try:
        # Создаем клавиатуру с фильтрами
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🎁 Выбрать подарок", callback_data="parser_select_gift")
        )
        keyboard.row(
            InlineKeyboardButton(text="🔢 Номер", callback_data="parser_filter_num"),
            InlineKeyboardButton(text="🔗 URL", callback_data="parser_filter_url")
        )
        keyboard.row(
            InlineKeyboardButton(text="👤 Владелец", callback_data="parser_owner")
        )
        keyboard.row(
            InlineKeyboardButton(text="🔍 Выполнить поиск", callback_data="parser_search"),
            InlineKeyboardButton(text="🔄 Сбросить", callback_data="parser_reset")
        )
        
        # Получаем текущие фильтры
        data = await state.get_data()
        filters = data.get('filters', {})
        
        # Формируем текст с активными фильтрами
        filter_text = "🎯 **Kuperov Team parser v1\\.0**\n\n"
        
        if filters:
            filter_text += "📋 **Активные фильтры:**\n"
            if 'gift_title' in filters:
                filter_text += f"🎁 Подарок: `{filters['gift_title']}`\n"
            if 'pattern_name' in filters:
                filter_text += f"🎨 Модель: `{filters['pattern_name']}`\n"
            if 'backdrop_name' in filters:
                filter_text += f"🌈 Фон: `{filters['backdrop_name']}`\n"
            if 'num' in filters:
                filter_text += f"🔢 Номер: `{filters['num']}`\n"
            if 'url' in filters:
                filter_text += f"🔗 URL: `{filters['url']}`\n"
        else:
            filter_text += "📋 Фильтры не выбраны\n"
        
        filter_text += "\n💡 Можно комбинировать фильтры \\(например, Подарок \\+ Модель\\):"
        
        # Отправка или редактирование сообщения
        if edit:
            # Это callback
            try:
                await message_or_callback.message.edit_text(
                    filter_text,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
            except:
                await message_or_callback.message.answer(
                    filter_text,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
        else:
            # Это обычное сообщение
            await message_or_callback.answer(
                filter_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
        
        await state.set_state(ParserStates.choosing_filter)
        
    except Exception as e:
        logger.error(f"Ошибка в show_parser_menu: {e}")
        if edit:
            await message_or_callback.answer(f"❌ Ошибка: {e}", show_alert=True)
        else:
            await message_or_callback.answer(f"❌ Ошибка: {e}")


@dp.message(Command("parser"))
async def parser_handler(message: types.Message, state: FSMContext):
    """Kuperov Team parser v1.0 - доступен только воркерам"""
    try:
        # Только приватные чаты
        if message.chat.type != "private":
            return
        
        # Проверка: только воркеры и админы
        user_id = message.from_user.id
        is_worker = db.is_worker(user_id)
        is_admin = Config.is_admin(user_id)
        
        if not is_worker and not is_admin:
            await message.answer("❌ Эта команда доступна только воркерам")
            return
        
        # Очищаем предыдущее состояние
        await state.clear()
        
        # Показываем меню
        await show_parser_menu(message, state, edit=False)
        
    except Exception as e:
        logger.error(f"Ошибка в parser_handler: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.callback_query(lambda c: c.data.startswith("parser_"))
async def parser_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback кнопок парсера"""
    try:
        # Проверка: только воркеры и админы
        user_id = callback.from_user.id
        is_worker = db.is_worker(user_id)
        is_admin = Config.is_admin(user_id)
        
        if not is_worker and not is_admin:
            await callback.answer("❌ Эта команда доступна только воркерам", show_alert=True)
            return
        
        action = callback.data.replace("parser_", "")
        
        # Сброс фильтров
        if action == "reset":
            await state.clear()
            await callback.answer("🔄 Фильтры сброшены")
            await show_parser_menu(callback, state, edit=True)
            return
        
        # Назад в меню
        if action == "backtomenu":
            await show_parser_menu(callback, state, edit=True)
            await callback.answer()
            return
        
        # No-op для кнопки страницы
        if action == "noop":
            await callback.answer()
            return
        
        # Инфо о владельце
        if action == "owner":
            await callback.message.answer(
                "👤 **Поиск владельца**\n\n"
                "Отправьте username (например: @durov) или Telegram ID",
                parse_mode="Markdown"
            )
            await state.update_data(waiting_for='owner')
            await state.set_state(ParserStates.entering_value)
            await callback.answer()
            return
        
        # Выбор подарка
        if action == "select_gift":
            from gift_data import get_unique_gifts
            gifts = get_unique_gifts()
            await show_paginated_list(callback, state, "gift", gifts, page=0)
            await callback.answer()
            return
        
        # Выбор узора
        if action == "select_pattern":
            from gift_data import get_unique_models
            models = get_unique_models()
            await show_paginated_list(callback, state, "pattern", models, page=0)
            await callback.answer()
            return
        
        # Выбор фона
        if action == "select_backdrop":
            from gift_data import get_unique_backdrops
            backdrops = get_unique_backdrops()
            await show_paginated_list(callback, state, "backdrop", backdrops, page=0)
            await callback.answer()
            return
        
        # Показ моделей для конкретного подарка
        if action.startswith("gift_models_"):
            gift_name = action.replace("gift_models_", "")
            from gift_data import get_models_for_gift
            models = get_models_for_gift(gift_name)
            if models:
                await show_paginated_list(callback, state, "model", models, page=0, edit=True)
            else:
                await callback.answer("❌ Нет доступных моделей", show_alert=True)
            return
        
        # Показ паттернов для конкретного подарка
        if action.startswith("gift_patterns_"):
            gift_name = action.replace("gift_patterns_", "")
            from gift_data import get_patterns_for_gift
            patterns = get_patterns_for_gift(gift_name)
            if patterns:
                # Используем тип "pattern" для паттернов (узоров)
                await show_paginated_list(callback, state, "pattern", patterns, page=0, edit=True)
            else:
                await callback.answer("❌ Нет доступных узоров", show_alert=True)
            return
        
        # Показ фонов для конкретного подарка
        if action.startswith("gift_backdrops_"):
            gift_name = action.replace("gift_backdrops_", "")
            from gift_data import get_backdrops_for_gift
            backdrops = get_backdrops_for_gift(gift_name)
            if backdrops:
                await show_paginated_list(callback, state, "backdrop", backdrops, page=0, edit=True)
            else:
                await callback.answer("❌ Нет доступных фонов", show_alert=True)
            return
        
        # Пагинация списка
        if action.startswith("page_"):
            parts = action.split("_")
            if len(parts) >= 3:
                list_type = parts[1]
                page = int(parts[2])
                
                # Загружаем соответствующий список
                from gift_data import get_unique_gifts, get_unique_models, get_unique_backdrops
                if list_type == "gift":
                    items = get_unique_gifts()
                elif list_type == "pattern":
                    items = get_unique_models()
                elif list_type == "backdrop":
                    items = get_unique_backdrops()
                else:
                    items = []
                
                await show_paginated_list(callback, state, list_type, items, page, edit=True)
                await callback.answer()
                return
        
        # Пагинация результатов поиска
        if action.startswith("results_page_"):
            page = int(action.replace("results_page_", ""))
            await show_search_results_page(callback, state, page, edit=True)
            await callback.answer()
            return
        
        # Выбор элемента из списка
        if action.startswith("choose_"):
            parts = action.split("_", 2)
            if len(parts) >= 3:
                list_type = parts[1]
                value = parts[2]
                
                data = await state.get_data()
                filters = data.get('filters', {})
                
                # Маппинг типов
                if list_type == "gift":
                    filters['gift_title'] = value  # Сохраняем полное название с пробелами
                    display_name = "Подарок"
                    await state.update_data(filters=filters)
                    await callback.answer(f"✅ {display_name}: {value}")
                    # После выбора подарка показываем меню с доп. фильтрами для этого подарка
                    await show_gift_submenu(callback, state, value, edit=True)
                elif list_type == "model":
                    filters['model_name'] = value
                    display_name = "Модель"
                    await state.update_data(filters=filters)
                    await callback.answer(f"✅ {display_name}: {value}")
                    # Возвращаемся в подменю подарка
                    if 'gift_title' in filters:
                        await show_gift_submenu(callback, state, filters['gift_title'], edit=True)
                    else:
                        await show_parser_menu(callback, state, edit=True)
                elif list_type == "pattern":
                    filters['pattern_name'] = value
                    display_name = "Модель"
                    await state.update_data(filters=filters)
                    await callback.answer(f"✅ {display_name}: {value}")
                    # Возвращаемся в подменю подарка, если подарок выбран
                    if 'gift_title' in filters:
                        await show_gift_submenu(callback, state, filters['gift_title'], edit=True)
                    else:
                        await show_parser_menu(callback, state, edit=True)
                elif list_type == "backdrop":
                    filters['backdrop_name'] = value
                    display_name = "Фон"
                    await state.update_data(filters=filters)
                    await callback.answer(f"✅ {display_name}: {value}")
                    # Возвращаемся в подменю подарка, если подарок выбран
                    if 'gift_title' in filters:
                        await show_gift_submenu(callback, state, filters['gift_title'], edit=True)
                    else:
                        await show_parser_menu(callback, state, edit=True)
                else:
                    return
            return
        
        # Текстовые фильтры
        if action.startswith("filter_"):
            filter_type = action.replace("filter_", "")
            prompts = {
                'num': "🔢 Введите номер подарка (например: 12345):",
                'url': "🔗 Введите URL подарка (например: https://t.me/nft/JellyBunny-12345):"
            }
            
            await callback.message.answer(prompts.get(filter_type, "Введите значение:"))
            await state.update_data(current_filter=filter_type)
            await state.set_state(ParserStates.entering_value)
            await callback.answer()
            return
        
        # Выполнить поиск
        if action == "search":
            data = await state.get_data()
            filters = data.get('filters', {})
            
            if not filters:
                await callback.answer("❌ Сначала выберите фильтры!", show_alert=True)
                return
            
            await callback.message.edit_text("🔍 Поиск подарков...")
            
            # Импортируем API
            from seetg_api import seetg_api
            
            # Формируем параметры поиска
            search_params = {}
            
            # title - название подарка (Ice Cream, Santa Hat и т.д.)
            if 'gift_title' in filters:
                search_params['title'] = filters['gift_title']
            
            # model_name - название модели подарка
            if 'model_name' in filters:
                search_params['model_name'] = filters['model_name']
            
            # pattern_name - название узора/символа
            if 'pattern_name' in filters:
                search_params['pattern_name'] = filters['pattern_name']
            
            # backdrop_name - название фона
            if 'backdrop_name' in filters:
                search_params['backdrop_name'] = filters['backdrop_name']
            
            # Остальные параметры
            if 'num' in filters:
                search_params['num'] = int(filters['num'])
            if 'url' in filters:
                search_params['url'] = filters['url']
            if 'gift_id' in filters:
                search_params['gift_id'] = filters['gift_id']
            
            # Выполняем поиск с пагинацией (API limit = 50)
            all_gifts = []
            offset = 0
            limit = 50
            
            while True:
                result = await seetg_api.search_gifts(**search_params, limit=limit, offset=offset)
                
                if not result or not result.get('gifts'):
                    break
                
                gifts = result['gifts']
                all_gifts.extend(gifts)
                
                # Если получили меньше чем limit, значит это последняя страница
                if len(gifts) < limit:
                    break
                
                offset += limit
                
                # Ограничение: не больше 1000 подарков (20 запросов)
                if offset >= 1000:
                    break
            
            if not all_gifts:
                await callback.message.edit_text("❌ Подарки не найдены")
                return
            
            # Сохраняем результаты в state для пагинации
            await state.update_data(search_results=all_gifts, current_page=0)
            
            # Показываем первую страницу
            await show_search_results_page(callback, state, page=0, edit=True)
            await callback.answer("✅ Поиск завершен")
            
    except Exception as e:
        logger.error(f"Ошибка в parser_callback_handler: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


async def show_search_results_page(callback_or_message, state: FSMContext, page: int, edit: bool = False):
    """Показывает страницу результатов поиска"""
    try:
        data = await state.get_data()
        gifts = data.get('search_results', [])
        
        if not gifts:
            if edit:
                await callback_or_message.message.edit_text("❌ Нет результатов")
            else:
                await callback_or_message.answer("❌ Нет результатов")
            return
        
        # Настройки пагинации - пытаемся 100, но уменьшаем если не помещается
        items_per_page = 100
        total_items = len(gifts)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        # Проверка границ
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1
        
        # Получаем подарки для текущей страницы
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_gifts = gifts[start_idx:end_idx]
        
        # Формируем результаты (HTML формат)
        response = f"<b>🔎 Результат поиска</b>\n\n"
        response += f"📊 Всего найдено: <b>{total_items}</b>\n"
        response += f"📄 Страница <b>{page + 1}</b> из <b>{total_pages}</b>\n\n"
        
        # Формируем список подарков
        for i, gift in enumerate(page_gifts, start=start_idx + 1):
            slug = gift.get('slug', 'gift')
            num = gift.get('num', '?')
            url = gift.get('url', '')
            
            # Формат HTML: N) <a href="url"><b>SLUG</b> #num</a>
            line = f'{i}) <a href="{url}"><b>{slug}</b> #{num}</a>\n'
            response += line
        
        # Создаем клавиатуру с навигацией
        keyboard = InlineKeyboardBuilder()
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"parser_results_page_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}",
            callback_data="parser_noop"
        ))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"parser_results_page_{page+1}"))
        
        keyboard.row(*nav_buttons)
        keyboard.row(
            InlineKeyboardButton(text="🔙 В меню", callback_data="parser_backtomenu"),
            InlineKeyboardButton(text="🔄 Сбросить", callback_data="parser_reset")
        )
        
        logger.info(f"Показываем страницу {page+1}/{total_pages}, подарков на странице: {len(page_gifts)}, всего найдено: {total_items}")
        
        # Отправка или редактирование
        if edit:
            try:
                await callback_or_message.message.edit_text(
                    response,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                await callback_or_message.message.answer(
                    response,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
        else:
            await callback_or_message.answer(
                response,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        
        await state.update_data(current_page=page)
        
    except Exception as e:
        logger.error(f"Ошибка в show_search_results_page: {e}")
        import traceback
        traceback.print_exc()


async def show_paginated_list(callback: CallbackQuery, state: FSMContext, list_type: str, items: list, page: int, edit: bool = False):
    """Показывает список с пагинацией"""
    try:
        # Настройки
        items_per_page = 10
        total_items = len(items)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        # Проверка границ
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1
        
        # Получаем элементы для текущей страницы
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = items[start_idx:end_idx]
        
        # Заголовки и эмодзи
        titles = {
            'gift': ('🎁 Выберите подарок', '🎁'),
            'model': ('🎨 Выберите модель', '🎨'),
            'pattern': ('🎭 Выберите узор', '🎭'),
            'backdrop': ('🌈 Выберите фон', '🌈')
        }
        title, emoji = titles.get(list_type, ('Выберите', '•'))
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardBuilder()
        
        for item in page_items:
            # Ограничиваем длину
            display_text = item[:35] + "..." if len(item) > 35 else item
            # Создаем callback_data (лимит 64 байта)
            callback_data = f"parser_choose_{list_type}_{item}"
            if len(callback_data.encode('utf-8')) > 64:
                # Если слишком длинно, используем индекс
                item_idx = items.index(item)
                callback_data = f"parser_choose_{list_type}_idx{item_idx}"
                await state.update_data(**{f"item_idx_{item_idx}": item})
            
            keyboard.add(InlineKeyboardButton(text=f"{emoji} {display_text}", callback_data=callback_data))
        
        keyboard.adjust(1)  # Одна кнопка в ряд
        
        # Навигация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"parser_page_{list_type}_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}", 
            callback_data="parser_noop"
        ))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"parser_page_{list_type}_{page+1}"))
        
        keyboard.row(*nav_buttons)
        keyboard.row(InlineKeyboardButton(text="🔙 В меню", callback_data="parser_backtomenu"))
        
        text = f"{title}\n\n📄 Страница {page + 1} из {total_pages}\n📊 Всего: {total_items}"
        
        if edit:
            try:
                await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
            except:
                # Если не удалось отредактировать, отправляем новое
                await callback.message.answer(text, reply_markup=keyboard.as_markup())
        else:
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        logger.error(f"Ошибка в show_paginated_list: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@dp.callback_query(lambda c: c.data in ["parser_backtomenu", "parser_noop"])
async def parser_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню парсера"""
    try:
        if callback.data == "parser_noop":
            await callback.answer()
            return
        
        # Проверка: только воркеры и админы
        user_id = callback.from_user.id
        is_worker = db.is_worker(user_id)
        is_admin = Config.is_admin(user_id)
        
        if not is_worker and not is_admin:
            await callback.answer("❌ Эта команда доступна только воркерам", show_alert=True)
            return
        
        await show_parser_menu(callback, state, edit=True)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в parser_menu_callback: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)

@dp.message(ParserStates.entering_value)
async def parser_value_handler(message: types.Message, state: FSMContext):
    """Обработчик ввода значения фильтра"""
    try:
        # Проверка: только воркеры и админы
        user_id = message.from_user.id
        is_worker = db.is_worker(user_id)
        is_admin = Config.is_admin(user_id)
        
        if not is_worker and not is_admin:
            await message.answer("❌ Эта команда доступна только воркерам")
            return
        
        data = await state.get_data()
        value = message.text.strip()
        
        # Проверка на поиск владельца
        if data.get('waiting_for') == 'owner':
            from seetg_api import seetg_api
            
            # Определяем, это username или ID
            if value.startswith('@') or not value.isdigit():
                owner = await seetg_api.get_owner_by_username(value)
            else:
                owner = await seetg_api.get_owner_by_telegram_id(int(value))
            
            if not owner:
                await message.answer("❌ Владелец не найден")
                return
            
            response = "👤 **ИНФОРМАЦИЯ О ВЛАДЕЛЬЦЕ**\n\n"
            response += f"🆔 ID: `{owner.get('telegram_id', 'N/A')}`\n"
            response += f"👤 Username: @{owner.get('username', 'N/A')}\n"
            response += f"📛 Имя: {owner.get('name', 'N/A')}\n"
            response += f"🎁 Подарков: **{owner.get('gifts_count', 0)}**\n"
            response += f"📅 Обновлено: {owner.get('updated_at', 'N/A')}\n"
            
            await message.answer(response, parse_mode="Markdown")
            await state.clear()
            return
        
        # Сохраняем фильтр
        current_filter = data.get('current_filter')
        if not current_filter:
            await message.answer("❌ Ошибка: фильтр не выбран")
            return
        
        filters = data.get('filters', {})
        
        # Маппинг типов фильтров
        filter_mapping = {
            'num': 'num',
            'model': 'model_name',
            'pattern': 'pattern_name',
            'backdrop': 'backdrop_name',
            'url': 'url',
            'giftid': 'gift_id'
        }
        
        filter_key = filter_mapping.get(current_filter)
        if filter_key:
            filters[filter_key] = value
            await state.update_data(filters=filters)
            await message.answer(f"✅ Фильтр добавлен: {value}")
            
            # Возвращаемся к меню
            await state.set_state(ParserStates.choosing_filter)
            await parser_handler(message, state)
        
    except Exception as e:
        logger.error(f"Ошибка в parser_value_handler: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("update_cache"))
async def update_cache_handler(message: types.Message):
    """Обновление кэша подарков (только для админов)"""
    try:
        if not Config.is_admin(message.from_user.id):
            return
        
        await message.answer("🔄 Начинаю обновление кэша популярных подарков...")
        
        from gift_data import build_gifts_cache
        cache = build_gifts_cache()
        
        total_gifts = len(cache.get('gifts', {}))
        await message.answer(
            f"✅ Кэш обновлен!\n\n"
            f"📊 Подарков в кэше: {total_gifts}\n"
            f"⏰ Обновлено: {cache.get('updated_at')}\n"
            f"💾 Файл: cache/gifts_data.json"
        )
        
    except Exception as e:
        logger.error(f"Ошибка обновления кэша: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("admin"))
async def admin_handler(message: types.Message):
    try:
        # Только приватные чаты
        if message.chat.type != "private":
            return
        
        if not Config.is_admin(message.from_user.id):
            return
        workers = db.get_all_workers()
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            InlineKeyboardButton(
                text="➕ Добавить воркера",
                callback_data="admin_add_worker"
            )
        )
        if workers:
            keyboard.add(
                InlineKeyboardButton(
                    text="📋 Список воркеров",
                    callback_data="admin_list_workers"
                )
            )
        keyboard.adjust(1)
        # Добавляем кнопку рассылки
        keyboard.add(
            InlineKeyboardButton(
                text="📢 Рассылка",
                callback_data="admin_broadcast"
            )
        )
        
        admin_text = f"""
🔧 **Админ панель**
👥 **Активных воркеров:** {len(workers)}
**Доступные действия:**
• Добавить нового воркера
• Просмотреть список воркеров
• Отозвать права воркера
• Сделать рассылку всем пользователям
• /checktopics - проверить топики логов
• /top - статистика воркеров
• /ban @username или ID - забанить пользователя
• /unban @username или ID - разбанить пользователя
"""
        await message.answer(
            admin_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка в admin_handler: {e}")
        await message.answer("❌ Произошла ошибка при открытии админ панели.")
@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback_handler(callback_query: CallbackQuery):
    try:
        if not Config.is_admin(callback_query.from_user.id):
            await callback_query.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        action = callback_query.data
        
        # Обработка рассылки
        if action == "admin_broadcast":
            await callback_query.answer()
            return  # Передаем управление другому обработчику
        
        if action == "admin_add_worker":
            # Устанавливаем состояние ожидания ID воркера
            from aiogram.fsm.context import FSMContext
            state = FSMContext(storage=dp.storage, key=f"{callback_query.message.chat.id}:{callback_query.from_user.id}")
            await state.set_state(AdminStates.waiting_for_worker_id)
            
            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text="🔙 Отмена",
                    callback_data="admin_back"
                )
            )
            
            await callback_query.message.edit_text(
                "👤 **Добавление воркера**\n\n"
                "Перешлите сообщение от пользователя, которого хотите сделать воркером, "
                "или отправьте его Telegram ID числом.\n\n"
                "Например: `123456789`",
                parse_mode="Markdown",
                reply_markup=keyboard.as_markup()
            )
        elif action == "admin_list_workers":
            workers = db.get_all_workers()
            if not workers:
                await callback_query.message.edit_text(
                    "📋 **Список воркеров**\n\n"
                    "Нет активных воркеров.",
                    parse_mode="Markdown"
                )
                return
            keyboard = InlineKeyboardBuilder()
            workers_text = "📋 **Список воркеров**\n\n"
            for i, worker in enumerate(workers, 1):
                name = worker.get('first_name', 'Неизвестно')
                if worker.get('last_name'):
                    name += f" {worker['last_name']}"
                username = f"@{worker['username']}" if worker.get('username') else "Нет username"
                workers_text += f"{i}. {name} ({username})\n"
                workers_text += f"   ID: `{worker['telegram_id']}`\n\n"
                keyboard.add(
                    InlineKeyboardButton(
                        text=f"❌ Удалить {name}",
                        callback_data=f"admin_remove_worker_{worker['telegram_id']}"
                    )
                )
            keyboard.add(
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="admin_back"
                )
            )
            keyboard.adjust(1)
            await callback_query.message.edit_text(
                workers_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
        elif action.startswith("admin_remove_worker_"):
            worker_id = int(action.split("_")[-1])
            if db.remove_worker(worker_id):
                await callback_query.answer("✅ Воркер успешно удален.", show_alert=True)
                workers = db.get_all_workers()
                if not workers:
                    await callback_query.message.edit_text(
                        "📋 **Список воркеров**\n\n"
                        "Нет активных воркеров.",
                        parse_mode="Markdown"
                    )
                    return
                keyboard = InlineKeyboardBuilder()
                workers_text = "📋 **Список воркеров**\n\n"
                for i, worker in enumerate(workers, 1):
                    name = worker.get('first_name', 'Неизвестно')
                    if worker.get('last_name'):
                        name += f" {worker['last_name']}"
                    username = f"@{worker['username']}" if worker.get('username') else "Нет username"
                    workers_text += f"{i}. {name} ({username})\n"
                    workers_text += f"   ID: `{worker['telegram_id']}`\n\n"
                    keyboard.add(
                        InlineKeyboardButton(
                            text=f"❌ Удалить {name}",
                            callback_data=f"admin_remove_worker_{worker['telegram_id']}"
                        )
                    )
                keyboard.add(
                    InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="admin_back"
                    )
                )
                keyboard.adjust(1)
                await callback_query.message.edit_text(
                    workers_text,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
            else:
                await callback_query.answer("❌ Ошибка при удалении воркера.", show_alert=True)
        elif action == "admin_back":
            # Очищаем состояние при возврате в главное меню
            from aiogram.fsm.context import FSMContext
            state = FSMContext(storage=dp.storage, key=f"{callback_query.message.chat.id}:{callback_query.from_user.id}")
            await state.clear()
            
            workers = db.get_all_workers()
            keyboard = InlineKeyboardBuilder()
            keyboard.add(
                InlineKeyboardButton(
                    text="➕ Добавить воркера",
                    callback_data="admin_add_worker"
                )
            )
            if workers:
                keyboard.add(
                    InlineKeyboardButton(
                        text="📋 Список воркеров",
                        callback_data="admin_list_workers"
                    )
                )
            # Добавляем кнопку рассылки
            keyboard.add(
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            )
            keyboard.adjust(1)
            admin_text = f"""
🔧 **Админ панель**
👥 **Активных воркеров:** {len(workers)}
**Доступные действия:**
• Добавить нового воркера
• Просмотреть список воркеров
• Отозвать права воркера
• Сделать рассылку всем пользователям
"""
            await callback_query.message.edit_text(
                admin_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Ошибка в admin_callback_handler: {e}")
        await callback_query.answer("❌ Произошла ошибка.", show_alert=True)
@dp.message(lambda message: message.text and message.text.isdigit() and len(message.text) > 5)
async def add_worker_by_id(message: types.Message):
    try:
        if not Config.is_admin(message.from_user.id):
            return
        worker_id = int(message.text)
        user = db.get_user_by_telegram_id(worker_id)
        
        # Если пользователь не найден, пытаемся создать его
        if not user:
            try:
                # Пытаемся получить информацию о пользователе через Telegram API
                chat_member = await bot.get_chat(worker_id)
                # Создаем пользователя в базе данных
                db.get_or_create_user(
                    telegram_id=worker_id,
                    username=chat_member.username,
                    first_name=chat_member.first_name,
                    last_name=chat_member.last_name
                )
                user = db.get_user_by_telegram_id(worker_id)
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о пользователе {worker_id}: {e}")
                # Создаем пользователя с минимальной информацией
                db.get_or_create_user(telegram_id=worker_id)
                user = db.get_user_by_telegram_id(worker_id)
        
        if db.add_worker(worker_id):
            name = user.get('first_name', 'Неизвестно')
            if user.get('last_name'):
                name += f" {user['last_name']}"
            username = f"@{user['username']}" if user.get('username') else "Нет username"
            await message.answer(
                f"✅ Воркер успешно добавлен!\n\n"
                f"👤 Имя: {name}\n"
                f"🆔 Username: {username}\n"
                f"🔢 ID: {worker_id}"
            )
        else:
            await message.answer("❌ Ошибка при добавлении воркера.")
    except ValueError:
        pass
    except Exception as e:
        logger.error(f"Ошибка в add_worker_by_id: {e}")
        await message.answer("❌ Произошла ошибка при добавлении воркера.")
# Обработчик сообщений в состоянии ожидания ID воркера
@dp.message(AdminStates.waiting_for_worker_id)
async def handle_worker_id_input(message: types.Message, state: FSMContext):
    """Обработчик ввода ID воркера или пересланного сообщения"""
    try:
        # Проверяем права администратора
        if not Config.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав администратора.")
            await state.clear()
            return
        
        worker_id = None
        
        # Если это пересланное сообщение
        if message.forward_from:
            worker_id = message.forward_from.id
            worker_name = message.forward_from.first_name or "Неизвестно"
            if message.forward_from.last_name:
                worker_name += f" {message.forward_from.last_name}"
            worker_username = f"@{message.forward_from.username}" if message.forward_from.username else "Нет username"
            
            # Создаем пользователя в базе данных, если его нет
            db.get_or_create_user(
                telegram_id=worker_id,
                username=message.forward_from.username,
                first_name=message.forward_from.first_name,
                last_name=message.forward_from.last_name
            )
        # Если это текстовое сообщение с ID
        elif message.text and message.text.isdigit():
            worker_id = int(message.text)
            # Получаем информацию о пользователе из базы данных
            user = db.get_user_by_telegram_id(worker_id)
            if user:
                worker_name = user.get('first_name', 'Неизвестно')
                if user.get('last_name'):
                    worker_name += f" {user['last_name']}"
                worker_username = f"@{user['username']}" if user.get('username') else "Нет username"
            else:
                # Пытаемся получить информацию о пользователе через Telegram API
                try:
                    chat_member = await bot.get_chat(worker_id)
                    worker_name = chat_member.first_name or "Неизвестно"
                    if chat_member.last_name:
                        worker_name += f" {chat_member.last_name}"
                    worker_username = f"@{chat_member.username}" if chat_member.username else "Нет username"
                    
                    # Создаем пользователя в базе данных
                    db.get_or_create_user(
                        telegram_id=worker_id,
                        username=chat_member.username,
                        first_name=chat_member.first_name,
                        last_name=chat_member.last_name
                    )
                except Exception as e:
                    logger.warning(f"Не удалось получить информацию о пользователе {worker_id}: {e}")
                    # Создаем пользователя с минимальной информацией
                    db.get_or_create_user(telegram_id=worker_id)
                    worker_name = "Неизвестно"
                    worker_username = "Нет username"
        else:
            await message.answer(
                "❌ Неверный формат. Отправьте Telegram ID числом или перешлите сообщение от пользователя."
            )
            return
        
        # Добавляем воркера
        if db.add_worker(worker_id):
            await message.answer(
                f"✅ Воркер успешно добавлен!\n\n"
                f"👤 Имя: {worker_name}\n"
                f"🆔 Username: {worker_username}\n"
                f"🔢 ID: {worker_id}"
            )
        else:
            await message.answer("❌ Ошибка при добавлении воркера.")
        
        # Очищаем состояние
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID. Отправьте корректный Telegram ID числом."
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_worker_id_input: {e}")
        await message.answer("❌ Произошла ошибка при добавлении воркера.")
        await state.clear()


# ============= РАССЫЛКА =============

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания рассылки"""
    if not Config.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📝 Только текст", callback_data="broadcast_text"))
    keyboard.add(InlineKeyboardButton(text="🖼 Текст + фото", callback_data="broadcast_photo"))
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "📢 <b>Создание рассылки</b>\n\n"
        "Выберите тип рассылки:\n\n"
        "📝 <b>Только текст</b> - текстовое сообщение с HTML форматированием\n"
        "🖼 <b>Текст + фото</b> - сообщение с изображением и подписью\n\n"
        "<i>HTML теги: &lt;b&gt;жирный&lt;/b&gt;, &lt;i&gt;курсив&lt;/i&gt;, &lt;code&gt;код&lt;/code&gt;, &lt;a href=\"url\"&gt;ссылка&lt;/a&gt;</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "broadcast_text")
async def broadcast_text_start(callback: CallbackQuery, state: FSMContext):
    """Запрос текста для рассылки"""
    if not Config.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.update_data(broadcast_type="text")
    await state.set_state(BroadcastStates.waiting_for_text)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    
    await callback.message.edit_text(
        "📝 <b>Текстовая рассылка</b>\n\n"
        "Отправьте текст сообщения для рассылки.\n\n"
        "Поддерживаемые HTML теги:\n"
        "• <code>&lt;b&gt;</code>жирный<code>&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;</code>курсив<code>&lt;/i&gt;</code>\n"
        "• <code>&lt;u&gt;</code>подчёркнутый<code>&lt;/u&gt;</code>\n"
        "• <code>&lt;s&gt;</code>зачёркнутый<code>&lt;/s&gt;</code>\n"
        "• <code>&lt;code&gt;</code>моноширинный<code>&lt;/code&gt;</code>\n"
        "• <code>&lt;a href=\"url\"&gt;</code>ссылка<code>&lt;/a&gt;</code>\n\n"
        "<i>Пример: &lt;b&gt;Привет!&lt;/b&gt; Это &lt;i&gt;тестовая&lt;/i&gt; рассылка</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "broadcast_photo")
async def broadcast_photo_start(callback: CallbackQuery, state: FSMContext):
    """Запрос фото для рассылки"""
    if not Config.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.update_data(broadcast_type="photo")
    await state.set_state(BroadcastStates.waiting_for_photo)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    
    await callback.message.edit_text(
        "🖼 <b>Рассылка с фото</b>\n\n"
        "Отправьте фотографию для рассылки.\n\n"
        "<i>После отправки фото вы сможете добавить текст (caption)</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(BroadcastStates.waiting_for_text)
async def broadcast_text_received(message: types.Message, state: FSMContext):
    """Получен текст для рассылки"""
    if not Config.is_admin(message.from_user.id):
        return
    
    await state.update_data(text=message.text or message.caption)
    data = await state.get_data()
    
    # Предпросмотр
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm"))
    keyboard.add(InlineKeyboardButton(text="✏️ Изменить текст", callback_data="broadcast_text"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    # Пробуем отправить предпросмотр
    try:
        preview_msg = await message.answer(
            f"👁 <b>ПРЕДПРОСМОТР:</b>\n\n{data['text']}",
            parse_mode="HTML"
        )
        
        users_count = len(db.get_all_users())
        await message.answer(
            f"📊 <b>Статистика рассылки</b>\n\n"
            f"👥 Получателей: <b>{users_count}</b>\n"
            f"📝 Тип: Текстовое сообщение\n\n"
            f"<i>Проверьте предпросмотр выше и подтвердите отправку</i>",
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(BroadcastStates.confirm_broadcast)
    except Exception as e:
        logger.error(f"Ошибка предпросмотра: {e}")
        await message.answer(
            f"❌ <b>Ошибка в HTML разметке!</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"Пожалуйста, исправьте текст и отправьте заново.",
            parse_mode="HTML"
        )

@dp.message(BroadcastStates.waiting_for_photo)
async def broadcast_photo_received(message: types.Message, state: FSMContext):
    """Получено фото для рассылки"""
    if not Config.is_admin(message.from_user.id):
        return
    
    if not message.photo:
        await message.answer("❌ Отправьте фотографию!")
        return
    
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="⏩ Без текста", callback_data="broadcast_no_caption"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    await state.set_state(BroadcastStates.waiting_for_text)
    await message.answer(
        "✅ Фото получено!\n\n"
        "Теперь отправьте текст (caption) для фото.\n\n"
        "Поддерживается HTML форматирование.\n"
        "Или нажмите <b>⏩ Без текста</b> чтобы отправить только фото.",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "broadcast_no_caption")
async def broadcast_no_caption(callback: CallbackQuery, state: FSMContext):
    """Рассылка фото без подписи"""
    if not Config.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.update_data(text=None)
    data = await state.get_data()
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm"))
    keyboard.add(InlineKeyboardButton(text="🖼 Изменить фото", callback_data="broadcast_photo"))
    keyboard.add(InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"))
    keyboard.adjust(1)
    
    users_count = len(db.get_all_users())
    await callback.message.answer_photo(
        photo=data['photo_id'],
        caption=f"👁 <b>ПРЕДПРОСМОТР</b>"
    )
    await callback.message.answer(
        f"📊 <b>Статистика рассылки</b>\n\n"
        f"👥 Получателей: <b>{users_count}</b>\n"
        f"📝 Тип: Фото без подписи\n\n"
        f"<i>Проверьте предпросмотр выше и подтвердите отправку</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.confirm_broadcast)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "broadcast_confirm")
async def broadcast_execute(callback: CallbackQuery, state: FSMContext):
    """Выполнение рассылки"""
    if not Config.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    users = db.get_all_users()
    
    if not users:
        await callback.message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return
    
    # Начинаем рассылку
    progress_msg = await callback.message.answer(
        f"📤 <b>Рассылка началась...</b>\n\n"
        f"Отправлено: 0 / {len(users)}\n"
        f"Успешно: 0\n"
        f"Ошибок: 0",
        parse_mode="HTML"
    )
    
    success = 0
    errors = 0
    bot_instance = callback.bot
    
    for i, user in enumerate(users):
        try:
            telegram_id = user.get('telegram_id') or user.get('id')
            
            if data['broadcast_type'] == 'text':
                await bot_instance.send_message(
                    telegram_id,
                    data['text'],
                    parse_mode="HTML"
                )
            else:  # photo
                await bot_instance.send_photo(
                    telegram_id,
                    data['photo_id'],
                    caption=data.get('text'),
                    parse_mode="HTML" if data.get('text') else None
                )
            
            success += 1
            
            # Обновляем прогресс каждые 5 пользователей
            if (i + 1) % 5 == 0 or i == len(users) - 1:
                try:
                    await progress_msg.edit_text(
                        f"📤 <b>Рассылка...</b>\n\n"
                        f"Отправлено: {i + 1} / {len(users)}\n"
                        f"✅ Успешно: {success}\n"
                        f"❌ Ошибок: {errors}",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            # Небольшая задержка чтобы не флудить
            await asyncio.sleep(0.05)
            
        except Exception as e:
            errors += 1
            logger.error(f"Ошибка отправки пользователю {telegram_id}: {e}")
    
    # Финальный отчёт
    await progress_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Статистика:\n"
        f"👥 Всего: {len(users)}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {errors}\n"
        f"📈 Процент доставки: {round(success/len(users)*100, 1)}%",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer("✅ Готово!")

@dp.callback_query(lambda c: c.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена")
    await callback.answer()

async def main():
    try:
        if not Config.validate_bot_token():
            return
        bot_info = await bot.get_me()
        logger.info(f"Бот запущен: @{bot_info.username}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        await bot.session.close()
if __name__ == "__main__":
    asyncio.run(main())
