# api/views.py
from django.shortcuts import render

from rest_framework import generics
from django.contrib.auth.models import User
from .serializers import UserSerializer

class UserCreate(generics.CreateAPIView):
    """
    Creates a new user.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []  # Allow non-authenticated user registration
