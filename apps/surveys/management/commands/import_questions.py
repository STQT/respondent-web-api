import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.surveys.models import Survey, Question, Choice
from apps.contrib.constants import UserWorkDomainChoices, QuestionCategoryChoices


class Command(BaseCommand):
    help = 'Import questions and choices for a specific survey from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'survey_id',
            type=int,
            help='ID of the survey to import questions for'
        )
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing questions and choices data'
        )

    def handle(self, *args, **options):
        survey_id = options['survey_id']
        csv_file_path = options['csv_file']
        
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV file "{csv_file_path}" does not exist.')

        try:
            survey = Survey.objects.get(id=survey_id)
        except Survey.DoesNotExist:
            raise CommandError(f'Survey with ID {survey_id} does not exist.')

        questions_created = 0
        questions_updated = 0
        choices_created = 0
        choices_updated = 0
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # Start from 2 because of header
                        try:
                            # Required fields
                            question_order = int(row.get('question_order', 0))
                            question_type = row.get('question_type', '').strip()
                            text_uz = row.get('text_uz', '').strip()
                            
                            if not text_uz:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Skipping question without text_uz')
                                )
                                continue

                            # Validate question type
                            valid_types = ['single', 'multiple', 'open']
                            if question_type not in valid_types:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Invalid question_type "{question_type}". Using "single".')
                                )
                                question_type = 'single'

                            # Get or create question
                            question, question_created = Question.objects.get_or_create(
                                survey=survey,
                                order=question_order,
                                defaults={
                                    'question_type': question_type,
                                    'text_uz': text_uz,
                                    'text_uz_cyrl': row.get('text_uz_cyrl', '').strip(),
                                    'text_ru': row.get('text_ru', '').strip(),
                                    'points': int(row.get('points', 1)),
                                    'is_active': row.get('is_active', 'true').lower() == 'true',
                                    'work_domain': row.get('work_domain', '').strip(),
                                    'category': row.get('category', 'other').strip(),
                                }
                            )
                            
                            if question_created:
                                questions_created += 1
                                self.stdout.write(f'Created question {question_order}: {text_uz[:50]}...')
                            else:
                                # Update existing question
                                question.question_type = question_type
                                question.text_uz = text_uz
                                question.text_uz_cyrl = row.get('text_uz_cyrl', '').strip()
                                question.text_ru = row.get('text_ru', '').strip()
                                question.points = int(row.get('points', 1))
                                question.is_active = row.get('is_active', 'true').lower() == 'true'
                                question.work_domain = row.get('work_domain', '').strip()
                                question.category = row.get('category', 'other').strip()
                                question.save()
                                questions_updated += 1
                                self.stdout.write(f'Updated question {question_order}: {text_uz[:50]}...')

                            # Handle choices for single/multiple choice questions
                            if question_type in ['single', 'multiple']:
                                # Clear existing choices
                                question.choices.all().delete()
                                
                                # Parse choices
                                choices_data = []
                                choice_num = 1
                                while True:
                                    choice_text_uz = row.get(f'choice_{choice_num}_text_uz', '').strip()
                                    if not choice_text_uz:
                                        break
                                    
                                    choice_text_uz_cyrl = row.get(f'choice_{choice_num}_text_uz_cyrl', '').strip()
                                    choice_text_ru = row.get(f'choice_{choice_num}_text_ru', '').strip()
                                    is_correct = row.get(f'choice_{choice_num}_is_correct', 'false').lower() == 'true'
                                    
                                    choices_data.append({
                                        'text_uz': choice_text_uz,
                                        'text_uz_cyrl': choice_text_uz_cyrl,
                                        'text_ru': choice_text_ru,
                                        'is_correct': is_correct,
                                        'order': choice_num
                                    })
                                    
                                    choice_num += 1
                                
                                # Create choices
                                for choice_data in choices_data:
                                    choice, choice_created = Choice.objects.get_or_create(
                                        question=question,
                                        order=choice_data['order'],
                                        defaults=choice_data
                                    )
                                    
                                    if choice_created:
                                        choices_created += 1
                                    else:
                                        # Update existing choice
                                        for key, value in choice_data.items():
                                            setattr(choice, key, value)
                                        choice.save()
                                        choices_updated += 1

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Row {row_num}: Error processing question - {str(e)}')
                            )
                            continue

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed for survey "{survey.title}". '
                f'Questions: Created {questions_created}, Updated {questions_updated}. '
                f'Choices: Created {choices_created}, Updated {choices_updated}.'
            )
        )
