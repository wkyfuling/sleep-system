from django.db import models


class AIAdvice(models.Model):
    class TriggerType(models.TextChoices):
        MANUAL = "manual", "手动触发"
        AUTO = "auto", "自动触发"

    student = models.ForeignKey(
        "users.StudentProfile",
        on_delete=models.CASCADE,
        related_name="ai_advices",
        verbose_name="学生",
    )
    trigger_type = models.CharField(
        "触发方式", max_length=16, choices=TriggerType.choices, default=TriggerType.MANUAL
    )
    prompt_summary = models.CharField("数据摘要", max_length=512, blank=True, default="")
    advice_text = models.TextField("AI 建议")
    is_mock = models.BooleanField("Mock 兜底", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "AI 建议"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.student.real_name} @ {self.created_at:%Y-%m-%d %H:%M}"
