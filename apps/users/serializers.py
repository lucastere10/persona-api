from rest_framework import serializers
from .models import User, UserProfile, MagicLinkToken, EmailConfirmationToken, UserStatus, AuthProvider
from .authentication import JWTManager


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile in passwordless system
    """
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'birth_date', 'bio', 'location', 'website', 
            'avatar', 'registration_completed', 'provider', 'last_login_method'
        ]
        read_only_fields = ['provider', 'registration_completed']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data in passwordless system
    """
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 
            'status', 'is_email_verified', 'profile', 'date_joined', 'last_login'
        ]
        read_only_fields = ['status', 'is_email_verified']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate_email(self, value):
        """
        Validate email format (uniqueness is handled in the view)
        """
        return value

    def create(self, validated_data):
        """
        Create user for passwordless system
        """
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token response
    """
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    user = UserSerializer(read_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer for refresh token request
    """
    refresh_token = serializers.CharField(required=True)

    def validate_refresh_token(self, value):
        try:
            JWTManager.refresh_access_token(value)
            return value
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class MagicLinkRequestSerializer(serializers.Serializer):
    """
    Serializer for magic link request
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """
        Basic email validation (user existence is handled in the view)
        """
        return value


class MagicLinkLoginSerializer(serializers.Serializer):
    """
    Serializer for magic link login
    """
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        try:
            JWTManager.verify_magic_link_token(value)
            return value
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class SocialAuthSerializer(serializers.Serializer):
    """
    Serializer for social authentication (Google, GitHub)
    """
    provider = serializers.ChoiceField(choices=[AuthProvider.GOOGLE, AuthProvider.GITHUB])
    access_token = serializers.CharField()
    
    # Optional fields that might come from the frontend
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    avatar_url = serializers.URLField(required=False, allow_blank=True)
    social_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """
        Validate social auth data and create/get user
        """
        email = attrs.get('email')
        provider = attrs.get('provider')
        
        if not email:
            raise serializers.ValidationError("Email is required from social provider")
        
        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': attrs.get('first_name', ''),
                'last_name': attrs.get('last_name', ''),
                'status': UserStatus.ACTIVE,  # Social users are active immediately
                'is_email_verified': True,  # Social providers verify emails
            }
        )
        
        # Update profile with social info
        profile = user.profile
        profile.provider = provider
        profile.social_id = attrs.get('social_id', '')
        profile.last_login_method = provider
        
        if created:
            # New social user needs to complete registration
            profile.registration_completed = False
        
        profile.save()
        
        attrs['user'] = user
        attrs['created'] = created
        return attrs


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user information
    """
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile']

    def validate_email(self, value):
        """
        Validate email uniqueness (excluding current user)
        """
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value

    def update(self, instance, validated_data):
        """
        Update user and profile information
        """
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update profile fields
        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance


class EmailConfirmationSerializer(serializers.Serializer):
    """
    Serializer for email confirmation
    """
    token = serializers.UUIDField(required=True)

    def validate_token(self, value):
        """
        Validate confirmation token
        """
        try:
            token = EmailConfirmationToken.objects.get(
                token=value,
                is_used=False
            )
            if token.is_expired():
                raise serializers.ValidationError("Token expirado")
            return value
        except EmailConfirmationToken.DoesNotExist:
            raise serializers.ValidationError("Token inválido")


class ResendConfirmationEmailSerializer(serializers.Serializer):
    """
    Serializer for resending confirmation email
    """
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """
        Validate that user exists and is not verified
        """
        try:
            user = User.objects.get(email=value)
            if user.is_email_verified:
                raise serializers.ValidationError("Esta conta já está verificada")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuário não encontrado")


class CompleteRegistrationSerializer(serializers.Serializer):
    """
    Serializer for completing registration after social login
    """
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)

    def update_user_profile(self, user, validated_data):
        """
        Update user and profile with provided data and mark registration as complete
        """
        # Update user fields
        user.first_name = validated_data.get('first_name', user.first_name)
        user.last_name = validated_data.get('last_name', user.last_name)
        user.save()

        # Update profile fields
        profile = user.profile
        profile.phone_number = validated_data.get('phone_number', profile.phone_number)
        profile.birth_date = validated_data.get('birth_date', profile.birth_date)
        profile.bio = validated_data.get('bio', profile.bio)
        profile.location = validated_data.get('location', profile.location)
        profile.website = validated_data.get('website', profile.website)
        
        # Mark registration as completed
        profile.complete_registration()
        
        return user
