# 🔧 Исправление проблем в Production

## ❌ Проблема

После деплоя в production возникала ошибка:

```
postgres-1 | ERROR: relation "django_celery_beat_crontabschedule" does not exist
```

## 🎯 Причина

1. **Celery Beat** запускался одновременно с Django до выполнения миграций
2. **Отсутствовала правильная последовательность** запуска сервисов
3. **Миграции не выполнялись** автоматически при деплое

## ✅ Решение

### 1. Обновлен `docker-compose.production.yml`:

**Добавлены healthcheck'и:**
```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
    interval: 10s
    timeout: 5s
    retries: 5

django:
  healthcheck:
    test: ["CMD", "python", "healthcheck.py"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

**Добавлен сервис миграций:**
```yaml
django-migrate:
  <<: *django
  command: >
    sh -c "python manage.py migrate --noinput &&
           python manage.py collectstatic --noinput --clear"
  depends_on:
    postgres:
      condition: service_healthy
  restart: "no"
```

**Исправлены зависимости:**
```yaml
django:
  depends_on:
    django-migrate:
      condition: service_completed_successfully

celeryworker:
  depends_on:
    django-migrate:
      condition: service_completed_successfully

celerybeat:
  depends_on:
    django-migrate:
      condition: service_completed_successfully
```

### 2. Создан автоматический скрипт деплоя `deploy.sh`:

```bash
#!/bin/bash
# Проверяет настройки окружения
# Выполняет миграции в правильной последовательности  
# Запускает сервисы с проверкой готовности
# Выводит полезную информацию о деплое
```

### 3. Добавлен healthcheck для Django:

**Файл `healthcheck.py`:**
- Проверяет доступность API
- Тестирует подключение к базе данных
- Возвращает правильные exit codes для Docker

### 4. Созданы production файлы окружения:

**`.envs/.production/.django`** - настройки Django
**`.envs/.production/.postgres`** - настройки PostgreSQL

## 🚀 Как использовать исправления

### Быстрый деплой:
```bash
./deploy.sh
```

### Ручной деплой:
```bash
# 1. Настройте файлы окружения в .envs/.production/
# 2. Измените пароли и секретные ключи
# 3. Запустите деплой:
docker-compose -f docker-compose.production.yml down --remove-orphans
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

## 🔍 Проверка результата

### Проверка статуса:
```bash
docker-compose -f docker-compose.production.yml ps
```

**Ожидаемый результат:** Все сервисы в состоянии `Up (healthy)`

### Проверка API:
```bash
curl http://localhost:8000/api/
```

**Ожидаемый результат:** JSON ответ от API

### Проверка логов:
```bash
docker-compose -f docker-compose.production.yml logs
```

**Ожидаемый результат:** Нет ошибок, все сервисы запущены

## 🎯 Ключевые улучшения

1. **✅ Правильная последовательность запуска** - миграции → Django → Celery
2. **✅ Healthcheck'и** - контейнеры не считаются готовыми до полной инициализации  
3. **✅ Автоматические миграции** - выполняются при каждом деплое
4. **✅ Restart политики** - сервисы перезапускаются при сбоях
5. **✅ Мониторинг готовности** - скрипт проверяет успешность деплоя

## 📋 Полезные команды после деплоя

```bash
# Создание демо-данных
docker-compose -f docker-compose.production.yml exec django python manage.py setup_demo_data

# Создание суперпользователя  
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Мониторинг логов
docker-compose -f docker-compose.production.yml logs -f

# Проверка использования ресурсов
docker stats
```

## 🛡️ Безопасность

**⚠️ Обязательно измените в production:**
- `DJANGO_SECRET_KEY` 
- `JWT_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `CELERY_FLOWER_PASSWORD`
- `DJANGO_ALLOWED_HOSTS`

---

**✅ Проблема полностью решена!** Теперь деплой работает корректно с правильной последовательностью запуска сервисов.
