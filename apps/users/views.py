from django.contrib.auth import logout
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from rest_framework import generics, status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
import hashlib
import utils.email as email_utils
import secrets
from .models import User, UserProfile, MagicLinkToken, EmailConfirmationToken, UserStatus, AuthProvider
from .authentication import JWTManager
from .email_confirmation import EmailConfirmationService
from .serializers import (
    UserSerializer, UserUpdateSerializer, UserProfileSerializer,
    TokenResponseSerializer, RefreshTokenSerializer, MagicLinkRequestSerializer,
    MagicLinkLoginSerializer, SocialAuthSerializer, EmailConfirmationSerializer,
    ResendConfirmationEmailSerializer, CompleteRegistrationSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user in passwordless system
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        
        # Check if user already exists
        try:
            existing_user = User.objects.get(email=email)
            if existing_user.status == UserStatus.PENDING_VERIFICATION:
                # Create new confirmation token and resend email
                token = EmailConfirmationService.create_confirmation_token(existing_user, request)
                email_sent = EmailConfirmationService.send_confirmation_email(existing_user, token, request)
                
                return Response({
                    'message': 'Seu email está pendente de confirmação. Um novo email de confirmação foi enviado.',
                    'email_sent': email_sent,
                    'next_step': 'email_confirmation'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Este email já está cadastrado.',
                    'email_sent': False,
                    'next_step': 'login'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            # Create new user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Create email confirmation token
            token = EmailConfirmationService.create_confirmation_token(user, request)
            
            # Send confirmation email
            email_sent = EmailConfirmationService.send_confirmation_email(user, token, request)
            
            return Response({
                'message': 'Usuário criado com sucesso. Verifique seu email para ativar a conta.',
                'email_sent': email_sent,
                'next_step': 'email_confirmation'
            }, status=status.HTTP_201_CREATED)


class MagicLinkRequestView(APIView):
    """
    Request a magic link for passwordless authentication
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MagicLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            # Check if user exists
            user = User.objects.get(email=email)
            
            # If user is pending verification, send confirmation email instead
            if user.status == UserStatus.PENDING_VERIFICATION:
                token = EmailConfirmationService.create_confirmation_token(user, request)
                email_sent = EmailConfirmationService.send_confirmation_email(user, token, request)
                
                return Response({
                    'message': 'Seu email está pendente de confirmação. Um email de confirmação foi enviado.',
                    'email_sent': email_sent,
                    'next_step': 'email_confirmation'
                }, status=status.HTTP_200_OK)
            
            # If user is active, send magic link
            elif user.status == UserStatus.ACTIVE:
                # Generate magic link token
                token = JWTManager.create_magic_link_token(email)
                
                # Store token info for security tracking
                MagicLinkToken.objects.create(
                    email=email,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Send magic link email
                magic_link = f"{settings.FRONTEND_URL}/verify-your-email?token={token}"
                
                success, _ = email_utils.EmailService.send_magic_link_email(
                    to_email=email,
                    magic_link=magic_link,
                    valid_minutes=15
                )
                
                return Response({
                    'message': 'Link de acesso enviado para seu email.',
                    'email_sent': success,
                    'next_step': 'magic_link_login'
                }, status=status.HTTP_200_OK)
            
            else:
                return Response({
                    'error': 'Conta suspensa ou inativa. Entre em contato com o suporte.'
                }, status=status.HTTP_403_FORBIDDEN)
                
        except User.DoesNotExist:
            return Response({
                'error': 'Usuário não encontrado. Você precisa se registrar primeiro.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({
                'error': 'Erro ao processar solicitação. Tente novamente.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MagicLinkLoginView(APIView):
    """
    Login using magic link token
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MagicLinkLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            # Verify and get email from token
            email = JWTManager.verify_magic_link_token(token)
            
            # Get user
            user = User.objects.get(email=email)
            
            # Mark magic link as used
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            magic_link_token = MagicLinkToken.objects.filter(
                email=email, 
                token_hash=token_hash,
                is_used=False
            ).first()
            
            if magic_link_token:
                magic_link_token.is_used = True
                magic_link_token.used_at = timezone.now()
                magic_link_token.save()
            
            # Update last login method
            user.profile.last_login_method = AuthProvider.EMAIL
            user.profile.save()
            
            # Activate user if not active
            if user.status != UserStatus.ACTIVE:
                user.activate()
            
            # Create JWT tokens
            tokens = JWTManager.create_tokens(user)
            
            return Response({
                'message': 'Login realizado com sucesso',
                'user': UserSerializer(user).data,
                **tokens
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'Usuário não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({
                'error': 'Token inválido ou expirado'
            }, status=status.HTTP_400_BAD_REQUEST)


class SocialAuthView(APIView):
    """
    Social authentication (Google, GitHub) - Passwordless System
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        created = serializer.validated_data['created']
        
        # Update last login method
        user.profile.last_login_method = serializer.validated_data.get('provider', user.profile.provider)
        user.profile.save()
        
        # Create JWT tokens
        tokens = JWTManager.create_tokens(user)
        
        response_data = {
            'user': UserSerializer(user).data,
            'registration_completed': user.profile.registration_completed,
            'created': created,
            **tokens
        }
        
        if created:
            response_data['message'] = 'Conta criada com sucesso via social login'
            response_data['next_step'] = 'complete_registration' if not user.profile.registration_completed else None
        else:
            response_data['message'] = 'Login realizado com sucesso'
            
        return Response(response_data, status=status.HTTP_200_OK)


class CompleteRegistrationView(APIView):
    """
    Complete registration after social login
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = CompleteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.update_user_profile(request.user, serializer.validated_data)
        
        return Response({
            'message': 'Cadastro concluído com sucesso',
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User logout (for JWT token invalidation if needed)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # For JWT-based auth, logout is typically handled client-side
        # Here we could add token blacklisting if needed
        logout(request)
        return Response({
            'message': 'Logout realizado com sucesso'
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update user profile
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserProfileDetailView(generics.RetrieveAPIView):
    """
    Retrieve user profile details only
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


class EmailConfirmationView(APIView):
    """
    Confirm email address using token
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, token=None):
        # Token can come from URL parameter or request body
        token_value = token or request.data.get('token')
        
        if not token_value:
            return Response({
                'error': 'Token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        success, message = EmailConfirmationService.confirm_email(token_value)
        
        if success:
            # Get the user to create tokens
            try:
                confirmation_token = EmailConfirmationToken.objects.get(
                    token=token_value,
                    is_used=True
                )
                user = confirmation_token.user
                
                # Create JWT tokens for the now active user
                tokens = JWTManager.create_tokens(user)
                
                return Response({
                    'message': message,
                    **tokens
                }, status=status.HTTP_200_OK)
                
            except EmailConfirmationToken.DoesNotExist:
                return Response({
                    'message': message
                }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendConfirmationEmailView(APIView):
    """
    Resend email confirmation
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendConfirmationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        success, message = EmailConfirmationService.resend_confirmation_email(email, request)
        
        if success:
            return Response({
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user information
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_account(request):
    """
    Delete user account (passwordless system - no password verification)
    """
    user = request.user
    
    # For passwordless system, we'll use a different verification method
    # Could be email confirmation or other secure method
    confirmation = request.data.get('confirmation')
    if confirmation != 'DELETE_MY_ACCOUNT':
        return Response({
            'error': 'Please type "DELETE_MY_ACCOUNT" to confirm account deletion'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete user account
    user.delete()
    
    return Response({
        'message': 'Account deleted successfully'
    }, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    """
    Refresh JWT access token
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            tokens = JWTManager.refresh_access_token(serializer.validated_data['refresh_token'])
            return Response(tokens, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)