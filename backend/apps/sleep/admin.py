from django.contrib import admin

from .models import SleepRecord


@admin.register(SleepRecord)
class SleepRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "bedtime", "wake_time", "duration_minutes", "status", "quality_score")
    list_filter = ("status", "date")
    search_fields = ("student__real_name", "student__student_no")
    date_hierarchy = "date"
    readonly_fields = ("created_at", "modified_at")
