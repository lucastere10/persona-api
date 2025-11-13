# apps/analysis/urls.py
from django.urls import path
from .views import (
    InitialAnalysisView,
    InitialAnalysisResultView,
    InitialAnalysisListView
)

urlpatterns = [   
    # Initial analysis endpoints
    path('initial-analysis/', InitialAnalysisView.as_view(), name='initial-analysis'),
    path('initial-analysis/<uuid:analysis_id>/', InitialAnalysisResultView.as_view(), name='initial-analysis-result'),
    path('initial-analysis-list/', InitialAnalysisListView.as_view(), name='initial-analysis-list'),
]
