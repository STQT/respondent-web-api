from django.core.management.base import BaseCommand
from django.db import transaction
from apps.surveys.models import Survey, Question, Choice


class Command(BaseCommand):
    help = 'Создает тестовые опросы с вопросами для демонстрации системы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--survey-type',
            type=str,
            choices=['programming', 'math', 'general', 'all'],
            default='all',
            help='Тип опроса для создания (programming, math, general, all)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить все существующие опросы',
        )

    def handle(self, *args, **options):
        survey_type = options['survey_type']
        clear_surveys = options['clear']

        if clear_surveys:
            self.stdout.write('Удаление существующих опросов...')
            Survey.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Все опросы удалены.')
            )

        surveys_to_create = []
        
        if survey_type in ['programming', 'all']:
            surveys_to_create.append('programming')
        if survey_type in ['math', 'all']:
            surveys_to_create.append('math')
        if survey_type in ['general', 'all']:
            surveys_to_create.append('general')

        for survey in surveys_to_create:
            if survey == 'programming':
                self.create_programming_survey()
            elif survey == 'math':
                self.create_math_survey()
            elif survey == 'general':
                self.create_general_survey()

        self.stdout.write(
            self.style.SUCCESS(f'\nУспешно создано {len(surveys_to_create)} опросов!')
        )

    def create_programming_survey(self):
        """Создает опрос по программированию."""
        with transaction.atomic():
            survey = Survey.objects.create(
                title='Тест по основам программирования',
                description='Тестирование знаний основ программирования и алгоритмов',
                time_limit_minutes=45,
                questions_count=10,
                passing_score=70,
                max_attempts=3
            )
            
            self.stdout.write(f'Создан опрос: {survey.title}')

            questions_data = [
                {
                    'type': 'single',
                    'text': {
                        'uz': 'Python tilida o\'zgaruvchi yaratish uchun qaysi kalit so\'z ishlatiladi?',
                        'uz_cyrl': 'Python тилида ўзгарувчи яратиш учун қайси калит сўз ишлатилади?',
                        'ru': 'Какое ключевое слово используется для создания переменной в Python?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': 'var', 'uz_cyrl': 'var', 'ru': 'var'}, 'correct': False},
                        {'text': {'uz': 'let', 'uz_cyrl': 'let', 'ru': 'let'}, 'correct': False},
                        {'text': {'uz': 'def', 'uz_cyrl': 'def', 'ru': 'def'}, 'correct': False},
                        {'text': {'uz': 'Kalit so\'z kerak emas', 'uz_cyrl': 'Калит сўз керак эмас', 'ru': 'Ключевое слово не нужно'}, 'correct': True}
                    ]
                },
                {
                    'type': 'multiple',
                    'text': {
                        'uz': 'Quyidagilardan qaysilari Python ma\'lumot turlari?',
                        'uz_cyrl': 'Қуйидагилардан қайсилари Python маълумот турлари?',
                        'ru': 'Какие из следующих являются типами данных Python?'
                    },
                    'points': 2,
                    'choices': [
                        {'text': {'uz': 'int', 'uz_cyrl': 'int', 'ru': 'int'}, 'correct': True},
                        {'text': {'uz': 'string', 'uz_cyrl': 'string', 'ru': 'string'}, 'correct': False},
                        {'text': {'uz': 'str', 'uz_cyrl': 'str', 'ru': 'str'}, 'correct': True},
                        {'text': {'uz': 'list', 'uz_cyrl': 'list', 'ru': 'list'}, 'correct': True}
                    ]
                },
                {
                    'type': 'open',
                    'text': {
                        'uz': 'Python da "Hello World" ni ekranga chiqarish uchun qanday kod yozasiz?',
                        'uz_cyrl': 'Python да "Hello World" ни экранга чиқариш учун қандай код ёзасиз?',
                        'ru': 'Какой код напишете для вывода "Hello World" на экран в Python?'
                    },
                    'points': 2
                },
                {
                    'type': 'single',
                    'text': {
                        'uz': 'Qaysi operatordan shartli bayonotlar uchun foydalaniladi?',
                        'uz_cyrl': 'Қайси операторни шартли баёнотлар учун фойдаланилади?',
                        'ru': 'Какой оператор используется для условных выражений?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': 'if', 'uz_cyrl': 'if', 'ru': 'if'}, 'correct': True},
                        {'text': {'uz': 'for', 'uz_cyrl': 'for', 'ru': 'for'}, 'correct': False},
                        {'text': {'uz': 'while', 'uz_cyrl': 'while', 'ru': 'while'}, 'correct': False},
                        {'text': {'uz': 'def', 'uz_cyrl': 'def', 'ru': 'def'}, 'correct': False}
                    ]
                },
                {
                    'type': 'single',
                    'text': {
                        'uz': 'Python da funksiya yaratish uchun qaysi kalit so\'z ishlatiladi?',
                        'uz_cyrl': 'Python да функция яратиш учун қайси калит сўз ишлатилади?',
                        'ru': 'Какое ключевое слово используется для создания функции в Python?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': 'function', 'uz_cyrl': 'function', 'ru': 'function'}, 'correct': False},
                        {'text': {'uz': 'def', 'uz_cyrl': 'def', 'ru': 'def'}, 'correct': True},
                        {'text': {'uz': 'func', 'uz_cyrl': 'func', 'ru': 'func'}, 'correct': False},
                        {'text': {'uz': 'method', 'uz_cyrl': 'method', 'ru': 'method'}, 'correct': False}
                    ]
                }
            ]

            self.create_questions(survey, questions_data)

    def create_math_survey(self):
        """Создает математический опрос."""
        with transaction.atomic():
            survey = Survey.objects.create(
                title='Тест по математике',
                description='Базовые математические знания и задачи',
                time_limit_minutes=30,
                questions_count=8,
                passing_score=60,
                max_attempts=3
            )
            
            self.stdout.write(f'Создан опрос: {survey.title}')

            questions_data = [
                {
                    'type': 'single',
                    'text': {
                        'uz': '2 + 2 nechiga teng?',
                        'uz_cyrl': '2 + 2 нечига тенг?',
                        'ru': 'Чему равно 2 + 2?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': '3', 'uz_cyrl': '3', 'ru': '3'}, 'correct': False},
                        {'text': {'uz': '4', 'uz_cyrl': '4', 'ru': '4'}, 'correct': True},
                        {'text': {'uz': '5', 'uz_cyrl': '5', 'ru': '5'}, 'correct': False},
                        {'text': {'uz': '22', 'uz_cyrl': '22', 'ru': '22'}, 'correct': False}
                    ]
                },
                {
                    'type': 'single',
                    'text': {
                        'uz': '10 ning kvadrat ildizi nechiga teng?',
                        'uz_cyrl': '10 нинг квадрат илдизи нечига тенг?',
                        'ru': 'Чему равен квадратный корень из 100?'
                    },
                    'points': 2,
                    'choices': [
                        {'text': {'uz': '10', 'uz_cyrl': '10', 'ru': '10'}, 'correct': True},
                        {'text': {'uz': '20', 'uz_cyrl': '20', 'ru': '20'}, 'correct': False},
                        {'text': {'uz': '50', 'uz_cyrl': '50', 'ru': '50'}, 'correct': False},
                        {'text': {'uz': '5', 'uz_cyrl': '5', 'ru': '5'}, 'correct': False}
                    ]
                },
                {
                    'type': 'open',
                    'text': {
                        'uz': '15% dan 200 ni hisoblang',
                        'uz_cyrl': '15% дан 200 ни ҳисобланг',
                        'ru': 'Вычислите 15% от 200'
                    },
                    'points': 3
                },
                {
                    'type': 'multiple',
                    'text': {
                        'uz': 'Quyidagi sonlardan qaysilari tub sonlar?',
                        'uz_cyrl': 'Қуйидаги сонлардан қайсилари туб сонлар?',
                        'ru': 'Какие из следующих чисел являются простыми?'
                    },
                    'points': 2,
                    'choices': [
                        {'text': {'uz': '2', 'uz_cyrl': '2', 'ru': '2'}, 'correct': True},
                        {'text': {'uz': '4', 'uz_cyrl': '4', 'ru': '4'}, 'correct': False},
                        {'text': {'uz': '7', 'uz_cyrl': '7', 'ru': '7'}, 'correct': True},
                        {'text': {'uz': '9', 'uz_cyrl': '9', 'ru': '9'}, 'correct': False}
                    ]
                }
            ]

            self.create_questions(survey, questions_data)

    def create_general_survey(self):
        """Создает общий опрос."""
        with transaction.atomic():
            survey = Survey.objects.create(
                title='Общие знания',
                description='Тест на общую эрудицию и знания',
                time_limit_minutes=25,
                questions_count=12,
                passing_score=50,
                max_attempts=5
            )
            
            self.stdout.write(f'Создан опрос: {survey.title}')

            questions_data = [
                {
                    'type': 'single',
                    'text': {
                        'uz': 'O\'zbekistonning poytaxti qaysi shahar?',
                        'uz_cyrl': 'Ўзбекистоннинг пойтахти қайси шаҳар?',
                        'ru': 'Какой город является столицей Узбекистана?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': 'Samarqand', 'uz_cyrl': 'Самарқанд', 'ru': 'Самарканд'}, 'correct': False},
                        {'text': {'uz': 'Toshkent', 'uz_cyrl': 'Тошкент', 'ru': 'Ташкент'}, 'correct': True},
                        {'text': {'uz': 'Buxoro', 'uz_cyrl': 'Бухоро', 'ru': 'Бухара'}, 'correct': False},
                        {'text': {'uz': 'Andijon', 'uz_cyrl': 'Андижон', 'ru': 'Андижан'}, 'correct': False}
                    ]
                },
                {
                    'type': 'single',
                    'text': {
                        'uz': 'Yilda necha kun bor?',
                        'uz_cyrl': 'Йилда неча кун бор?',
                        'ru': 'Сколько дней в году?'
                    },
                    'points': 1,
                    'choices': [
                        {'text': {'uz': '364', 'uz_cyrl': '364', 'ru': '364'}, 'correct': False},
                        {'text': {'uz': '365', 'uz_cyrl': '365', 'ru': '365'}, 'correct': True},
                        {'text': {'uz': '366', 'uz_cyrl': '366', 'ru': '366'}, 'correct': False},
                        {'text': {'uz': '360', 'uz_cyrl': '360', 'ru': '360'}, 'correct': False}
                    ]
                },
                {
                    'type': 'open',
                    'text': {
                        'uz': 'Eng katta okean qaysi?',
                        'uz_cyrl': 'Энг катта океан қайси?',
                        'ru': 'Какой океан самый большой?'
                    },
                    'points': 2
                },
                {
                    'type': 'multiple',
                    'text': {
                        'uz': 'Quyidagilardan qaysilari qit\'alar?',
                        'uz_cyrl': 'Қуйидагилардан қайсилари қитъалар?',
                        'ru': 'Какие из следующих являются континентами?'
                    },
                    'points': 2,
                    'choices': [
                        {'text': {'uz': 'Osiyo', 'uz_cyrl': 'Осиё', 'ru': 'Азия'}, 'correct': True},
                        {'text': {'uz': 'Rossiya', 'uz_cyrl': 'Россия', 'ru': 'Россия'}, 'correct': False},
                        {'text': {'uz': 'Afrika', 'uz_cyrl': 'Африка', 'ru': 'Африка'}, 'correct': True},
                        {'text': {'uz': 'Avstraliya', 'uz_cyrl': 'Австралия', 'ru': 'Австралия'}, 'correct': True}
                    ]
                }
            ]

            self.create_questions(survey, questions_data)

    def create_questions(self, survey, questions_data):
        """Создает вопросы для опроса."""
        for i, q_data in enumerate(questions_data, 1):
            question = Question.objects.create(
                survey=survey,
                question_type=q_data['type'],
                text_uz=q_data['text']['uz'],
                text_uz_cyrl=q_data['text']['uz_cyrl'],
                text_ru=q_data['text']['ru'],
                points=q_data['points'],
                order=i
            )

            if 'choices' in q_data:
                for j, choice_data in enumerate(q_data['choices'], 1):
                    Choice.objects.create(
                        question=question,
                        text_uz=choice_data['text']['uz'],
                        text_uz_cyrl=choice_data['text']['uz_cyrl'],
                        text_ru=choice_data['text']['ru'],
                        is_correct=choice_data['correct'],
                        order=j
                    )

            self.stdout.write(f'  Создан вопрос {i}: {question.text_ru[:50]}...')
