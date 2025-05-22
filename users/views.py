# api/views.py
import uuid

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.contrib.auth.models import User
from .serializers import UserSerializer
from .services.data_profiler import profile_file 
from .services.data_cleaner import clean_file

class UserCreate(generics.CreateAPIView):
    """
    Creates a new user.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []  # Allow non-authenticated user registration

class DataProfileAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        f = request.FILES.get('file')
        if not f:
            return Response({"error": "No file provided."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            result = profile_file(f, f.name)
        except ValueError as ve:
            return Response({"error": str(ve)},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": "Profiling failed: " + str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 1. generate a unique key
        key = str(uuid.uuid4())
        # 2. store the JSON result in cache with TTL (e.g. 1 hour)
        cache.set(f"profile:{key}", result, timeout=60 * 60)

        # 3. return only the key
        return Response({"id": key}, status=status.HTTP_200_OK)
    
class DataProfileResultAPIView(APIView):
    permission_classes = []

    def get(self, request, profile_id, *args, **kwargs):
        # look up in Redis
        data = cache.get(f"profile:{profile_id}")
        if not data:
            return Response(
                {"error": "Profile not found or expired."},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(data, status=status.HTTP_200_OK)
        

class DataCleanAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = []

    def post(self, request, *args, **kwargs):
        f = request.FILES.get("file")
        if not f:
            return Response(...)

        zero = float(request.data.get("zero_threshold", 0.5))
        out = float(request.data.get("outlier_contamination", 0.05))

        result = clean_file(f, f.name, zero, out)
        key = str(uuid.uuid4())
        # cache the entire result dict, or save a CSV to disk and cache the path
        cache.set(f"clean:{key}", result, timeout=60 * 60)
        return Response({"id": key})

class DataCleanResultAPIView(APIView):
    permission_classes = []

    def get(self, request, clean_id, *args, **kwargs):
        data = cache.get(f"clean:{clean_id}")
        if not data:
            return Response({"error": "Not found"}, status=404)
        return Response(data)