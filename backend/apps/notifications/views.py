"""M6 通知/消息/预警视图。

端点：
- GET  /api/notifications/                 我收到的通知（支持 ?unread=1）
- POST /api/notifications/<id>/read/       标已读
- POST /api/notifications/read-all/        全部已读
- GET  /api/notifications/unread-count/    未读数（轮询用）
- POST /api/notifications/send/            发消息（学生↔老师↔家长）
- POST /api/notifications/broadcast/       老师群发公告
- GET  /api/notifications/alerts/          老师/家长预警列表（severe 记录）
"""
from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.models import StudentProfile, User
from apps.users.permissions import role_required
from apps.sleep.models import SleepRecord

from .models import Notification
from .serializers import BroadcastSerializer, NotificationSerializer, SendMessageSerializer


# ──────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────

def _create_notification(sender, receiver, ntype, title, content):
    return Notification.objects.create(
        sender=sender,
        receiver=receiver,
        type=ntype,
        title=title,
        content=content,
    )


# ──────────────────────────────────────────────
# 消息列表 / 已读
# ──────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def notification_list(request):
    return _notification_list_response(request)


def _notification_list_response(request):
    qs = Notification.objects.filter(receiver=request.user)
    if request.query_params.get("unread") == "1":
        qs = qs.filter(is_read=False)
    page_size = 30
    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        page = 1
    start = (page - 1) * page_size
    total = qs.count()
    items = qs[start: start + page_size]
    ser = NotificationSerializer(items, many=True)
    return Response({"count": total, "results": ser.data})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_read(request, pk: int):
    n = Notification.objects.filter(pk=pk, receiver=request.user).first()
    if not n:
        return Response({"detail": "未找到"}, status=status.HTTP_404_NOT_FOUND)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    cnt = Notification.objects.filter(receiver=request.user, is_read=False).count()
    return Response({"count": cnt})


# ──────────────────────────────────────────────
# 发消息（点对点）
# ──────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_message(request):
    return _send_message_response(request)


def _send_message_response(request):
    ser = SendMessageSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    try:
        receiver = User.objects.get(pk=d["receiver_id"])
    except User.DoesNotExist:
        return Response({"detail": "接收者不存在"}, status=status.HTTP_400_BAD_REQUEST)

    # 权限校验：学生只能发给自己的老师或家长；家长只能发给孩子的老师或孩子
    sender = request.user
    allowed = True
    if sender.role == User.Role.STUDENT:
        student = getattr(sender, "student_profile", None)
        teacher_id = student.classroom.teacher_id if student and student.classroom else None
        parent = getattr(student, "parent_profile", None)
        parent_user_id = parent.user_id if parent else None
        allowed = receiver.id in filter(None, [teacher_id, parent_user_id])
    elif sender.role == User.Role.PARENT:
        parent_profile = getattr(sender, "parent_profile", None)
        if parent_profile and parent_profile.child:
            child = parent_profile.child
            teacher_id = child.classroom.teacher_id if child.classroom else None
            allowed = receiver.id in filter(None, [teacher_id, child.user_id])
        else:
            allowed = False
    elif sender.role == User.Role.TEACHER:
        allowed_ids = set()
        for classroom in sender.classrooms.prefetch_related("students__parent_profile"):
            for student in classroom.students.select_related("user"):
                allowed_ids.add(student.user_id)
                parent = getattr(student, "parent_profile", None)
                if parent:
                    allowed_ids.add(parent.user_id)
        allowed = receiver.id in allowed_ids
    elif sender.role == User.Role.ADMIN:
        allowed = True

    if not allowed:
        return Response({"detail": "无权向该用户发送消息"}, status=status.HTTP_403_FORBIDDEN)

    n = _create_notification(sender, receiver, d["type"], d["title"], d["content"])
    return Response(NotificationSerializer(n).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def message_center(request):
    """设计文档兼容入口：GET 收件箱，POST 点对点发消息。"""
    if request.method == "GET":
        return _notification_list_response(request)
    return _send_message_response(request)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def recipients(request):
    """当前用户可发送消息的收件人，匹配三角色消息边界。"""
    user = request.user
    items = []
    seen = set()

    def add(target, relation):
        if not target or target.id in seen or target.id == user.id:
            return
        seen.add(target.id)
        profile = (
            getattr(target, "teacher_profile", None)
            or getattr(target, "student_profile", None)
            or getattr(target, "parent_profile", None)
        )
        name = getattr(profile, "real_name", None) or target.username
        items.append({
            "id": target.id,
            "username": target.username,
            "name": name,
            "role": target.role,
            "role_display": target.get_role_display(),
            "relation": relation,
        })

    if user.role == User.Role.STUDENT:
        student = getattr(user, "student_profile", None)
        if student and student.classroom:
            add(student.classroom.teacher, "班主任")
        parent = getattr(student, "parent_profile", None) if student else None
        if parent:
            add(parent.user, "我的家长")

    elif user.role == User.Role.PARENT:
        parent = getattr(user, "parent_profile", None)
        if parent and parent.child:
            child = parent.child
            add(child.user, "我的孩子")
            if child.classroom:
                add(child.classroom.teacher, "孩子班主任")

    elif user.role == User.Role.TEACHER:
        for classroom in user.classrooms.prefetch_related("students__user", "students__parent_profile__user"):
            for student in classroom.students.select_related("user"):
                add(student.user, f"{classroom.name} 学生")
                parent = getattr(student, "parent_profile", None)
                if parent:
                    add(parent.user, f"{classroom.name} 家长")

    elif user.role == User.Role.ADMIN:
        for target in User.objects.exclude(id=user.id).order_by("role", "username")[:200]:
            add(target, "系统用户")

    return Response({"results": items, "count": len(items)})


# ──────────────────────────────────────────────
# 老师群发公告
# ──────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def broadcast(request):
    ser = BroadcastSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    teacher = request.user
    classrooms = teacher.classrooms.prefetch_related("students__user", "students__parent_profile__user")
    if not classrooms.exists():
        return Response({"detail": "您还未创建班级"}, status=status.HTTP_400_BAD_REQUEST)

    created = 0
    for classroom in classrooms:
        for student in classroom.students.select_related("user"):
            _create_notification(
                teacher, student.user,
                Notification.Type.ANNOUNCEMENT,
                d["title"], d["content"],
            )
            created += 1
            if d["include_parents"]:
                parent = getattr(student, "parent_profile", None)
                if parent:
                    _create_notification(
                        teacher, parent.user,
                        Notification.Type.ANNOUNCEMENT,
                        d["title"], d["content"],
                    )
                    created += 1

    return Response({"sent": created})


# ──────────────────────────────────────────────
# 预警列表（老师/家长）
# ──────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def alerts(request):
    user = request.user

    if user.role == User.Role.TEACHER:
        teacher_profile = getattr(user, "teacher_profile", None)
        classrooms = user.classrooms.prefetch_related("students")
        student_ids = []
        for c in classrooms:
            student_ids.extend(c.students.values_list("id", flat=True))
        records = (
            SleepRecord.objects
            .filter(student_id__in=student_ids, status__in=["severe", "abnormal"])
            .select_related("student")
            .order_by("-date")[:100]
        )

    elif user.role == User.Role.PARENT:
        parent = getattr(user, "parent_profile", None)
        if not parent or not parent.child:
            return Response({"results": []})
        records = (
            SleepRecord.objects
            .filter(student=parent.child, status__in=["severe", "abnormal"])
            .order_by("-date")[:50]
        )

    else:
        return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

    data = []
    for r in records:
        data.append({
            "id": r.id,
            "student_name": r.student.real_name,
            "date": r.date.isoformat(),
            "status": r.status,
            "quality_score": r.quality_score,
            "duration_minutes": r.duration_minutes,
        })
    return Response({"results": data})
