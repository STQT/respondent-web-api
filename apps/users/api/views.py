from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

from apps.users.models import User, OTPVerification
from .serializers import (
    UserSerializer, 
    SendOTPSerializer, 
    VerifyOTPSerializer, 
    PhoneLoginSerializer,
    CustomTokenObtainPairSerializer,
    OTPResponseSerializer,
    LoginResponseSerializer,
    TokenResponseSerializer,
    UserSearchResponseSerializer
)


@extend_schema_view(
    post=extend_schema(
        summary="Отправить OTP код",
        description="""Отправляет OTP код на указанный номер телефона для верификации.
        
        В режиме разработки возвращает OTP код в ответе для тестирования.
        В продакшене код отправляется только через SMS.""",
        tags=["Аутентификация"],
        request=SendOTPSerializer,
        responses={
            200: OTPResponseSerializer,
            400: {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Phone number must be an Uzbek number starting with +998"]
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Успешная отправка OTP",
                request_only=True,
                value={"phone_number": "+998901234567"}
            )
        ]
    )
)
class SendOTPView(APIView):
    """Send OTP to phone number for verification."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.save()
            return Response({
                'message': _('OTP sent successfully'),
                'phone_number': str(otp.phone_number),
                # In development, return the OTP code. Remove in production!
                'otp_code': otp.otp_code if settings.DEBUG else None
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Верифицировать OTP код",
        description="""Проверяет правильность введенного OTP кода.
        
        Код должен быть получен через эндпоинт send-otp и не должен быть просрочен.""",
        tags=["Аутентификация"],
        request=VerifyOTPSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "example": "OTP verified successfully"},
                    "phone_number": {"type": "string", "example": "+998901234567"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "non_field_errors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Invalid OTP code"]
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Верификация OTP",
                request_only=True,
                value={
                    "phone_number": "+998901234567",
                    "otp_code": "123456"
                }
            )
        ]
    )
)
class VerifyOTPView(APIView):
    """Verify OTP code."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            otp.is_verified = True
            otp.save()
            
            return Response({
                'message': _('OTP verified successfully'),
                'phone_number': str(otp.phone_number)
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Вход/регистрация через номер телефона",
        description="""Авторизует пользователя по номеру телефона и OTP коду.
        
        Если пользователь с данным номером не существует, создается новый аккаунт.
        Возвращает JWT токены для дальнейшей аутентификации.""",
        tags=["Аутентификация"],
        request=PhoneLoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: {
                "type": "object",
                "properties": {
                    "non_field_errors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Invalid OTP code"]
                    }
                }
            }
        },
        examples=[
            OpenApiExample(
                name="Вход существующего пользователя",
                request_only=True,
                value={
                    "phone_number": "+998901234567",
                    "otp_code": "123456"
                }
            ),
            OpenApiExample(
                name="Регистрация нового пользователя",
                request_only=True,
                value={
                    "phone_number": "+998901234567",
                    "otp_code": "123456",
                    "name": "Иван Иванов",
                    "branch": "Ташкент",
                    "position": "Менеджер"
                }
            )
        ]
    )
)
class PhoneLoginView(APIView):
    """Login or register user with phone number and OTP."""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            # Add custom claims
            access['name'] = user.name
            access['phone_number'] = str(user.phone_number)
            access['is_moderator'] = user.is_moderator
            
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access),
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Получить JWT токены",
    description="""Получает пары JWT токенов (access и refresh) для аутентификации.
    
    Альтернативный способ получения токенов через стандартный эндпоинт DRF.""",
    tags=["Аутентификация"],
    request=CustomTokenObtainPairSerializer,
    responses={
        200: TokenResponseSerializer,
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "No active account found with the given credentials"}
            }
        }
    }
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain pair view for phone number authentication."""
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Список пользователей",
        description="""Получить список пользователей.
        
        Модераторы видят всех пользователей, обычные пользователи - только себя.""",
        tags=["Пользователи"],
        responses={200: UserSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Детали пользователя",
        description="Получить подробную информацию о пользователе по ID.",
        tags=["Пользователи"],
        responses={200: UserSerializer}
    ),
    update=extend_schema(
        summary="Обновить пользователя",
        description="Обновить информацию о пользователе.",
        tags=["Пользователи"],
        request=UserSerializer,
        responses={200: UserSerializer}
    ),
    partial_update=extend_schema(
        summary="Частично обновить пользователя",
        description="Частично обновить информацию о пользователе.",
        tags=["Пользователи"],
        request=UserSerializer,
        responses={200: UserSerializer}
    )
)
class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    
    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        if user.is_moderator:
            # Moderators can see all users
            return self.queryset.all()
        else:
            # Regular users can only see themselves
            return self.queryset.filter(id=user.id)

    @extend_schema(
        summary="Мой профиль",
        description="Получить информацию о текущем аутентифицированном пользователе.",
        tags=["Пользователи"],
        responses={200: UserSerializer}
    )
    @action(detail=False)
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    
    @extend_schema(
        summary="Поиск пользователей",
        description="""Поиск пользователей по имени или номеру телефона.
        
        Доступно только модераторам. Возвращает максимум 20 результатов.""",
        tags=["Пользователи"],
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Поисковый запрос (имя или номер телефона)',
                required=True,
                examples=[OpenApiExample(name="Поиск по имени", value="Иван")]
            )
        ],
        responses={
            200: UserSearchResponseSerializer,
            403: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "example": "Permission denied"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def search(self, request):
        """Search users by name or phone number (for moderators only)."""
        if not request.user.is_moderator:
            return Response(
                {'error': _('Permission denied')}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        query = request.query_params.get('q', '')
        if not query:
            return Response({'results': []}, status=status.HTTP_200_OK)
        
        users = User.objects.filter(
            Q(name__icontains=query) | 
            Q(phone_number__icontains=query)
        )[:20]  # Limit to 20 results
        
        serializer = UserSerializer(users, many=True)
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)
