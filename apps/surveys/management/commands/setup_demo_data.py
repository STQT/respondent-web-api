from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction


class Command(BaseCommand):
    help = 'Настраивает полную демонстрационную систему с пользователями и опросами'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users-count',
            type=int,
            default=15,
            help='Количество тестовых пользователей (по умолчанию: 15)',
        )
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='Удалить все существующие данные перед созданием новых',
        )
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Не создавать пользователей, только опросы',
        )
        parser.add_argument(
            '--skip-surveys',
            action='store_true',
            help='Не создавать опросы, только пользователей',
        )

    def handle(self, *args, **options):
        users_count = options['users_count']
        clear_all = options['clear_all']
        skip_users = options['skip_users']
        skip_surveys = options['skip_surveys']

        self.stdout.write(
            self.style.SUCCESS('🚀 Настройка демонстрационных данных для системы опросов')
        )
        self.stdout.write('=' * 60)

        try:
            with transaction.atomic():
                # Создаем опросы
                if not skip_surveys:
                    self.stdout.write('\n📊 Создание тестовых опросов...')
                    call_command(
                        'create_test_surveys',
                        survey_type='all',
                        clear=clear_all,
                        verbosity=0
                    )
                    self.stdout.write(
                        self.style.SUCCESS('✅ Опросы созданы успешно!')
                    )

                # Создаем пользователей
                if not skip_users:
                    self.stdout.write('\n👥 Создание тестовых пользователей...')
                    call_command(
                        'create_test_users',
                        count=users_count,
                        with_moderator=True,
                        clear=clear_all,
                        verbosity=0
                    )
                    self.stdout.write(
                        self.style.SUCCESS('✅ Пользователи созданы успешно!')
                    )

                self.stdout.write('\n' + '=' * 60)
                self.stdout.write(
                    self.style.SUCCESS('🎉 Демонстрационная система настроена!')
                )
                
                self.display_usage_info()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при настройке: {e}')
            )
            raise

    def display_usage_info(self):
        """Выводит информацию о том, как использовать систему."""
        self.stdout.write('\n📖 Как использовать систему:')
        self.stdout.write('-' * 30)
        
        self.stdout.write('\n🔐 Авторизация:')
        self.stdout.write('• Модератор: +998901000000 / moderator123')
        self.stdout.write('• Пользователи: +99890100XXXX / user123')
        self.stdout.write('  (где XXXX от 1000 до количества созданных пользователей)')

        self.stdout.write('\n🌐 API Endpoints:')
        self.stdout.write('• Отправка OTP: POST /api/auth/send-otp/')
        self.stdout.write('• Авторизация: POST /api/auth/login/')
        self.stdout.write('• Список опросов: GET /api/surveys/')
        self.stdout.write('• Запуск опроса: POST /api/surveys/{id}/start/')
        
        self.stdout.write('\n👨‍💼 Панель модератора:')
        self.stdout.write('• Dashboard: GET /api/moderator/dashboard/')
        self.stdout.write('• Пользователи: GET /api/moderator/users/')
        self.stdout.write('• Статистика: GET /api/moderator/surveys/')

        self.stdout.write('\n🐳 Docker команды:')
        self.stdout.write('• Запуск: docker-compose -f docker-compose.local.yml up -d')
        self.stdout.write('• Логи: docker-compose -f docker-compose.local.yml logs django')
        self.stdout.write('• Shell: docker-compose -f docker-compose.local.yml exec django python manage.py shell')

        self.stdout.write('\n📱 Тестирование:')
        self.stdout.write('• Система работает на http://localhost:8000')
        self.stdout.write('• API документация: http://localhost:8000/api/')
        self.stdout.write('• Админка: http://localhost:8000/admin/')

        self.stdout.write('\n🎯 Созданные опросы:')
        self.stdout.write('• "Тест по основам программирования" - 5 вопросов')
        self.stdout.write('• "Тест по математике" - 4 вопроса') 
        self.stdout.write('• "Общие знания" - 4 вопроса')

        self.stdout.write('\n💡 Полезные команды:')
        self.stdout.write('• Только пользователи: python manage.py create_test_users --count 20')
        self.stdout.write('• Только опросы: python manage.py create_test_surveys --survey-type programming')
        self.stdout.write('• Очистить всё: python manage.py setup_demo_data --clear-all')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.WARNING('⚠️  Это демонстрационные данные! Не используйте в продакшене.')
        )
