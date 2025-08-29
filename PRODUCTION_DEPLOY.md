# 🚀 Production Deployment Guide

Руководство по деплою системы опросов в production окружение.

## 🔧 Подготовка к деплою

### 1. Системные требования

- **Docker** версии 20.10 или выше
- **Docker Compose** версии 2.0 или выше
- **Минимум 2GB RAM** для всех сервисов
- **Минимум 10GB** свободного места на диске

### 2. Настройка переменных окружения

#### 📝 Обязательные изменения в `.envs/.production/.django`:

```bash
# Сгенерируйте сильный секретный ключ (50+ символов)
DJANGO_SECRET_KEY=your_super_secret_key_here_50_characters_minimum

# JWT секретный ключ
JWT_SECRET_KEY=your_jwt_secret_key_here

# Укажите ваши домены
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-ip-address

# Для HTTPS (рекомендуется)
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True

# Email настройки (опционально)
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=mg.yourdomain.com

# Flower (Celery monitoring)
CELERY_FLOWER_USER=admin
CELERY_FLOWER_PASSWORD=secure_flower_password
```

#### 📝 Обязательные изменения в `.envs/.production/.postgres`:

```bash
# Измените пароль базы данных
POSTGRES_PASSWORD=secure_database_password
```

### 3. Генерация секретных ключей

```bash
# Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# JWT SECRET_KEY  
openssl rand -base64 64
```

## 🚀 Деплой

### Автоматический деплой (рекомендуется)

```bash
./deploy.sh
```

### Ручной деплой

```bash
# 1. Остановка старых контейнеров
docker-compose -f docker-compose.production.yml down --remove-orphans

# 2. Создание образов
docker-compose -f docker-compose.production.yml build --no-cache

# 3. Запуск базы данных
docker-compose -f docker-compose.production.yml up -d postgres redis

# 4. Ожидание готовности базы
sleep 10

# 5. Выполнение миграций
docker-compose -f docker-compose.production.yml run --rm django-migrate

# 6. Запуск всех сервисов
docker-compose -f docker-compose.production.yml up -d
```

## 🔍 Проверка деплоя

### Проверка статуса сервисов

```bash
docker-compose -f docker-compose.production.yml ps
```

Все сервисы должны быть в состоянии `Up`:
- `postgres` - База данных
- `redis` - Кэш и очереди
- `django` - API сервер
- `celeryworker` - Обработчик задач
- `celerybeat` - Планировщик задач
- `flower` - Мониторинг Celery
- `nginx` - Веб-сервер

### Проверка API

```bash
# Проверка основного API
curl http://localhost/api/

# Проверка health check (если настроен)
curl http://localhost/health/
```

### Проверка логов

```bash
# Логи всех сервисов
docker-compose -f docker-compose.production.yml logs

# Логи конкретного сервиса
docker-compose -f docker-compose.production.yml logs django
docker-compose -f docker-compose.production.yml logs postgres
docker-compose -f docker-compose.production.yml logs celeryworker
```

## 🎯 Пост-деплой настройка

### 1. Создание суперпользователя

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser
```

### 2. Создание демонстрационных данных

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py setup_demo_data
```

### 3. Проверка Celery

Откройте Flower: http://localhost:5555
- Логин: admin (или ваш CELERY_FLOWER_USER)
- Пароль: ваш CELERY_FLOWER_PASSWORD

## 🌐 Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| API | http://localhost/api/ | REST API |
| Admin | http://localhost/admin/ | Django админка |
| Flower | http://localhost:5555 | Мониторинг Celery |
| Static files | http://localhost/static/ | Статические файлы |
| Media files | http://localhost/media/ | Загруженные файлы |

## 🔧 Управление в production

### Обновление кода

```bash
# Получение обновлений
git pull origin main

# Пересборка и перезапуск
./deploy.sh
```

### Backup базы данных

```bash
# Создание backup
docker-compose -f docker-compose.production.yml exec postgres backup

# Список backup'ов
docker-compose -f docker-compose.production.yml exec postgres backups

# Восстановление из backup
docker-compose -f docker-compose.production.yml exec postgres restore backup_filename.sql
```

### Выполнение команд Django

```bash
# Django shell
docker-compose -f docker-compose.production.yml exec django python manage.py shell

# Создание пользователей
docker-compose -f docker-compose.production.yml exec django python manage.py create_test_users --count 50

# Сбор статических файлов
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput
```

### Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование места на диске
docker system df

# Логи с ротацией
docker-compose -f docker-compose.production.yml logs --tail=100 -f
```

## 🛠 Troubleshooting

### Проблема: Django не запускается

**Симптомы:**
```
django-1 | django.db.utils.OperationalError: could not connect to server
```

**Решение:**
1. Проверьте статус PostgreSQL: `docker-compose -f docker-compose.production.yml logs postgres`
2. Проверьте настройки подключения в `.envs/.production/.postgres`
3. Перезапустите postgres: `docker-compose -f docker-compose.production.yml restart postgres`

### Проблема: Celery не работает

**Симптомы:**
```
relation "django_celery_beat_crontabschedule" does not exist
```

**Решение:**
1. Убедитесь, что миграции выполнились: `docker-compose -f docker-compose.production.yml run --rm django-migrate`
2. Перезапустите Celery сервисы:
   ```bash
   docker-compose -f docker-compose.production.yml restart celeryworker celerybeat
   ```

### Проблема: Nginx показывает 502 Bad Gateway

**Решение:**
1. Проверьте, что Django запущен: `docker-compose -f docker-compose.production.yml logs django`
2. Проверьте настройки nginx: `docker-compose -f docker-compose.production.yml logs nginx`
3. Перезапустите nginx: `docker-compose -f docker-compose.production.yml restart nginx`

### Проблема: Нет места на диске

**Решение:**
```bash
# Очистка неиспользуемых образов
docker image prune -a

# Очистка volumes (ОСТОРОЖНО!)
docker volume prune

# Полная очистка Docker
docker system prune -a --volumes
```

## 🔒 Безопасность

### SSL/TLS сертификаты

1. **Let's Encrypt (рекомендуется):**
   ```bash
   # Добавьте Certbot в docker-compose
   # Или используйте Traefik с автоматическими сертификатами
   ```

2. **Собственные сертификаты:**
   - Поместите сертификаты в `./ssl/`
   - Обновите nginx конфигурацию

### Файрвол

```bash
# Разрешить только необходимые порты
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### Мониторинг безопасности

- Регулярно обновляйте Docker образы
- Мониторьте логи на подозрительную активность
- Используйте сканеры уязвимостей

## 📊 Мониторинг и метрики

### Логирование

```bash
# Настройка ротации логов
docker-compose -f docker-compose.production.yml config | grep logging -A 5

# Отправка логов в внешние системы (опционально)
# Elasticsearch, Fluentd, Logstash, etc.
```

### Мониторинг производительности

- **Flower** - для мониторинга Celery задач
- **Django Admin** - для управления данными
- **Sentry** - для отслеживания ошибок (настройте SENTRY_DSN)

## 🔄 Резервное копирование

### Автоматический backup

Создайте cron job для регулярного backup:

```bash
# Добавьте в crontab (crontab -e)
0 2 * * * cd /path/to/project && docker-compose -f docker-compose.production.yml exec -T postgres backup
```

### Backup стратегия

1. **Ежедневно** - backup базы данных
2. **Еженедельно** - backup media файлов
3. **Ежемесячно** - полный backup системы

---

## 🎉 Готово!

Ваша система опросов успешно развернута в production!

**Следующие шаги:**
1. Настройте мониторинг
2. Настройте SSL сертификаты
3. Создайте backup стратегию
4. Настройте домен и DNS
5. Проведите нагрузочное тестирование

**Поддержка:**
- Документация: [DEMO_SETUP.md](DEMO_SETUP.md)
- API документация: http://localhost/api/docs/
- Мониторинг: http://localhost:5555
