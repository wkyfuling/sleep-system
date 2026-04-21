from django.contrib import admin

from .models import Achievement, StudentAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "icon", "description")
    search_fields = ("name", "code")


@admin.register(StudentAchievement)
class StudentAchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "achievement", "unlocked_at")
    list_filter = ("achievement",)
