from __future__ import annotations

from django.conf import settings
from django.db import models


class SleepRecord(models.Model):
    class Status(models.TextChoices):
        NORMAL = "normal", "健康"
        WARNING = "warning", "一般"
        ABNORMAL = "abnormal", "异常"
        SEVERE = "severe", "严重"
        MISSED = "missed", "未打卡"

    class Mood(models.TextChoices):
        GREAT = "great", "😄 极佳"
        GOOD = "good", "🙂 良好"
        NORMAL = "normal", "😐 一般"
        TIRED = "tired", "😪 疲惫"
        BAD = "bad", "😣 糟糕"

    student = models.ForeignKey(
        "users.StudentProfile",
        on_delete=models.CASCADE,
        related_name="sleep_records",
        verbose_name="学生",
    )
    date = models.DateField("记录日期（那晚所属日期）", db_index=True)

    bedtime = models.DateTimeField("入睡时间", null=True, blank=True)
    wake_time = models.DateTimeField("起床时间", null=True, blank=True)
    duration_minutes = models.IntegerField("睡眠时长(分钟)", default=0)

    subjective_score = models.PositiveSmallIntegerField("主观评分(1-5)", default=3)
    quality_score = models.PositiveSmallIntegerField("质量分(0-100)", default=0)
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.MISSED)

    mood_tag = models.CharField(
        "心情", max_length=16, choices=Mood.choices, blank=True, default=""
    )
    diary = models.TextField("日记", blank=True, default="")

    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_sleep_records",
        verbose_name="修改人",
    )
    modified_reason = models.CharField("修改原因", max_length=255, blank=True, default="")
    modified_at = models.DateTimeField("修改时间", null=True, blank=True)

    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "睡眠记录"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="uniq_student_date"),
        ]
        ordering = ["-date"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.student.real_name} @ {self.date} [{self.get_status_display()}]"
