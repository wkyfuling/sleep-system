"""M7 成就视图。"""
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.users.models import User
from apps.users.permissions import role_required
from .models import Achievement, StudentAchievement
from .unlock import ensure_achievements_seeded


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.STUDENT)])
def my_achievements(request):
    """返回学生的成就列表（已解锁 + 未解锁全量）。"""
    ensure_achievements_seeded()
    student = getattr(request.user, "student_profile", None)
    if not student:
        return Response({"detail": "无学生档案"})

    all_ach = Achievement.objects.all()
    unlocked_ids = set(
        StudentAchievement.objects.filter(student=student).values_list("achievement_id", flat=True)
    )
    unlocked_at_map = {
        sa.achievement_id: sa.unlocked_at
        for sa in StudentAchievement.objects.filter(student=student).select_related("achievement")
    }

    result = []
    for a in all_ach:
        is_unlocked = a.id in unlocked_ids
        result.append({
            "code": a.code,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "unlocked": is_unlocked,
            "unlocked_at": unlocked_at_map.get(a.id),
        })

    unlocked_count = len(unlocked_ids)
    return Response({
        "total": len(result),
        "unlocked_count": unlocked_count,
        "achievements": result,
    })
