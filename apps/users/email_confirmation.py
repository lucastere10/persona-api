"""
Email confirmation utilities
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
import utils.email as email_utils
from .models import EmailConfirmationToken


class EmailConfirmationService:
    """
    Service for handling email confirmations
    """
    
    @staticmethod
    def create_confirmation_token(user, request=None):
        """
        Create a new email confirmation token for the user
        """
        # Invalidate any existing active tokens for this user
        EmailConfirmationToken.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True, used_at=timezone.now())
        
        # Create new token
        token = EmailConfirmationToken.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
        
        return token
    
    @staticmethod
    def send_confirmation_email(user, token, request=None):
        """
        Send confirmation email to user
        """
        confirmation_url = f"{settings.FRONTEND_URL}/auth/confirm-email/{token.token}/"
        
        try:
            # Use the new email service
            success, message = email_utils.EmailService.send_email_confirmation(
                to_email=user.email,
                confirmation_url=confirmation_url,
                user_name=user.first_name or user.email.split('@')[0]
            )
            
            if success:
                return True
            else:
                print(f"Erro ao enviar email de confirmação: {message}")
                return False
                
        except Exception as e:
            print(f"Erro ao enviar email de confirmação: {str(e)}")
            return False
    
    @staticmethod
    def confirm_email(token_uuid):
        """
        Confirm email using token
        """
        try:
            token = EmailConfirmationToken.objects.get(
                token=token_uuid,
                is_used=False
            )
            
            if token.is_expired():
                return False, "Token expirado"
            
            # Mark token as used
            token.is_used = True
            token.used_at = timezone.now()
            token.save()
            
            # Activate user
            user = token.user
            user.activate()  # Use the activate() method instead of setting is_active directly
            
            return True, "Email confirmado com sucesso"
            
        except EmailConfirmationToken.DoesNotExist:
            return False, "Token inválido"
    
    @staticmethod
    def resend_confirmation_email(email, request=None):
        """
        Resend confirmation email for a user
        """
        from .models import User, UserStatus
        
        try:
            # Filter by status instead of is_active property
            user = User.objects.get(
                email=email, 
                status=UserStatus.PENDING_VERIFICATION
            )
            
            # Create new token
            token = EmailConfirmationService.create_confirmation_token(user, request)
            
            # Send email
            success = EmailConfirmationService.send_confirmation_email(user, token, request)
            
            if success:
                return True, "Email de confirmação reenviado com sucesso"
            else:
                return False, "Erro ao enviar email de confirmação"
                
        except User.DoesNotExist:
            return False, "Usuário não encontrado ou já está verificado"
