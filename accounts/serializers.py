from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile, Address, OTPVerification

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 
                  'phone_number', 'is_verified', 'date_joined']
        read_only_fields = ['id', 'date_joined', 'is_verified']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'avatar', 'date_of_birth', 'gender',
                 'receive_email_notifications', 'receive_sms_notifications',
                 'default_delivery_address', 'default_delivery_city']
        read_only_fields = ['id']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password2', 
                  'first_name', 'last_name', 'phone_number']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', '')
        )
        return user

class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD  # 'email'

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom response data
        data.update({
            'user': {
                'id': str(self.user.id),
                'email': self.user.email,
                'username': self.user.username,
                'is_verified': self.user.is_verified,
            }
        })
        return data

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'name', 'phone_number', 'address_line1', 'address_line2',
                 'city', 'town', 'province', 'postal_code', 'is_default', 'address_type']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    token = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

class OTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    otp_type = serializers.ChoiceField(choices=['email_verification', 'phone_verification', 'password_reset'])

class OTPVerifySerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    otp_code = serializers.CharField(required=True, max_length=6)
    otp_type = serializers.ChoiceField(choices=['email_verification', 'phone_verification', 'password_reset'])