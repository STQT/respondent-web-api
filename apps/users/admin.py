from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User, OTPVerification, BranchStaff, PositionStaff, GTFStaff

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (_("Personal info"), {"fields": ("name", "branch", "position")}),
        (_("Phone Verification"), {"fields": ("is_phone_verified",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_moderator",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "name", "branch", "position", "is_moderator", "password1", "password2"),
            },
        ),
    )
    list_display = ["phone_number", "name", "branch", "position", "is_moderator", "is_phone_verified", "is_superuser"]
    list_filter = ["is_staff", "is_superuser", "is_active", "is_moderator", "is_phone_verified", "branch"]
    search_fields = ["name", "phone_number", "branch", "position"]
    ordering = ["phone_number"]


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "otp_code", "is_verified", "created_at", "expires_at"]
    list_filter = ["is_verified", "created_at", "expires_at"]
    search_fields = ["phone_number"]
    readonly_fields = ["created_at", "expires_at"]
    ordering = ["-created_at"]


@admin.register(BranchStaff)
class BranchStaffAdmin(admin.ModelAdmin):
    list_display = ["id", "name_uz", "name_uz_cyrl", "name_ru"]
    search_fields = ["name_uz", "name_uz_cyrl", "name_ru"]
    ordering = ["name_uz"]


@admin.register(PositionStaff)
class PositionStaffAdmin(admin.ModelAdmin):
    list_display = ["id", "name_uz", "name_uz_cyrl", "name_ru"]
    search_fields = ["name_uz", "name_uz_cyrl", "name_ru"]
    ordering = ["name_uz"]


@admin.register(GTFStaff)
class GTFStaffAdmin(admin.ModelAdmin):
    list_display = ["id", "name_uz", "name_uz_cyrl", "name_ru"]
    search_fields = ["name_uz", "name_uz_cyrl", "name_ru"]
    ordering = ["name_uz"]
