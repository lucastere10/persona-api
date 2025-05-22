# api/urls.py
from django.urls import path
from .views import UserCreate, DataProfileAPIView, DataCleanAPIView, DataProfileResultAPIView, DataCleanResultAPIView

urlpatterns = [
    path('register', UserCreate.as_view(), name='account-create'),
    path('profile-data', DataProfileAPIView.as_view(), name='profile-data'),
    path("profile-results/<uuid:profile_id>/", DataProfileResultAPIView.as_view(), name="profile-results"),
    path('clean-data', DataCleanAPIView.as_view(), name='clean-data'),
    path("clean-results/<uuid:clean_id>/", DataCleanResultAPIView.as_view(), name="clean-results"),  # com barra
]
