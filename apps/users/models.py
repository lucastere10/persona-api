from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid


class UserStatus(models.TextChoices):
    """User status choices"""
    PENDING_VERIFICATION = 'pending_verification', 'Pending Email Verification'
    ACTIVE = 'active', 'Active'
    SUSPENDED = 'suspended', 'Suspended'
    INACTIVE = 'inactive', 'Inactive'


class AuthProvider(models.TextChoices):
    """Authentication provider choices"""
    EMAIL = 'email', 'Email/Magic Link'
    GOOGLE = 'google', 'Google'
    GITHUB = 'github', 'GitHub'


class UserManager(BaseUserManager):
    """
    Custom passwordless user manager
    """
    def create_user(self, email, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        # Por padrão, novos usuários estão pendentes de verificação
        extra_fields.setdefault('status', UserStatus.PENDING_VERIFICATION)
        
        user = self.model(email=email, **extra_fields)
        # Não definir senha - sistema passwordless
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', UserStatus.ACTIVE)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, **extra_fields)


class User(AbstractUser):
    """
    Custom passwordless User model using email as the unique identifier
    """
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.PENDING_VERIFICATION
    )
    is_email_verified = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    @property
    def is_active(self):
        """Override is_active to use status field"""
        return self.status == UserStatus.ACTIVE
    
    def activate(self):
        """Activate user after email verification"""
        self.status = UserStatus.ACTIVE
        self.is_email_verified = True
        self.save(update_fields=['status', 'is_email_verified'])
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class UserProfile(models.Model):
    """
    Extended user profile model for passwordless authentication
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Authentication and registration status
    registration_completed = models.BooleanField(default=False)
    provider = models.CharField(
        max_length=20, 
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL
    )
    social_id = models.CharField(max_length=200, blank=True)
    last_login_method = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        blank=True
    )
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    def complete_registration(self):
        """Mark registration as completed"""
        self.registration_completed = True
        self.save(update_fields=['registration_completed'])
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class MagicLinkToken(models.Model):
    """
    Model to track magic link tokens for security
    """
    email = models.EmailField()
    token_hash = models.CharField(max_length=64)  # SHA256 hash of the token
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Magic Link Token"
        verbose_name_plural = "Magic Link Tokens"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Magic link for {self.email} - {'Used' if self.is_used else 'Active'}"


class EmailConfirmationToken(models.Model):
    """
    Model to track email confirmation tokens
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_confirmation_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Email Confirmation Token"
        verbose_name_plural = "Email Confirmation Tokens"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.is_used:
            status = 'Used'
        elif self.is_expired():
            status = 'Expired'
        else:
            status = 'Active'
        return f"Email confirmation for {self.user.email} - {status}"
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Token expires in 24 hours by default
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile instance when a User is created
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile instance when the User is saved
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()