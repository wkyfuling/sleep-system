"""M4.3 定时任务：次日 10:00 标 missed。

独立函数以便被 scheduler 或 management 命令调用，也便于单元测试。
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.sleep.models import SleepRecord
from apps.users.models import StudentProfile


logger = logging.getLogger(__name__)


@transaction.atomic
def mark_missed_for_date(target_date) -> dict:
    """为某一天没打卡的学生插入 missed 占位。返回 {created, skipped} 统计。"""
    students = StudentProfile.objects.all()
    existing = set(
        SleepRecord.objects
        .filter(date=target_date, student__in=students)
        .values_list("student_id", flat=True)
    )
    to_create = [
        SleepRecord(
            student=s,
            date=target_date,
            duration_minutes=0,
            subjective_score=0,
            quality_score=0,
            status=SleepRecord.Status.MISSED,
        )
        for s in students if s.id not in existing
    ]
    if to_create:
        SleepRecord.objects.bulk_create(to_create)
        previous_date = target_date - timedelta(days=1)
        focus_ids = []
        for record in to_create:
            if SleepRecord.objects.filter(
                student=record.student,
                date=previous_date,
                status=SleepRecord.Status.MISSED,
            ).exists():
                focus_ids.append(record.student_id)
        if focus_ids:
            StudentProfile.objects.filter(id__in=focus_ids).update(
                risk_level=StudentProfile.RiskLevel.FOCUS
            )
    logger.info(
        "mark_missed_for_date(%s): created=%d, existing=%d",
        target_date, len(to_create), len(existing),
    )
    return {"date": str(target_date), "created": len(to_create), "existing": len(existing)}


def mark_missed_yesterday() -> dict:
    """入口：处理昨天的未打卡。"""
    yesterday = timezone.localdate() - timedelta(days=1)
    return mark_missed_for_date(yesterday)
