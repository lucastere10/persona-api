from django.db import models
import uuid
import json
import secrets


def generate_access_token():
    """Generate a secure random access token."""
    return secrets.token_urlsafe(16)


class AnalysisResult(models.Model):
    """Model to store comprehensive analysis results."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access_token = models.CharField(max_length=64, default=generate_access_token, unique=True, 
                                   help_text="Access token for secure retrieval")
    file_name = models.CharField(max_length=255, help_text="Original filename")
    sheet_name = models.CharField(max_length=100, blank=True, default='', help_text="Excel sheet name if applicable")
    use_ai = models.BooleanField(default=True, help_text="Whether AI insights were generated")
    results = models.JSONField(help_text="Complete analysis results in JSON format")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analysis_results'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['file_name']),
            models.Index(fields=['access_token']),
        ]
    
    def __str__(self):
        return f"Analysis {self.id} - {self.file_name}"
    
    @property
    def analysis_summary(self):
        """Get a quick summary of the analysis."""
        if not self.results:
            return {}
        
        summary = self.results.get('results', {}).get('summary', {})
        return {
            'datasets_analyzed': summary.get('total_datasets_analyzed', 0),
            'steps_completed': len(summary.get('steps_completed', [])),
            'errors_count': summary.get('errors_encountered', 0),
            'overall_success': summary.get('overall_success', False),
            'ai_insights_generated': summary.get('ai_insights_generated', False)
        }
