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

from apps.users.models import User, OTPVerification
from .serializers import (
    UserSerializer, 
    SendOTPSerializer, 
    VerifyOTPSerializer, 
    PhoneLoginSerializer,
    CustomTokenObtainPairSerializer
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


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain pair view for phone number authentication."""
    serializer_class = CustomTokenObtainPairSerializer


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

    @action(detail=False)
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)
    
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
