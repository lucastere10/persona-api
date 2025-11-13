import resend
import os
from django.conf import settings
from django.template import Template, Context
from typing import Dict, Any, Tuple, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Resend API
resend.api_key = settings.RESEND_API_KEY


class EmailTemplateService:
    """
    Service for loading and rendering email templates
    """
    
    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'email_templates')
    
    @classmethod
    def load_template(cls, template_name: str, is_html: bool = True) -> str:
        """
        Load email template from file
        
        Args:
            template_name: Name of the template (without extension)
            is_html: Whether to load HTML or text version
            
        Returns:
            Template content as string
        """
        extension = 'html' if is_html else 'txt'
        template_path = os.path.join(cls.TEMPLATE_DIR, f"{template_name}.{extension}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"Template not found: {template_path}")
            raise FileNotFoundError(f"Email template '{template_name}.{extension}' not found")
    
    @classmethod
    def render_template(cls, template_content: str, context: Dict[str, Any]) -> str:
        """
        Render template with context data
        
        Args:
            template_content: Template content string
            context: Dictionary with template variables
            
        Returns:
            Rendered template content
        """
        template = Template(template_content)
        django_context = Context(context)
        return template.render(django_context)
    
    @classmethod
    def prepare_email_content(cls, template_name: str, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        Prepare both HTML and text versions of email content
        
        Args:
            template_name: Name of the template
            context: Dictionary with template variables
            
        Returns:
            Tuple of (html_content, text_content)
        """
        try:
            # Load and render HTML template
            html_template = cls.load_template(template_name, is_html=True)
            html_content = cls.render_template(html_template, context)
            
            # Load and render text template
            text_template = cls.load_template(template_name, is_html=False)
            text_content = cls.render_template(text_template, context)
            
            return html_content, text_content
            
        except Exception as e:
            logger.error(f"Error preparing email content for template '{template_name}': {str(e)}")
            raise


class EmailService:
    """
    Enhanced email service using Resend API with template support
    """
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Send email using Resend API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Name of email template (if using templates)
            context: Context data for template rendering
            html_content: Direct HTML content (if not using templates)
            text_content: Direct text content (if not using templates)
            from_email: Sender email (defaults to settings.DEFAULT_FROM_EMAIL)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Determine content source
            if template_name and context:
                html_content, text_content = EmailTemplateService.prepare_email_content(
                    template_name, context
                )
            elif not html_content and not text_content:
                raise ValueError("Either provide template_name with context or direct content")
            
            # Prepare email data
            email_data = {
                "from": from_email or f"Persona API <{settings.DEFAULT_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
            }
            
            # Add content
            if html_content:
                email_data["html"] = html_content
            if text_content:
                email_data["text"] = text_content
            
            # Send email
            response = resend.Emails.send(email_data)
            
            logger.info(f"Email sent successfully to {to_email}. ID: {response.get('id', 'N/A')}")
            return True, f"Email sent successfully. ID: {response.get('id', 'N/A')}"
            
        except Exception as e:
            error_msg = f"Failed to send email to {to_email}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def send_magic_link_email(to_email: str, magic_link: str, valid_minutes: int = 15) -> Tuple[bool, str]:
        """
        Send magic link email
        
        Args:
            to_email: Recipient email address
            magic_link: The magic link URL
            valid_minutes: Number of minutes the link is valid
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        context = {
            'magic_link': magic_link,
            'email': to_email,
            'valid_minutes': valid_minutes,
        }
        
        return EmailService.send_email(
            to_email=to_email,
            subject='DRO/P - Link de acesso',
            template_name='magic_link',
            context=context
        )
    
    @staticmethod
    def send_email_confirmation(
        to_email: str, 
        confirmation_url: str, 
        user_name: str = None
    ) -> Tuple[bool, str]:
        """
        Send email confirmation email
        
        Args:
            to_email: Recipient email address
            confirmation_url: The confirmation URL
            user_name: User's name (optional)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        context = {
            'confirmation_url': confirmation_url,
            'email': to_email,
            'user_name': user_name or 'usuário',
        }
        
        return EmailService.send_email(
            to_email=to_email,
            subject='DRO/P - Confirme seu email',
            template_name='email_confirmation',
            context=context
        )


# Backward compatibility functions
def send_magic_link_email(to_email: str, subject: str, html: str):
    """
    Legacy function for backward compatibility
    """
    return resend.Emails.send({
        "from": f"No Reply <{settings.DEFAULT_FROM_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html
    })


def send_html_email(to_email: str, subject: str, html_content: str, plain_content: str = None):
    """
    Enhanced function for sending HTML emails with fallback text
    """
    success, message = EmailService.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=plain_content
    )
    
    if not success:
        raise RuntimeError(message)
    
    return True