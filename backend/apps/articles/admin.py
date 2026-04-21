from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "views", "created_at")
    search_fields = ("title", "content")
    readonly_fields = ("views", "created_at")
