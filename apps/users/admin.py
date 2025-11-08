from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, MagicLinkToken, EmailConfirmationToken


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'phone_number', 'birth_date', 'bio', 'location', 'website', 'avatar', 
        'registration_completed', 'provider', 'social_id', 'last_login_method'
    ]
    readonly_fields = ['provider', 'social_id', 'last_login_method']


class UserAdmin(BaseUserAdmin):
    """
    Extended User admin for passwordless system
    """
    inlines = [UserProfileInline]
    list_display = ['email', 'first_name', 'last_name', 'status', 'is_email_verified', 'is_staff', 'date_joined']
    list_filter = ['status', 'is_staff', 'is_email_verified', 'date_joined', 'profile__provider']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    # Customize the fieldsets for passwordless system
    fieldsets = (
        (None, {'fields': ('email', 'status', 'is_email_verified')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'status'),
        }),
    )
    readonly_fields = ['is_email_verified']


class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile
    """
    list_display = ['user', 'phone_number', 'location', 'registration_completed', 'provider', 'created_at']
    list_filter = ['registration_completed', 'provider', 'created_at']
    search_fields = ['user__email', 'phone_number', 'location']
    readonly_fields = ['created_at', 'updated_at', 'provider', 'social_id', 'last_login_method']
    ordering = ['-created_at']


class MagicLinkTokenAdmin(admin.ModelAdmin):
    """
    Admin for MagicLinkToken
    """
    list_display = ['email', 'is_used', 'created_at', 'used_at', 'ip_address']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['token_hash', 'created_at', 'used_at']


class EmailConfirmationTokenAdmin(admin.ModelAdmin):
    """
    Admin for EmailConfirmationToken
    """
    list_display = ['user', 'is_used', 'is_expired_display', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['token', 'created_at', 'used_at']
    
    def is_expired_display(self, obj):
        return obj.is_expired()
    is_expired_display.short_description = 'Is Expired'
    is_expired_display.boolean = True


# Register the models
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(MagicLinkToken, MagicLinkTokenAdmin)
admin.site.register(EmailConfirmationToken, EmailConfirmationTokenAdmin)
