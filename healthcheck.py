#!/usr/bin/env python3
"""
Healthcheck script for Django application.
Used by Docker to check if the application is ready to receive requests.
"""

import os
import sys
import requests
from urllib.parse import urljoin

def check_health():
    """Check if Django application is healthy."""
    
    # Get the base URL from environment or use default
    base_url = os.environ.get('HEALTH_CHECK_URL', 'http://localhost:8000')
    health_endpoint = urljoin(base_url, '/api/')
    
    try:
        # Make a request to the API endpoint
        response = requests.get(
            health_endpoint,
            timeout=10,
            headers={'User-Agent': 'HealthCheck/1.0'}
        )
        
        # Check if the response is successful
        if response.status_code == 200:
            print("✅ Django application is healthy")
            return True
        else:
            print(f"❌ Django responded with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Django application")
        return False
    except requests.exceptions.Timeout:
        print("❌ Django application response timeout")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_database():
    """Check database connectivity using Django management command."""
    
    try:
        # Import Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
        
        import django
        django.setup()
        
        from django.db import connection
        from django.core.management import execute_from_command_line
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            
        print("✅ Database connection is healthy")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    # Check if we should test database connectivity
    check_db = '--check-db' in sys.argv
    
    # Perform health checks
    app_healthy = check_health()
    
    if check_db:
        db_healthy = check_database()
        overall_healthy = app_healthy and db_healthy
    else:
        overall_healthy = app_healthy
    
    # Exit with appropriate code
    if overall_healthy:
        print("🎉 All health checks passed!")
        sys.exit(0)
    else:
        print("💥 Health check failed!")
        sys.exit(1)
