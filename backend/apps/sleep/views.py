"""M4/M5 SleepRecord 视图。

路由（见 urls.py）：
- `GET  /api/sleep/records/`              学生列表自己的记录，支持 ?from=YYYY-MM-DD&to=YYYY-MM-DD
- `POST /api/sleep/records/`              学生打卡/补卡
- `GET  /api/sleep/records/{id}/`         详情
- `PATCH /api/sleep/records/{id}/`        学生 2h 内自改
- `PATCH /api/sleep/teacher/records/{id}/` 老师代改（审计）
- `GET  /api/sleep/statistics/week/`      近 7 天统计
- `GET  /api/sleep/heatmap/?year=YYYY`    全年热力图数据
- `GET  /api/sleep/ranking/`              班级排行（匿名）
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.models import StudentProfile, User
from apps.users.permissions import role_required

from .models import SleepRecord
from .serializers import (
    SleepRecordCreateSerializer,
    SleepRecordReadSerializer,
    SleepRecordStudentEditSerializer,
    SleepRecordTeacherEditSerializer,
)


def _student_of(user) -> StudentProfile | None:
    return getattr(user, "student_profile", None)


class SleepRecordViewSet(viewsets.ModelViewSet):
    """学生端专用：仅返回自己的记录。"""

    permission_classes = [permissions.IsAuthenticated, role_required(User.Role.STUDENT)]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        student = _student_of(self.request.user)
        if not student:
            return SleepRecord.objects.none()
        qs = SleepRecord.objects.filter(student=student)

        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs.order_by("-date")

    def get_serializer_class(self):
        if self.action == "create":
            return SleepRecordCreateSerializer
        if self.action in ("partial_update", "update"):
            return SleepRecordStudentEditSerializer
        return SleepRecordReadSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["student"] = _student_of(self.request.user)
        return ctx

    def create(self, request, *args, **kwargs):
        student = _student_of(request.user)
        if not student:
            return Response({"detail": "当前用户不是学生"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read = SleepRecordReadSerializer(instance, context=self.get_serializer_context())
        return Response(read.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read = SleepRecordReadSerializer(instance, context=self.get_serializer_context())
        return Response(read.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def week_statistics(request):
    """近 7 夜统计 + 连续打卡天数。

    睡眠记录的 date 表示"那晚所属日期"。早上填写昨晚睡眠时，记录应计入昨夜，
    因此学生首页的完成状态以昨天作为统计截止日。
    """
    student = _student_of(request.user)
    if not student:
        return Response({"detail": "无学生档案"}, status=status.HTTP_400_BAD_REQUEST)

    target_date = timezone.localdate() - timedelta(days=1)
    week_start = target_date - timedelta(days=6)  # 包含昨夜共 7 夜

    records = list(
        SleepRecord.objects.filter(student=student, date__gte=week_start, date__lte=target_date)
        .order_by("date")
    )

    # 构建 7 夜日期列表
    days = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        rec = next((r for r in records if r.date == d), None)
        days.append({
            "date": d.isoformat(),
            "quality_score": rec.quality_score if rec else 0,
            "duration_minutes": rec.duration_minutes if rec else 0,
            "status": rec.status if rec else "missed",
            "bedtime": rec.bedtime.strftime("%H:%M") if rec and rec.bedtime else None,
            "wake_time": rec.wake_time.strftime("%H:%M") if rec and rec.wake_time else None,
        })

    # 连续打卡天数
    streak = 0
    d = target_date
    while True:
        rec = SleepRecord.objects.filter(student=student, date=d).exclude(status="missed").first()
        if rec:
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    checked = [r for r in records if r.status != "missed"]
    avg_quality = round(sum(r.quality_score for r in checked) / len(checked), 1) if checked else 0
    avg_duration = round(sum(r.duration_minutes for r in checked) / len(checked)) if checked else 0

    # 昨夜状态。字段名保持兼容，前端文案显示为"昨夜"。
    target_record = SleepRecord.objects.filter(student=student, date=target_date).first()

    return Response({
        "target_date": target_date.isoformat(),
        "days": days,
        "streak": streak,
        "avg_quality": avg_quality,
        "avg_duration": avg_duration,
        "today_status": target_record.status if target_record else "missed",
        "today_checked": target_record is not None and target_record.status != "missed",
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def heatmap_data(request):
    """全年热力图数据，返回 {date: YYYY-MM-DD, value: quality_score, status: ...}。"""
    student = _student_of(request.user)
    if not student:
        return Response({"detail": "无学生档案"}, status=status.HTTP_400_BAD_REQUEST)

    year = request.query_params.get("year", str(date.today().year))
    try:
        year_int = int(year)
    except ValueError:
        year_int = date.today().year

    records = SleepRecord.objects.filter(
        student=student,
        date__year=year_int,
    ).values("date", "quality_score", "status")

    data = [
        {
            "date": r["date"].isoformat(),
            "value": r["quality_score"],
            "status": r["status"],
        }
        for r in records
    ]
    return Response({"year": year_int, "data": data})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def class_ranking(request):
    """班级近 30 天平均质量分排行（匿名，自己显示真名）。"""
    student = _student_of(request.user)
    if not student or not student.classroom:
        return Response({"detail": "未加入班级"}, status=status.HTTP_400_BAD_REQUEST)

    since = date.today() - timedelta(days=29)
    classmates = StudentProfile.objects.filter(classroom=student.classroom)

    ranking = []
    for idx, s in enumerate(classmates):
        records = SleepRecord.objects.filter(
            student=s, date__gte=since
        ).exclude(status="missed")
        checked_count = records.count()
        avg_q = records.aggregate(avg=Avg("quality_score"))["avg"] or 0
        ranking.append({
            "student_id": s.id,
            "avg_quality": round(avg_q, 1),
            "checked_count": checked_count,
        })

    ranking.sort(key=lambda x: -x["avg_quality"])

    result = []
    for rank, item in enumerate(ranking, start=1):
        s_id = item["student_id"]
        is_me = (s_id == student.id)
        sp = classmates.get(id=s_id)
        label = sp.real_name if is_me else f"同学{chr(64 + rank)}"
        result.append({
            "rank": rank,
            "name": label,
            "is_me": is_me,
            "avg_quality": item["avg_quality"],
            "checked_count": item["checked_count"],
        })

    my_rank = next((r for r in result if r["is_me"]), None)
    return Response({"ranking": result, "my_rank": my_rank, "total": len(result)})


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def teacher_edit_record(request, pk: int):
    """老师代改学生记录。自动校验老师只能改自己班级的学生。"""
    record = get_object_or_404(SleepRecord.objects.select_related("student__classroom"), pk=pk)
    classroom = record.student.classroom
    if not classroom or classroom.teacher_id != request.user.id:
        return Response({"detail": "无权修改非本班学生的记录"}, status=status.HTTP_403_FORBIDDEN)

    serializer = SleepRecordTeacherEditSerializer(
        record, data=request.data, partial=True, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    read = SleepRecordReadSerializer(instance, context={"request": request})
    return Response(read.data)
