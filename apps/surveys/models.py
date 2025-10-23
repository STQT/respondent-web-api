from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import random
from datetime import timedelta
from apps.contrib.constants import UserWorkDomainChoices, EmployeeLevelChoices, QuestionCategoryChoices


class Survey(models.Model):
    """Model for surveys/tests."""
    
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    time_limit_minutes = models.PositiveIntegerField(
        _("Time Limit (minutes)"), 
        default=60,
        validators=[MinValueValidator(1), MaxValueValidator(240)]
    )
    questions_count = models.PositiveIntegerField(
        _("Questions Count"), 
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_("Number of random questions to show from the pool")
    )
    passing_score = models.PositiveIntegerField(
        _("Passing Score"), 
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Minimum score percentage to pass")
    )
    max_attempts = models.PositiveIntegerField(
        _("Max Attempts"), 
        default=3,
        validators=[MinValueValidator(1)]
    )
    
    # Category distribution settings
    safety_logic_psychology_percentage = models.PositiveIntegerField(
        _("Safety, Logic, Psychology Percentage"), 
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage of questions from Safety, Logic (IQ), Psychology category")
    )
    other_percentage = models.PositiveIntegerField(
        _("Other Category Percentage"), 
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage of questions from Other category")
    )
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Survey")
        verbose_name_plural = _("Surveys")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_random_questions(self, count=None, language='uz', user_work_domain=None, user_employee_level=None):
        """Get random questions for the survey, optionally filtered by work domain and employee level."""
        if count is None:
            # Try to get count from employee level config first
            if user_employee_level:
                try:
                    config = self.employee_level_configs.get(employee_level=user_employee_level)
                    count = config.questions_count
                except SurveyEmployeeLevelConfig.DoesNotExist:
                    count = self.questions_count
            else:
                count = self.questions_count
        
        # Get all active questions for this survey
        all_questions = self.questions.filter(is_active=True)
        
        # Filter by work domain if provided
        if user_work_domain:
            # Include questions that are either for this work domain or for all domains (blank)
            all_questions = all_questions.filter(
                models.Q(work_domain=user_work_domain) | models.Q(work_domain='')
            )
        
        # If we have fewer questions than requested, use all available
        total_available = all_questions.count()
        if total_available == 0:
            return []
        
        actual_count = min(count, total_available)
        
        # Calculate questions per category based on percentages
        safety_logic_psychology_count = int(actual_count * self.safety_logic_psychology_percentage / 100)
        other_count = actual_count - safety_logic_psychology_count
        
        # Get questions by category
        safety_logic_psychology_questions = all_questions.filter(
            category=QuestionCategoryChoices.SAFETY_LOGIC_PSYCHOLOGY
        )
        other_questions = all_questions.filter(
            category=QuestionCategoryChoices.OTHER
        )
        
        selected_questions = []
        
        # Select questions from Safety, Logic, Psychology category FIRST
        if safety_logic_psychology_count > 0 and safety_logic_psychology_questions.exists():
            available_safety_count = min(safety_logic_psychology_count, safety_logic_psychology_questions.count())
            safety_question_ids = list(safety_logic_psychology_questions.values_list('id', flat=True))
            selected_safety_ids = random.sample(safety_question_ids, available_safety_count)
            selected_questions.extend(safety_logic_psychology_questions.filter(id__in=selected_safety_ids))
        
        # Select questions from Other category SECOND
        if other_count > 0 and other_questions.exists():
            available_other_count = min(other_count, other_questions.count())
            other_question_ids = list(other_questions.values_list('id', flat=True))
            selected_other_ids = random.sample(other_question_ids, available_other_count)
            selected_questions.extend(other_questions.filter(id__in=selected_other_ids))
        
        # If we don't have enough questions from categories, fill with remaining questions
        if len(selected_questions) < actual_count:
            remaining_count = actual_count - len(selected_questions)
            remaining_questions = all_questions.exclude(id__in=[q.id for q in selected_questions])
            if remaining_questions.exists():
                remaining_question_ids = list(remaining_questions.values_list('id', flat=True))
                selected_remaining_ids = random.sample(remaining_question_ids, min(remaining_count, len(remaining_question_ids)))
                selected_questions.extend(remaining_questions.filter(id__in=selected_remaining_ids))
        
        # Return questions in order: Safety/Logic/Psychology first, then Other
        # No shuffling to maintain the order
        return selected_questions
    
    def get_total_available_questions(self):
        """Get total number of available active questions."""
        return self.questions.filter(is_active=True).count()
    
    def clean(self):
        """Validate that percentage fields don't exceed 100%."""
        from django.core.exceptions import ValidationError
        
        if self.safety_logic_psychology_percentage + self.other_percentage > 100:
            raise ValidationError({
                'safety_logic_psychology_percentage': _('Total percentage cannot exceed 100%.'),
                'other_percentage': _('Total percentage cannot exceed 100%.')
            })
    
    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.clean()
        super().save(*args, **kwargs)


class SurveyEmployeeLevelConfig(models.Model):
    """Model for configuring question count per employee level for surveys."""
    
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='employee_level_configs')
    employee_level = models.CharField(
        _("Employee Level"), 
        max_length=100, 
        choices=EmployeeLevelChoices.choices
    )
    questions_count = models.PositiveIntegerField(
        _("Questions Count"), 
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_("Number of questions for this employee level")
    )
    
    class Meta:
        verbose_name = _("Survey Employee Level Config")
        verbose_name_plural = _("Survey Employee Level Configs")
        unique_together = ['survey', 'employee_level']
        ordering = ['survey', 'employee_level']
    
    def __str__(self):
        return f"{self.survey.title} - {self.get_employee_level_display()} ({self.questions_count} questions)"


class Question(models.Model):
    """Model for survey questions with multi-language support."""
    
    QUESTION_TYPES = [
        ('single', _('Single Choice')),
        ('multiple', _('Multiple Choice')),
        ('open', _('Open Answer')),
    ]
    
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(_("Question Type"), max_length=10, choices=QUESTION_TYPES)
    
    # Multi-language question text
    text_uz = models.TextField(_("Question Text (Uzbek Latin)"))
    text_uz_cyrl = models.TextField(_("Question Text (Uzbek Cyrillic)"), blank=True)
    text_ru = models.TextField(_("Question Text (Russian)"), blank=True)
    
    # Optional media
    image = models.ImageField(_("Image"), upload_to='questions/images/', blank=True, null=True)
    video = models.FileField(_("Video"), upload_to='questions/videos/', blank=True, null=True)
    
    points = models.PositiveIntegerField(_("Points"), default=1)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Work domain for filtering questions by user's work domain
    work_domain = models.CharField(
        _("Work Domain"), 
        max_length=100, 
        blank=True, 
        choices=UserWorkDomainChoices.choices,
        help_text=_("Work domain this question is relevant for. Leave blank for all domains.")
    )
    
    # Question category
    category = models.CharField(
        _("Category"), 
        max_length=50, 
        choices=QuestionCategoryChoices.choices,
        help_text=_("Question category for percentage distribution")
    )
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['survey', 'order']
        unique_together = ['survey', 'order']
    
    def get_text(self, language='uz'):
        """Get question text based on language."""
        language_map = {
            'uz': self.text_uz,
            'uz-cyrl': self.text_uz_cyrl or self.text_uz,
            'ru': self.text_ru or self.text_uz,
        }
        return language_map.get(language, self.text_uz)
    
    def __str__(self):
        return f"{self.survey.title} - Question {self.order}"


class Choice(models.Model):
    """Model for question choices (for single/multiple choice questions)."""
    
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    
    # Multi-language choice text
    text_uz = models.CharField(_("Choice Text (Uzbek Latin)"), max_length=500)
    text_uz_cyrl = models.CharField(_("Choice Text (Uzbek Cyrillic)"), max_length=500, blank=True)
    text_ru = models.CharField(_("Choice Text (Russian)"), max_length=500, blank=True)
    
    is_correct = models.BooleanField(_("Is Correct"), default=False)
    order = models.PositiveIntegerField(_("Order"), default=0)
    
    class Meta:
        verbose_name = _("Choice")
        verbose_name_plural = _("Choices")
        ordering = ['question', 'order']
        unique_together = ['question', 'order']
    
    def get_text(self, language='uz'):
        """Get choice text based on language."""
        language_map = {
            'uz': self.text_uz,
            'uz-cyrl': self.text_uz_cyrl or self.text_uz,
            'ru': self.text_ru or self.text_uz,
        }
        return language_map.get(language, self.text_uz)
    
    def __str__(self):
        return f"{self.question} - {self.text_uz[:50]}"


class SurveySession(models.Model):
    """Model for tracking user survey sessions."""
    
    STATUS_CHOICES = [
        ('started', _('Started')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='survey_sessions')
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='sessions')
    
    # Session tracking
    status = models.CharField(_("Status"), max_length=15, choices=STATUS_CHOICES, default='started')
    attempt_number = models.PositiveIntegerField(_("Attempt Number"), default=1)
    certificate_order = models.PositiveIntegerField(
        _("Certificate Order Number"), 
        null=True, 
        blank=True,
        help_text=_("Auto-incrementing order number for certificate identification")
    )
    
    # Time tracking
    started_at = models.DateTimeField(_("Started At"), auto_now_add=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)
    expires_at = models.DateTimeField(_("Expires At"))
    
    # Results
    score = models.PositiveIntegerField(_("Score"), null=True, blank=True)
    total_points = models.PositiveIntegerField(_("Total Points"), null=True, blank=True)
    percentage = models.DecimalField(_("Percentage"), max_digits=5, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(_("Is Passed"), null=True, blank=True)
    
    # Questions for this session (to maintain consistency)
    session_questions = models.ManyToManyField(Question, through='SessionQuestion', related_name='sessions')
    
    # Language used in this session
    language = models.CharField(_("Language"), max_length=10, default='uz')
    
    # Proctoring fields
    proctoring_enabled = models.BooleanField(_("Proctoring Enabled"), default=True, help_text=_("Face monitoring enabled for this session"))
    initial_face_verified = models.BooleanField(_("Initial Face Verified"), default=False, help_text=_("Initial face verification completed"))
    face_reference_image = models.ImageField(_("Face Reference Image"), upload_to='face_references/%Y/%m/%d/', null=True, blank=True)
    violations_count = models.IntegerField(_("Violations Count"), default=0)
    flagged_for_review = models.BooleanField(_("Flagged for Review"), default=False)
    
    # Moderator approval
    can_retake = models.BooleanField(_("Can Retake"), default=False, help_text=_("Moderator granted permission for retake"))
    retake_reason = models.TextField(_("Retake Reason"), blank=True, help_text=_("Reason for granting retake permission"))
    retake_granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_retakes',
        verbose_name=_("Retake Granted By")
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_sessions'
    )
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Survey Session")
        verbose_name_plural = _("Survey Sessions")
        ordering = ['-started_at']
        unique_together = ['user', 'survey', 'attempt_number']
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=self.survey.time_limit_minutes)
        
        # Auto-assign certificate order number when session is completed
        if self.status == 'completed' and not self.certificate_order:
            # Get the next certificate order number
            last_certificate = SurveySession.objects.filter(
                status='completed',
                certificate_order__isnull=False
            ).order_by('-certificate_order').first()
            
            if last_certificate:
                self.certificate_order = last_certificate.certificate_order + 1
            else:
                self.certificate_order = 1
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if session is expired."""
        return timezone.now() > self.expires_at and self.status not in ['completed', 'cancelled']
    
    def duration_minutes(self):
        """Calculate session duration in minutes."""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None
    
    def initialize_questions(self, questions_count=None):
        """Initialize random questions for this session."""
        if self.sessionquestion_set.exists():
            return  # Questions already initialized
        
        questions = self.survey.get_random_questions(
            count=questions_count, 
            user_work_domain=self.user.work_domain,
            user_employee_level=self.user.employee_level
        )
        
        # If no questions found, try without work domain filter
        if not questions:
            questions = self.survey.get_random_questions(
                count=questions_count, 
                user_work_domain=None,  # Remove work domain filter
                user_employee_level=self.user.employee_level
            )
        
        # If still no questions, try with just basic questions
        if not questions:
            questions = self.survey.questions.filter(is_active=True)[:questions_count or 30]
        
        for i, question in enumerate(questions, 1):
            SessionQuestion.objects.create(
                session=self,
                question=question,
                order=i
            )
    
    def get_next_unanswered_question(self):
        """Get the next unanswered question in the session."""
        return self.sessionquestion_set.filter(is_answered=False).order_by('order').first()
    
    def get_question_by_order(self, order):
        """Get question by specific order number."""
        try:
            return self.sessionquestion_set.get(order=order)
        except SessionQuestion.DoesNotExist:
            return None
    
    def get_previous_question(self, current_order):
        """Get the previous question in the session."""
        if current_order <= 1:
            return None
        try:
            return self.sessionquestion_set.get(order=current_order - 1)
        except SessionQuestion.DoesNotExist:
            return None
    
    def get_next_question(self, current_order):
        """Get the next question in the session (answered or not)."""
        try:
            return self.sessionquestion_set.get(order=current_order + 1)
        except SessionQuestion.DoesNotExist:
            return None
    
    def can_modify_answer(self, question_id):
        """Check if user can modify answer for specific question."""
        try:
            session_question = self.sessionquestion_set.get(question_id=question_id)
            # Allow modification if session is still active and question was answered
            return (self.status in ['started', 'in_progress'] and 
                   not self.is_expired() and 
                   session_question.is_answered)
        except SessionQuestion.DoesNotExist:
            return False
    
    def get_current_progress(self):
        """Get current session progress."""
        total_questions = self.sessionquestion_set.count()
        answered_questions = self.sessionquestion_set.filter(is_answered=True).count()
        
        return {
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'remaining_questions': total_questions - answered_questions,
            'progress_percentage': (answered_questions / total_questions * 100) if total_questions > 0 else 0
        }
    
    def calculate_final_score(self):
        """Calculate final score for the session."""
        if self.status != 'completed':
            return None
        
        total_points = sum(sq.question.points for sq in self.sessionquestion_set.all())
        earned_points = sum(answer.points_earned for answer in self.answers.all())
        
        if total_points > 0:
            percentage = (earned_points / total_points) * 100
            self.score = earned_points
            self.total_points = total_points
            self.percentage = percentage
            self.is_passed = percentage >= self.survey.passing_score
            self.save()
            
            return {
                'score': earned_points,
                'total_points': total_points,
                'percentage': percentage,
                'is_passed': self.is_passed
            }
        return None
    
    def record_violation(self, violation_type, snapshot=None, metadata=None):
        """Record a proctoring violation."""
        if metadata is None:
            metadata = {}
        
        self.violations_count += 1
        if self.violations_count >= 3:  # Threshold for automatic flagging
            self.flagged_for_review = True
        self.save()
        
        # Create violation record
        from apps.surveys.models import FaceVerification
        verification = FaceVerification.objects.create(
            session=self,
            is_violation=True,
            violation_type=violation_type,
            snapshot=snapshot,
            **metadata
        )
        return verification
    
    def __str__(self):
        return f"{self.user.name} - {self.survey.title} (Attempt {self.attempt_number})"


class SessionQuestion(models.Model):
    """Through model for survey session questions to maintain order and state."""
    
    session = models.ForeignKey(SurveySession, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(_("Order"))
    is_answered = models.BooleanField(_("Is Answered"), default=False)
    points_earned = models.PositiveIntegerField(_("Points Earned"), default=0)
    
    class Meta:
        verbose_name = _("Session Question")
        verbose_name_plural = _("Session Questions")
        ordering = ['session', 'order']
        unique_together = ['session', 'order']
    
    def __str__(self):
        return f"{self.session} - Question {self.order}"


class Answer(models.Model):
    """Model for storing user answers."""
    
    session = models.ForeignKey(SurveySession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For single/multiple choice questions
    selected_choices = models.ManyToManyField(Choice, blank=True)
    
    # For open questions
    text_answer = models.TextField(_("Text Answer"), blank=True)
    
    # Scoring
    is_correct = models.BooleanField(_("Is Correct"), null=True, blank=True)
    points_earned = models.PositiveIntegerField(_("Points Earned"), default=0)
    
    answered_at = models.DateTimeField(_("Answered At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")
        unique_together = ['session', 'question']
    
    def calculate_score(self):
        """Calculate score for this answer."""
        if self.question.question_type == 'open':
            # Open questions need manual scoring
            return 0
        
        if self.question.question_type == 'single':
            # Single choice
            correct_choices = self.question.choices.filter(is_correct=True)
            selected_choices = self.selected_choices.all()
            
            if len(selected_choices) == 1 and selected_choices[0] in correct_choices:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        
        elif self.question.question_type == 'multiple':
            # Multiple choice
            correct_choices = set(self.question.choices.filter(is_correct=True))
            selected_choices = set(self.selected_choices.all())
            
            if correct_choices == selected_choices:
                self.is_correct = True
                self.points_earned = self.question.points
            else:
                self.is_correct = False
                self.points_earned = 0
        
        return self.points_earned
    
    def __str__(self):
        return f"{self.session.user.name} - {self.question}"


class UserSurveyHistory(models.Model):
    """Model for tracking user survey history and statistics."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='survey_history')
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='user_history')
    
    # Statistics
    total_attempts = models.PositiveIntegerField(_("Total Attempts"), default=0)
    best_score = models.PositiveIntegerField(_("Best Score"), null=True, blank=True)
    best_percentage = models.DecimalField(_("Best Percentage"), max_digits=5, decimal_places=2, null=True, blank=True)
    last_attempt_at = models.DateTimeField(_("Last Attempt"), null=True, blank=True)
    is_passed = models.BooleanField(_("Is Passed"), default=False)
    
    # Current status
    current_status = models.CharField(_("Current Status"), max_length=15, default='not_started')
    can_continue = models.BooleanField(_("Can Continue"), default=True)
    
    class Meta:
        verbose_name = _("User Survey History")
        verbose_name_plural = _("User Survey Histories")
        unique_together = ['user', 'survey']
    
    def __str__(self):
        return f"{self.user.name} - {self.survey.title} History"


class FaceVerification(models.Model):
    """Model for storing face verifications during survey sessions."""
    
    session = models.ForeignKey(SurveySession, on_delete=models.CASCADE, related_name='face_verifications')
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    
    # Verification results
    face_detected = models.BooleanField(_("Face Detected"), default=False)
    face_count = models.IntegerField(_("Face Count"), default=0, help_text=_("Number of detected faces"))
    confidence_score = models.FloatField(_("Confidence Score"), null=True, blank=True, help_text=_("Detection confidence 0-1"))
    
    # Additional checks
    looking_at_screen = models.BooleanField(_("Looking at Screen"), default=True, help_text=_("Gaze direction check"))
    mobile_device_detected = models.BooleanField(_("Mobile Device Detected"), default=False, help_text=_("Mobile phone in frame"))
    
    # Saved image (only for violations)
    snapshot = models.ImageField(_("Snapshot"), upload_to='face_verifications/%Y/%m/%d/', null=True, blank=True)
    
    # Violation status
    is_violation = models.BooleanField(_("Is Violation"), default=False)
    violation_type = models.CharField(_("Violation Type"), max_length=50, blank=True, help_text=_("e.g., 'no_face', 'multiple_faces', 'mobile_detected'"))
    
    class Meta:
        verbose_name = _("Face Verification")
        verbose_name_plural = _("Face Verifications")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.session} - {self.timestamp} ({'Violation' if self.is_violation else 'OK'})"


class SessionRecording(models.Model):
    """Model for storing full video recordings of survey sessions."""
    
    session = models.OneToOneField(SurveySession, on_delete=models.CASCADE, related_name='recording')
    
    # Video file
    video_file = models.FileField(_("Video File"), upload_to='session_recordings/%Y/%m/%d/')
    file_size = models.BigIntegerField(_("File Size"), help_text=_("Size in bytes"))
    duration_seconds = models.IntegerField(_("Duration"), help_text=_("Duration in seconds"))
    
    # Metadata
    uploaded_at = models.DateTimeField(_("Uploaded At"), auto_now_add=True)
    processed = models.BooleanField(_("Processed"), default=False)
    
    # Violation statistics
    total_violations = models.IntegerField(_("Total Violations"), default=0)
    violation_summary = models.JSONField(_("Violation Summary"), default=dict, blank=True)
    
    class Meta:
        verbose_name = _("Session Recording")
        verbose_name_plural = _("Session Recordings")
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Recording for {self.session}"


class ProctorReview(models.Model):
    """Model for moderator review of flagged sessions."""
    
    REVIEW_STATUS_CHOICES = [
        ('pending', _('Pending Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('flagged', _('Flagged for Additional Review')),
    ]
    
    session = models.OneToOneField(SurveySession, on_delete=models.CASCADE, related_name='proctor_review')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='reviewed_sessions',
        verbose_name=_("Reviewer")
    )
    
    status = models.CharField(_("Status"), max_length=20, choices=REVIEW_STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField(_("Reviewed At"), null=True, blank=True)
    
    # Moderator comments
    notes = models.TextField(_("Notes"), blank=True)
    
    # Auto-flagging
    auto_flagged = models.BooleanField(_("Auto Flagged"), default=False)
    flag_reason = models.TextField(_("Flag Reason"), blank=True)
    
    class Meta:
        verbose_name = _("Proctor Review")
        verbose_name_plural = _("Proctor Reviews")
        ordering = ['-session__started_at']
    
    def __str__(self):
        return f"Review for {self.session} - {self.get_status_display()}"
