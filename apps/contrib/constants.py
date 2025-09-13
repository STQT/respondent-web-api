from django.db import models
from django.utils.translation import gettext_lazy as _


class UserWorkDomainChoices(models.TextChoices):
    """Choices for user work domain."""
    NATURALGAS = 'natural_gas', _('Natural Gas')
    LPGGAS = 'lpg_gas', _('LPG Gas')


class EmployeeLevelChoices(models.TextChoices):
    """Choices for employee level."""
    JUNIOR = 'junior', _('Junior')
    ENGINEER = 'engineer', _('Engineer')