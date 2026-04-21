from django.db import models


class Achievement(models.Model):
    code = models.CharField("标识码", max_length=64, unique=True)
    name = models.CharField("名称", max_length=64)
    description = models.CharField("描述", max_length=255)
    icon = models.CharField("图标(emoji 或 URL)", max_length=255, blank=True, default="🏅")

    class Meta:
        verbose_name = "成就"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class StudentAchievement(models.Model):
    student = models.ForeignKey(
        "users.StudentProfile",
        on_delete=models.CASCADE,
        related_name="achievements",
        verbose_name="学生",
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE, related_name="unlocked_by", verbose_name="成就"
    )
    unlocked_at = models.DateTimeField("解锁时间", auto_now_add=True)

    class Meta:
        verbose_name = "学生成就"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=["student", "achievement"], name="uniq_student_achievement"),
        ]
        ordering = ["-unlocked_at"]

    def __str__(self) -> str:
        return f"{self.student.real_name} → {self.achievement.name}"
