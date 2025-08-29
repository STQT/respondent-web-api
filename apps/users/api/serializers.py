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


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "phone_number", "name", "branch", "position", "is_moderator", "is_phone_verified"]
        read_only_fields = ["id", "is_phone_verified"]


class UserCreateSerializer(serializers.ModelSerializer[User]):
    phone_number = PhoneNumberField()
    
    class Meta:
        model = User
        fields = ["phone_number", "name", "branch", "position"]
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class SendOTPSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    
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


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
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


class PhoneLoginSerializer(serializers.Serializer):
    phone_number = PhoneNumberField()
    otp_code = serializers.CharField(max_length=6, min_length=6)
    name = serializers.CharField(max_length=255, required=False)
    branch = serializers.CharField(max_length=100, required=False)
    position = serializers.CharField(max_length=100, required=False)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        
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
        
        # Get or create user
        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'name': attrs.get('name', ''),
                'branch': attrs.get('branch', ''),
                'position': attrs.get('position', ''),
                'is_phone_verified': True
            }
        )
        
        if not created:
            # Update user info if provided
            if attrs.get('name'):
                user.name = attrs.get('name')
            if attrs.get('branch'):
                user.branch = attrs.get('branch')
            if attrs.get('position'):
                user.position = attrs.get('position')
            user.is_phone_verified = True
            user.save()
        
        # Mark OTP as verified
        otp.is_verified = True
        otp.save()
        
        attrs['user'] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'phone_number'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'] = PhoneNumberField()
        del self.fields['username']
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['name'] = user.name
        token['phone_number'] = str(user.phone_number)
        token['is_moderator'] = user.is_moderator
        return token
