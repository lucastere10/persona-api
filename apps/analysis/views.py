from django.shortcuts import render

import uuid

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .services.comprehensive_analysis import ComprehensiveAnalysisService
from .models import AnalysisResult
import tempfile
import os
import json


class InitialAnalysisView(APIView):
    """
    View for performing initial/simplified data analysis.
    No authentication required for easy access.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = []  # No authentication required

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        sheet_name = request.data.get('sheet_name')
        cleaning_config = request.data.get('cleaning_config')
        use_ai = request.data.get('use_ai', 'true').lower() == 'true'  # Default: True

        if not file_obj:
            return Response({'error': 'No file provided.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 1. Pegue a extensão original
        original_name = file_obj.name
        _, ext = os.path.splitext(original_name)

        # 2. Parse cleaning_config
        config = None
        if cleaning_config:
            try:
                config = json.loads(cleaning_config)
            except json.JSONDecodeError:
                return Response({'error': 'Invalid cleaning_config JSON.'},
                                status=status.HTTP_400_BAD_REQUEST)

        # 3. Crie o arquivo temporário COM A MESMA EXTENSÃO
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            # opcional: anexe o nome original para seu serviço achar depois
            tmp.original_filename = original_name  
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            # 4. Initialize service with AI setting from request
            service = ComprehensiveAnalysisService(use_openai=use_ai)
            # 5. Execute analysis
            results = service.analyze_file(tmp_path,
                                           sheet_name=sheet_name,
                                           cleaning_config=config)
            
            # 6. Save results to database
            analysis_result = AnalysisResult.objects.create(
                file_name=original_name,
                sheet_name=sheet_name or '',
                use_ai=use_ai,
                results=results
            )
            
            # 7. Return analysis ID, access token, and summary (no JWT required)
            return Response({
                'id': str(analysis_result.id),
                'access_token': analysis_result.access_token,
                'summary': analysis_result.analysis_summary,
                'created_at': analysis_result.created_at.isoformat(),
                'message': 'Initial analysis completed successfully. Use the access_token in the "access-token" header to retrieve full results.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Analysis failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        finally:
            os.remove(tmp_path)


class InitialAnalysisResultView(APIView):
    """
    View to retrieve initial analysis results by ID with access token validation.
    No JWT authentication required.
    """
    permission_classes = []  # No authentication required
    
    def get(self, request, analysis_id, format=None):
        # Extract access token from access-token header
        access_token = request.headers.get('access-token')
        if not access_token:
            return Response(
                {'error': 'Access token header required. Include access token as: access-token: <token>'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            # Find analysis by ID and validate access token
            analysis_result = AnalysisResult.objects.get(id=analysis_id, access_token=access_token)
            
            # Return complete results
            return Response({
                'id': str(analysis_result.id),
                'file_name': analysis_result.file_name,
                'sheet_name': analysis_result.sheet_name,
                'use_ai': analysis_result.use_ai,
                'created_at': analysis_result.created_at.isoformat(),
                'updated_at': analysis_result.updated_at.isoformat(),
                'summary': analysis_result.analysis_summary,
                'results': analysis_result.results
            }, status=status.HTTP_200_OK)
            
        except AnalysisResult.DoesNotExist:
            return Response(
                {'error': 'Analysis result not found or invalid access token.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid analysis ID format.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class InitialAnalysisListView(APIView):
    """
    View to list all analysis results (with pagination).
    No JWT authentication required.
    """
    permission_classes = []  # No authentication required
    
    def get(self, request, format=None):
        # Get query parameters
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)  # Max 50 per page
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get paginated results
        total_count = AnalysisResult.objects.count()
        analyses = AnalysisResult.objects.all()[offset:offset + page_size]
        
        # Prepare response
        results = []
        for analysis in analyses:
            results.append({
                'id': str(analysis.id),
                'file_name': analysis.file_name,
                'sheet_name': analysis.sheet_name,
                'use_ai': analysis.use_ai,
                'created_at': analysis.created_at.isoformat(),
                'summary': analysis.analysis_summary
            })
        
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': results
        }, status=status.HTTP_200_OK)
