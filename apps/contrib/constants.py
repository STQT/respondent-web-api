from django.db import models
from django.utils.translation import gettext_lazy as _


class UserWorkDomainChoices(models.TextChoices):
    """Choices for user work domain."""
    NATURALGAS = 'natural_gas', _('Natural Gas')
    LPGGAS = 'lpg_gas', _('LPG Gas')
    BOTH = 'both', _('Both')

class EmployeeLevelChoices(models.TextChoices):
    """Choices for employee level."""
    JUNIOR = 'junior', _('Junior')
    ENGINEER = 'engineer', _('Engineer')


class QuestionCategoryChoices(models.TextChoices):
    """Choices for question categories."""
    SAFETY_LOGIC_PSYCHOLOGY = 'safety_logic_psychology', _('Safety, Logic (IQ), Psychology')
    OTHER = 'other', _('Other')