# api/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password')

    def create(self, validated_data):
        # Use create_user to ensure the password is hashed
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user
