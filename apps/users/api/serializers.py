from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from phonenumber_field.serializerfields import PhoneNumberField
from apps.users.models import User, OTPVerification
import random
import string
from datetime import datetime, timedelta
from django.conf import settings
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Пример пользователя",
            value={
                "id": 1,
                "phone_number": "+998901234567",
                "name": "Иван Иванов",
                "position": 1,
                "gtf": 1,
                "work_domain": "natural_gas",
                "employee_level": "engineer",
                "is_moderator": False,
                "is_phone_verified": True,
                # Основные поля (обратная совместимость)
                "branch_name": "Ташкентский филиал",
                "position_name": "Менеджер",
                "gtf_name": "ГТФ-1",
                # Мультиязычные поля
                "branch_name_uz": "Ташкентский филиал",
                "branch_name_uz_cyrl": "Ташкентский филиал",
                "branch_name_ru": "Ташкентский филиал",
                "position_name_uz": "Менеджер",
                "position_name_uz_cyrl": "Менеджер",
                "position_name_ru": "Менеджер",
                "gtf_name_uz": "ГТФ-1",
                "gtf_name_uz_cyrl": "ГТФ-1",
                "gtf_name_ru": "ГТФ-1"
            }
        )
    ]
)
class UserSerializer(serializers.ModelSerializer[User]):
    """Сериализатор для модели пользователя."""
    
    # Основные поля (для обратной совместимости)
    branch_name = serializers.CharField(source='position.branch.name_uz', read_only=True)
    position_name = serializers.CharField(source='position.name_uz', read_only=True)
    gtf_name = serializers.CharField(source='gtf.name_uz', read_only=True)
    
    # Мультиязычные поля
    branch_name_uz = serializers.CharField(source='position.branch.name_uz', read_only=True)
    branch_name_uz_cyrl = serializers.CharField(source='position.branch.name_uz_cyrl', read_only=True)
    branch_name_ru = serializers.CharField(source='position.branch.name_ru', read_only=True)
    
    position_name_uz = serializers.CharField(source='position.name_uz', read_only=True)
    position_name_uz_cyrl = serializers.CharField(source='position.name_uz_cyrl', read_only=True)
    position_name_ru = serializers.CharField(source='position.name_ru', read_only=True)
    
    gtf_name_uz = serializers.CharField(source='gtf.name_uz', read_only=True)
    gtf_name_uz_cyrl = serializers.CharField(source='gtf.name_uz_cyrl', read_only=True)
    gtf_name_ru = serializers.CharField(source='gtf.name_ru', read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id", "phone_number", "name", "position", "gtf", "work_domain", "employee_level", 
            "is_moderator", "is_phone_verified",
            # Основные поля (обратная совместимость)
            "branch_name", "position_name", "gtf_name",
            # Мультиязычные поля
            "branch_name_uz", "branch_name_uz_cyrl", "branch_name_ru",
            "position_name_uz", "position_name_uz_cyrl", "position_name_ru",
            "gtf_name_uz", "gtf_name_uz_cyrl", "gtf_name_ru"
        ]
        read_only_fields = [
            "id", "is_phone_verified", 
            "branch_name", "position_name", "gtf_name",
            "branch_name_uz", "branch_name_uz_cyrl", "branch_name_ru",
            "position_name_uz", "position_name_uz_cyrl", "position_name_ru",
            "gtf_name_uz", "gtf_name_uz_cyrl", "gtf_name_ru"
        ]


class UserCreateSerializer(serializers.ModelSerializer[User]):
    phone_number = PhoneNumberField()
    
    class Meta:
        model = User
        fields = ["phone_number", "name", "position", "gtf", "work_domain", "employee_level"]
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Отправка OTP",
            value={"phone_number": "+998901234567"}
        )
    ]
)
class SendOTPSerializer(serializers.Serializer):
    """Сериализатор для отправки OTP кода."""
    
    phone_number = PhoneNumberField(help_text="Номер телефона в формате +998XXXXXXXXX")
    
    def validate_phone_number(self, value):
        # Check if phone number is valid format for Uzbekistan
        if not str(value).startswith('+998'):
            raise serializers.ValidationError(_("Phone number must be an Uzbek number starting with +998"))
        return value
    
    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        
        # Delete old OTP codes for this phone number
        OTPVerification.objects.filter(phone_number=phone_number, is_verified=False).delete()
        
        # Create new OTP
        otp = OTPVerification.objects.create(phone_number=phone_number)
        
        # TODO: Integrate with SMS service to send OTP
        # For now, we'll just log it or return it in development
        print(f"OTP for {phone_number}: {otp.otp_code}")
        
        return otp


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Верификация OTP",
            value={
                "phone_number": "+998901234567",
                "otp_code": "123456"
            }
        )
    ]
)
class VerifyOTPSerializer(serializers.Serializer):
    """Сериализатор для проверки OTP кода."""
    
    phone_number = PhoneNumberField(help_text="Номер телефона")
    otp_code = serializers.CharField(
        max_length=6, 
        min_length=6, 
        help_text="6-значный OTP код"
    )
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
        # Логирование для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Verifying OTP: phone={phone_number}, code={otp_code}")

        # Специальный код для разработки
        if otp_code == "111111":
            # Создаем фиктивный объект OTP для тестирования
            class MockOTP:
                def __init__(self, phone_number):
                    self.phone_number = phone_number
                    self.is_verified = False
                
                def save(self):
                    pass
            
            attrs['otp'] = MockOTP(phone_number)
            return attrs
        try:
            otp = OTPVerification.objects.get(
                phone_number=phone_number,
                otp_code=otp_code,
                is_verified=False
            )
            
        except OTPVerification.DoesNotExist:
            raise serializers.ValidationError(_("Invalid OTP code"))
        
        if otp.is_expired():
            raise serializers.ValidationError(_("OTP code has expired"))
        
        attrs['otp'] = otp
        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Вход существующего пользователя",
            value={
                "phone_number": "+998901234567",
                "otp_code": "123456"
            }
        ),
        OpenApiExample(
            name="Регистрация нового пользователя",
            value={
                "phone_number": "+998901234567",
                "otp_code": "123456",
                "name": "Иван Иванов",
                "position_id": 1,
                "gtf_id": 1,
                "work_domain": "natural_gas",
                "employee_level": "engineer"
            }
        )
    ]
)
class PhoneLoginSerializer(serializers.Serializer):
    """Сериализатор для входа/регистрации по номеру телефона."""
    
    phone_number = PhoneNumberField(help_text="Номер телефона")
    otp_code = serializers.CharField(
        max_length=6, 
        min_length=6, 
        help_text="6-значный OTP код"
    )
    name = serializers.CharField(
        max_length=255, 
        required=False, 
        help_text="Полное имя (для новых пользователей)"
    )
    position_id = serializers.IntegerField(
        required=False, 
        help_text="ID должности (для новых пользователей)"
    )
    gtf_id = serializers.IntegerField(
        required=False, 
        help_text="ID GTF (для новых пользователей)"
    )
    work_domain = serializers.ChoiceField(
        choices=[('natural_gas', 'Natural Gas'), ('lpg_gas', 'LPG Gas')],
        required=False,
        help_text="Домен работы (для новых пользователей)"
    )
    employee_level = serializers.ChoiceField(
        choices=[('junior', 'Junior'), ('engineer', 'Engineer')],
        required=False,
        help_text="Уровень сотрудника (для новых пользователей)"
    )
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
        # Логирование для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"PhoneLoginSerializer validating: phone={phone_number}, code={otp_code}")

        # Специальный код для разработки
        if otp_code == "111111":
            # Создаем фиктивный объект OTP для тестирования
            class MockOTP:
                def __init__(self, phone_number):
                    self.phone_number = phone_number
                    self.is_verified = False
                
                def save(self):
                    pass
            
            otp = MockOTP(phone_number)
        else:
            # Verify OTP
            try:
                otp = OTPVerification.objects.get(
                    phone_number=phone_number,
                    otp_code=otp_code,
                    is_verified=False
                )
            except OTPVerification.DoesNotExist:
                raise serializers.ValidationError(_("Invalid OTP code"))
            
            if otp.is_expired():
                raise serializers.ValidationError(_("OTP code has expired"))
        
        # Validate position_id if provided
        if attrs.get('position_id'):
            try:
                from apps.users.models import PositionStaff
                position = PositionStaff.objects.get(id=attrs.get('position_id'))
                work_domain = attrs.get('work_domain', '')
                if not work_domain and position.work_domain:
                    work_domain = position.work_domain
                attrs['work_domain'] = work_domain
            except PositionStaff.DoesNotExist:
                raise serializers.ValidationError(_("Invalid position_id"))
        
        # Validate gtf_id if provided
        if attrs.get('gtf_id'):
            try:
                from apps.users.models import GTFStaff
                GTFStaff.objects.get(id=attrs.get('gtf_id'))
            except GTFStaff.DoesNotExist:
                raise serializers.ValidationError(_("Invalid gtf_id"))

        # Get or create user
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'name': attrs.get('name', ''),
                'position_id': attrs.get('position_id'),
                'gtf_id': attrs.get('gtf_id'),
                'work_domain': work_domain,
                'employee_level': attrs.get('employee_level', ''),
                'is_phone_verified': True
            }
        )
        
        if not created:
            # Update user info if provided
            if attrs.get('name'):
                user.name = attrs.get('name')
            if attrs.get('position_id'):
                user.position_id = attrs.get('position_id')
                # Update work_domain from position if not explicitly provided
                if not attrs.get('work_domain'):
                    try:
                        from apps.users.models import PositionStaff
                        position = PositionStaff.objects.get(id=attrs.get('position_id'))
                        if position.work_domain:
                            user.work_domain = position.work_domain
                    except PositionStaff.DoesNotExist:
                        pass
            if attrs.get('gtf_id'):
                user.gtf_id = attrs.get('gtf_id')
            if attrs.get('work_domain'):
                user.work_domain = attrs.get('work_domain')
            if attrs.get('employee_level'):
                user.employee_level = attrs.get('employee_level')
            user.is_phone_verified = True
            user.save()
        
        # Mark OTP as verified
        otp.is_verified = True
        otp.save()
        
        attrs['user'] = user
        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Получение JWT токенов",
            value={
                "phone_number": "+998901234567",
                "password": "password123"
            }
        )
    ]
)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный сериализатор для получения JWT токенов."""
    
    username_field = 'phone_number'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'] = PhoneNumberField(help_text="Номер телефона")
        if 'username' in self.fields:
            del self.fields['username']
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['name'] = user.name
        token['phone_number'] = str(user.phone_number)
        token['is_moderator'] = user.is_moderator
        return token


# Дополнительные сериализаторы для Swagger документации

class TokenResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа с токенами."""
    
    access = serializers.CharField(help_text="Access токен")
    refresh = serializers.CharField(help_text="Refresh токен")


class LoginResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа при входе."""
    
    user = UserSerializer(help_text="Информация о пользователе")
    tokens = TokenResponseSerializer(help_text="JWT токены")


class OTPResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа при отправке OTP."""
    
    message = serializers.CharField(help_text="Сообщение о статусе")
    phone_number = serializers.CharField(help_text="Номер телефона")
    otp_code = serializers.CharField(
        required=False, 
        help_text="OTP код (только в режиме разработки)"
    )


class UserSearchResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа поиска пользователей."""
    
    results = UserSerializer(many=True, help_text="Результаты поиска")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Обновление профиля",
            value={
                "name": "Иван Петров",
                "position": 2,
                "gtf": 2,
                "work_domain": "lpg_gas",
                "employee_level": "junior"
            }
        )
    ]
)
class UserProfileUpdateSerializer(serializers.ModelSerializer[User]):
    """Сериализатор для обновления профиля пользователя."""
    
    class Meta:
        model = User
        fields = ["name", "position", "gtf", "employee_level", "work_domain"]
    
    def validate_name(self, value):
        """Валидация имени."""
        if not value or not value.strip():
            raise serializers.ValidationError(_("Name cannot be empty"))
        return value.strip()
