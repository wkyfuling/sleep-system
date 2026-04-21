from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        SYSTEM_ALERT = "system_alert", "系统预警"
        TEACHER_MSG = "teacher_msg", "老师留言"
        PARENT_MSG = "parent_msg", "家长留言"
        STUDENT_MSG = "student_msg", "学生留言"
        ANNOUNCEMENT = "announcement", "班级公告"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
        verbose_name="发送者",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_notifications",
        verbose_name="接收者",
    )
    type = models.CharField("类型", max_length=32, choices=Type.choices)
    title = models.CharField("标题", max_length=128)
    content = models.TextField("内容")
    is_read = models.BooleanField("已读", default=False, db_index=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "通知/消息"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.get_type_display()}] {self.title}"
