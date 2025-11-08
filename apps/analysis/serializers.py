from rest_framework import serializers
from .models import AnalysisResult


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisResult model."""
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'file_name', 'sheet_name', 'use_ai', 
            'created_at', 'updated_at', 'analysis_summary'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalysisResultDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for AnalysisResult including full results."""
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'file_name', 'sheet_name', 'use_ai', 
            'created_at', 'updated_at', 'analysis_summary', 'results'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InitialAnalysisRequestSerializer(serializers.Serializer):
    """Serializer for initial analysis request data."""
    
    file = serializers.FileField(help_text="Data file to analyze (CSV, Excel, etc.)")
    sheet_name = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Excel sheet name (optional)"
    )
    cleaning_config = serializers.JSONField(
        required=False,
        help_text="Data cleaning configuration (optional JSON)"
    )
    use_ai = serializers.BooleanField(
        default=True,
        help_text="Whether to generate AI insights"
    )
