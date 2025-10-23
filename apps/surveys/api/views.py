from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string
import requests
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

from apps.surveys.models import (
    Survey, SurveySession, SessionQuestion, Answer, UserSurveyHistory,
    FaceVerification, SessionRecording, ProctorReview
)
from .serializers import (
    SurveyListSerializer, SurveyDetailSerializer, StartSurveySerializer,
    SurveySessionSerializer, SubmitAnswerSerializer, AnswerSerializer,
    UserSurveyHistorySerializer, SessionQuestionSerializer, CertificateDataSerializer,
    FaceVerificationSerializer, SessionRecordingSerializer, ProctorReviewSerializer
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
    list=extend_schema(
        summary="Список сессий",
        description="Получить список всех сессий прохождения опросов текущим пользователем.",
        tags=["Сессии"],
        responses={
            200: SurveySessionSerializer(many=True)
        }
    ),
    retrieve=extend_schema(
        summary="Детали сессии",
        description="Получить подробную информацию о сессии прохождения опроса.",
        tags=["Сессии"],
        responses={
            200: SurveySessionSerializer
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
    
    def list(self, request):
        """Get all user's survey sessions."""
        sessions = self.get_queryset()
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)
    
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
        summary="Отправить/обновить ответ",
        description="""Отправить ответ на вопрос в рамках сессии.
        
        Поддерживает различные типы вопросов: один вариант, множественный выбор, открытый ответ.
        Позволяет обновлять уже данные ответы, если пользователь передумал.
        Автоматически завершает сессию при ответе на последний вопрос.
        Поддерживает принудительное завершение опроса.""",
        tags=["Сессии"],
        request={
            "type": "object",
            "properties": {
                "question_id": {"type": "integer"},
                "choice_ids": {"type": "array", "items": {"type": "integer"}},
                "text_answer": {"type": "string"},
                "force_finish": {"type": "boolean", "description": "Принудительно завершить опрос после этого ответа"}
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
            ),
            OpenApiExample(
                name="Обновление ответа",
                request_only=True,
                value={
                    "question_id": 1,
                    "choice_ids": [4]  # Изменен выбор с [3] на [4]
                }
            ),
            OpenApiExample(
                name="Принудительное завершение",
                request_only=True,
                value={
                    "question_id": 5,
                    "choice_ids": [2],
                    "force_finish": True
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
                'text_answer': request.data.get('text_answer', ''),
                'force_finish': request.data.get('force_finish', False)
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
                    # Update existing answer
                    answer.text_answer = validated_data.get('text_answer', '')
                    answer.selected_choices.clear()
                else:
                    # New answer
                    answer.text_answer = validated_data.get('text_answer', '')
                
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
                
                # Check if user wants to force finish or all questions are answered
                force_finish = validated_data.get('force_finish', False)
                remaining_questions = session.sessionquestion_set.filter(is_answered=False).count()
                
                if force_finish or remaining_questions == 0:
                    # Complete session
                    session.status = 'completed'
                    session.completed_at = timezone.now()
                    session.save()
                    
                    # Calculate final score
                    final_score = session.calculate_final_score()
                    
                    # Update user history
                    try:
                        history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
                        history.current_status = 'completed'
                        
                        if not history.best_score or session.score > history.best_score:
                            history.best_score = session.score
                            history.best_percentage = session.percentage
                        
                        if session.is_passed:
                            history.is_passed = True
                        
                        history.save()
                    except UserSurveyHistory.DoesNotExist:
                        pass
                    
                    # Get completion statistics
                    total_questions = session.sessionquestion_set.count()
                    answered_questions = session.sessionquestion_set.filter(is_answered=True).count()
                    completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
                    
                    completion_stats = {
                        'total_questions': total_questions,
                        'answered_questions': answered_questions,
                        'unanswered_questions': remaining_questions,
                        'completion_percentage': round(completion_percentage, 2)
                    }
                    
                    message = _('Survey completed') if remaining_questions == 0 else _('Survey finished by user request')
                    return Response({
                        'message': message,
                        'session': SurveySessionSerializer(session, context={'request': request}).data,
                        'final_score': final_score,
                        'completion_stats': completion_stats
                    })
                
                message = _('Answer updated successfully') if not created else _('Answer submitted successfully')
                return Response({
                    'message': message,
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
        summary="Завершить опрос",
        description="""Принудительно завершить опрос и рассчитать финальный результат.
        
        Завершает сессию независимо от количества отвеченных вопросов.
        Рассчитывает финальный балл на основе отвеченных вопросов.
        Обновляет историю пользователя.""",
        tags=["Сессии"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "example": "Survey finished successfully"},
                    "session": {"type": "object", "title": "Session"},
                    "final_score": {"type": "object", "description": "Финальный результат опроса"},
                    "completion_stats": {
                        "type": "object",
                        "properties": {
                            "total_questions": {"type": "integer", "description": "Общее количество вопросов"},
                            "answered_questions": {"type": "integer", "description": "Количество отвеченных вопросов"},
                            "unanswered_questions": {"type": "integer", "description": "Количество неотвеченных вопросов"},
                            "completion_percentage": {"type": "number", "description": "Процент завершения"}
                        }
                    }
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Cannot finish this session"}
                }
            }
        }
    )
    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        """Finish survey session and calculate final results."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Check if session can be finished
        if session.status not in ['started', 'in_progress']:
            return Response(
                {'error': _('Cannot finish this session')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Mark all unanswered questions as skipped (optional)
            # This could be useful for analytics
            unanswered_questions = session.sessionquestion_set.filter(is_answered=False)
            unanswered_count = unanswered_questions.count()
            
            # Complete the session
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            
            # Calculate final score based on answered questions
            final_score = session.calculate_final_score()
            
            # Get completion statistics
            total_questions = session.sessionquestion_set.count()
            answered_questions = session.sessionquestion_set.filter(is_answered=True).count()
            completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Update user history
            try:
                history = UserSurveyHistory.objects.get(user=request.user, survey=session.survey)
                history.current_status = 'completed'
                
                # Update best score if current is better
                if not history.best_score or session.score > history.best_score:
                    history.best_score = session.score
                    history.best_percentage = session.percentage
                
                # Mark as passed if score meets requirements
                if session.is_passed:
                    history.is_passed = True
                
                history.save()
            except UserSurveyHistory.DoesNotExist:
                pass
            
            completion_stats = {
                'total_questions': total_questions,
                'answered_questions': answered_questions,
                'unanswered_questions': unanswered_count,
                'completion_percentage': round(completion_percentage, 2)
            }
            
            return Response({
                'message': _('Survey finished successfully'),
                'session': SurveySessionSerializer(session, context={'request': request}).data,
                'final_score': final_score,
                'completion_stats': completion_stats
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
        summary="Получить вопрос по номеру",
        description="""Получить конкретный вопрос сессии по его порядковому номеру.
        
        Возвращает вопрос с возможностью навигации к предыдущему и следующему вопросу.""",
        tags=["Сессии"],
        parameters=[
            OpenApiParameter(
                name='order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Порядковый номер вопроса',
                required=True
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "question": {"type": "object", "description": "Информация о вопросе"},
                    "navigation": {
                        "type": "object",
                        "properties": {
                            "has_previous": {"type": "boolean"},
                            "has_next": {"type": "boolean"},
                            "previous_order": {"type": "integer", "nullable": True},
                            "next_order": {"type": "integer", "nullable": True}
                        }
                    },
                    "answer": {
                        "type": "object", 
                        "nullable": True,
                        "description": "Ответ пользователя на этот вопрос (если есть)"
                    }
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Question not found"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def get_question(self, request, pk=None):
        """Get specific question by order number."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        order = request.query_params.get('order')
        
        if not order:
            return Response(
                {'error': _('Order parameter is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = int(order)
        except ValueError:
            return Response(
                {'error': _('Invalid order parameter')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session_question = session.get_question_by_order(order)
        if not session_question:
            return Response(
                {'error': _('Question not found')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get navigation info
        previous_question = session.get_previous_question(order)
        next_question = session.get_next_question(order)
        
        # Get answer if exists
        try:
            answer = session.answers.get(question=session_question.question)
            answer_data = AnswerSerializer(answer).data
        except Answer.DoesNotExist:
            answer_data = None
        
        # Serialize question with language context
        question_data = SessionQuestionSerializer(
            session_question, 
            context={'language': session.language}
        ).data
        
        navigation_data = {
            'has_previous': previous_question is not None,
            'has_next': next_question is not None,
            'previous_order': previous_question.order if previous_question else None,
            'next_order': next_question.order if next_question else None
        }
        
        return Response({
            'question': question_data,
            'navigation': navigation_data,
            'answer': answer_data
        })
    
    @extend_schema(
        summary="Обновить ответ",
        description="""Обновить уже данный ответ на вопрос.
        
        Доступно только для активных сессий и отвеченных вопросов.
        Альтернативно можно использовать submit_answer для обновления ответов.""",
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
                    "answer": {"type": "object"},
                    "session": {"type": "object"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        }
    )
    @action(detail=True, methods=['post'])
    def modify_answer(self, request, pk=None):
        """Modify existing answer for a question."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        question_id = request.data.get('question_id')
        
        if not question_id:
            return Response(
                {'error': _('Question ID is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if can modify answer
        if not session.can_modify_answer(question_id):
            return Response(
                {'error': _('Cannot modify this answer')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get existing answer
        try:
            answer = session.answers.get(question_id=question_id)
        except Answer.DoesNotExist:
            return Response(
                {'error': _('Answer not found')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update answer
        if 'choice_ids' in request.data:
            answer.selected_choices.clear()
            if request.data['choice_ids']:
                answer.selected_choices.set(request.data['choice_ids'])
        
        if 'text_answer' in request.data:
            answer.text_answer = request.data['text_answer']
        
        # Recalculate score
        points_earned = answer.calculate_score()
        answer.save()
        
        # Update session question
        session_question = session.sessionquestion_set.get(question_id=question_id)
        session_question.points_earned = points_earned
        session_question.save()
        
        return Response({
            'message': _('Answer updated successfully'),
            'answer': AnswerSerializer(answer).data,
            'session': SurveySessionSerializer(session, context={'request': request}).data
        })
    
    @extend_schema(
        summary="Все ответы пользователя",
        description="""Получить все вопросы сессии с ответами пользователя.
        
        Возвращает список всех вопросов с информацией об ответах и заработанных баллах.""",
        tags=["Сессии"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "object", "description": "Информация о вопросе"},
                                "answer": {
                                    "type": "object", 
                                    "nullable": True,
                                    "description": "Ответ пользователя"
                                },
                                "points_earned": {"type": "number", "description": "Заработанные баллы"},
                                "max_points": {"type": "number", "description": "Максимальные баллы"}
                            }
                        }
                    },
                    "total_points": {"type": "number", "description": "Общее количество заработанных баллов"},
                    "max_total_points": {"type": "number", "description": "Максимально возможные баллы"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def all_answers(self, request, pk=None):
        """Get all questions with user answers for the session."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Get all session questions with answers
        session_questions = session.sessionquestion_set.select_related('question').prefetch_related(
            'question__choices'
        ).order_by('order')
        
        questions_data = []
        total_points = 0
        max_total_points = 0
        
        for session_question in session_questions:
            # Get answer if exists
            try:
                answer = session.answers.get(question=session_question.question)
                answer_data = AnswerSerializer(answer).data
            except Answer.DoesNotExist:
                answer_data = None
            
            # Serialize question with language context
            question_data = SessionQuestionSerializer(
                session_question, 
                context={'language': session.language}
            ).data
            
            questions_data.append({
                'question': question_data,
                'answer': answer_data,
                'points_earned': session_question.points_earned or 0,
                'max_points': session_question.question.points or 0
            })
            
            total_points += session_question.points_earned or 0
            max_total_points += session_question.question.points or 0
        
        return Response({
            'questions': questions_data,
            'total_points': total_points,
            'max_total_points': max_total_points
        })
    
    @extend_schema(
        summary="Следующий вопрос по порядку",
        description="""Получить следующий вопрос в сессии по порядковому номеру.
        
        Возвращает следующий вопрос по порядку, независимо от того, отвечен он или нет.""",
        tags=["Сессии"],
        parameters=[
            OpenApiParameter(
                name='current_order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Порядковый номер текущего вопроса',
                required=True
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "question": {"type": "object", "description": "Информация о следующем вопросе"},
                    "answer": {
                        "type": "object", 
                        "nullable": True,
                        "description": "Ответ пользователя на этот вопрос (если есть)"
                    }
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "No next question"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def next_question_by_order(self, request, pk=None):
        """Get next question in the session by order."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        current_order = request.query_params.get('current_order')
        
        if not current_order:
            return Response(
                {'error': _('Current order parameter is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            current_order = int(current_order)
        except ValueError:
            return Response(
                {'error': _('Invalid current order parameter')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        next_question = session.get_next_question(current_order)
        if not next_question:
            return Response(
                {'error': _('No next question')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get answer if exists
        try:
            answer = session.answers.get(question=next_question.question)
            answer_data = AnswerSerializer(answer).data
        except Answer.DoesNotExist:
            answer_data = None
        
        # Serialize question with language context
        question_data = SessionQuestionSerializer(
            next_question, 
            context={'language': session.language}
        ).data
        
        return Response({
            'question': question_data,
            'answer': answer_data
        })
    
    @extend_schema(
        summary="Предыдущий вопрос",
        description="""Получить предыдущий вопрос в сессии.
        
        Возвращает предыдущий вопрос по порядку, независимо от того, отвечен он или нет.""",
        tags=["Сессии"],
        parameters=[
            OpenApiParameter(
                name='current_order',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Порядковый номер текущего вопроса',
                required=True
            )
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "question": {"type": "object", "description": "Информация о предыдущем вопросе"},
                    "answer": {
                        "type": "object", 
                        "nullable": True,
                        "description": "Ответ пользователя на этот вопрос (если есть)"
                    }
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "No previous question"}
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def previous_question(self, request, pk=None):
        """Get previous question in the session."""
        session = get_object_or_404(self.get_queryset(), pk=pk)
        current_order = request.query_params.get('current_order')
        
        if not current_order:
            return Response(
                {'error': _('Current order parameter is required')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            current_order = int(current_order)
        except ValueError:
            return Response(
                {'error': _('Invalid current order parameter')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        previous_question = session.get_previous_question(current_order)
        if not previous_question:
            return Response(
                {'error': _('No previous question')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get answer if exists
        try:
            answer = session.answers.get(question=previous_question.question)
            answer_data = AnswerSerializer(answer).data
        except Answer.DoesNotExist:
            answer_data = None
        
        # Serialize question with language context
        question_data = SessionQuestionSerializer(
            previous_question, 
            context={'language': session.language}
        ).data
        
        return Response({
            'question': question_data,
            'answer': answer_data
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
                    "allOf": [
                        {"$ref": "#/components/schemas/SurveySession"}
                    ],
                    "nullable": True,
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


from django.views import View
from django.http import HttpResponse
import requests
import time
import logging

logger = logging.getLogger(__name__)


class DownloadCertificatePDFView(View):
    """Download PDF certificate from HTML page using Gotenberg."""
    
    def get(self, request, session_id, *args, **kwargs):
        """Generate and download PDF certificate for survey session."""
        from apps.surveys.models import SurveySession
        
        try:
            # Get session with related data
            session = SurveySession.objects.select_related(
                'user', 'survey'
            ).get(id=session_id)
        except SurveySession.DoesNotExist:
            return HttpResponse(
                '{"error": "Session not found"}', 
                content_type="application/json", 
                status=404
            )
        
        # Check permissions - user can only access their own certificates
        # or moderators can access any certificate
        if not request.user.is_authenticated:
            return HttpResponse(
                '{"error": "Authentication required"}', 
                content_type="application/json", 
                status=401
            )
        
        if not (request.user == session.user or request.user.is_moderator):
            return HttpResponse(
                '{"error": "Access denied"}', 
                content_type="application/json", 
                status=403
            )
        
        # Check if session is completed
        if session.status != 'completed':
            return HttpResponse(
                '{"error": "Certificate can only be generated for completed sessions"}', 
                content_type="application/json", 
                status=400
            )
        
        # Construct certificate URL - используем базовый URL из настроек или дефолтный
        from django.conf import settings
        base_url = getattr(settings, 'CERTIFICATE_BASE_URL', 'https://savollar.leetcode.uz')
        if not base_url.endswith('/'):
            base_url += '/'
        
        certificate_url = f"{base_url}certificate/{session_id}"
        
        # Prepare data for Gotenberg
        gotenberg_url = "http://gotenberg:3000/forms/chromium/convert/url"
        
        # Options for PDF generation - using multipart/form-data
        # Need at least one file to trigger multipart/form-data content type
        files = {"dummy": ("", "", "text/plain")}
        data = {
            "url": certificate_url,
            "marginTop": "0",
            "marginBottom": "0", 
            "marginLeft": "0",
            "marginRight": "0",
            "format": "A4",
            "landscape": "true",
            "waitTimeout": "10s",
            "waitForSelector": "body",
        }
        
        try:
            # Give the certificate page time to fully render on the frontend
            time.sleep(4)
            logger.info(f"Converting certificate to PDF: {certificate_url}")
            
            # Send request to Gotenberg with multipart/form-data
            response = requests.post(
                gotenberg_url, 
                data=data,
                files=files,
                timeout=60
            )
            response.raise_for_status()
            
            # Get PDF content from Gotenberg response
            pdf_content = response.content
            
            # Return PDF file for download
            http_response = HttpResponse(pdf_content, content_type="application/pdf")
            http_response["Content-Disposition"] = f'attachment; filename="certificate_{session.user.name}_{session.survey.title}.pdf"'
            return http_response
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout when converting certificate to PDF: {certificate_url}")
            return HttpResponse(
                '{"error": "Timeout: Certificate page took too long to load"}', 
                content_type="application/json", 
                status=500
            )
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when connecting to Gotenberg")
            return HttpResponse(
                '{"error": "Error generating PDF: Cannot connect to PDF service"}', 
                content_type="application/json", 
                status=500
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when converting certificate to PDF: {str(e)}")
            return HttpResponse(
                f'{{"error": "Error generating PDF: {str(e)}"}}', 
                content_type="application/json", 
                status=500
            )
        except Exception as e:
            logger.error(f"Unexpected error when converting certificate to PDF: {str(e)}")
            return HttpResponse(
                f'{{"error": "Unexpected error: {str(e)}"}}', 
                content_type="application/json", 
                status=500
            )


@extend_schema(
    summary="Получить данные сертификата",
    description="""Получить данные сертификата для завершенной сессии опроса.
    
    Возвращает информацию о пользователе, опросе и результатах для отображения на фронтенде.""",
    tags=["Сертификаты"],
    parameters=[
        OpenApiParameter(
            name='session_id',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='UUID сессии опроса',
            required=True
        )
    ],
    responses={
        200: {
            "description": "Данные сертификата",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "certificate_order": {"type": "integer", "description": "Порядковый номер сертификата"},
                            "attempt_number": {"type": "integer"},
                            "user_name": {"type": "string", "description": "ФИО пользователя"},
                            "user_branch": {"type": "string", "description": "Филиал пользователя"},
                            "user_position": {"type": "string", "description": "Должность пользователя"},
                            "user_work_domain": {"type": "string", "description": "Домен работы пользователя"},
                            "user_employee_level": {"type": "string", "description": "Уровень сотрудника"},
                            "survey_title": {"type": "string", "description": "Название опроса"},
                            "survey_description": {"type": "string", "description": "Описание опроса"},
                            "score": {"type": "integer", "description": "Получено баллов"},
                            "total_points": {"type": "integer", "description": "Максимум баллов"},
                            "percentage": {"type": "number", "description": "Процент выполнения"},
                            "is_passed": {"type": "boolean", "description": "Пройден ли опрос"},
                            "started_at": {"type": "string", "format": "date-time"},
                            "completed_at": {"type": "string", "format": "date-time"},
                            "duration_minutes": {"type": "integer", "description": "Время выполнения в минутах"},
                            "language": {"type": "string", "description": "Язык опроса"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Сессия не найдена",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "Session not found"}
                        }
                    }
                }
            }
        },
        403: {
            "description": "Нет доступа к данным сертификата",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "Access denied"}
                        }
                    }
                }
            }
        }
    }
)
class GetCertificateDataView(APIView):
    """Get certificate data for completed survey session."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, session_id, *args, **kwargs):
        """Get certificate data for survey session."""
        try:
            # Get session with related data
            session = SurveySession.objects.select_related(
                'user', 'survey'
            ).get(id=session_id)
        except SurveySession.DoesNotExist:
            return Response(
                {'error': _('Session not found')}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - user can only access their own certificates
        # or moderators can access any certificate
        if not (request.user == session.user or request.user.is_moderator):
            return Response(
                {'error': _('Access denied')}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if session is completed
        if session.status != 'completed':
            return Response(
                {'error': _('Certificate data is only available for completed sessions')}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize certificate data
        serializer = CertificateDataSerializer(session)
        return Response(serializer.data)


@extend_schema(
    summary="Получить данные сертификата по UUID пользователя",
    description="""Получить данные сертификата для пользователя по его UUID.
    
    Возвращает информацию о сессии с наивысшим баллом у пользователя.""",
    tags=["Сертификаты"],
    parameters=[
        OpenApiParameter(
            name='user_uuid',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='UUID пользователя',
            required=True
        )
    ],
    responses={
        200: {
            "description": "Данные сертификата",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "certificate_order": {"type": "integer", "description": "Порядковый номер сертификата"},
                            "attempt_number": {"type": "integer"},
                            "user_name": {"type": "string", "description": "ФИО пользователя"},
                            "user_branch": {"type": "string", "description": "Филиал пользователя"},
                            "user_position": {"type": "string", "description": "Должность пользователя"},
                            "user_work_domain": {"type": "string", "description": "Домен работы пользователя"},
                            "user_employee_level": {"type": "string", "description": "Уровень сотрудника"},
                            "survey_title": {"type": "string", "description": "Название опроса"},
                            "survey_description": {"type": "string", "description": "Описание опроса"},
                            "score": {"type": "integer", "description": "Получено баллов"},
                            "total_points": {"type": "integer", "description": "Максимум баллов"},
                            "percentage": {"type": "number", "description": "Процент выполнения"},
                            "is_passed": {"type": "boolean", "description": "Пройден ли опрос"},
                            "started_at": {"type": "string", "format": "date-time"},
                            "completed_at": {"type": "string", "format": "date-time"},
                            "duration_minutes": {"type": "integer", "description": "Время выполнения в минутах"},
                            "language": {"type": "string", "description": "Язык опроса"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Пользователь не найден или нет сессий",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "User not found or no sessions available"}
                        }
                    }
                }
            }
        }
    }
)
class GetUserCertificateDataView(APIView):
    """Get certificate data for user by UUID - returns session with highest score."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_uuid, *args, **kwargs):
        """Get certificate data for user's best session."""
        from apps.users.models import User
        
        try:
            # Get user by UUID
            user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            return Response(
                {'error': _('User not found')}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get session with highest score for this user
        session = SurveySession.objects.filter(
            user=user,
            score__isnull=False  # Only sessions with scores
        ).order_by('-score', '-completed_at').first()
        
        if not session:
            return Response(
                {'error': _('No completed sessions found for this user')}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize certificate data
        serializer = CertificateDataSerializer(session)
        return Response(serializer.data)


@extend_schema(
    summary="Скачать PDF сертификат по UUID пользователя",
    description="""Скачать PDF сертификат для пользователя по его UUID.
    
    Генерирует сертификат для сессии с наивысшим баллом у пользователя.""",
    tags=["Сертификаты"],
    parameters=[
        OpenApiParameter(
            name='user_uuid',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='UUID пользователя',
            required=True
        )
    ],
    responses={
        200: {
            "description": "PDF сертификат",
            "content": {
                "application/pdf": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        404: {
            "description": "Пользователь не найден или нет сессий",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "User not found or no sessions available"}
                        }
                    }
                }
            }
        }
    }
)
class DownloadUserCertificatePDFView(View):
    """Download PDF certificate for user by UUID - generates certificate for session with highest score."""
    
    def get(self, request, user_uuid, *args, **kwargs):
        """Generate and download PDF certificate for user's best session."""
        from apps.users.models import User
        
        try:
            # Get user by UUID
            user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            return HttpResponse(
                '{"error": "User not found"}', 
                content_type="application/json", 
                status=404
            )
        
        # Get session with highest score for this user
        session = SurveySession.objects.filter(
            user=user,
            score__isnull=False  # Only sessions with scores
        ).order_by('-score', '-completed_at').first()
        
        if not session:
            return HttpResponse(
                '{"error": "No completed sessions found for this user"}', 
                content_type="application/json", 
                status=404
            )
        
        # Construct certificate URL
        from django.conf import settings
        base_url = getattr(settings, 'CERTIFICATE_BASE_URL', 'https://savollar.leetcode.uz')
        if not base_url.endswith('/'):
            base_url += '/'
        
        certificate_url = f"{base_url}certificate/{session.id}"
        
        # Prepare data for Gotenberg
        gotenberg_url = "http://gotenberg:3000/forms/chromium/convert/url"
        
        # Options for PDF generation - using multipart/form-data
        # Need at least one file to trigger multipart/form-data content type
        files = {"dummy": ("", "", "text/plain")}
        data = {
            "url": certificate_url,
            "marginTop": "0",
            "marginBottom": "0", 
            "marginLeft": "0",
            "marginRight": "0",
            "format": "A4",
            "landscape": "true",
            "waitTimeout": "10s",
            "waitForSelector": "body",
        }
        
        try:
            # Give the certificate page time to fully render on the frontend
            time.sleep(4)
            logger.info(f"Converting user certificate to PDF: {certificate_url}")
            
            # Send request to Gotenberg with multipart/form-data
            response = requests.post(
                gotenberg_url, 
                data=data,
                files=files,
                timeout=60
            )
            response.raise_for_status()
            
            # Get PDF content from Gotenberg response
            pdf_content = response.content
            
            # Return PDF file for download
            http_response = HttpResponse(pdf_content, content_type="application/pdf")
            http_response["Content-Disposition"] = f'attachment; filename="certificate_{user.name}_{session.survey.title}.pdf"'
            return http_response
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout when converting user certificate to PDF: {certificate_url}")
            return HttpResponse(
                '{"error": "Timeout: Certificate page took too long to load"}', 
                content_type="application/json", 
                status=500
            )
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when connecting to Gotenberg")
            return HttpResponse(
                '{"error": "Error generating PDF: Cannot connect to PDF service"}', 
                content_type="application/json", 
                status=500
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when converting user certificate to PDF: {str(e)}")
            return HttpResponse(
                f'{{"error": "Error generating PDF: {str(e)}"}}', 
                content_type="application/json", 
                status=500
            )
        except Exception as e:
            logger.error(f"Unexpected error when converting user certificate to PDF: {str(e)}")
            return HttpResponse(
                f'{{"error": "Unexpected error: {str(e)}"}}', 
                content_type="application/json", 
                status=500
            )


@extend_schema_view(
    tags=["Proctoring"]
)
class ProctorViewSet(GenericViewSet):
    """ViewSet for proctoring functionality."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Verify initial face",
        description="Verify and store user's face at the start of survey session.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "format": "uuid"},
                    "face_image": {"type": "string", "format": "binary"}
                },
                "required": ["session_id", "face_image"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "verified"},
                    "session_id": {"type": "string", "format": "uuid"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='verify-initial')
    def verify_initial_face(self, request):
        """Verify face at the start of session."""
        session_id = request.data.get('session_id')
        face_image = request.FILES.get('face_image')
        
        if not session_id or not face_image:
            return Response(
                {'error': 'session_id and face_image are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = get_object_or_404(SurveySession, id=session_id, user=request.user)
        
        # Save reference image
        session.face_reference_image = face_image
        session.initial_face_verified = True
        session.save()
        
        return Response({
            'status': 'verified',
            'session_id': str(session.id)
        })
    
    @extend_schema(
        summary="Record violation",
        description="Record a proctoring violation during survey session.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "format": "uuid"},
                    "violation_type": {"type": "string", "example": "no_face"},
                    "snapshot": {"type": "string", "format": "binary"},
                    "face_count": {"type": "integer"},
                    "confidence_score": {"type": "number"}
                },
                "required": ["session_id", "violation_type"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "violation_id": {"type": "integer"},
                    "total_violations": {"type": "integer"},
                    "flagged_for_review": {"type": "boolean"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='record-violation')
    def record_violation(self, request):
        """Record a proctoring violation."""
        session_id = request.data.get('session_id')
        violation_type = request.data.get('violation_type')
        snapshot = request.FILES.get('snapshot')
        
        if not session_id or not violation_type:
            return Response(
                {'error': 'session_id and violation_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = get_object_or_404(SurveySession, id=session_id, user=request.user)
        
        # Prepare metadata
        metadata = {
            'face_detected': request.data.get('face_detected', False),
            'face_count': int(request.data.get('face_count', 0)),
            'confidence_score': float(request.data.get('confidence_score')) if request.data.get('confidence_score') else None,
            'looking_at_screen': request.data.get('looking_at_screen', True),
            'mobile_device_detected': request.data.get('mobile_detected', False)
        }
        
        violation = session.record_violation(
            violation_type=violation_type,
            snapshot=snapshot,
            metadata=metadata
        )
        
        return Response({
            'violation_id': violation.id,
            'total_violations': session.violations_count,
            'flagged_for_review': session.flagged_for_review
        })
    
    @extend_schema(
        summary="Proctoring heartbeat",
        description="Regular heartbeat with face verification status (every 5 seconds).",
        request={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "format": "uuid"},
                "face_data": {
                    "type": "object",
                    "properties": {
                        "face_detected": {"type": "boolean"},
                        "face_count": {"type": "integer"},
                        "confidence": {"type": "number"},
                        "looking_at_screen": {"type": "boolean"},
                        "mobile_detected": {"type": "boolean"}
                    }
                }
            },
            "required": ["session_id", "face_data"]
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "ok"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='heartbeat')
    def proctoring_heartbeat(self, request):
        """Regular heartbeat with face verification status."""
        session_id = request.data.get('session_id')
        face_data = request.data.get('face_data', {})
        
        if not session_id:
            return Response(
                {'error': 'session_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = get_object_or_404(SurveySession, id=session_id, user=request.user)
        
        # Create verification record
        FaceVerification.objects.create(
            session=session,
            face_detected=face_data.get('face_detected', False),
            face_count=face_data.get('face_count', 0),
            confidence_score=face_data.get('confidence'),
            looking_at_screen=face_data.get('looking_at_screen', True),
            mobile_device_detected=face_data.get('mobile_detected', False)
        )
        
        return Response({'status': 'ok'})
    
    @extend_schema(
        summary="Upload recording",
        description="Upload full session video recording.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "format": "uuid"},
                    "video": {"type": "string", "format": "binary"},
                    "duration_seconds": {"type": "integer"}
                },
                "required": ["session_id", "video", "duration_seconds"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "recording_id": {"type": "integer"},
                    "status": {"type": "string", "example": "uploaded"}
                }
            }
        }
    )
    @action(detail=False, methods=['post'], url_path='upload-recording')
    def upload_recording(self, request):
        """Upload full session recording."""
        session_id = request.data.get('session_id')
        video_file = request.FILES.get('video')
        duration = request.data.get('duration_seconds')
        
        if not session_id or not video_file or not duration:
            return Response(
                {'error': 'session_id, video, and duration_seconds are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session = get_object_or_404(SurveySession, id=session_id, user=request.user)
        
        recording = SessionRecording.objects.create(
            session=session,
            video_file=video_file,
            file_size=video_file.size,
            duration_seconds=int(duration),
            total_violations=session.violations_count
        )
        
        return Response({
            'recording_id': recording.id,
            'status': 'uploaded'
        })
