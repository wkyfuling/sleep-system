"""M4 SleepRecord 序列化器。

设计：
- `SleepRecordReadSerializer`    — 通用读返回，diary 字段对非本人根据 share_diary_to_teacher 裁剪
- `SleepRecordCreateSerializer`  — 学生端 POST，调 score_engine 自动计算 date/duration/quality/status
- `SleepRecordStudentEditSerializer` — 学生端 PATCH，2h 窗口内有效，重算评分
- `SleepRecordTeacherEditSerializer` — 老师端 PATCH，必须带 modified_reason，写审计字段
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.users.models import StudentProfile, User

from .models import SleepRecord
from utils.score_engine import compute_score


def _send_severe_alert(student: StudentProfile, record) -> None:
    """打卡结果为 severe 时，自动向老师 + 家长推送站内预警。"""
    try:
        from apps.notifications.models import Notification  # 延迟导入避免循环
        from django.conf import settings
        from django.core.mail import send_mail

        msg = (
            f"【睡眠严重异常】{student.real_name} 于 {record.date} 的睡眠质量分为 "
            f"{record.quality_score}（{record.get_status_display()}），"
            f"时长 {record.duration_minutes // 60}h{record.duration_minutes % 60}min，"
            f"请关注。"
        )

        email_receivers = []

        # 通知老师
        if student.classroom and student.classroom.teacher:
            Notification.objects.create(
                sender=None,
                receiver=student.classroom.teacher,
                type=Notification.Type.SYSTEM_ALERT,
                title=f"⚠️ 睡眠严重异常预警：{student.real_name}",
                content=msg,
            )
            teacher = student.classroom.teacher
            if teacher.email_alert_enabled and teacher.email:
                email_receivers.append(teacher.email)

        # 通知家长
        parent = getattr(student, "parent_profile", None)
        if parent:
            Notification.objects.create(
                sender=None,
                receiver=parent.user,
                type=Notification.Type.SYSTEM_ALERT,
                title=f"⚠️ 孩子睡眠严重异常预警",
                content=msg,
            )
            if parent.user.email_alert_enabled and parent.user.email:
                email_receivers.append(parent.user.email)

        if email_receivers:
            send_mail(
                subject=f"睡眠严重异常预警：{student.real_name}",
                message=msg,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=list(set(email_receivers)),
                fail_silently=True,
            )
    except Exception:
        pass  # 通知失败不影响打卡主流程


MAX_BACKFILL_DAYS = 3
EDIT_WINDOW_HOURS = 2


class SleepRecordReadSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    mood_display = serializers.CharField(source="get_mood_tag_display", read_only=True)
    student_name = serializers.CharField(source="student.real_name", read_only=True)
    editable = serializers.SerializerMethodField()

    class Meta:
        model = SleepRecord
        fields = [
            "id",
            "student",
            "student_name",
            "date",
            "bedtime",
            "wake_time",
            "duration_minutes",
            "subjective_score",
            "quality_score",
            "status",
            "status_display",
            "mood_tag",
            "mood_display",
            "diary",
            "modified_by",
            "modified_reason",
            "modified_at",
            "created_at",
            "editable",
        ]
        read_only_fields = fields

    def get_editable(self, obj: SleepRecord) -> bool:
        """学生视角下是否仍在 2h 自改窗口内。"""
        if obj.status == SleepRecord.Status.MISSED:
            return False
        return (timezone.now() - obj.created_at) <= timedelta(hours=EDIT_WINDOW_HOURS)

    def to_representation(self, instance: SleepRecord):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return data
        # 隐私裁剪：非学生本人查看时，根据 share 开关决定是否回 diary
        viewer = request.user
        owner_user_id = instance.student.user_id
        if viewer.id != owner_user_id:
            if viewer.role == User.Role.TEACHER and instance.student.share_diary_to_teacher:
                pass  # 老师被显式授权
            else:
                data["diary"] = ""  # 其他人一律裁掉
        return data


class SleepRecordCreateSerializer(serializers.ModelSerializer):
    """学生打卡/补卡。date 由 bedtime 推导，忽略传入。"""

    class Meta:
        model = SleepRecord
        fields = [
            "bedtime",
            "wake_time",
            "subjective_score",
            "mood_tag",
            "diary",
        ]
        extra_kwargs = {
            "subjective_score": {"required": False, "default": 3},
            "mood_tag": {"required": False, "default": ""},
            "diary": {"required": False, "default": "", "allow_blank": True},
        }

    def validate(self, attrs):
        bedtime = attrs.get("bedtime")
        wake_time = attrs.get("wake_time")
        if not bedtime or not wake_time:
            raise serializers.ValidationError("bedtime 和 wake_time 必填")
        if wake_time <= bedtime:
            raise serializers.ValidationError("起床时间必须晚于入睡时间")

        subjective = attrs.get("subjective_score", 3)
        try:
            result = compute_score(bedtime, wake_time, subjective)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        # 补卡边界：date 不能早于今天前 3 天
        today = timezone.localdate()
        min_date = today - timedelta(days=MAX_BACKFILL_DAYS)
        if result.date < min_date:
            raise serializers.ValidationError(
                f"只能补打最近 {MAX_BACKFILL_DAYS} 天内的记录（最早 {min_date.isoformat()}）"
            )
        if result.date > today:
            raise serializers.ValidationError("不能对未来日期打卡")

        attrs["_score_result"] = result
        return attrs

    def create(self, validated_data):
        result = validated_data.pop("_score_result")
        student: StudentProfile = self.context["student"]

        # unique (student, date) — 冲突即视为重复打卡
        if SleepRecord.objects.filter(student=student, date=result.date).exists():
            raise serializers.ValidationError(
                {"date": f"{result.date.isoformat()} 已有打卡记录，请使用编辑功能"}
            )

        record = SleepRecord.objects.create(
            student=student,
            date=result.date,
            duration_minutes=result.duration_minutes,
            quality_score=result.quality_score,
            status=result.status,
            **validated_data,
        )

        # 严重异常自动推送预警
        if result.status == SleepRecord.Status.SEVERE:
            _send_severe_alert(student, record)

        # 检查并解锁成就
        try:
            from apps.achievements.unlock import check_and_unlock
            check_and_unlock(student)
        except Exception:
            pass

        return record


class SleepRecordStudentEditSerializer(serializers.ModelSerializer):
    """学生 2h 窗口内修改。允许改 bedtime/wake_time/subjective/mood/diary，重算评分。"""

    class Meta:
        model = SleepRecord
        fields = ["bedtime", "wake_time", "subjective_score", "mood_tag", "diary"]
        extra_kwargs = {f: {"required": False} for f in fields}

    def validate(self, attrs):
        instance: SleepRecord = self.instance
        # 2h 窗口
        if (timezone.now() - instance.created_at) > timedelta(hours=EDIT_WINDOW_HOURS):
            raise serializers.ValidationError("已超过 2 小时自改窗口")
        if instance.status == SleepRecord.Status.MISSED:
            raise serializers.ValidationError("未打卡记录无法通过编辑补齐，请使用补打接口")

        bedtime = attrs.get("bedtime", instance.bedtime)
        wake_time = attrs.get("wake_time", instance.wake_time)
        subjective = attrs.get("subjective_score", instance.subjective_score)

        if bedtime and wake_time:
            try:
                result = compute_score(bedtime, wake_time, subjective)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
            attrs["_score_result"] = result
        return attrs

    def update(self, instance, validated_data):
        result = validated_data.pop("_score_result", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if result:
            instance.date = result.date
            instance.duration_minutes = result.duration_minutes
            instance.quality_score = result.quality_score
            instance.status = result.status
        instance.save()
        return instance


class SleepRecordTeacherEditSerializer(serializers.ModelSerializer):
    """老师代改：必须带 modified_reason；写 modified_by/modified_at 审计。"""

    class Meta:
        model = SleepRecord
        fields = ["bedtime", "wake_time", "subjective_score", "mood_tag", "modified_reason"]
        extra_kwargs = {
            "bedtime": {"required": False},
            "wake_time": {"required": False},
            "subjective_score": {"required": False},
            "mood_tag": {"required": False},
            "modified_reason": {"required": False, "allow_blank": True},  # 在 validate 手动强制
        }

    def validate(self, attrs):
        # partial=True 下 required=True 不生效，手动校验 modified_reason
        reason = attrs.get("modified_reason", "")
        if not reason or not reason.strip():
            raise serializers.ValidationError({"modified_reason": "老师代改必须填写修改原因"})

        instance: SleepRecord = self.instance
        bedtime = attrs.get("bedtime", instance.bedtime)
        wake_time = attrs.get("wake_time", instance.wake_time)
        subjective = attrs.get("subjective_score", instance.subjective_score)

        if bedtime and wake_time:
            try:
                result = compute_score(bedtime, wake_time, subjective)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
            attrs["_score_result"] = result
        return attrs

    def update(self, instance, validated_data):
        result = validated_data.pop("_score_result", None)
        instance.modified_reason = validated_data.pop("modified_reason")
        instance.modified_by = self.context["request"].user
        instance.modified_at = timezone.now()
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if result:
            instance.date = result.date
            instance.duration_minutes = result.duration_minutes
            instance.quality_score = result.quality_score
            instance.status = result.status
            # 若之前是 MISSED（老师代录），升级为真实状态
        instance.save()
        return instance
