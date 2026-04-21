"""成就解锁引擎。

在打卡完成后调用 `check_and_unlock(student)`，检查所有条件并批量解锁。
"""
from __future__ import annotations

from datetime import date, timedelta

from apps.sleep.models import SleepRecord
from .models import Achievement, StudentAchievement

# 预置 10 个成就定义
ACHIEVEMENT_DEFS = [
    {
        "code": "first_checkin",
        "name": "睡眠初体验",
        "description": "完成第一次打卡",
        "icon": "🌱",
    },
    {
        "code": "streak_7",
        "name": "一周坚持",
        "description": "连续打卡 7 天",
        "icon": "🔥",
    },
    {
        "code": "streak_30",
        "name": "月度达人",
        "description": "连续打卡 30 天",
        "icon": "💪",
    },
    {
        "code": "streak_100",
        "name": "睡眠大师",
        "description": "连续打卡 100 天",
        "icon": "🏆",
    },
    {
        "code": "full_week_healthy",
        "name": "完美一周",
        "description": "连续 7 天状态均为「健康」",
        "icon": "⭐",
    },
    {
        "code": "early_bird",
        "name": "早睡达人",
        "description": "连续 5 天在 23:00 前入睡",
        "icon": "🌙",
    },
    {
        "code": "diary_author",
        "name": "日记作者",
        "description": "累计写了 10 篇睡眠日记",
        "icon": "📝",
    },
    {
        "code": "ai_user",
        "name": "智慧睡眠",
        "description": "首次使用 AI 健康建议",
        "icon": "🤖",
    },
    {
        "code": "class_top3",
        "name": "班级之星",
        "description": "班级排行榜进入前 3 名",
        "icon": "🌟",
    },
    {
        "code": "total_50",
        "name": "坚持不懈",
        "description": "累计打卡 50 次",
        "icon": "🎯",
    },
]


def ensure_achievements_seeded():
    """确保成就定义存在（可重复调用，幂等）。"""
    for d in ACHIEVEMENT_DEFS:
        Achievement.objects.get_or_create(code=d["code"], defaults={
            "name": d["name"],
            "description": d["description"],
            "icon": d["icon"],
        })


def _unlock(student, code: str) -> bool:
    """尝试解锁，已有则忽略。返回是否是新解锁。"""
    ach = Achievement.objects.filter(code=code).first()
    if not ach:
        return False
    _, created = StudentAchievement.objects.get_or_create(student=student, achievement=ach)
    return created


def _streak(student) -> int:
    """计算当前连续打卡天数。"""
    today = date.today()
    count = 0
    d = today
    while True:
        rec = SleepRecord.objects.filter(student=student, date=d).exclude(status="missed").first()
        if rec:
            count += 1
            d -= timedelta(days=1)
        else:
            break
    return count


def check_and_unlock(student) -> list[str]:
    """检查并解锁所有符合条件的成就。返回新解锁成就名列表。"""
    ensure_achievements_seeded()
    unlocked = []

    total_records = SleepRecord.objects.filter(student=student).exclude(status="missed").count()

    # 首次打卡
    if total_records >= 1:
        if _unlock(student, "first_checkin"):
            unlocked.append("睡眠初体验")

    # 累计 50 次
    if total_records >= 50:
        if _unlock(student, "total_50"):
            unlocked.append("坚持不懈")

    # 连续天数
    streak = _streak(student)
    if streak >= 7:
        if _unlock(student, "streak_7"):
            unlocked.append("一周坚持")
    if streak >= 30:
        if _unlock(student, "streak_30"):
            unlocked.append("月度达人")
    if streak >= 100:
        if _unlock(student, "streak_100"):
            unlocked.append("睡眠大师")

    # 连续 7 天全健康
    today = date.today()
    last_7 = [today - timedelta(days=i) for i in range(7)]
    week_records = SleepRecord.objects.filter(student=student, date__in=last_7)
    if week_records.count() == 7 and all(r.status == "normal" for r in week_records):
        if _unlock(student, "full_week_healthy"):
            unlocked.append("完美一周")

    # 连续 5 天 23:00 前入睡
    last_5 = [today - timedelta(days=i) for i in range(5)]
    early_records = SleepRecord.objects.filter(student=student, date__in=last_5).exclude(status="missed")
    if early_records.count() == 5 and all(
        r.bedtime and (r.bedtime.hour < 23 or (r.bedtime.hour == 23 and r.bedtime.minute == 0))
        for r in early_records
    ):
        if _unlock(student, "early_bird"):
            unlocked.append("早睡达人")

    # 日记作者：累计 10 篇有内容的日记
    diary_count = SleepRecord.objects.filter(student=student).exclude(diary="").count()
    if diary_count >= 10:
        if _unlock(student, "diary_author"):
            unlocked.append("日记作者")

    return unlocked
