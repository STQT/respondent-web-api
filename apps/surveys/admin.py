from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Survey, Question, Choice, SurveySession, 
    SessionQuestion, Answer, UserSurveyHistory, SurveyEmployeeLevelConfig,
    FaceVerification, SessionRecording, VideoChunk, ProctorReview
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0
    fields = ('text_uz', 'text_uz_cyrl', 'text_ru', 'is_correct', 'order')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('text_uz', 'question_type', 'category', 'work_domain', 'points', 'order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


class SurveyEmployeeLevelConfigInline(admin.TabularInline):
    model = SurveyEmployeeLevelConfig
    extra = 0
    fields = ('employee_level', 'questions_count')
    min_num = 1  # At least one config required


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'time_limit_minutes', 'questions_count', 'passing_score', 'safety_logic_psychology_percentage', 'other_percentage', 'created_at')
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
        (_('Category Distribution'), {
            'fields': ('safety_logic_psychology_percentage', 'other_percentage'),
            'description': _('Set the percentage distribution of questions by category. Total should not exceed 100%.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'survey', 'question_type', 'category', 'work_domain', 'points', 'order', 'is_active')
    list_filter = ('survey', 'question_type', 'category', 'work_domain', 'is_active')
    search_fields = ('text_uz', 'text_ru')
    ordering = ('survey', 'order')
    inlines = [ChoiceInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('survey', 'question_type', 'category', 'work_domain', 'order', 'points', 'is_active')
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
    list_display = ('__str__', 'user', 'survey', 'status', 'attempt_number', 'certificate_order', 'score', 'percentage', 'is_passed', 'started_at')
    list_filter = ('status', 'is_passed', 'survey', 'language', 'started_at', 'flagged_for_review', 'proctoring_enabled')
    search_fields = ('user__name', 'user__phone_number', 'survey__title')
    ordering = ('-started_at',)
    readonly_fields = ('id', 'started_at', 'expires_at', 'duration_minutes')
    
    fieldsets = (
        (_('Session Information'), {
            'fields': ('id', 'user', 'survey', 'attempt_number', 'certificate_order', 'language')
        }),
        (_('Status'), {
            'fields': ('status', 'can_retake', 'retake_reason', 'retake_granted_by', 'approved_by', 'approved_at')
        }),
        (_('Timing'), {
            'fields': ('started_at', 'completed_at', 'expires_at', 'duration_minutes')
        }),
        (_('Results'), {
            'fields': ('score', 'total_points', 'percentage', 'is_passed')
        }),
        (_('Proctoring'), {
            'fields': ('proctoring_enabled', 'initial_face_verified', 'face_reference_image', 'violations_count', 'flagged_for_review'),
            'classes': ('collapse',)
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


@admin.register(SessionQuestion)
class SessionQuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'question', 'order', 'is_answered', 'points_earned')
    list_filter = ('is_answered', 'session__survey', 'session__status')
    search_fields = ('session__user__name', 'question__text_uz')
    ordering = ('session', 'order')
    
    fieldsets = (
        (_('Session Question'), {
            'fields': ('session', 'question', 'order')
        }),
        (_('Progress'), {
            'fields': ('is_answered', 'points_earned')
        }),
    )


@admin.register(FaceVerification)
class FaceVerificationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'timestamp', 'face_detected', 'face_count', 'is_violation', 'violation_type')
    list_filter = ('face_detected', 'is_violation', 'looking_at_screen', 'mobile_device_detected', 'timestamp')
    search_fields = ('session__user__name', 'session__survey__title', 'violation_type')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)
    
    fieldsets = (
        (_('Verification'), {
            'fields': ('session', 'timestamp', 'face_detected', 'face_count', 'confidence_score')
        }),
        (_('Additional Checks'), {
            'fields': ('looking_at_screen', 'mobile_device_detected')
        }),
        (_('Violation'), {
            'fields': ('is_violation', 'violation_type', 'snapshot'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SessionRecording)
class SessionRecordingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'uploaded_at', 'duration_seconds', 'file_size', 'processed', 'total_violations')
    list_filter = ('processed', 'uploaded_at')
    search_fields = ('session__user__name', 'session__survey__title')
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at',)
    
    fieldsets = (
        (_('Recording'), {
            'fields': ('session', 'video_file', 'file_size', 'duration_seconds')
        }),
        (_('Processing'), {
            'fields': ('uploaded_at', 'processed')
        }),
        (_('Violations'), {
            'fields': ('total_violations', 'violation_summary'),
            'classes': ('collapse',)
        }),
    )


@admin.register(VideoChunk)
class VideoChunkAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'chunk_number', 'uploaded_at', 'duration_seconds', 'file_size', 'processed')
    list_filter = ('processed', 'uploaded_at', 'has_audio')
    search_fields = ('session__user__name', 'session__survey__title')
    ordering = ('session', 'chunk_number')
    readonly_fields = ('uploaded_at',)
    
    fieldsets = (
        (_('Chunk Information'), {
            'fields': ('session', 'chunk_number', 'chunk_file', 'file_size')
        }),
        (_('Timing'), {
            'fields': ('duration_seconds', 'start_time', 'end_time')
        }),
        (_('Processing'), {
            'fields': ('uploaded_at', 'processed')
        }),
        (_('Quality Metrics'), {
            'fields': ('has_audio', 'resolution', 'fps'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProctorReview)
class ProctorReviewAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'session', 'reviewer', 'status', 'reviewed_at', 'auto_flagged')
    list_filter = ('status', 'auto_flagged', 'reviewed_at')
    search_fields = ('session__user__name', 'session__survey__title', 'notes', 'flag_reason')
    ordering = ('-session__started_at',)
    readonly_fields = ('reviewed_at',)
    
    fieldsets = (
        (_('Review'), {
            'fields': ('session', 'reviewer', 'status', 'reviewed_at')
        }),
        (_('Comments'), {
            'fields': ('notes',)
        }),
        (_('Auto-flagging'), {
            'fields': ('auto_flagged', 'flag_reason'),
            'classes': ('collapse',)
        }),
    )
