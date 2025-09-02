"""
ВРЕМЕННО ОТКЛЮЧЕНО: Проверки в методе start отключены для разработки фронтенда
TODO: Восстановить все проверки после завершения разработки фронтенда

Отключенные проверки:
- Максимальное количество попыток
- Активные сессии пользователя
- Валидация параметров через сериализатор
"""

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

from apps.surveys.models import (
    Survey, SurveySession, SessionQuestion, Answer, UserSurveyHistory
)
from .serializers import (
    SurveyListSerializer, SurveyDetailSerializer, StartSurveySerializer,
    SurveySessionSerializer, SubmitAnswerSerializer, AnswerSerializer,
    UserSurveyHistorySerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Список опросов",
        description="""Получить список активных опросов доступных пользователю.
        
        Отображает информацию о количестве попыток пользователя и возможности начать новую попытку.""",
        tags=["Опросы"],
        parameters=[
            OpenApiParameter(
                name='lang',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Язык для отображения (по умолчанию: uz)',
                enum=['uz', 'uz-cyrl', 'ru'],
                default='uz'
            )
        ],
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "title": "SurveyList",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "time_limit_minutes": {"type": "integer"},
                        "questions_count": {"type": "integer"},
                        "passing_score": {"type": "integer"},
                        "max_attempts": {"type": "integer"},
                        "total_questions": {"type": "integer"},
                        "user_attempts": {"type": "integer"},
                        "can_start": {"type": "boolean"}
                    }
                }
            }
        }
    ),
    retrieve=extend_schema(
        summary="Детали опроса",
        description="Получить подробную информацию об опросе по ID.",
        tags=["Опросы"],
        parameters=[
            OpenApiParameter(
                name='lang',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Язык для отображения',
                enum=['uz', 'uz-cyrl', 'ru'],
                default='uz'
            )
        ],
        responses={
            200: {
                "type": "object",
                "title": "SurveyDetail",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "time_limit_minutes": {"type": "integer"},
                    "questions_count": {"type": "integer"},
                    "passing_score": {"type": "integer"},
                    "max_attempts": {"type": "integer"},
                    "total_questions": {"type": "integer"}
                }
            }
        }
    )
)
class SurveyViewSet(ReadOnlyModelViewSet):
    """ViewSet for surveys."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get active surveys."""
        return Survey.objects.filter(is_active=True).order_by('-created_at')
    
    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return SurveyListSerializer
        return SurveyDetailSerializer
    
    def get_serializer_context(self):
        """Add request context to serializer."""
        context = super().get_serializer_context()
        context['language'] = self.request.query_params.get('lang', 'uz')
        return context
    
    @extend_schema(
        summary="Начать опрос",
        description="""Начать новую сессию прохождения опроса.
        
        Создает новую сессию и инициализирует случайные вопросы для прохождения.
        Пользователь может указать количество вопросов и язык.""",
        tags=["Опросы"],
        request={
            "type": "object",
            "title": "StartSurveyRequest",
            "properties": {
                "questions_count": {"type": "integer", "minimum": 1, "maximum": 100},
                "language": {"type": "string", "enum": ["uz", "uz-cyrl", "ru"], "default": "uz"}
            }
        },
        responses={
            201: {
                "type": "object",
                "title": "SurveySession",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "survey": {"type": "object", "title": "Survey"},
                    "status": {"type": "string"},
                    "attempt_number": {"type": "integer"},
                    "started_at": {"type": "string", "format": "date-time"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "language": {"type": "string"},
                    "progress": {"type": "object", "title": "Progress"},
                    "time_remaining": {"type": "integer"},
                    "current_question": {"type": "object", "title": "Question", "nullable": True},
                    "score": {"type": "integer", "nullable": True},
                    "total_points": {"type": "integer", "nullable": True},
                    "percentage": {"type": "number", "nullable": True},
                    "is_passed": {"type": "boolean", "nullable": True}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "non_field_errors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Maximum attempts reached. Contact moderator for permission to retake."]
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Начать опрос с параметрами",
                request_only=True,
                value={
                    "questions_count": 10,
                    "language": "ru"
                }
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a new survey session."""
        survey = self.get_object()
        
        # ВРЕМЕННО ОТКЛЮЧЕНО: Все проверки отключены для разработки фронтенда
        # TODO: Восстановить проверки после завершения разработки фронтенда
        
        # Получаем параметры из запроса напрямую, пропуская валидацию
        questions_count = request.data.get('questions_count', survey.questions_count)
        language = request.data.get('language', 'uz')
        
        with transaction.atomic():
            # Get next attempt number
            last_attempt = SurveySession.objects.filter(
                user=request.user,
                survey=survey
            ).order_by('-attempt_number').first()
            
            next_attempt = (last_attempt.attempt_number + 1) if last_attempt else 1
            
            # Create new session
            session = SurveySession.objects.create(
                user=request.user,
                survey=survey,
                attempt_number=next_attempt,
                language=language,
                status='started'
            )
            
            # Initialize questions
            session.initialize_questions(questions_count)
            
            # Update session status
            session.status = 'in_progress'
            session.save()
            
            # Update user survey history
            history, created = UserSurveyHistory.objects.get_or_create(
                user=request.user,
                survey=survey,
                defaults={
                    'total_attempts': 1,
                    'current_status': 'in_progress',
                    'last_attempt_at': timezone.now()
                }
            )
            
            if not created:
                history.total_attempts += 1
                history.current_status = 'in_progress'
                history.last_attempt_at = timezone.now()
                history.save()
            
            return Response(
                SurveySessionSerializer(session, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
    
    @extend_schema(
        summary="Моя история опросов",
        description="Получить историю прохождения опросов текущим пользователем.",
        tags=["Опросы"],
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "survey": {"type": "object"},
                        "total_attempts": {"type": "integer"},
                        "best_score": {"type": "integer", "nullable": True},
                        "best_percentage": {"type": "number", "nullable": True},
                        "last_attempt_at": {"type": "string", "format": "date-time"},
                        "is_passed": {"type": "boolean"},
                        "current_status": {"type": "string"},
                        "can_continue": {"type": "boolean"}
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def my_history(self, request):
        """Get user's survey history."""
        history = UserSurveyHistory.objects.filter(user=request.user).select_related('survey')
        serializer = UserSurveyHistorySerializer(history, many=True)
        return Response(serializer.data)


@extend_schema_view(
    retrieve=extend_schema(
        summary="Детали сессии",
        description="Получить подробную информацию о сессии прохождения опроса.",
        tags=["Сессии"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "survey": {"type": "object"},
                    "status": {"type": "string"},
                    "attempt_number": {"type": "integer"},
                    "started_at": {"type": "string", "format": "date-time"},
                    "expires_at": {"type": "string", "format": "date-time"},
                    "language": {"type": "string"},
                    "progress": {"type": "object"},
                    "time_remaining": {"type": "integer"},
                    "current_question": {"type": "object", "nullable": True},
                    "score": {"type": "integer", "nullable": True},
                    "total_points": {"type": "integer", "nullable": True},
                    "percentage": {"type": "number", "nullable": True},
                    "is_passed": {"type": "boolean", "nullable": True}
                }
            }
        }
    )
)
class SurveySessionViewSet(GenericViewSet):
    """ViewSet for survey sessions."""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SurveySessionSerializer
    
    def get_queryset(self):
        """Get user's survey sessions."""
        return SurveySession.objects.filter(user=self.request.user).order_by('-started_at')
    
    def retrieve(self, request, pk=None):
        """Get session details."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Check if session is expired
        if session.is_expired() and session.status not in ['completed', 'cancelled']:
            session.status = 'expired'
            session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Отправить ответ",
        description="""Отправить ответ на вопрос в рамках сессии.
        
        Поддерживает различные типы вопросов: один вариант, множественный выбор, открытый ответ.
        Автоматически завершает сессию при ответе на последний вопрос.""",
        tags=["Сессии"],
        request={
            "type": "object",
            "properties": {
                "question_id": {"type": "integer"},
                "choice_ids": {"type": "array", "items": {"type": "integer"}},
                "text_answer": {"type": "string"}
            },
            "required": ["question_id"]
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "session": {"type": "object", "title": "Session"},
                    "final_score": {"type": "object", "description": "Только при завершении сессии"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "non_field_errors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Session has expired"]
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Ответ один вариант",
                request_only=True,
                value={
                    "question_id": 1,
                    "choice_ids": [3]
                }
            ),
            OpenApiExample(
                name="Ответ множественный выбор",
                request_only=True,
                value={
                    "question_id": 2,
                    "choice_ids": [5, 7, 9]
                }
            ),
            OpenApiExample(
                name="Открытый ответ",
                request_only=True,
                value={
                    "question_id": 3,
                    "text_answer": "Мой развернутый ответ на вопрос"
                }
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """Submit an answer for a question."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        serializer = SubmitAnswerSerializer(
            data={
                'session_id': session.id,
                'question_id': request.data.get('question_id'),
                'choice_ids': request.data.get('choice_ids', []),
                'text_answer': request.data.get('text_answer', '')
            },
            context={'request': request}
        )
        
        if serializer.is_valid():
            with transaction.atomic():
                validated_data = serializer.validated_data
                session = validated_data['session']
                session_question = validated_data['session_question']
                question = validated_data['question']
                
                # Create or update answer
                answer, created = Answer.objects.get_or_create(
                    session=session,
                    question=question,
                    defaults={
                        'text_answer': validated_data.get('text_answer', '')
                    }
                )
                
                if not created:
                    answer.text_answer = validated_data.get('text_answer', '')
                    answer.selected_choices.clear()
                
                # Add selected choices
                if validated_data.get('choice_ids'):
                    answer.selected_choices.set(validated_data['choice_ids'])
                
                # Calculate score
                points_earned = answer.calculate_score()
                answer.save()
                
                # Update session question
                session_question.is_answered = True
                session_question.points_earned = points_earned
                session_question.save()
                
                # Check if all questions are answered
                remaining_questions = session.sessionquestion_set.filter(is_answered=False).count()
                
                if remaining_questions == 0:
                    # Complete session
                    session.status = 'completed'
                    session.completed_at = timezone.now()
                    session.save()
                    
                    # Calculate final score
                    final_score = session.calculate_final_score()
                    
                    # Update user history
                    history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
                    history.current_status = 'completed'
                    
                    if not history.best_score or session.score > history.best_score:
                        history.best_score = session.score
                        history.best_percentage = session.percentage
                    
                    if session.is_passed:
                        history.is_passed = True
                    
                    history.save()
                    
                    return Response({
                        'message': _('Survey completed'),
                        'session': SurveySessionSerializer(session, context={'request': request}).data,
                        'final_score': final_score
                    })
                
                return Response({
                    'message': _('Answer submitted successfully'),
                    'session': SurveySessionSerializer(session, context={'request': request}).data
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Отменить сессию",
        description="Отменить активную сессию прохождения опроса.",
        tags=["Сессии"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "example": "Session cancelled successfully"},
                    "session": {"type": "object", "title": "Session"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Cannot cancel this session"}
                }
            }
        }
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel active session."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        if session.status not in ['started', 'in_progress']:
            return Response(
                {'error': _('Cannot cancel this session')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'cancelled'
        session.save()
        
        # Update user history
        try:
            history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
            history.current_status = 'cancelled'
            history.save()
        except UserSurveyHistory.DoesNotExist:
            pass
        
        return Response({
            'message': _('Session cancelled successfully'),
            'session': SurveySessionSerializer(session, context={'request': request}).data
        })
    
    @extend_schema(
        summary="Прогресс сессии",
        description="""Получить детальный прогресс прохождения сессии.
        
        Возвращает информацию о всех вопросах сессии, ответах и набранных баллах.""",
        tags=["Сессии"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "progress": {"type": "object", "description": "Общий прогресс сессии"},
                    "questions": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Детальная информация по каждому вопросу"
                    },
                    "session": {"type": "object", "title": "Session"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get session progress and answered questions."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        progress = session.get_current_progress()
        
        # Get all session questions with answers
        session_questions = session.sessionquestion_set.select_related('question').order_by('order')
        questions_data = []
        
        for sq in session_questions:
            question_data = {
                'order': sq.order,
                'question_id': sq.question.id,
                'is_answered': sq.is_answered,
                'points_earned': sq.points_earned,
                'max_points': sq.question.points
            }
            
            # Add answer if exists
            try:
                answer = session.answers.get(question=sq.question)
                question_data['answer'] = AnswerSerializer(answer).data
            except Answer.DoesNotExist:
                question_data['answer'] = None
            
            questions_data.append(question_data)
        
        return Response({
            'progress': progress,
            'questions': questions_data,
            'session': SurveySessionSerializer(session, context={'request': request}).data
        })


@extend_schema(
    summary="Текущая активная сессия",
    description="""Получить информацию о текущей активной сессии пользователя.
    
    Если пользователь сейчас не проходит опрос, возвращает null.
    Автоматически проверяет срок действия сессии.""",
    tags=["Сессии"],
    responses={
        200: {
            "type": "object",
            "properties": {
                "session": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/SurveySession"},
                        {"type": "null"}
                    ],
                    "description": "Информация о сессии или null"
                }
            }
        }
    }
)
class CurrentSessionView(APIView):
    """Get user's current active session."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current active session if any."""
        active_session = SurveySession.objects.filter(
            user=request.user,
            status__in=['started', 'in_progress']
        ).select_related('survey').first()
        
        if active_session:
            # Check if expired
            if active_session.is_expired():
                active_session.status = 'expired'
                active_session.save()
                return Response({'session': None})
            
            serializer = SurveySessionSerializer(active_session, context={'request': request})
            return Response({'session': serializer.data})
        
        return Response({'session': None})
