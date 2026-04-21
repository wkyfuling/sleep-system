from django.contrib import admin

from .models import AIAdvice


@admin.register(AIAdvice)
class AIAdviceAdmin(admin.ModelAdmin):
    list_display = ("student", "trigger_type", "is_mock", "created_at")
    list_filter = ("trigger_type", "is_mock")
    readonly_fields = ("created_at",)
