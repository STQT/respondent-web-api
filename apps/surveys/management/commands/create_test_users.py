from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User
from phonenumber_field.phonenumber import PhoneNumber
import random


class Command(BaseCommand):
    help = 'Создает тестовых пользователей для демонстрации системы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Количество тестовых пользователей для создания (по умолчанию: 10)',
        )
        parser.add_argument(
            '--with-moderator',
            action='store_true',
            help='Создать также пользователя-модератора',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить всех существующих пользователей (кроме суперпользователей)',
        )

    def handle(self, *args, **options):
        count = options['count']
        with_moderator = options['with_moderator']
        clear_users = options['clear']

        if clear_users:
            self.stdout.write('Удаление существующих пользователей...')
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(
                self.style.WARNING('Все пользователи (кроме суперпользователей) удалены.')
            )

        # Списки для генерации случайных данных
        first_names = [
            'Азиз', 'Анвар', 'Бахтиёр', 'Дилшод', 'Жахонгир', 'Илхом', 'Камол', 'Лазиз',
            'Мансур', 'Нодир', 'Отабек', 'Пулат', 'Рустам', 'Саид', 'Тохир', 'Умид',
            'Фарход', 'Хасан', 'Шерзод', 'Эльёр', 'Юсуф', 'Яшин'
        ]
        
        last_names = [
            'Абдуллаев', 'Ахмедов', 'Бакиев', 'Валиев', 'Гафуров', 'Джалилов', 'Ешанов',
            'Зокиров', 'Исмаилов', 'Кадыров', 'Латипов', 'Мирзаев', 'Назаров', 'Отаев',
            'Петров', 'Рахимов', 'Собиров', 'Турсунов', 'Усманов', 'Фаттахов', 'Хамидов',
            'Шарипов', 'Эргашев', 'Юлдашев', 'Яхьяев'
        ]

        branches = [
            'Главный офис',
            'Филиал Ташкент-Сити',
            'Филиал Мирзо-Улугбек',
            'Филиал Чиланзар',
            'Филиал Юнусабад',
            'Филиал Сергели',
            'Филиал Алмазар',
            'Филиал Шайхантахур',
            'Региональный офис Самарканд',
            'Региональный офис Бухара',
            'Региональный офис Фергана',
            'Региональный офис Андижан'
        ]

        positions = [
            'Специалист',
            'Старший специалист',
            'Ведущий специалист',
            'Менеджер',
            'Старший менеджер',
            'Начальник отдела',
            'Заместитель директора',
            'Консультант',
            'Аналитик',
            'Координатор',
            'Администратор',
            'Операционист'
        ]

        with transaction.atomic():
            # Создаем модератора если требуется
            if with_moderator:
                moderator_phone = '+998901000000'
                if not User.objects.filter(phone_number=moderator_phone).exists():
                    moderator = User.objects.create_user(
                        phone_number=PhoneNumber.from_string(moderator_phone),
                        name='Модератор Тестовый',
                        password='moderator123',
                        is_moderator=True,
                        branch='Главный офис',
                        position='Модератор системы',
                        is_phone_verified=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Создан модератор: {moderator.name} ({moderator.phone_number})')
                    )

            # Создаем обычных пользователей
            created_count = 0
            for i in range(count):
                # Генерируем уникальный номер телефона
                phone_base = f'+99890{1001000 + i:07d}'
                
                # Проверяем, что пользователь с таким номером не существует
                if User.objects.filter(phone_number=phone_base).exists():
                    continue

                # Генерируем случайные данные
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                full_name = f'{first_name} {last_name}'
                branch = random.choice(branches)
                position = random.choice(positions)

                try:
                    user = User.objects.create_user(
                        phone_number=PhoneNumber.from_string(phone_base),
                        name=full_name,
                        password='user123',  # Простой пароль для тестирования
                        is_moderator=False,
                        branch=branch,
                        position=position,
                        is_phone_verified=True
                    )
                    created_count += 1
                    
                    if created_count <= 3:  # Показываем первых 3 для примера
                        self.stdout.write(
                            f'Создан пользователь: {user.name} ({user.phone_number}) - {user.position.branch.name_uz if user.position and user.position.branch else "N/A"}, {user.position.name_uz if user.position else "N/A"}'
                        )
                    elif created_count == 4:
                        self.stdout.write('...')

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Ошибка при создании пользователя {phone_base}: {e}')
                    )
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f'\nУспешно создано {created_count} тестовых пользователей!'
            )
        )
        
        if created_count > 0:
            self.stdout.write('\nДля авторизации используйте:')
            self.stdout.write('- Логин: номер телефона пользователя')
            self.stdout.write('- Пароль: user123 (для обычных пользователей)')
            if with_moderator:
                self.stdout.write('- Пароль модератора: moderator123')
            self.stdout.write('\nВсе пользователи имеют подтвержденные номера телефонов.')
