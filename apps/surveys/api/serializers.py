from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from apps.surveys.models import (
    Survey, Question, Choice, SurveySession, 
    SessionQuestion, Answer, UserSurveyHistory
)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Пример варианта ответа",
            value={
                "id": 1,
                "text": "Правильный ответ",
                "text_uz": "To'g'ri javob",
                "text_uz_cyrl": "Тўғри жавоб",
                "text_ru": "Правильный ответ",
                "order": 1
            }
        )
    ]
)
class ChoiceSerializer(serializers.ModelSerializer):
    """Serializer for question choices."""
    
    text = serializers.SerializerMethodField(help_text="Текст варианта ответа")
    text_uz = serializers.CharField(read_only=True, help_text="Текст на узбекском языке (латиница)")
    text_uz_cyrl = serializers.CharField(read_only=True, help_text="Текст на узбекском языке (кириллица)")
    text_ru = serializers.CharField(read_only=True, help_text="Текст на русском языке")
    
    class Meta:
        model = Choice
        fields = ['id', 'text', 'text_uz', 'text_uz_cyrl', 'text_ru', 'order']
    
    def get_text(self, obj):
        """Get localized choice text."""
        language = self.context.get('language', 'uz')
        return obj.get_text(language)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Пример вопроса",
            value={
                "id": 1,
                "question_type": "single",
                "text": "Какой язык программирования вы предпочитаете?",
                "text_uz": "Qaysi dasturlash tilini afzal ko'rasiz?",
                "text_uz_cyrl": "Қайси дастурлаш тилини афзал кўрасиз?",
                "text_ru": "Какой язык программирования вы предпочитаете?",
                "image": None,
                "video": None,
                "points": 5,
                "order": 1,
                "category": "safety_logic_psychology",
                "work_domain": "natural_gas",
                "choices": [
                    {
                        "id": 1, 
                        "text": "Python", 
                        "text_uz": "Python", 
                        "text_uz_cyrl": "Python", 
                        "text_ru": "Python", 
                        "order": 1
                    },
                    {
                        "id": 2, 
                        "text": "JavaScript", 
                        "text_uz": "JavaScript", 
                        "text_uz_cyrl": "JavaScript", 
                        "text_ru": "JavaScript", 
                        "order": 2
                    },
                    {
                        "id": 3, 
                        "text": "Java", 
                        "text_uz": "Java", 
                        "text_uz_cyrl": "Java", 
                        "text_ru": "Java", 
                        "order": 3
                    }
                ]
            }
        )
    ]
)
class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for survey questions."""
    
    text = serializers.SerializerMethodField(help_text="Текст вопроса")
    text_uz = serializers.CharField(read_only=True, help_text="Текст вопроса на узбекском языке (латиница)")
    text_uz_cyrl = serializers.CharField(read_only=True, help_text="Текст вопроса на узбекском языке (кириллица)")
    text_ru = serializers.CharField(read_only=True, help_text="Текст вопроса на русском языке")
    choices = ChoiceSerializer(many=True, read_only=True, help_text="Варианты ответов")
    
    class Meta:
        model = Question
        fields = [
            'id', 'question_type', 'text', 'text_uz', 'text_uz_cyrl', 'text_ru',
            'image', 'video', 'points', 'order', 'category', 'work_domain', 'choices'
        ]
    
    def get_text(self, obj):
        """Get localized question text."""
        language = self.context.get('language', 'uz')
        return obj.get_text(language)


class SurveyListSerializer(serializers.ModelSerializer):
    """Serializer for survey list view."""
    
    total_questions = serializers.SerializerMethodField()
    user_attempts = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()
    
    class Meta:
        model = Survey
        fields = [
            'id', 'title', 'description', 'time_limit_minutes',
            'questions_count', 'passing_score', 'max_attempts',
            'safety_logic_psychology_percentage', 'other_percentage',
            'total_questions', 'user_attempts', 'can_start'
        ]
    
    def get_total_questions(self, obj):
        """Get total available questions."""
        return obj.get_total_available_questions()
    
    def get_user_attempts(self, obj):
        """Get user's attempts count."""
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.sessions.filter(user=user).count()
        return 0
    
    def get_can_start(self, obj):
        """Check if user can start a new attempt."""
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        
        user_attempts = self.get_user_attempts(obj)
        
        # Check if user has reached max attempts
        if user_attempts >= obj.max_attempts:
            # Check if moderator allowed retake
            last_session = obj.sessions.filter(user=user).order_by('-started_at').first()
            if last_session and last_session.can_retake:
                return True
            return False
        
        # Check if user has an active session
        active_session = obj.sessions.filter(
            user=user, 
            status__in=['started', 'in_progress']
        ).first()
        
        return active_session is None


class SurveyDetailSerializer(serializers.ModelSerializer):
    """Serializer for survey detail view."""
    
    total_questions = serializers.SerializerMethodField()
    
    class Meta:
        model = Survey
        fields = [
            'id', 'title', 'description', 'time_limit_minutes',
            'questions_count', 'passing_score', 'max_attempts',
            'safety_logic_psychology_percentage', 'other_percentage',
            'total_questions'
        ]
    
    def get_total_questions(self, obj):
        """Get total available questions."""
        return obj.get_total_available_questions()


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Начать опрос с параметрами",
            value={
                "questions_count": 10,
                "language": "ru"
            }
        )
    ]
)
class StartSurveySerializer(serializers.Serializer):
    """Serializer for starting a survey session."""
    
    survey_id = serializers.IntegerField(help_text="ID опроса")
    questions_count = serializers.IntegerField(
        required=False, 
        min_value=1, 
        max_value=100,
        help_text="Количество вопросов (опционально)"
    )
    language = serializers.ChoiceField(
        choices=['uz', 'uz-cyrl', 'ru'], 
        default='uz',
        help_text="Язык опроса"
    )
    
    def validate_survey_id(self, value):
        """Validate survey exists and is active."""
        try:
            survey = Survey.objects.get(id=value, is_active=True)
        except Survey.DoesNotExist:
            raise serializers.ValidationError(_("Survey not found or inactive"))
        return value
    
    def validate(self, attrs):
        """Validate user can start survey."""
        user = self.context['request'].user
        survey = Survey.objects.get(id=attrs['survey_id'])
        
        # Check if user has reached max attempts
        user_attempts = survey.sessions.filter(user=user).count()
        if user_attempts >= survey.max_attempts:
            # Check if moderator allowed retake
            last_session = survey.sessions.filter(user=user).order_by('-started_at').first()
            if not (last_session and last_session.can_retake):
                raise serializers.ValidationError(
                    _("Maximum attempts reached. Contact moderator for permission to retake.")
                )
        
        # Check if user has an active session
        active_session = survey.sessions.filter(
            user=user, 
            status__in=['started', 'in_progress']
        ).first()
        
        if active_session:
            raise serializers.ValidationError(_("You already have an active session for this survey"))
        
        # Validate questions_count
        questions_count = attrs.get('questions_count', survey.questions_count)
        max_available = survey.get_total_available_questions()
        
        if questions_count > max_available:
            attrs['questions_count'] = max_available
        
        attrs['survey'] = survey
        return attrs


class SessionQuestionSerializer(serializers.ModelSerializer):
    """Serializer for session questions."""
    
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = SessionQuestion
        fields = ['id', 'question', 'order', 'is_answered', 'points_earned']


class SurveySessionSerializer(serializers.ModelSerializer):
    """Serializer for survey sessions."""
    
    survey = SurveyDetailSerializer(read_only=True)
    progress = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    current_question = serializers.SerializerMethodField()
    
    class Meta:
        model = SurveySession
        fields = [
            'id', 'survey', 'status', 'attempt_number', 'started_at',
            'expires_at', 'language', 'progress', 'time_remaining',
            'current_question', 'score', 'total_points', 'percentage', 'is_passed'
        ]
    
    def get_progress(self, obj):
        """Get session progress."""
        return obj.get_current_progress()
    
    def get_time_remaining(self, obj):
        """Get time remaining in minutes."""
        if obj.status in ['completed', 'expired', 'cancelled']:
            return 0
        
        from django.utils import timezone
        remaining = obj.expires_at - timezone.now()
        return max(0, int(remaining.total_seconds() / 60))
    
    def get_current_question(self, obj):
        """Get current unanswered question."""
        next_question = obj.get_next_unanswered_question()
        if next_question:
            language = obj.language
            context = {'language': language}
            return SessionQuestionSerializer(next_question, context=context).data
        return None


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Ответ один вариант",
            value={
                "question_id": 1,
                "choice_ids": [3]
            }
        ),
        OpenApiExample(
            name="Ответ множественный выбор",
            value={
                "question_id": 2,
                "choice_ids": [5, 7, 9]
            }
        ),
        OpenApiExample(
            name="Открытый ответ",
            value={
                "question_id": 3,
                "text_answer": "Мой развернутый ответ на вопрос"
            }
        )
    ]
)
class SubmitAnswerSerializer(serializers.Serializer):
    """Serializer for submitting answers."""
    
    session_id = serializers.UUIDField(help_text="ID сессии")
    question_id = serializers.IntegerField(help_text="ID вопроса")
    choice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Список ID выбранных вариантов"
    )
    text_answer = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Текстовый ответ (для открытых вопросов)"
    )
    force_finish = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Принудительно завершить опрос после этого ответа"
    )
    
    def validate(self, attrs):
        """Validate answer submission."""
        user = self.context['request'].user
        
        # Validate session
        try:
            session = SurveySession.objects.get(
                id=attrs['session_id'],
                user=user,
                status__in=['started', 'in_progress']
            )
        except SurveySession.DoesNotExist:
            raise serializers.ValidationError(_("Invalid or inactive session"))
        
        if session.is_expired():
            session.status = 'expired'
            session.save()
            raise serializers.ValidationError(_("Session has expired"))
        
        # Validate question belongs to session
        try:
            session_question = session.sessionquestion_set.get(
                question_id=attrs['question_id']
            )
        except SessionQuestion.DoesNotExist:
            raise serializers.ValidationError(_("Question not found in this session"))
        
        question = session_question.question
        
        # If question is already answered, allow updating the answer
        if session_question.is_answered:
            # Check if we can modify the answer
            if not session.can_modify_answer(attrs['question_id']):
                raise serializers.ValidationError(_("Cannot modify this answer. Session may be completed or expired."))
        
        # Validate answer based on question type
        if question.question_type in ['single', 'multiple']:
            if not attrs.get('choice_ids'):
                raise serializers.ValidationError(_("Choice selection required"))
            
            # Validate choices belong to question
            valid_choice_ids = list(question.choices.values_list('id', flat=True))
            for choice_id in attrs['choice_ids']:
                if choice_id not in valid_choice_ids:
                    raise serializers.ValidationError(_("Invalid choice selected"))
            
            # Validate single choice constraint
            if question.question_type == 'single' and len(attrs['choice_ids']) > 1:
                raise serializers.ValidationError(_("Only one choice allowed for single choice questions"))
        
        elif question.question_type == 'open':
            if not attrs.get('text_answer', '').strip():
                raise serializers.ValidationError(_("Text answer required"))
        
        attrs['session'] = session
        attrs['session_question'] = session_question
        attrs['question'] = question
        return attrs


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for answers."""
    
    selected_choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Answer
        fields = [
            'id', 'question', 'selected_choices', 'text_answer',
            'is_correct', 'points_earned', 'answered_at'
        ]


class UserSurveyHistorySerializer(serializers.ModelSerializer):
    """Serializer for user survey history."""
    
    survey = SurveyDetailSerializer(read_only=True)
    
    class Meta:
        model = UserSurveyHistory
        fields = [
            'survey', 'total_attempts', 'best_score', 'best_percentage',
            'last_attempt_at', 'is_passed', 'current_status', 'can_continue'
        ]


class CertificateDataSerializer(serializers.ModelSerializer):
    """Serializer for certificate data."""
    
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    # Основные поля (обратная совместимость)
    user_branch = serializers.CharField(source='user.position.branch.name_uz', read_only=True)
    user_position = serializers.CharField(source='user.position.name_uz', read_only=True)
    
    # Мультиязычные поля
    user_branch_uz = serializers.CharField(source='user.position.branch.name_uz', read_only=True)
    user_branch_uz_cyrl = serializers.CharField(source='user.position.branch.name_uz_cyrl', read_only=True)
    user_branch_ru = serializers.CharField(source='user.position.branch.name_ru', read_only=True)
    
    user_position_uz = serializers.CharField(source='user.position.name_uz', read_only=True)
    user_position_uz_cyrl = serializers.CharField(source='user.position.name_uz_cyrl', read_only=True)
    user_position_ru = serializers.CharField(source='user.position.name_ru', read_only=True)
    
    user_work_domain = serializers.CharField(source='user.get_work_domain_display', read_only=True)
    user_employee_level = serializers.CharField(source='user.get_employee_level_display', read_only=True)
    survey_title = serializers.CharField(source='survey.title', read_only=True)
    survey_description = serializers.CharField(source='survey.description', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = SurveySession
        fields = [
            'id', 'certificate_order', 'attempt_number',
            'user_name', 
            # Основные поля (обратная совместимость)
            'user_branch', 'user_position',
            # Мультиязычные поля
            'user_branch_uz', 'user_branch_uz_cyrl', 'user_branch_ru',
            'user_position_uz', 'user_position_uz_cyrl', 'user_position_ru',
            'user_work_domain', 'user_employee_level',
            'survey_title', 'survey_description',
            'score', 'total_points', 'percentage', 'is_passed',
            'started_at', 'completed_at', 'duration_minutes',
            'language'
        ]
    
    def get_duration_minutes(self, obj):
        """Calculate duration in minutes."""
        return obj.duration_minutes()
