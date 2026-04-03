from django.contrib import admin

from .models import AlertTemplate


@admin.register(AlertTemplate)
class AlertTemplateAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'channel', 'is_active', 'is_default', 'updated_at')
	list_filter = ('category', 'channel', 'is_active', 'is_default')
	search_fields = ('name', 'description', 'content')
	readonly_fields = ('created_at', 'updated_at')
