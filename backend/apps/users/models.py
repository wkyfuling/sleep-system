from __future__ import annotations

import secrets
import string
from datetime import time as _time, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def _default_bedtime() -> _time:
    return _time(23, 0)


def _gen_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "学生"
        TEACHER = "teacher", "老师"
        PARENT = "parent", "家长"
        ADMIN = "admin", "管理员"

    role = models.CharField("角色", max_length=16, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField("手机号", max_length=20, blank=True, default="")
    avatar = models.ImageField("头像", upload_to="avatars/", blank=True, null=True)
    email_alert_enabled = models.BooleanField("接收邮件预警", default=False)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"{self.username}({self.get_role_display()})"


class ClassRoom(models.Model):
    name = models.CharField("班级名称", max_length=64)
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
        limit_choices_to={"role": User.Role.TEACHER},
        verbose_name="班主任",
    )
    invite_code = models.CharField("班级邀请码", max_length=8, unique=True, db_index=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "班级"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            for _ in range(10):
                code = _gen_code(6)
                if not ClassRoom.objects.filter(invite_code=code).exists():
                    self.invite_code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class StudentProfile(models.Model):
    class RiskLevel(models.TextChoices):
        NORMAL = "normal", "正常"
        FOCUS = "focus", "重点关注"

    class Gender(models.TextChoices):
        MALE = "M", "男"
        FEMALE = "F", "女"
        OTHER = "O", "其他"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile", verbose_name="用户"
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="students", verbose_name="班级",
    )
    student_no = models.CharField("学号", max_length=32, unique=True)
    real_name = models.CharField("姓名", max_length=32)
    gender = models.CharField("性别", max_length=2, choices=Gender.choices, default=Gender.OTHER)
    grade = models.CharField("年级", max_length=16, blank=True, default="")

    target_sleep_hours = models.DecimalField(
        "目标睡眠时长(小时)", max_digits=3, decimal_places=1, default=8.0,
    )
    target_bedtime = models.TimeField("目标入睡时间", default=_default_bedtime)
    risk_level = models.CharField(
        "风险等级", max_length=16, choices=RiskLevel.choices, default=RiskLevel.NORMAL,
    )

    parent_invite_code = models.CharField("家长邀请码", max_length=8, blank=True, default="", db_index=True)
    invite_expires_at = models.DateTimeField("邀请码过期时间", null=True, blank=True)

    share_diary_to_teacher = models.BooleanField("允许老师查看我的日记", default=False)

    class Meta:
        verbose_name = "学生档案"
        verbose_name_plural = verbose_name

    def generate_parent_invite(self, ttl_hours: int = 24) -> str:
        for _ in range(10):
            code = _gen_code(6)
            if not StudentProfile.objects.filter(parent_invite_code=code).exists():
                self.parent_invite_code = code
                break
        self.invite_expires_at = timezone.now() + timedelta(hours=ttl_hours)
        self.save(update_fields=["parent_invite_code", "invite_expires_at"])
        return self.parent_invite_code

    def invite_is_valid(self) -> bool:
        return bool(
            self.parent_invite_code
            and self.invite_expires_at
            and self.invite_expires_at > timezone.now()
        )

    def __str__(self) -> str:
        return f"{self.real_name}({self.student_no})"


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile", verbose_name="用户"
    )
    teacher_no = models.CharField("工号", max_length=32, unique=True)
    real_name = models.CharField("姓名", max_length=32)

    class Meta:
        verbose_name = "老师档案"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"{self.real_name}({self.teacher_no})"


class ParentProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="parent_profile", verbose_name="用户"
    )
    real_name = models.CharField("姓名", max_length=32)
    child = models.OneToOneField(
        StudentProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profile",
        verbose_name="绑定的孩子",
    )

    class Meta:
        verbose_name = "家长档案"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"{self.real_name}"
