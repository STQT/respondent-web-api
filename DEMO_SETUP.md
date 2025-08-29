# 🚀 Быстрая настройка демонстрационной системы опросов

Этот документ описывает, как быстро настроить систему опросов с тестовыми данными для демонстрации.

## 📋 Доступные команды

### 1. 🎯 Полная настройка системы (рекомендуется)

```bash
# Настройка полной демонстрационной системы
docker-compose -f docker-compose.local.yml exec django python manage.py setup_demo_data

# С дополнительными параметрами
docker-compose -f docker-compose.local.yml exec django python manage.py setup_demo_data \
  --users-count 20 \
  --clear-all
```

**Что создается:**
- 3 тестовых опроса (программирование, математика, общие знания)
- 15 тестовых пользователей (по умолчанию)
- 1 модератор
- Полная структура данных для тестирования

### 2. 👥 Создание только пользователей

```bash
# Создание 10 пользователей + модератор
docker-compose -f docker-compose.local.yml exec django python manage.py create_test_users \
  --count 10 \
  --with-moderator

# Очистка и создание новых пользователей
docker-compose -f docker-compose.local.yml exec django python manage.py create_test_users \
  --count 25 \
  --with-moderator \
  --clear
```

**Параметры:**
- `--count N` - количество пользователей (по умолчанию: 10)
- `--with-moderator` - создать модератора
- `--clear` - удалить существующих пользователей

### 3. 📊 Создание только опросов

```bash
# Создание всех типов опросов
docker-compose -f docker-compose.local.yml exec django python manage.py create_test_surveys \
  --survey-type all

# Создание только опроса по программированию
docker-compose -f docker-compose.local.yml exec django python manage.py create_test_surveys \
  --survey-type programming

# Очистка и создание новых опросов
docker-compose -f docker-compose.local.yml exec django python manage.py create_test_surveys \
  --survey-type all \
  --clear
```

**Типы опросов:**
- `programming` - тест по программированию (5 вопросов)
- `math` - тест по математике (4 вопроса)
- `general` - общие знания (4 вопроса)
- `all` - все типы опросов

## 🔐 Тестовые учетные данные

### Модератор
- **Номер телефона:** `+998901000000`
- **Пароль:** `moderator123`
- **Роль:** Модератор системы

### Обычные пользователи
- **Номера телефонов:** `+998901001000` до `+998901001XXX`
- **Пароль:** `user123`
- **Роли:** Обычные пользователи

> **Примечание:** Все номера телефонов уже подтверждены, авторизация работает через OTP.

## 🌐 Тестирование API

### 1. Авторизация пользователя

```bash
# Получение OTP
curl -X POST http://localhost:8000/api/auth/send-otp/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+998901001000"}'

# Авторизация с OTP
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+998901001000",
    "otp_code": "ПОЛУЧЕННЫЙ_OTP_КОД"
  }'
```

### 2. Работа с опросами

```bash
# Получение списка опросов
curl -X GET http://localhost:8000/api/surveys/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN"

# Запуск опроса с динамическим количеством вопросов
curl -X POST http://localhost:8000/api/surveys/2/start/ \
  -H "Authorization: Bearer ВАШ_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "questions_count": 3,
    "language": "ru"
  }'
```

### 3. Панель модератора

```bash
# Dashboard модератора
curl -X GET http://localhost:8000/api/moderator/dashboard/ \
  -H "Authorization: Bearer МОДЕРАТОР_ACCESS_TOKEN"

# Список пользователей
curl -X GET http://localhost:8000/api/moderator/users/ \
  -H "Authorization: Bearer МОДЕРАТОР_ACCESS_TOKEN"

# Поиск пользователей
curl -X GET "http://localhost:8000/api/moderator/users/?search=Нодир" \
  -H "Authorization: Bearer МОДЕРАТОР_ACCESS_TOKEN"
```

## 📊 Созданные опросы

### 1. "Тест по основам программирования"
- **Вопросов:** 5
- **Время:** 45 минут
- **Проходной балл:** 70%
- **Максимум попыток:** 3
- **Типы вопросов:** одиночный выбор, множественный выбор, открытые

### 2. "Тест по математике"
- **Вопросов:** 4
- **Время:** 30 минут
- **Проходной балл:** 60%
- **Максимум попыток:** 3
- **Типы вопросов:** одиночный выбор, множественный выбор, открытые

### 3. "Общие знания"
- **Вопросов:** 4
- **Время:** 25 минут
- **Проходной балл:** 50%
- **Максимум попыток:** 5
- **Типы вопросов:** одиночный выбор, множественный выбор, открытые

## 🎭 Пример пользователей

Команда создает пользователей с реалистичными данными:

```
Нодир Бакиев - Филиал Юнусабад, Администратор
Юсуф Джалилов - Филиал Чиланзар, Администратор  
Шерзод Шарипов - Филиал Алмазар, Заместитель директора
Азиз Мирзаев - Региональный офис Самарканд, Старший специалист
```

## 🚀 Быстрый старт

1. **Запустите Docker контейнеры:**
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

2. **Настройте демонстрационные данные:**
   ```bash
   docker-compose -f docker-compose.local.yml exec django python manage.py setup_demo_data
   ```

3. **Откройте систему:**
   - API: http://localhost:8000/api/
   - Админка: http://localhost:8000/admin/

4. **Начните тестирование с авторизации модератора или пользователя**

## ⚠️ Важные замечания

- **Безопасность:** Эти данные предназначены только для демонстрации и тестирования
- **Продакшен:** Никогда не используйте эти пароли и данные в реальной системе
- **Очистка:** Используйте `--clear` для удаления старых данных перед созданием новых
- **OTP коды:** В демо-режиме OTP коды выводятся в ответе API для удобства тестирования

## 🛠 Дополнительные команды

```bash
# Просмотр логов
docker-compose -f docker-compose.local.yml logs django

# Django shell
docker-compose -f docker-compose.local.yml exec django python manage.py shell

# Создание суперпользователя
docker-compose -f docker-compose.local.yml exec django python manage.py createsuperuser

# Просмотр всех команд
docker-compose -f docker-compose.local.yml exec django python manage.py help
```

---

🎉 **Система готова к демонстрации!** Все функции протестированы и работают корректно.
