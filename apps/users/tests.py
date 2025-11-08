from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import UserProfile


class UserModelTest(TestCase):
    """
    Test User and UserProfile models
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_profile_creation(self):
        """Test that UserProfile is created when User is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
    
    def test_user_profile_str(self):
        """Test UserProfile string representation"""
        expected_str = f"{self.user.username}'s Profile"
        self.assertEqual(str(self.user.profile), expected_str)


class UserRegistrationTest(APITestCase):
    """
    Test user registration functionality
    """
    
    def setUp(self):
        self.register_url = reverse('user-register')
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
    
    def test_valid_registration(self):
        """Test user registration with valid data"""
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertIn('token', response.data)
    
    def test_duplicate_username(self):
        """Test registration with duplicate username"""
        User.objects.create_user(username='newuser', email='other@example.com')
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(username='otheruser', email='newuser@example.com')
        response = self.client.post(self.register_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_mismatch(self):
        """Test registration with password mismatch"""
        data = self.valid_data.copy()
        data['password_confirm'] = 'differentpass'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTest(APITestCase):
    """
    Test user login functionality
    """
    
    def setUp(self):
        self.login_url = reverse('user-login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_valid_login(self):
        """Test login with valid credentials"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
    
    def test_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_inactive_user_login(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileTest(APITestCase):
    """
    Test user profile functionality
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.profile_url = reverse('user-profile')
    
    def test_get_profile(self):
        """Test retrieving user profile"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
    
    def test_update_profile(self):
        """Test updating user profile"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'profile': {
                'bio': 'Updated bio',
                'location': 'New Location'
            }
        }
        response = self.client.put(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.profile.bio, 'Updated bio')


class ChangePasswordTest(APITestCase):
    """
    Test password change functionality
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.change_password_url = reverse('change-password')
    
    def test_valid_password_change(self):
        """Test password change with valid data"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.put(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was actually changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))
    
    def test_wrong_old_password(self):
        """Test password change with wrong old password"""
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.put(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_password_confirmation_mismatch(self):
        """Test password change with confirmation mismatch"""
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        response = self.client.put(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTest(APITestCase):
    """
    Test user logout functionality
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.logout_url = reverse('user-logout')
    
    def test_logout(self):
        """Test user logout"""
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify token was deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())
