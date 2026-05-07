from django.contrib import admin
from .models import DataSource, Script, BatchTask


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name']


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'type', 'framework', 'is_module', 'created_by', 'created_at']
    list_filter = ['type', 'framework', 'is_module', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BatchTask)
class BatchTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'total_count', 'completed_count', 'failed_count', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
