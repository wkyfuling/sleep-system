from django.conf import settings
from django.db import models


class Article(models.Model):
    title = models.CharField("标题", max_length=128)
    content = models.TextField("正文 (Markdown)")
    cover_image = models.ImageField("封面图", upload_to="articles/", blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        verbose_name="作者",
    )
    views = models.PositiveIntegerField("浏览量", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "科普文章"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
