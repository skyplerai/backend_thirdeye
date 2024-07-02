from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from .utils import generate_otp, is_otp_valid
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache

def validate_password_strength(password):
    import re
    if len(password) < 8:
        raise serializers.ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[a-z]', password):
        raise serializers.ValidationError('Password must contain at least one lowercase letter.')
    if not re.search(r'[A-Z]', password):
        raise serializers.ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[0-9]', password):
        raise serializers.ValidationError('Password must contain at least one digit.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise serializers.ValidationError('Password must contain at least one special character: !@#$%^&*()-+')
    return password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=68, min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password']

    def validate(self, attrs):
        email = attrs.get('email', '')
        username = attrs.get('username', '')
        password = attrs.get('password', '')

        if not username.isalnum():
            raise serializers.ValidationError('The username should only contain alphanumeric characters')

        validate_password_strength(password)

        return attrs

class EmailVerificationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    class Meta:
        fields = ['code']

    def validate(self, attrs):
        code = attrs.get('code')

        user_data = cache.get(code)
        if not user_data:
            raise serializers.ValidationError('Invalid or expired verification code')

        return attrs

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255, min_length=3)
    password = serializers.CharField(max_length=68, min_length=6, write_only=True)
    username = serializers.CharField(max_length=255, min_length=3, read_only=True)
    tokens = serializers.SerializerMethodField()

    def get_tokens(self, obj):
        user = User.objects.get(email=obj['email'])
        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access']
        }

    class Meta:
        model = User
        fields = ['email', 'password', 'username', 'tokens']

    def validate(self, attrs):
        email = attrs.get('email', '')
        password = attrs.get('password', '')

        user = authenticate(username=email, password=password)
        if not user:
            raise AuthenticationFailed('Invalid credentials, try again')

        if not user.is_active:
            raise AuthenticationFailed('Account disabled, contact admin')

        if not user.is_verified:
            raise AuthenticationFailed('Email is not verified')

        return {
            'user': user,
            'email': user.email,
            'username': user.username,
            'tokens': user.tokens()
        }

class RequestPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    class Meta:
        fields = ['email']

    def validate(self, attrs):
        email = attrs.get('email', '')
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Email not found')
        return attrs

class SetNewPasswordWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, max_length=68, write_only=True)
    confirm_password = serializers.CharField(min_length=8, max_length=68, write_only=True)

    class Meta:
        fields = ['email', 'otp', 'new_password', 'confirm_password']

    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError('Passwords do not match')

        validate_password_strength(new_password)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or OTP')

        if not is_otp_valid(user) or user.otp != otp:
            raise serializers.ValidationError('Invalid or expired OTP')

        return attrs

    def save(self, **kwargs):
        email = self.validated_data['email']
        new_password = self.validated_data['new_password']
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.otp = None
        user.otp_created_at = None
        user.save()
        return user
