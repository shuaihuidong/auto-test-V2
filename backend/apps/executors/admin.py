from django.contrib import admin
from .models import Variable


@admin.register(Variable)
class VariableAdmin(admin.ModelAdmin):
    list_display = ['name', 'scope', 'project', 'script', 'type', 'is_sensitive', 'created_by', 'created_at']
    list_filter = ['scope', 'type', 'is_sensitive']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
