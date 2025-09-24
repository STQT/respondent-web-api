import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.surveys.models import Survey, SurveyEmployeeLevelConfig
from apps.contrib.constants import EmployeeLevelChoices


class Command(BaseCommand):
    help = 'Import surveys from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing survey data'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV file "{csv_file_path}" does not exist.')

        created_count = 0
        updated_count = 0
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # Start from 2 because of header
                        try:
                            # Required fields
                            title = row.get('title', '').strip()
                            if not title:
                                self.stdout.write(
                                    self.style.WARNING(f'Row {row_num}: Skipping survey without title')
                                )
                                continue

                            # Get or create survey
                            survey, created = Survey.objects.get_or_create(
                                title=title,
                                defaults={
                                    'description': row.get('description', '').strip(),
                                    'is_active': row.get('is_active', 'true').lower() == 'true',
                                    'time_limit_minutes': int(row.get('time_limit_minutes', 60)),
                                    'questions_count': int(row.get('questions_count', 30)),
                                    'passing_score': int(row.get('passing_score', 70)),
                                    'max_attempts': int(row.get('max_attempts', 3)),
                                    'safety_logic_psychology_percentage': int(row.get('safety_logic_psychology_percentage', 70)),
                                    'other_percentage': int(row.get('other_percentage', 30)),
                                }
                            )
                            
                            if created:
                                created_count += 1
                                self.stdout.write(f'Created survey: {survey.title}')
                            else:
                                # Update existing survey
                                survey.description = row.get('description', '').strip()
                                survey.is_active = row.get('is_active', 'true').lower() == 'true'
                                survey.time_limit_minutes = int(row.get('time_limit_minutes', 60))
                                survey.questions_count = int(row.get('questions_count', 30))
                                survey.passing_score = int(row.get('passing_score', 70))
                                survey.max_attempts = int(row.get('max_attempts', 3))
                                survey.safety_logic_psychology_percentage = int(row.get('safety_logic_psychology_percentage', 70))
                                survey.other_percentage = int(row.get('other_percentage', 30))
                                survey.save()
                                updated_count += 1
                                self.stdout.write(f'Updated survey: {survey.title}')

                            # Handle employee level configurations
                            for level_choice, level_display in EmployeeLevelChoices.choices:
                                level_key = f'questions_count_{level_choice}'
                                if level_key in row and row[level_key].strip():
                                    questions_count = int(row[level_key])
                                    
                                    config, config_created = SurveyEmployeeLevelConfig.objects.get_or_create(
                                        survey=survey,
                                        employee_level=level_choice,
                                        defaults={'questions_count': questions_count}
                                    )
                                    
                                    if not config_created:
                                        config.questions_count = questions_count
                                        config.save()
                                    
                                    action = 'Created' if config_created else 'Updated'
                                    self.stdout.write(f'  {action} config for {level_display}: {questions_count} questions')

                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Row {row_num}: Error processing survey - {str(e)}')
                            )
                            continue

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed. Created: {created_count}, Updated: {updated_count}'
            )
        )
