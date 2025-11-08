from django.urls import path
from .views import (
    UserRegistrationView, LogoutView, UserProfileView, UserProfileDetailView,
    current_user, delete_account, RefreshTokenView, MagicLinkRequestView, 
    MagicLinkLoginView, SocialAuthView, EmailConfirmationView, 
    ResendConfirmationEmailView, CompleteRegistrationView
)

urlpatterns = [
    # Authentication endpoints (passwordless)
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    
    # JWT endpoints
    path('token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    
    # Magic link endpoints
    path('magic-link/request/', MagicLinkRequestView.as_view(), name='magic-link-request'),
    path('magic-link/login/', MagicLinkLoginView.as_view(), name='magic-link-login'),
    
    # Social authentication
    path('social-auth/', SocialAuthView.as_view(), name='social-auth'),
    path('complete-registration/', CompleteRegistrationView.as_view(), name='complete-registration'),
    
    # Email confirmation
    path('confirm-email/<uuid:token>/', EmailConfirmationView.as_view(), name='email-confirmation'),
    path('resend-confirmation/', ResendConfirmationEmailView.as_view(), name='resend-confirmation'),
    
    # Profile management
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile-details/', UserProfileDetailView.as_view(), name='user-profile-details'),
    path('me/', current_user, name='current-user'),
    
    # Account management
    path('delete-account/', delete_account, name='delete-account'),
]
