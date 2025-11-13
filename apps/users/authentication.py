import jwt
import datetime
from django.conf import settings
from rest_framework import authentication, exceptions
from typing import Optional, Tuple, Dict, Any
from .models import User


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication class for Django REST Framework
    """
    
    def authenticate(self, request) -> Optional[Tuple[User, Dict[str, Any]]]:
        """
        Authenticate the request and return a two-tuple of (user, token) if successful.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        try:
            payload = self.verify_token(token)
            user = self.get_user_from_payload(payload)
            return user, payload
        except (jwt.InvalidTokenError, User.DoesNotExist, ValueError):
            return None
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode the JWT token
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE
            )
            
            # Check if token is expired
            if payload.get('exp', 0) < datetime.datetime.now(datetime.timezone.utc).timestamp():
                raise jwt.ExpiredSignatureError('Token has expired')
                
            return payload
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def get_user_from_payload(self, payload: Dict[str, Any]) -> User:
        """
        Get user from JWT payload
        """
        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Token payload invalid')
            
        try:
            user = User.objects.get(id=user_id)
            if not user.is_active:
                raise exceptions.AuthenticationFailed('User account is disabled')
            return user
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')


class JWTManager:
    """
    JWT Token Manager for creating and managing tokens
    """
    
    @staticmethod
    def create_tokens(user: User) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Access token payload
        access_payload = {
            'user_id': user.id,
            'email': user.email,
            'type': 'access',
            'iat': now.timestamp(),
            'exp': (now + settings.JWT_ACCESS_TOKEN_LIFETIME).timestamp(),
            'iss': settings.JWT_ISSUER,
            'aud': settings.JWT_AUDIENCE,
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': user.id,
            'type': 'refresh',
            'iat': now.timestamp(),
            'exp': (now + settings.JWT_REFRESH_TOKEN_LIFETIME).timestamp(),
            'iss': settings.JWT_ISSUER,
            'aud': settings.JWT_AUDIENCE,
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Dict[str, str]:
        """
        Create a new access token from a valid refresh token
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE
            )
            
            if payload.get('type') != 'refresh':
                raise jwt.InvalidTokenError('Not a refresh token')
            
            user = User.objects.get(id=payload['user_id'])
            if not user.is_active:
                raise ValueError('User account is disabled')
                
            # Create new access token
            now = datetime.datetime.now(datetime.timezone.utc)
            access_payload = {
                'user_id': user.id,
                'email': user.email,
                'type': 'access',
                'iat': now.timestamp(),
                'exp': (now + settings.JWT_ACCESS_TOKEN_LIFETIME).timestamp(),
                'iss': settings.JWT_ISSUER,
                'aud': settings.JWT_AUDIENCE,
            }
            
            access_token = jwt.encode(
                access_payload,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': int(settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
            }
            
        except (jwt.InvalidTokenError, User.DoesNotExist) as e:
            raise ValueError(f'Invalid refresh token: {str(e)}')
    
    @staticmethod
    def create_magic_link_token(email: str) -> str:
        """
        Create a magic link token for passwordless authentication
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            'email': email,
            'type': 'magic_link',
            'iat': now.timestamp(),
            'exp': (now + settings.MAGIC_LINK_TOKEN_LIFETIME).timestamp(),
            'iss': settings.JWT_ISSUER,
            'aud': settings.JWT_AUDIENCE,
        }
        
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
    
    @staticmethod
    def verify_magic_link_token(token: str) -> str:
        """
        Verify magic link token and return email
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE
            )
            
            if payload.get('type') != 'magic_link':
                raise jwt.InvalidTokenError('Not a magic link token')
                
            return payload['email']
        except jwt.InvalidTokenError as e:
            raise ValueError(f'Invalid magic link token: {str(e)}')
