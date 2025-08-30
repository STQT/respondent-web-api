from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Max, Avg
from django.db import transaction
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

from apps.users.models import User
from apps.surveys.models import Survey, SurveySession, UserSurveyHistory
from apps.surveys.permissions import IsModeratorPermission, IsSuperUserOrModeratorPermission
from .moderator_serializers import (
    ModeratorUserListSerializer,
    ModeratorUserDetailSerializer, 
    ModeratorUserOverviewSerializer,
    RetakePermissionSerializer,
    SurveyStatisticsSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Список пользователей (модератор)",
        description="""Получить список всех пользователей с возможностью фильтрации и поиска.
        
        Доступно только модераторам и администраторам.""",
        tags=["Модераторы"],
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Поиск по имени или номеру телефона'
            ),
            OpenApiParameter(
                name='branch',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по филиалу'
            ),
            OpenApiParameter(
                name='position',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по должности'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Фильтр по статусу',
                enum=['active', 'completed', 'never_started']
            )
        ],
        responses={200: "ModeratorUserListSerializer"}
    ),
    retrieve=extend_schema(
        summary="Детали пользователя (модератор)",
        description="Получить подробную информацию о пользователе с историей опросов.",
        tags=["Модераторы"],
        responses={200: "ModeratorUserDetailSerializer"}
    )
)
class ModeratorUserViewSet(ReadOnlyModelViewSet):
    """ViewSet for moderator user management."""
    
    permission_classes = [IsModeratorPermission]
    
    def get_queryset(self):
        """Get users queryset with search filtering."""
        queryset = User.objects.filter(is_superuser=False).order_by('-date_joined')
        
        # Search by name, phone number
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone_number__icontains=search)
            )
        
        # Filter by branch
        branch = self.request.query_params.get('branch', '')
        if branch:
            queryset = queryset.filter(branch__icontains=branch)
        
        # Filter by position
        position = self.request.query_params.get('position', '')
        if position:
            queryset = queryset.filter(position__icontains=position)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', '')
        if status_filter:
            if status_filter == 'active':
                # Users with active sessions
                active_user_ids = SurveySession.objects.filter(
                    status__in=['started', 'in_progress']
                ).values_list('user_id', flat=True)
                queryset = queryset.filter(id__in=active_user_ids)
            elif status_filter == 'completed':
                # Users with completed sessions
                completed_user_ids = SurveySession.objects.filter(
                    status='completed'
                ).values_list('user_id', flat=True)
                queryset = queryset.filter(id__in=completed_user_ids)
            elif status_filter == 'never_started':
                # Users who never started any survey
                started_user_ids = SurveySession.objects.values_list('user_id', flat=True)
                queryset = queryset.exclude(id__in=started_user_ids)
        
        return queryset
    
    def get_serializer_class(self):
        """Get appropriate serializer class."""
        if self.action == 'list':
            return ModeratorUserListSerializer
        return ModeratorUserDetailSerializer
    
    @extend_schema(
        summary="Обзор пользователей",
        description="Получить краткий обзор всех пользователей для панели модератора.",
        tags=["Модераторы"],
        responses={200: "ModeratorUserOverviewSerializer"}
    )
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get users overview for moderator dashboard."""
        queryset = self.get_queryset()
        serializer = ModeratorUserOverviewSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Разрешить повторное прохождение",
        description="""Предоставить пользователю разрешение на повторное прохождение опроса.
        
        Используется когда пользователь исчерпал лимит попыток.""",
        tags=["Модераторы"],
        request="RetakePermissionSerializer",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "example": "Retake permission granted successfully"},
                    "user": {"type": "string", "example": "Иван Иванов"},
                    "survey_id": {"type": "integer", "example": 1},
                    "reason": {"type": "string", "example": "Технические проблемы"}
                }
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "No sessions found for this user and survey"}
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Разрешение на повтор",
                request_only=True,
                value={
                    "survey_id": 1,
                    "reason": "Технические проблемы во время прохождения"
                }
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def grant_retake(self, request, pk=None):
        """Grant retake permission to user for specific survey."""
        user = self.get_object()
        
        serializer = RetakePermissionSerializer(data=request.data)
        if serializer.is_valid():
            survey_id = serializer.validated_data['survey_id']
            reason = serializer.validated_data.get('reason', '')
            
            # Find the last session for this user and survey
            last_session = SurveySession.objects.filter(
                user=user,
                survey_id=survey_id
            ).order_by('-started_at').first()
            
            if last_session:
                # Grant retake permission
                last_session.can_retake = True
                last_session.retake_reason = reason
                last_session.retake_granted_by = request.user
                last_session.save()
                
                return Response({
                    'message': _('Retake permission granted successfully'),
                    'user': user.name,
                    'survey_id': survey_id,
                    'reason': reason
                })
            else:
                return Response(
                    {'error': _('No sessions found for this user and survey')},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="История опросов пользователя",
        description="""Получить детальную историю прохождения опросов конкретным пользователем.
        
        Включает все ответы, баллы и статистику по каждой сессии.""",
        tags=["Модераторы"],
        parameters=[
            OpenApiParameter(
                name='survey_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Фильтр по ID опроса (опционально)'
            )
        ],
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "survey": {"type": "object"},
                        "attempt_number": {"type": "integer"},
                        "status": {"type": "string"},
                        "score": {"type": "integer"},
                        "percentage": {"type": "number"},
                        "answers": {"type": "array"}
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def survey_history(self, request, pk=None):
        """Get detailed survey history for specific user."""
        user = self.get_object()
        survey_id = request.query_params.get('survey_id')
        
        sessions_query = SurveySession.objects.filter(user=user).select_related('survey')
        
        if survey_id:
            sessions_query = sessions_query.filter(survey_id=survey_id)
        
        sessions = sessions_query.order_by('-started_at')
        
        history = []
        for session in sessions:
            duration = None
            if session.completed_at and session.started_at:
                delta = session.completed_at - session.started_at
                duration = int(delta.total_seconds() / 60)
            
            # Get detailed answers
            answers = []
            for answer in session.answers.select_related('question').prefetch_related('selected_choices'):
                answer_data = {
                    'question_id': answer.question.id,
                    'question_text': answer.question.get_text('ru'),  # Default to Russian
                    'question_type': answer.question.question_type,
                    'points_earned': answer.points_earned,
                    'max_points': answer.question.points,
                    'is_correct': answer.is_correct,
                    'text_answer': answer.text_answer,
                    'selected_choices': [
                        {
                            'id': choice.id,
                            'text': choice.get_text('ru'),
                            'is_correct': choice.is_correct
                        }
                        for choice in answer.selected_choices.all()
                    ]
                }
                answers.append(answer_data)
            
            history.append({
                'id': session.id,
                'survey': {
                    'id': session.survey.id,
                    'title': session.survey.title
                },
                'attempt_number': session.attempt_number,
                'status': session.status,
                'score': session.score,
                'total_points': session.total_points,
                'percentage': float(session.percentage) if session.percentage else None,
                'is_passed': session.is_passed,
                'started_at': session.started_at,
                'completed_at': session.completed_at,
                'duration_minutes': duration,
                'language': session.language,
                'answers': answers
            })
        
        return Response(history)


@extend_schema_view(
    list=extend_schema(
        summary="Статистика опросов",
        description="Получить статистику по всем активным опросам.",
        tags=["Модераторы"],
        responses={200: "SurveyStatisticsSerializer"}
    ),
    retrieve=extend_schema(
        summary="Детальная статистика опроса",
        description="Получить детальную статистику конкретного опроса.",
        tags=["Модераторы"],
        responses={200: "SurveyStatisticsSerializer"}
    )
)
class ModeratorSurveyStatsViewSet(ReadOnlyModelViewSet):
    """ViewSet for survey statistics for moderators."""
    
    permission_classes = [IsModeratorPermission]
    serializer_class = SurveyStatisticsSerializer
    
    def get_queryset(self):
        """Get surveys with statistics."""
        return Survey.objects.filter(is_active=True).order_by('-created_at')
    
    @extend_schema(
        summary="Детальные результаты опроса",
        description="""Получить детальные результаты всех сессий конкретного опроса.
        
        Включает информацию о всех пользователях, прошедших опрос, с баллами и статистикой.""",
        tags=["Модераторы"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "survey": {"$ref": "#/components/schemas/SurveyStatistics"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "user": {"type": "object"},
                                "score": {"type": "integer"},
                                "percentage": {"type": "number"},
                                "is_passed": {"type": "boolean"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def detailed_results(self, request, pk=None):
        """Get detailed results for specific survey."""
        survey = self.get_object()
        
        # Get all sessions for this survey
        sessions = SurveySession.objects.filter(survey=survey).select_related('user').order_by('-started_at')
        
        results = []
        for session in sessions:
            duration = None
            if session.completed_at and session.started_at:
                delta = session.completed_at - session.started_at
                duration = int(delta.total_seconds() / 60)
            
            results.append({
                'session_id': session.id,
                'user': {
                    'id': session.user.id,
                    'name': session.user.name,
                    'phone_number': str(session.user.phone_number),
                    'branch': session.user.branch,
                    'position': session.user.position
                },
                'attempt_number': session.attempt_number,
                'status': session.status,
                'score': session.score,
                'total_points': session.total_points,
                'percentage': float(session.percentage) if session.percentage else None,
                'is_passed': session.is_passed,
                'started_at': session.started_at,
                'completed_at': session.completed_at,
                'duration_minutes': duration,
                'language': session.language
            })
        
        return Response({
            'survey': SurveyStatisticsSerializer(survey).data,
            'results': results
        })
    
    @extend_schema(
        summary="Статистика панели управления",
        description="Получить общую статистику для панели управления модератора.",
        tags=["Модераторы"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_users": {"type": "integer", "description": "Общее количество пользователей"},
                    "active_users": {"type": "integer", "description": "Количество активных пользователей"},
                    "current_active_users": {"type": "integer", "description": "Пользователи сейчас проходящие опросы"},
                    "total_surveys": {"type": "integer", "description": "Общее количество опросов"},
                    "completed_sessions": {"type": "integer", "description": "Количество завершенных сессий"},
                    "average_pass_rate": {"type": "number", "description": "Средний процент прохождения"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for moderators."""
        
        # Total users
        total_users = User.objects.filter(is_superuser=False).count()
        
        # Users who started at least one survey
        active_users = User.objects.filter(
            id__in=SurveySession.objects.values_list('user_id', flat=True)
        ).count()
        
        # Users currently taking surveys
        current_active = User.objects.filter(
            id__in=SurveySession.objects.filter(
                status__in=['started', 'in_progress']
            ).values_list('user_id', flat=True)
        ).count()
        
        # Total surveys
        total_surveys = Survey.objects.filter(is_active=True).count()
        
        # Total completed sessions
        completed_sessions = SurveySession.objects.filter(status='completed').count()
        
        # Average pass rate across all surveys
        surveys_with_sessions = Survey.objects.filter(
            id__in=SurveySession.objects.filter(
                status='completed'
            ).values_list('survey_id', flat=True)
        )
        
        total_pass_rate = 0
        survey_count = 0
        
        for survey in surveys_with_sessions:
            completed = SurveySession.objects.filter(survey=survey, status='completed')
            total = completed.count()
            passed = completed.filter(is_passed=True).count()
            
            if total > 0:
                pass_rate = (passed / total) * 100
                total_pass_rate += pass_rate
                survey_count += 1
        
        average_pass_rate = total_pass_rate / survey_count if survey_count > 0 else 0
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'current_active_users': current_active,
            'total_surveys': total_surveys,
            'completed_sessions': completed_sessions,
            'average_pass_rate': round(average_pass_rate, 2)
        })


@extend_schema(
    summary="Панель управления модератора",
    description="""Получить данные для панели управления модератора.
    
    Включает:
    - Последнюю активность (последние завершенные сессии)
    - Лучших пользователей по средним баллам
    - Опросы, требующие внимания (низкий процент прохождения)""",
    tags=["Модераторы"],
    responses={
        200: {
            "type": "object",
            "properties": {
                "recent_activity": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Последняя активность"
                },
                "top_performers": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Лучшие пользователи"
                },
                "surveys_needing_attention": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Опросы, требующие внимания"
                }
            }
        }
    }
)
class ModeratorDashboardView(APIView):
    """Dashboard view for moderators."""
    
    permission_classes = [IsModeratorPermission]
    
    def get(self, request):
        """Get moderator dashboard data."""
        
        # Recent activity - last 10 completed sessions
        recent_sessions = SurveySession.objects.filter(
            status='completed'
        ).select_related('user', 'survey').order_by('-completed_at')[:10]
        
        recent_activity = []
        for session in recent_sessions:
            recent_activity.append({
                'user_name': session.user.name,
                'survey_title': session.survey.title,
                'score': session.score,
                'percentage': float(session.percentage) if session.percentage else None,
                'is_passed': session.is_passed,
                'completed_at': session.completed_at
            })
        
        # Top performers - users with highest average scores
        from django.db.models import Avg
        top_performers = User.objects.filter(
            id__in=SurveySession.objects.filter(
                status='completed'
            ).values_list('user_id', flat=True)
        ).annotate(
            avg_score=Avg('survey_sessions__percentage')
        ).order_by('-avg_score')[:5]
        
        top_performers_data = []
        for user in top_performers:
            top_performers_data.append({
                'name': user.name,
                'branch': user.branch,
                'position': user.position,
                'average_score': round(float(user.avg_score), 2) if user.avg_score else 0
            })
        
        # Surveys needing attention - surveys with low pass rates
        surveys_attention = []
        for survey in Survey.objects.filter(is_active=True):
            completed_sessions = SurveySession.objects.filter(survey=survey, status='completed')
            total = completed_sessions.count()
            
            if total >= 5:  # Only consider surveys with at least 5 attempts
                passed = completed_sessions.filter(is_passed=True).count()
                pass_rate = (passed / total) * 100
                
                if pass_rate < 50:  # Low pass rate threshold
                    surveys_attention.append({
                        'id': survey.id,
                        'title': survey.title,
                        'pass_rate': round(pass_rate, 2),
                        'total_attempts': total
                    })
        
        surveys_attention.sort(key=lambda x: x['pass_rate'])
        
        return Response({
            'recent_activity': recent_activity,
            'top_performers': top_performers_data,
            'surveys_needing_attention': surveys_attention[:5]
        })
