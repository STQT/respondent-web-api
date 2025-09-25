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
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("phone_number",)}),
        (_("Password"), {"fields": ("password1", "password2")}),
        (_("Personal info"), {"fields": ("name", "position", "gtf", "work_domain", "employee_level")}),
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
                "fields": ("phone_number", "password1", "password2"),
            },
        ),
        (
            _("Personal info"),
            {
                "fields": ("name", "position", "gtf", "work_domain", "employee_level"),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": ("is_moderator",),
            },
        ),
    )
    list_display = ["phone_number", "name", "get_position_name", "get_gtf_name", "work_domain", "employee_level", "is_moderator", "is_phone_verified", "is_superuser"]
    list_filter = ["is_staff", "is_superuser", "is_active", "is_moderator", "is_phone_verified", "position", "gtf", "work_domain", "employee_level"]
    search_fields = ["name", "phone_number", "position__name_uz", "gtf__name_uz"]
    ordering = ["phone_number"]
    
    def get_position_name(self, obj):
        """Получить название должности"""
        return obj.position.name_uz if obj.position else "-"
    get_position_name.short_description = "Должность"
    get_position_name.admin_order_field = "position__name_uz"
    
    def get_gtf_name(self, obj):
        """Получить название GTF"""
        return obj.gtf.name_uz if obj.gtf else "-"
    get_gtf_name.short_description = "GTF"
    get_gtf_name.admin_order_field = "gtf__name_uz"


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
    list_display = ["id", "name_uz", "name_uz_cyrl", "name_ru", "branch"]
    list_filter = ["branch"]
    search_fields = ["name_uz", "name_uz_cyrl", "name_ru", "branch__name_uz"]
    ordering = ["name_uz"]


@admin.register(GTFStaff)
class GTFStaffAdmin(admin.ModelAdmin):
    list_display = ["id", "name_uz", "name_uz_cyrl", "name_ru"]
    search_fields = ["name_uz", "name_uz_cyrl", "name_ru"]
    ordering = ["name_uz"]
