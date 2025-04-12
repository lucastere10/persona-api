# api/urls.py
from django.urls import path
from .views import UserCreate

urlpatterns = [
    path('register/', UserCreate.as_view(), name='account-create'),
]
