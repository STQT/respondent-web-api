#!/bin/bash

# Скрипт для деплоя в production
# Использование: ./deploy.sh

set -e  # Остановка при любой ошибке

echo "🚀 Начинаем деплой системы опросов..."

# Проверяем наличие файлов окружения
if [ ! -f ".envs/.production/.django" ]; then
    echo "❌ Файл .envs/.production/.django не найден!"
    echo "Создайте файлы окружения перед деплоем."
    exit 1
fi

if [ ! -f ".envs/.production/.postgres" ]; then
    echo "❌ Файл .envs/.production/.postgres не найден!"
    echo "Создайте файлы окружения перед деплоем."
    exit 1
fi

echo "✅ Файлы окружения найдены"

# Останавливаем и удаляем старые контейнеры
echo "🛑 Останавливаем старые контейнеры..."
docker-compose -f docker-compose.production.yml down --remove-orphans

# Создаем новые образы
echo "🔨 Создаем Docker образы..."
docker-compose -f docker-compose.production.yml build --no-cache

# Запускаем базу данных и Redis
echo "🗄️ Запускаем базу данных и Redis..."
docker-compose -f docker-compose.production.yml up -d postgres redis

# Ждем готовности базы данных
echo "⏳ Ждем готовности базы данных..."
sleep 10

# Проверяем готовность PostgreSQL
echo "🔍 Проверяем готовность PostgreSQL..."
docker-compose -f docker-compose.production.yml exec postgres pg_isready -U postgres || {
    echo "❌ PostgreSQL не готов!"
    docker-compose -f docker-compose.production.yml logs postgres
    exit 1
}

echo "✅ PostgreSQL готов"

# Выполняем миграции
echo "📊 Выполняем миграции..."
docker-compose -f docker-compose.production.yml run --rm django-migrate

# Проверяем успешность миграций
if [ $? -eq 0 ]; then
    echo "✅ Миграции выполнены успешно"
else
    echo "❌ Ошибка при выполнении миграций"
    docker-compose -f docker-compose.production.yml logs django-migrate
    exit 1
fi

# Запускаем все остальные сервисы
echo "🌐 Запускаем все сервисы..."
docker-compose -f docker-compose.production.yml up -d

# Ждем запуска всех сервисов
echo "⏳ Ждем запуска всех сервисов..."
sleep 15

# Проверяем статус сервисов
echo "🔍 Проверяем статус сервисов..."
docker-compose -f docker-compose.production.yml ps

# Проверяем работу Django
echo "🔗 Проверяем работу Django API..."
sleep 5
if curl -f http://localhost:8000/api/ > /dev/null 2>&1; then
    echo "✅ Django API работает"
else
    echo "⚠️ Django API может быть еще не готов, проверьте логи:"
    echo "docker-compose -f docker-compose.production.yml logs django"
fi

echo ""
echo "🎉 Деплой завершен!"
echo ""
echo "📋 Информация о сервисах:"
echo "  • Django API: http://localhost:8000"
echo "  • Nginx: http://localhost:80"
echo "  • Flower (Celery): http://localhost:5555"
echo "  • PostgreSQL: localhost:5432"
echo ""
echo "📊 Полезные команды:"
echo "  • Логи Django: docker-compose -f docker-compose.production.yml logs django"
echo "  • Логи всех сервисов: docker-compose -f docker-compose.production.yml logs"
echo "  • Статус: docker-compose -f docker-compose.production.yml ps"
echo "  • Остановка: docker-compose -f docker-compose.production.yml down"
echo ""
echo "🚀 Создание демо-данных:"
echo "  docker-compose -f docker-compose.production.yml exec django python manage.py setup_demo_data"
echo ""
echo "✅ Система готова к использованию!"
