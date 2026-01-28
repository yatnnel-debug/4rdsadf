#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        🎛️  УСТАНОВКА ПАНЕЛИ УПРАВЛЕНИЯ GETGEMS BOT           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Запустите скрипт с правами root: sudo bash setup_control.sh${NC}"
    exit 1
fi

echo "📋 Шаг 1: Проверка зависимостей..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не установлен${NC}"
    exit 1
fi

if ! python3 -c "import aiogram" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  aiogram не установлен, устанавливаем...${NC}"
    pip3 install aiogram python-dotenv
fi

echo -e "${GREEN}✅ Зависимости проверены${NC}"
echo ""

echo "📋 Шаг 2: Настройка переменных окружения..."
ENV_FILE="/root/getgems_webapp/getgems_webapp/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  Создаем .env файл...${NC}"
    touch "$ENV_FILE"
fi

# Проверяем наличие CONTROL_BOT_TOKEN
if ! grep -q "CONTROL_BOT_TOKEN" "$ENV_FILE"; then
    echo ""
    echo -e "${YELLOW}🔑 Введите токен для управляющего бота:${NC}"
    read -p "Token: " CONTROL_TOKEN
    echo "CONTROL_BOT_TOKEN=$CONTROL_TOKEN" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Токен сохранен${NC}"
else
    echo -e "${GREEN}✅ CONTROL_BOT_TOKEN уже установлен${NC}"
fi

# Проверяем наличие CONTROL_BOT_ADMINS
if ! grep -q "CONTROL_BOT_ADMINS" "$ENV_FILE"; then
    echo ""
    echo -e "${YELLOW}👤 Введите ID администраторов (через запятую):${NC}"
    read -p "Admin IDs: " ADMIN_IDS
    echo "CONTROL_BOT_ADMINS=$ADMIN_IDS" >> "$ENV_FILE"
    echo -e "${GREEN}✅ Админы сохранены${NC}"
else
    echo -e "${GREEN}✅ CONTROL_BOT_ADMINS уже установлен${NC}"
fi

echo ""
echo "📋 Шаг 3: Настройка systemd сервисов..."

# Перезагружаем systemd
systemctl daemon-reload

# Включаем сервисы
echo "   Включаем основной бот..."
systemctl enable getgems.service
echo "   Включаем управляющий бот..."
systemctl enable getgems-control.service

echo -e "${GREEN}✅ Сервисы настроены${NC}"
echo ""

echo "📋 Шаг 4: Настройка sudo для перезапуска без пароля..."
SUDOERS_FILE="/etc/sudoers.d/getgems"

cat > "$SUDOERS_FILE" << 'EOF'
# Разрешить root перезапускать getgems сервис без пароля
root ALL=(ALL) NOPASSWD: /bin/systemctl restart getgems
root ALL=(ALL) NOPASSWD: /bin/systemctl status getgems
root ALL=(ALL) NOPASSWD: /bin/systemctl stop getgems
root ALL=(ALL) NOPASSWD: /bin/systemctl start getgems
EOF

chmod 0440 "$SUDOERS_FILE"
echo -e "${GREEN}✅ Sudo настроен${NC}"
echo ""

echo "📋 Шаг 5: Запуск сервисов..."
echo "   Останавливаем screen сессии..."
pkill -9 screen 2>/dev/null
pkill -9 -f "python3 main.py" 2>/dev/null
sleep 2

echo "   Запускаем основной бот..."
systemctl start getgems.service
sleep 2

echo "   Запускаем управляющий бот..."
systemctl start getgems-control.service
sleep 2

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    ✅ УСТАНОВКА ЗАВЕРШЕНА                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Статус сервисов:"
systemctl status getgems.service --no-pager | grep "Active:"
systemctl status getgems-control.service --no-pager | grep "Active:"
echo ""
echo "📝 Полезные команды:"
echo ""
echo "   Основной бот:"
echo "   • Статус: systemctl status getgems"
echo "   • Логи: tail -f /var/log/getgems.log"
echo "   • Перезапуск: systemctl restart getgems"
echo ""
echo "   Управляющий бот:"
echo "   • Статус: systemctl status getgems-control"
echo "   • Логи: tail -f /var/log/getgems-control.log"
echo "   • Перезапуск: systemctl restart getgems-control"
echo ""
echo "🎛️  Откройте управляющего бота в Telegram и отправьте /start"
echo ""
