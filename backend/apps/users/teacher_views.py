"""老师端 API：班级概览、学生列表、学生睡眠趋势。"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Avg, Count
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import ClassRoom, User
from apps.users.permissions import role_required
from apps.sleep.models import SleepRecord


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def create_classroom(request):
    """老师创建班级并获得班级邀请码。"""
    name = (request.data.get("name") or request.data.get("classroom_name") or "").strip()
    if not name:
        return Response({"detail": "班级名称必填"}, status=status.HTTP_400_BAD_REQUEST)

    classroom = ClassRoom.objects.create(name=name, teacher=request.user)
    return Response({
        "classroom": {
            "id": classroom.id,
            "name": classroom.name,
            "invite_code": classroom.invite_code,
            "created_at": classroom.created_at,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def class_overview(request):
    """老师端班级整体概览：统计最近 7 天。"""
    classrooms = request.user.classrooms.prefetch_related("students")
    if not classrooms.exists():
        return Response({"detail": "您未创建班级", "classrooms": []})

    result = []
    for classroom in classrooms:
        students = list(classroom.students.select_related("user"))
        total = len(students)
        since = date.today() - timedelta(days=6)

        # 今日打卡率
        today_checked = SleepRecord.objects.filter(
            student__classroom=classroom,
            date=date.today(),
        ).exclude(status="missed").count()

        # 近 7 天严重人数
        severe_students = (
            SleepRecord.objects.filter(
                student__classroom=classroom,
                date__gte=since,
                status="severe",
            )
            .values("student_id")
            .distinct()
            .count()
        )

        # 近 7 天平均质量分
        avg_q = SleepRecord.objects.filter(
            student__classroom=classroom,
            date__gte=since,
        ).exclude(status="missed").aggregate(avg=Avg("quality_score"))["avg"]

        result.append({
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "invite_code": classroom.invite_code,
            "total_students": total,
            "today_checked": today_checked,
            "checkin_rate": round(today_checked / total * 100, 1) if total else 0,
            "severe_count": severe_students,
            "avg_quality_7d": round(avg_q, 1) if avg_q else 0,
        })

    return Response({"classrooms": result})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def student_list(request):
    """老师端学生列表，支持 ?status=severe&classroom_id=N。"""
    classrooms = request.user.classrooms.all()
    if not classrooms.exists():
        return Response({"results": []})

    classroom_id = request.query_params.get("classroom_id")
    if classroom_id:
        classrooms = classrooms.filter(id=classroom_id)

    status_filter = request.query_params.get("status")
    since = date.today() - timedelta(days=7)

    data = []
    for classroom in classrooms:
        for student in classroom.students.select_related("user").order_by("student_no"):
            latest = SleepRecord.objects.filter(student=student).order_by("-date").first()
            recent_severe = SleepRecord.objects.filter(
                student=student, date__gte=since, status="severe"
            ).count()
            avg_q = SleepRecord.objects.filter(
                student=student, date__gte=since
            ).exclude(status="missed").aggregate(avg=Avg("quality_score"))["avg"]

            entry = {
                "student_id": student.id,
                "student_no": student.student_no,
                "real_name": student.real_name,
                "classroom": classroom.name,
                "risk_level": student.risk_level,
                "latest_date": latest.date.isoformat() if latest else None,
                "latest_status": latest.status if latest else "missed",
                "avg_quality_7d": round(avg_q, 1) if avg_q else 0,
                "severe_count_7d": recent_severe,
            }

            if status_filter:
                if status_filter == "severe" and recent_severe == 0:
                    continue
                if status_filter == "focus" and student.risk_level != "focus":
                    continue
            data.append(entry)

    return Response({"results": data, "count": len(data)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def student_trend(request, student_id: int):
    """老师端：某学生近 30 天睡眠趋势。"""
    from apps.users.models import StudentProfile
    # 验证是本班学生
    student = None
    for classroom in request.user.classrooms.all():
        student = classroom.students.filter(id=student_id).first()
        if student:
            break
    if not student:
        return Response({"detail": "学生不在本班"}, status=status.HTTP_403_FORBIDDEN)

    since = date.today() - timedelta(days=29)
    records = SleepRecord.objects.filter(student=student, date__gte=since).order_by("date")

    data = []
    for r in records:
        entry = {
            "id": r.id,
            "date": r.date.isoformat(),
            "quality_score": r.quality_score,
            "duration_minutes": r.duration_minutes,
            "status": r.status,
            "bedtime": r.bedtime.strftime("%H:%M") if r.bedtime else None,
            "wake_time": r.wake_time.strftime("%H:%M") if r.wake_time else None,
        }
        # diary 根据 share_diary_to_teacher 开关
        if student.share_diary_to_teacher:
            entry["diary"] = r.diary
        data.append(entry)

    return Response({
        "student": {"id": student.id, "name": student.real_name, "no": student.student_no},
        "records": data,
    })
