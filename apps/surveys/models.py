from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import random
from datetime import timedelta


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
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Survey")
        verbose_name_plural = _("Surveys")
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_random_questions(self, count=None, language='uz'):
        """Get random questions for the survey."""
        if count is None:
            count = self.questions_count
        
        # Get all active questions for this survey
        all_questions = self.questions.filter(is_active=True)
        
        # If we have fewer questions than requested, use all available
        total_available = all_questions.count()
        if total_available == 0:
            return []
        
        actual_count = min(count, total_available)
        
        # Get random questions
        question_ids = list(all_questions.values_list('id', flat=True))
        selected_ids = random.sample(question_ids, actual_count)
        
        # Return questions in random order
        return all_questions.filter(id__in=selected_ids).order_by('?')
    
    def get_total_available_questions(self):
        """Get total number of available active questions."""
        return self.questions.filter(is_active=True).count()


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
        
        questions = self.survey.get_random_questions(count=questions_count)
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
