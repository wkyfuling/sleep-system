"""M7 AI 建议视图。

端点：
- POST /api/ai/advice/         手动触发（每天限 3 次）
- GET  /api/ai/advice/history/ 最近 30 条
- POST /api/ai/class-diagnosis/ 老师调用——班级整体诊断
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Avg
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.models import User
from apps.users.permissions import role_required
from apps.sleep.models import SleepRecord

from .models import AIAdvice
from .deepseek_client import AIResult, build_student_prompt, call_deepseek, _mock_advice

DAILY_LIMIT = 3


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def get_advice(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        return Response({"detail": "无学生档案"}, status=status.HTTP_400_BAD_REQUEST)

    # 限流：今天已触发次数
    today = date.today()
    today_count = AIAdvice.objects.filter(
        student=student,
        trigger_type=AIAdvice.TriggerType.MANUAL,
        created_at__date=today,
    ).count()
    if today_count >= DAILY_LIMIT:
        return Response(
            {"detail": f"今日 AI 建议已达上限（{DAILY_LIMIT} 次），请明天再试"},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # 收集近 7 天数据
    since = today - timedelta(days=6)
    records = list(SleepRecord.objects.filter(student=student, date__gte=since).exclude(status="missed"))
    checked = len(records)
    avg_quality = round(sum(r.quality_score for r in records) / checked, 1) if checked else 0
    avg_duration_mins = round(sum(r.duration_minutes for r in records) / checked) if checked else 0
    worst_status = "normal"
    status_order = ["severe", "abnormal", "warning", "normal"]
    for s in status_order:
        if any(r.status == s for r in records):
            worst_status = s
            break
    latest_bedtime = None
    latest = sorted(records, key=lambda r: r.date, reverse=True)
    if latest and latest[0].bedtime:
        latest_bedtime = latest[0].bedtime.strftime("%H:%M")

    # streak
    streak = 0
    d = today
    while True:
        rec = SleepRecord.objects.filter(student=student, date=d).exclude(status="missed").first()
        if rec:
            streak += 1
            d -= timedelta(days=1)
        else:
            break

    stats = {
        "avg_quality": avg_quality,
        "avg_duration_h": round(avg_duration_mins / 60, 1),
        "streak": streak,
        "worst_status": worst_status,
        "latest_bedtime": latest_bedtime,
    }
    prompt = build_student_prompt(stats)

    # 调用 AI（有 Key 则真实，否则 Mock）
    result: AIResult = call_deepseek(prompt)

    advice = AIAdvice.objects.create(
        student=student,
        trigger_type=AIAdvice.TriggerType.MANUAL,
        prompt_summary=str(stats),
        advice_text=result.text,
        is_mock=result.is_mock,
    )

    # 打卡解锁 AI 使用成就
    _try_unlock_achievement(student, "ai_user")

    return Response({
        "id": advice.id,
        "advice_text": advice.advice_text,
        "is_mock": advice.is_mock,
        "created_at": advice.created_at,
        "remaining_today": DAILY_LIMIT - today_count - 1,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def advice_history(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        return Response({"detail": "无学生档案"}, status=status.HTTP_400_BAD_REQUEST)

    advices = AIAdvice.objects.filter(student=student)[:30]
    data = [
        {
            "id": a.id,
            "trigger_type": a.trigger_type,
            "advice_text": a.advice_text,
            "is_mock": a.is_mock,
            "created_at": a.created_at,
        }
        for a in advices
    ]
    return Response({"results": data})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def class_diagnosis(request):
    """老师端：班级整体睡眠诊断（不含个人明细）。"""
    teacher = request.user
    classrooms = teacher.classrooms.prefetch_related("students")
    if not classrooms.exists():
        return Response({"detail": "您未创建班级"}, status=status.HTTP_400_BAD_REQUEST)

    since = date.today() - timedelta(days=6)
    all_records = []
    student_count = 0
    for classroom in classrooms:
        for student in classroom.students.all():
            student_count += 1
            records = list(SleepRecord.objects.filter(student=student, date__gte=since).exclude(status="missed"))
            all_records.extend(records)

    if not all_records:
        avg_q, avg_dur, severe_pct = 0, 0, 0
    else:
        avg_q = round(sum(r.quality_score for r in all_records) / len(all_records), 1)
        avg_dur = round(sum(r.duration_minutes for r in all_records) / len(all_records))
        severe_pct = round(sum(1 for r in all_records if r.status == "severe") / len(all_records) * 100, 1)

    prompt = (
        f"班级近 7 天整体睡眠数据（{student_count} 名学生）：\n"
        f"- 平均质量分：{avg_q}\n"
        f"- 平均睡眠时长：{round(avg_dur/60, 1)} 小时\n"
        f"- 严重异常比例：{severe_pct}%\n\n"
        "请给出 3-5 条针对班级的整体睡眠管理建议，供班主任参考。"
    )

    result = call_deepseek(prompt)
    return Response({
        "advice_text": result.text,
        "is_mock": result.is_mock,
        "stats": {"avg_quality": avg_q, "avg_duration_h": round(avg_dur/60, 1), "severe_pct": severe_pct},
    })


def _try_unlock_achievement(student, code: str):
    """尝试解锁成就（已有则跳过）。"""
    try:
        from apps.achievements.models import Achievement, StudentAchievement
        ach = Achievement.objects.filter(code=code).first()
        if ach:
            StudentAchievement.objects.get_or_create(student=student, achievement=ach)
    except Exception:
        pass
