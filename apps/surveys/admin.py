from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Survey, Question, Choice, SurveySession, 
    SessionQuestion, Answer, UserSurveyHistory, SurveyEmployeeLevelConfig
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0
    fields = ('text_uz', 'text_uz_cyrl', 'text_ru', 'is_correct', 'order')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('text_uz', 'question_type', 'work_domain', 'points', 'order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


class SurveyEmployeeLevelConfigInline(admin.TabularInline):
    model = SurveyEmployeeLevelConfig
    extra = 0
    fields = ('employee_level', 'questions_count')
    min_num = 1  # At least one config required


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'time_limit_minutes', 'questions_count', 'passing_score', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
    inlines = [SurveyEmployeeLevelConfigInline, QuestionInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'description', 'is_active')
        }),
        (_('Settings'), {
            'fields': ('time_limit_minutes', 'questions_count', 'passing_score', 'max_attempts')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'survey', 'question_type', 'work_domain', 'points', 'order', 'is_active')
    list_filter = ('survey', 'question_type', 'work_domain', 'is_active')
    search_fields = ('text_uz', 'text_ru')
    ordering = ('survey', 'order')
    inlines = [ChoiceInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('survey', 'question_type', 'work_domain', 'order', 'points', 'is_active')
        }),
        (_('Question Text'), {
            'fields': ('text_uz', 'text_uz_cyrl', 'text_ru')
        }),
        (_('Media'), {
            'fields': ('image', 'video'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SurveyEmployeeLevelConfig)
class SurveyEmployeeLevelConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'survey', 'employee_level', 'questions_count')
    list_filter = ('employee_level', 'survey')
    search_fields = ('survey__title',)
    ordering = ('survey', 'employee_level')
    
    fieldsets = (
        (_('Configuration'), {
            'fields': ('survey', 'employee_level', 'questions_count')
        }),
    )


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'question', 'is_correct', 'order')
    list_filter = ('question__survey', 'is_correct')
    search_fields = ('text_uz', 'text_ru')
    ordering = ('question', 'order')


@admin.register(SurveySession)
class SurveySessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'survey', 'status', 'attempt_number', 'score', 'percentage', 'is_passed', 'started_at')
    list_filter = ('status', 'is_passed', 'survey', 'language', 'started_at')
    search_fields = ('user__name', 'user__phone_number', 'survey__title')
    ordering = ('-started_at',)
    readonly_fields = ('id', 'started_at', 'expires_at', 'duration_minutes')
    
    fieldsets = (
        (_('Session Information'), {
            'fields': ('id', 'user', 'survey', 'attempt_number', 'language')
        }),
        (_('Status'), {
            'fields': ('status', 'can_retake', 'approved_by', 'approved_at')
        }),
        (_('Timing'), {
            'fields': ('started_at', 'completed_at', 'expires_at', 'duration_minutes')
        }),
        (_('Results'), {
            'fields': ('score', 'total_points', 'percentage', 'is_passed')
        }),
    )
    
    def duration_minutes(self, obj):
        return obj.duration_minutes()
    duration_minutes.short_description = _('Duration (minutes)')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'question', 'is_correct', 'points_earned', 'answered_at')
    list_filter = ('is_correct', 'question__survey', 'answered_at')
    search_fields = ('session__user__name', 'question__text_uz')
    ordering = ('-answered_at',)
    readonly_fields = ('answered_at',)


@admin.register(UserSurveyHistory)
class UserSurveyHistoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'survey', 'total_attempts', 'best_percentage', 'is_passed', 'last_attempt_at')
    list_filter = ('is_passed', 'survey', 'current_status')
    search_fields = ('user__name', 'user__phone_number', 'survey__title')
    ordering = ('-last_attempt_at',)
    readonly_fields = ('last_attempt_at',)
