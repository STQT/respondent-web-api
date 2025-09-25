from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Max, Avg
from apps.users.models import User
from apps.surveys.models import (
    Survey, SurveySession, UserSurveyHistory, Answer
)


class ModeratorUserListSerializer(serializers.ModelSerializer):
    """Serializer for moderator user list view."""
    
    # Основные поля (обратная совместимость)
    branch = serializers.CharField(source='position.branch.name_uz', read_only=True)
    position_name = serializers.CharField(source='position.name_uz', read_only=True)
    
    # Мультиязычные поля
    branch_uz = serializers.CharField(source='position.branch.name_uz', read_only=True)
    branch_uz_cyrl = serializers.CharField(source='position.branch.name_uz_cyrl', read_only=True)
    branch_ru = serializers.CharField(source='position.branch.name_ru', read_only=True)
    
    position_name_uz = serializers.CharField(source='position.name_uz', read_only=True)
    position_name_uz_cyrl = serializers.CharField(source='position.name_uz_cyrl', read_only=True)
    position_name_ru = serializers.CharField(source='position.name_ru', read_only=True)
    
    last_survey_attempt = serializers.SerializerMethodField()
    total_attempts = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'name', 'position',
            # Основные поля (обратная совместимость)
            'branch', 'position_name',
            # Мультиязычные поля
            'branch_uz', 'branch_uz_cyrl', 'branch_ru',
            'position_name_uz', 'position_name_uz_cyrl', 'position_name_ru',
            'last_survey_attempt', 'total_attempts', 'best_score', 'status',
            'is_phone_verified', 'date_joined'
        ]
    
    def get_last_survey_attempt(self, obj):
        """Get last survey attempt date."""
        last_session = SurveySession.objects.filter(user=obj).order_by('-started_at').first()
        return last_session.started_at if last_session else None
    
    def get_total_attempts(self, obj):
        """Get total number of survey attempts."""
        return SurveySession.objects.filter(user=obj).count()
    
    def get_best_score(self, obj):
        """Get best score across all surveys."""
        best_session = SurveySession.objects.filter(
            user=obj, 
            status='completed'
        ).order_by('-percentage').first()
        return float(best_session.percentage) if best_session and best_session.percentage else None
    
    def get_status(self, obj):
        """Get current user status."""
        active_session = SurveySession.objects.filter(
            user=obj,
            status__in=['started', 'in_progress']
        ).first()
        
        if active_session:
            return 'active'
        
        last_session = SurveySession.objects.filter(user=obj).order_by('-started_at').first()
        if last_session:
            return last_session.status
        
        return 'never_started'


class ModeratorUserDetailSerializer(serializers.ModelSerializer):
    """Serializer for moderator user detail view."""
    
    # Основные поля (обратная совместимость)
    branch = serializers.CharField(source='position.branch.name_uz', read_only=True)
    position_name = serializers.CharField(source='position.name_uz', read_only=True)
    
    # Мультиязычные поля
    branch_uz = serializers.CharField(source='position.branch.name_uz', read_only=True)
    branch_uz_cyrl = serializers.CharField(source='position.branch.name_uz_cyrl', read_only=True)
    branch_ru = serializers.CharField(source='position.branch.name_ru', read_only=True)
    
    position_name_uz = serializers.CharField(source='position.name_uz', read_only=True)
    position_name_uz_cyrl = serializers.CharField(source='position.name_uz_cyrl', read_only=True)
    position_name_ru = serializers.CharField(source='position.name_ru', read_only=True)
    
    survey_history = serializers.SerializerMethodField()
    total_statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'name', 'position',
            # Основные поля (обратная совместимость)
            'branch', 'position_name',
            # Мультиязычные поля
            'branch_uz', 'branch_uz_cyrl', 'branch_ru',
            'position_name_uz', 'position_name_uz_cyrl', 'position_name_ru',
            'is_phone_verified', 'date_joined', 'last_login',
            'survey_history', 'total_statistics'
        ]
    
    def get_survey_history(self, obj):
        """Get detailed survey history."""
        sessions = SurveySession.objects.filter(user=obj).select_related('survey').order_by('-started_at')
        
        history = []
        for session in sessions:
            duration = None
            if session.completed_at and session.started_at:
                delta = session.completed_at - session.started_at
                duration = int(delta.total_seconds() / 60)  # minutes
            
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
                'language': session.language
            })
        
        return history
    
    def get_total_statistics(self, obj):
        """Get total user statistics."""
        sessions = SurveySession.objects.filter(user=obj)
        completed_sessions = sessions.filter(status='completed')
        
        return {
            'total_attempts': sessions.count(),
            'completed_attempts': completed_sessions.count(),
            'passed_attempts': completed_sessions.filter(is_passed=True).count(),
            'average_score': completed_sessions.aggregate(
                avg_score=Avg('percentage')
            )['avg_score'],
            'best_score': completed_sessions.aggregate(
                max_score=Max('percentage')
            )['max_score'],
            'total_surveys': sessions.values('survey').distinct().count()
        }


class ModeratorUserOverviewSerializer(serializers.ModelSerializer):
    """Serializer for moderator users overview list."""
    
    # Основные поля (обратная совместимость)
    branch = serializers.CharField(source='position.branch.name_uz', read_only=True)
    position_name = serializers.CharField(source='position.name_uz', read_only=True)
    
    # Мультиязычные поля
    branch_uz = serializers.CharField(source='position.branch.name_uz', read_only=True)
    branch_uz_cyrl = serializers.CharField(source='position.branch.name_uz_cyrl', read_only=True)
    branch_ru = serializers.CharField(source='position.branch.name_ru', read_only=True)
    
    position_name_uz = serializers.CharField(source='position.name_uz', read_only=True)
    position_name_uz_cyrl = serializers.CharField(source='position.name_uz_cyrl', read_only=True)
    position_name_ru = serializers.CharField(source='position.name_ru', read_only=True)
    
    last_score = serializers.SerializerMethodField()
    attempts_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'position',
            # Основные поля (обратная совместимость)
            'branch', 'position_name',
            # Мультиязычные поля
            'branch_uz', 'branch_uz_cyrl', 'branch_ru',
            'position_name_uz', 'position_name_uz_cyrl', 'position_name_ru',
            'last_score', 'attempts_count', 'status'
        ]
    
    def get_last_score(self, obj):
        """Get last survey score."""
        last_session = SurveySession.objects.filter(
            user=obj, 
            status='completed'
        ).order_by('-completed_at').first()
        return float(last_session.percentage) if last_session and last_session.percentage else None
    
    def get_attempts_count(self, obj):
        """Get total attempts count."""
        return SurveySession.objects.filter(user=obj).count()
    
    def get_status(self, obj):
        """Get current status."""
        # Check if user has active session
        active_session = SurveySession.objects.filter(
            user=obj,
            status__in=['started', 'in_progress']
        ).exists()
        
        if active_session:
            return 'В процессе'
        
        # Check last completed session
        last_session = SurveySession.objects.filter(
            user=obj,
            status='completed'
        ).order_by('-completed_at').first()
        
        if last_session:
            return 'Пройден' if last_session.is_passed else 'Не пройден'
        
        return 'Не начинал'


class RetakePermissionSerializer(serializers.Serializer):
    """Serializer for granting retake permission."""
    
    user_id = serializers.IntegerField()
    survey_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate_user_id(self, value):
        """Validate user exists."""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(_("User not found"))
        return value
    
    def validate_survey_id(self, value):
        """Validate survey exists."""
        try:
            Survey.objects.get(id=value)
        except Survey.DoesNotExist:
            raise serializers.ValidationError(_("Survey not found"))
        return value
    
    def validate(self, attrs):
        """Validate user has sessions for this survey."""
        user_id = attrs['user_id']
        survey_id = attrs['survey_id']
        
        sessions = SurveySession.objects.filter(
            user_id=user_id,
            survey_id=survey_id
        )
        
        if not sessions.exists():
            raise serializers.ValidationError(_("User has no attempts for this survey"))
        
        # Check if user has reached max attempts
        survey = Survey.objects.get(id=survey_id)
        if sessions.count() < survey.max_attempts:
            raise serializers.ValidationError(_("User has not reached maximum attempts yet"))
        
        return attrs


class SurveyStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for survey statistics."""
    
    total_participants = serializers.SerializerMethodField()
    completed_attempts = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()
    average_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Survey
        fields = [
            'id', 'title', 'description', 'passing_score',
            'total_participants', 'completed_attempts', 'average_score',
            'pass_rate', 'average_duration', 'created_at'
        ]
    
    def get_total_participants(self, obj):
        """Get total number of unique participants."""
        return SurveySession.objects.filter(survey=obj).values('user').distinct().count()
    
    def get_completed_attempts(self, obj):
        """Get number of completed attempts."""
        return SurveySession.objects.filter(survey=obj, status='completed').count()
    
    def get_average_score(self, obj):
        """Get average score."""
        avg = SurveySession.objects.filter(
            survey=obj, 
            status='completed'
        ).aggregate(avg_score=Avg('percentage'))['avg_score']
        return float(avg) if avg else None
    
    def get_pass_rate(self, obj):
        """Get pass rate percentage."""
        completed = SurveySession.objects.filter(survey=obj, status='completed')
        total = completed.count()
        passed = completed.filter(is_passed=True).count()
        
        if total > 0:
            return (passed / total) * 100
        return None
    
    def get_average_duration(self, obj):
        """Get average completion duration in minutes."""
        sessions = SurveySession.objects.filter(
            survey=obj,
            status='completed',
            completed_at__isnull=False
        )
        
        total_duration = 0
        count = 0
        
        for session in sessions:
            if session.started_at and session.completed_at:
                duration = session.completed_at - session.started_at
                total_duration += duration.total_seconds()
                count += 1
        
        if count > 0:
            return int(total_duration / count / 60)  # minutes
        return None
