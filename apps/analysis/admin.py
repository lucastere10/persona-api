from django.contrib import admin
from .models import AnalysisResult


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'sheet_name', 'use_ai', 'created_at')
    list_filter = ('use_ai', 'created_at')
    search_fields = ('file_name', 'sheet_name')
    readonly_fields = ('id', 'access_token', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('File Information', {
            'fields': ('file_name', 'sheet_name')
        }),
        ('Analysis Settings', {
            'fields': ('use_ai',)
        }),
        ('Security', {
            'fields': ('access_token',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
        ('Results', {
            'fields': ('results',),
            'classes': ('collapse',)
        })
    )
