#!/bin/bash

echo "Starting GetGems WebApp..."
echo

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 не найден! Установите Python 3.8 или выше."
    exit 1
fi

# Проверка зависимостей
if [ ! -f "requirements.txt" ]; then
    echo "Файл requirements.txt не найден!"
    exit 1
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "Файл .env не найден! Создайте его по образцу из README.md"
    exit 1
fi

# Проверка виртуального окружения (опционально)
if [ -d "venv" ]; then
    echo "Активация виртуального окружения..."
    source venv/bin/activate
fi

echo "Очистка Python кэша..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "✅ Кэш очищен"

echo "Запуск GetGems WebApp..."
export $(grep -E '^(BOT_TOKEN|BOT_USERNAME|WEBAPP_URL|ADMIN_IDS|LOG_GROUP_ID|LOG_CHAT_ID|FLASK_HOST|FLASK_PORT|FLASK_DEBUG|GIFT_RECIPIENT_ID)=' .env | xargs)
python3 main.py
