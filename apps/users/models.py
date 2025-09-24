from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from apps.contrib.constants import UserWorkDomainChoices, EmployeeLevelChoices
import random
import string
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for phone number authentication."""
    
    def create_user(self, phone_number, password=None, **extra_fields):
        """Create and return a regular user with phone number."""
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Create and return a superuser with phone number."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_phone_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone_number, password, **extra_fields)

class GTFStaff(models.Model):
    """Model for storing GTF staff."""
    name_uz = models.CharField(_("Choice Name (Uzbek Latin)"), max_length=500)
    name_uz_cyrl = models.CharField(_("Choice Name (Uzbek Cyrillic)"), max_length=500, blank=True)
    name_ru = models.CharField(_("Choice Name (Russian)"), max_length=500, blank=True)
    
    def __str__(self):
        return self.name_uz

class BranchStaff(models.Model):
    """Model for storing Branch staff."""
    name_uz = models.CharField(_("Choice Name (Uzbek Latin)"), max_length=500)
    name_uz_cyrl = models.CharField(_("Choice Name (Uzbek Cyrillic)"), max_length=500, blank=True)
    name_ru = models.CharField(_("Choice Name (Russian)"), max_length=500, blank=True)
    
    def __str__(self):
        return self.name_uz

class PositionStaff(models.Model):
    """Model for storing Position staff."""
    branch = models.ForeignKey(BranchStaff, on_delete=models.SET_NULL, verbose_name=_("Branch"), blank=True, null=True)
    name_uz = models.CharField(_("Choice Name (Uzbek Latin)"), max_length=500)
    name_uz_cyrl = models.CharField(_("Choice Name (Uzbek Cyrillic)"), max_length=500, blank=True)
    name_ru = models.CharField(_("Choice Name (Russian)"), max_length=500, blank=True)
    work_domain = models.CharField(
        _("Work Domain"), max_length=100, blank=True, choices=UserWorkDomainChoices.choices)
    
    def __str__(self):
        return self.name_uz

class User(AbstractUser):
    """
    Default custom user model for Respondent Web.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # Phone authentication
    # Allow any unique identifier (not strictly validated as a phone)
    phone_number = models.CharField(_("Phone Number"), max_length=32, unique=True, null=True, blank=True)
    is_phone_verified = models.BooleanField(_("Phone Verified"), default=False)
    
    # User profile fields
    name = models.CharField(_("Full Name"), max_length=255, blank=True)
    position = models.ForeignKey(PositionStaff, on_delete=models.SET_NULL, verbose_name=_("Position"), blank=True, null=True)
    gtf = models.ForeignKey(GTFStaff, on_delete=models.SET_NULL, verbose_name=_("GTF"), blank=True, null=True)
    work_domain = models.CharField(
        _("Work Domain"), max_length=100, blank=True, choices=UserWorkDomainChoices.choices)
    employee_level = models.CharField(_("Employee Level"), max_length=100, blank=True, choices=EmployeeLevelChoices.choices)
    
    # User type
    is_moderator = models.BooleanField(_("Is Moderator"), default=False)
    
    # Remove default fields
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = None  # type: ignore[assignment]
    username = None  # type: ignore[assignment]
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']
    
    objects = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class OTPVerification(models.Model):
    """Model for storing OTP verification codes."""
    
    phone_number = PhoneNumberField(_("Phone Number"))
    otp_code = models.CharField(_("OTP Code"), max_length=6)
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    expires_at = models.DateTimeField(_("Expires At"))
    
    class Meta:
        verbose_name = _("OTP Verification")
        verbose_name_plural = _("OTP Verifications")
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        super().save(*args, **kwargs)
    
    def generate_otp(self):
        """Generate a random OTP code."""
        return ''.join(random.choices(string.digits, k=settings.OTP_LENGTH))
    
    def is_expired(self):
        """Check if OTP is expired."""
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"OTP for {self.phone_number} - {self.otp_code}"
