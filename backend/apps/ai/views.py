"""M7 AI 建议视图。

端点：
- POST /api/ai/advice/         手动触发（每天限 3 次）
- GET  /api/ai/advice/history/ 最近 30 条
- POST /api/ai/class-diagnosis/ 老师调用——班级整体诊断
"""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.models import ClassRoom, StudentProfile, User
from apps.users.permissions import role_required
from apps.sleep.models import SleepRecord

from .models import AIAdvice
from .deepseek_client import AIResult, build_student_prompt, call_deepseek

DAILY_LIMIT = 3
MAX_CHAT_MESSAGE_LEN = 800
MAX_CHAT_HISTORY = 6


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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def chat(request):
    """全角色悬浮 AI 助手：根据角色摘要上下文进行轻量问答。"""
    message = str(request.data.get("message") or "").strip()
    if not message:
        return Response({"detail": "请输入问题"}, status=status.HTTP_400_BAD_REQUEST)
    if len(message) > MAX_CHAT_MESSAGE_LEN:
        return Response({"detail": f"问题过长，请控制在 {MAX_CHAT_MESSAGE_LEN} 字以内"}, status=status.HTTP_400_BAD_REQUEST)

    page_context = str(request.data.get("page_context") or "").strip()[:120]
    history = _format_chat_history(request.data.get("history") or [])
    role_context = _build_role_context(request.user)

    prompt = (
        f"当前用户角色：{request.user.get_role_display()}端\n"
        f"当前页面：{page_context or '未知'}\n\n"
        f"系统业务数据摘要：\n{role_context}\n\n"
        f"最近对话：\n{history or '暂无'}\n\n"
        f"用户问题：{message}\n\n"
        "请基于以上信息回答。若数据不足，请明确说明还需要用户补充什么。"
    )
    system_prompt = (
        "你是 SleepCare AI 助手，服务于学生睡眠管理系统。"
        "回答必须使用中文，语气专业、简洁、可执行。"
        "只基于给出的业务摘要分析，不要编造具体学生、班级或打卡数据。"
        "涉及健康风险时提醒用户联系家长、老师或专业人士，不要做医疗诊断。"
        "除非用户要求详细说明，否则每次回复不超过 450 字。"
    )
    result = call_deepseek(prompt, system_prompt=system_prompt)
    return Response({
        "reply": result.text,
        "is_mock": result.is_mock,
        "provider": result.provider,
    })


def _format_chat_history(items) -> str:
    if not isinstance(items, list):
        return ""

    lines = []
    for item in items[-MAX_CHAT_HISTORY:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        label = "用户" if role == "user" else "助手"
        lines.append(f"{label}：{content[:500]}")
    return "\n".join(lines)


def _build_role_context(user: User) -> str:
    if user.role == User.Role.STUDENT:
        return _student_context(user)
    if user.role == User.Role.TEACHER:
        return _teacher_context(user)
    if user.role == User.Role.PARENT:
        return _parent_context(user)
    if user.role == User.Role.ADMIN:
        return _admin_context()
    return "未识别角色。"


def _student_context(user: User) -> str:
    student = getattr(user, "student_profile", None)
    if not student:
        return "当前用户暂无学生档案。"
    return _student_sleep_summary(student, days=14)


def _teacher_context(user: User) -> str:
    classrooms = list(user.classrooms.prefetch_related("students"))
    if not classrooms:
        return "当前老师尚未创建班级。"

    target_date = timezone.localdate() - timedelta(days=1)
    since = target_date - timedelta(days=6)
    lines = [f"统计区间：{since.isoformat()} 至 {target_date.isoformat()}。"]
    for classroom in classrooms[:5]:
        total = classroom.students.count()
        records = SleepRecord.objects.filter(
            student__classroom=classroom,
            date__gte=since,
            date__lte=target_date,
        )
        valid = records.exclude(status=SleepRecord.Status.MISSED)
        checked = records.filter(date=target_date).exclude(status=SleepRecord.Status.MISSED).count()
        severe_students = records.filter(status=SleepRecord.Status.SEVERE).values("student_id").distinct().count()
        valid_count = valid.count()
        avg_quality = round(sum(r.quality_score for r in valid) / valid_count, 1) if valid_count else 0
        avg_duration = round(sum(r.duration_minutes for r in valid) / valid_count / 60, 1) if valid_count else 0
        rate = round(checked / total * 100, 1) if total else 0
        lines.append(
            f"{classroom.name}：{total} 人，昨夜打卡率 {rate}%，近 7 夜平均质量 {avg_quality}，"
            f"平均时长 {avg_duration} 小时，严重异常涉及 {severe_students} 人。"
        )
    return "\n".join(lines)


def _parent_context(user: User) -> str:
    parent = getattr(user, "parent_profile", None)
    if not parent or not parent.child:
        return "当前家长尚未绑定孩子。"
    return "绑定孩子概况：\n" + _student_sleep_summary(parent.child, days=30)


def _admin_context() -> str:
    today = timezone.localdate()
    total_users = User.objects.count()
    students = User.objects.filter(role=User.Role.STUDENT).count()
    teachers = User.objects.filter(role=User.Role.TEACHER).count()
    parents = User.objects.filter(role=User.Role.PARENT).count()
    classrooms = ClassRoom.objects.count()
    today_submits = SleepRecord.objects.filter(created_at__date=today).exclude(status=SleepRecord.Status.MISSED).count()
    severe_today = SleepRecord.objects.filter(created_at__date=today, status=SleepRecord.Status.SEVERE).count()
    return (
        f"系统用户 {total_users} 人，其中学生 {students}、老师 {teachers}、家长 {parents}。"
        f"班级 {classrooms} 个。今日提交 {today_submits} 条，今日严重异常 {severe_today} 条。"
    )


def _student_sleep_summary(student: StudentProfile, *, days: int) -> str:
    today = timezone.localdate()
    since = today - timedelta(days=days - 1)
    records = list(
        SleepRecord.objects
        .filter(student=student, date__gte=since, date__lte=today)
        .order_by("-date")
    )
    valid = [r for r in records if r.status != SleepRecord.Status.MISSED]
    latest = records[0] if records else None
    avg_quality = round(sum(r.quality_score for r in valid) / len(valid), 1) if valid else 0
    avg_duration = round(sum(r.duration_minutes for r in valid) / len(valid) / 60, 1) if valid else 0
    severe_count = sum(1 for r in records if r.status == SleepRecord.Status.SEVERE)
    abnormal_count = sum(1 for r in records if r.status == SleepRecord.Status.ABNORMAL)
    latest_text = "暂无记录"
    if latest:
        latest_text = (
            f"{latest.date.isoformat()}，状态 {latest.get_status_display()}，"
            f"质量分 {latest.quality_score}，时长 {round(latest.duration_minutes / 60, 1)} 小时"
        )

    classroom = student.classroom.name if student.classroom else "未加入班级"
    return (
        f"学生：{student.real_name}，班级：{classroom}，目标睡眠 {student.target_sleep_hours} 小时，"
        f"目标入睡 {student.target_bedtime.strftime('%H:%M')}。\n"
        f"近 {days} 天有效打卡 {len(valid)} 天，平均质量 {avg_quality}，平均时长 {avg_duration} 小时，"
        f"严重异常 {severe_count} 次，异常 {abnormal_count} 次。\n"
        f"最近记录：{latest_text}。"
    )


def _try_unlock_achievement(student, code: str):
    """尝试解锁成就（已有则跳过）。"""
    try:
        from apps.achievements.models import Achievement, StudentAchievement
        ach = Achievement.objects.filter(code=code).first()
        if ach:
            StudentAchievement.objects.get_or_create(student=student, achievement=ach)
    except Exception:
        pass
