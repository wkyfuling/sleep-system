from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "sender", "receiver", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("title", "content")
