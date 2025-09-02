#!/usr/bin/env python3
"""
Тест для проверки новых эндпоинтов навигации по вопросам
"""

import requests
import json

# Базовый URL API
BASE_URL = "http://localhost:8000/api"

def test_api_endpoints():
    """Тестируем доступность новых эндпоинтов"""
    
    print("🔍 Тестирование новых эндпоинтов навигации...")
    print("=" * 50)
    
    # Тест 1: Проверяем схему API
    print("\n1. Проверка схемы API...")
    try:
        response = requests.get(f"{BASE_URL}/schema/?format=json")
        if response.status_code == 200:
            schema = response.json()
            print("✅ Схема API доступна")
            
            # Проверяем наличие наших эндпоинтов
            paths = schema.get('paths', {})
            required_endpoints = [
                '/api/sessions/{id}/get_question/',
                '/api/sessions/{id}/modify_answer/',
                '/api/sessions/{id}/all_answers/',
                '/api/sessions/{id}/next_question_by_order/',
                '/api/sessions/{id}/previous_question/'
            ]
            
            for endpoint in required_endpoints:
                if endpoint in paths:
                    print(f"✅ {endpoint} - найден")
                else:
                    print(f"❌ {endpoint} - НЕ найден")
                    
        else:
            print(f"❌ Ошибка получения схемы API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании схемы API: {e}")
    
    # Тест 2: Проверяем доступность Swagger UI
    print("\n2. Проверка Swagger UI...")
    try:
        response = requests.get(f"{BASE_URL}/schema/swagger-ui/")
        if response.status_code == 200:
            print("✅ Swagger UI доступен")
            print(f"   URL: {BASE_URL}/schema/swagger-ui/")
        else:
            print(f"❌ Swagger UI недоступен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка при проверке Swagger UI: {e}")
    
    # Тест 3: Проверяем доступность Redoc
    print("\n3. Проверка Redoc...")
    try:
        response = requests.get(f"{BASE_URL}/schema/redoc/")
        if response.status_code == 200:
            print("✅ Redoc доступен")
            print(f"   URL: {BASE_URL}/schema/redoc/")
        else:
            print(f"❌ Redoc недоступен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка при проверке Redoc: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Список новых эндпоинтов:")
    print("   • GET  /api/sessions/{id}/get_question/ - Получить вопрос по номеру")
    print("   • POST /api/sessions/{id}/modify_answer/ - Изменить ответ")
    print("   • GET  /api/sessions/{id}/all_answers/ - Все ответы пользователя")
    print("   • GET  /api/sessions/{id}/next_question_by_order/ - Следующий вопрос")
    print("   • GET  /api/sessions/{id}/previous_question/ - Предыдущий вопрос")
    
    print("\n🌐 Для тестирования API используйте:")
    print(f"   • Swagger UI: {BASE_URL}/schema/swagger-ui/")
    print(f"   • Redoc: {BASE_URL}/schema/redoc/")
    print(f"   • JSON Schema: {BASE_URL}/schema/?format=json")

if __name__ == "__main__":
    test_api_endpoints()
