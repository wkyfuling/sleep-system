from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import role_required
from .serializers import (
    AdminUserWriteSerializer,
    ParentRegisterSerializer,
    StudentRegisterSerializer,
    TeacherRegisterSerializer,
    UserBriefSerializer,
)

User = get_user_model()


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/  body: { role, ... }"""
    role = request.data.get("role")
    if role == User.Role.STUDENT:
        ser_cls = StudentRegisterSerializer
    elif role == User.Role.TEACHER:
        ser_cls = TeacherRegisterSerializer
    elif role == User.Role.PARENT:
        ser_cls = ParentRegisterSerializer
    else:
        return Response({"detail": "不支持的角色"}, status=status.HTTP_400_BAD_REQUEST)

    ser = ser_cls(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()
    tokens = _issue_tokens(user)
    return Response(
        {"user": UserBriefSerializer(user).data, **tokens},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """POST /api/auth/login/  body: { username, password }"""
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    if not username or not password:
        return Response({"detail": "用户名和密码必填"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password) or not user.is_active:
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)

    tokens = _issue_tokens(user)
    return Response({"user": UserBriefSerializer(user).data, **tokens})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({"user": UserBriefSerializer(request.user).data})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def profile_preferences(request):
    """当前用户偏好设置：学生日记分享开关、邮件预警开关。"""
    user = request.user
    allowed_user_fields = {"email", "phone", "email_alert_enabled"}
    user_updates = {}
    for field in allowed_user_fields:
        if field in request.data:
            if field == "email_alert_enabled":
                user_updates[field] = bool(request.data[field])
            else:
                user_updates[field] = str(request.data[field] or "").strip()
    if user_updates:
        for field, value in user_updates.items():
            setattr(user, field, value)
        user.save(update_fields=list(user_updates.keys()))

    if user.role == User.Role.STUDENT and hasattr(user, "student_profile"):
        profile = user.student_profile
        if "share_diary_to_teacher" in request.data:
            profile.share_diary_to_teacher = bool(request.data["share_diary_to_teacher"])
            profile.save(update_fields=["share_diary_to_teacher"])

    return Response({"user": UserBriefSerializer(user).data})


@api_view(["POST"])
@permission_classes([role_required(User.Role.STUDENT)])
def generate_parent_code(request):
    """学生生成家长邀请码（24h 有效）"""
    if not hasattr(request.user, "student_profile"):
        return Response({"detail": "缺少学生档案"}, status=status.HTTP_400_BAD_REQUEST)
    sp = request.user.student_profile
    code = sp.generate_parent_invite(ttl_hours=24)
    return Response({"code": code, "expires_at": sp.invite_expires_at})


# ──────────────────────────────────────────────
# 管理员端
# ──────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([role_required(User.Role.ADMIN)])
def admin_users(request):
    """管理员用户列表和基础创建。"""
    if request.method == "POST":
        ser = AdminUserWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"user": UserBriefSerializer(user).data}, status=status.HTTP_201_CREATED)

    qs = User.objects.all()
    role_filter = request.query_params.get("role")
    search = request.query_params.get("search", "")
    if role_filter:
        qs = qs.filter(role=role_filter)
    if search:
        qs = qs.filter(username__icontains=search)

    page_size = 20
    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        page = 1
    total = qs.count()
    items = qs[(page - 1) * page_size: page * page_size]
    return Response({
        "count": total,
        "results": UserBriefSerializer(items, many=True).data,
    })


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([role_required(User.Role.ADMIN)])
def admin_user_detail(request, pk: int):
    """管理员查看、更新、禁用/删除单个用户。"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response({"user": UserBriefSerializer(user).data})

    if request.method == "PATCH":
        ser = AdminUserWriteSerializer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        updated = ser.save()
        return Response({"user": UserBriefSerializer(updated).data})

    if user.id == request.user.id:
        return Response({"detail": "不能删除当前登录的管理员账号"}, status=status.HTTP_400_BAD_REQUEST)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([role_required(User.Role.ADMIN)])
def admin_global_stats(request):
    """全局统计：用户数、班级数、今日打卡数等。"""
    from apps.sleep.models import SleepRecord
    from apps.users.models import ClassRoom
    from datetime import date

    total_users = User.objects.count()
    student_count = User.objects.filter(role=User.Role.STUDENT).count()
    teacher_count = User.objects.filter(role=User.Role.TEACHER).count()
    classroom_count = ClassRoom.objects.count()
    today_checkins = SleepRecord.objects.filter(
        created_at__date=date.today()
    ).exclude(status="missed").count()
    severe_today = SleepRecord.objects.filter(
        created_at__date=date.today(), status="severe"
    ).count()

    return Response({
        "total_users": total_users,
        "student_count": student_count,
        "teacher_count": teacher_count,
        "classroom_count": classroom_count,
        "today_checkins": today_checkins,
        "severe_today": severe_today,
    })


@api_view(["POST"])
@permission_classes([role_required(User.Role.ADMIN)])
def admin_seed_demo(request):
    """管理员一键生成演示数据（API 版）。"""
    import io
    buf = io.StringIO()

    class _Writer:
        def __init__(self):
            self.lines = []
        def write(self, msg):
            self.lines.append(msg)

    writer = _Writer()
    try:
        from utils.seed_data import run
        run(stdout=writer)
        return Response({"ok": True, "log": "\n".join(writer.lines)})
    except Exception as e:
        return Response({"ok": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([role_required(User.Role.PARENT)])
def parent_child_overview(request):
    """家长端孩子概览：最近 30 天摘要 + 最近异常记录。"""
    from datetime import date, timedelta

    from apps.sleep.models import SleepRecord

    parent = getattr(request.user, "parent_profile", None)
    if not parent or not parent.child:
        return Response({"detail": "尚未绑定孩子"}, status=status.HTTP_400_BAD_REQUEST)

    child = parent.child
    since = date.today() - timedelta(days=29)
    records = list(
        SleepRecord.objects
        .filter(student=child, date__gte=since)
        .order_by("-date")
    )
    valid = [r for r in records if r.status != "missed"]
    latest = records[0] if records else None
    alerts = [r for r in records if r.status in ("severe", "abnormal")][:10]

    def rec_payload(r):
        if not r:
            return None
        return {
            "id": r.id,
            "date": r.date.isoformat(),
            "bedtime": r.bedtime.strftime("%H:%M") if r.bedtime else None,
            "wake_time": r.wake_time.strftime("%H:%M") if r.wake_time else None,
            "duration_minutes": r.duration_minutes,
            "quality_score": r.quality_score,
            "status": r.status,
            "mood_tag": r.mood_tag,
        }

    avg_quality = round(sum(r.quality_score for r in valid) / len(valid), 1) if valid else 0
    avg_duration = round(sum(r.duration_minutes for r in valid) / len(valid)) if valid else 0

    return Response({
        "child": {
            "id": child.id,
            "student_no": child.student_no,
            "real_name": child.real_name,
            "grade": child.grade,
            "risk_level": child.risk_level,
            "target_sleep_hours": str(child.target_sleep_hours),
            "target_bedtime": child.target_bedtime.strftime("%H:%M"),
            "classroom": child.classroom.name if child.classroom else None,
        },
        "summary_30d": {
            "checked_days": len(valid),
            "avg_quality": avg_quality,
            "avg_duration": avg_duration,
            "alert_count": len(alerts),
        },
        "latest_record": rec_payload(latest),
        "recent_alerts": [rec_payload(r) for r in alerts],
    })
