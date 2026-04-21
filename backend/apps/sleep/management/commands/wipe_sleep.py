"""Dev-only：清空指定学号的睡眠记录，便于重复跑 E2E 测试。

    python manage.py wipe_sleep --student_no M4001 M4002
    python manage.py wipe_sleep --all  # 清全表（慎用）
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.sleep.models import SleepRecord
from apps.users.models import StudentProfile


class Command(BaseCommand):
    help = "Dev only：清除睡眠记录"

    def add_arguments(self, parser):
        parser.add_argument("--student_no", nargs="*", default=None)
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **opts):
        if opts["all"]:
            n, _ = SleepRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"wiped ALL records: {n}"))
            return
        nos = opts["student_no"]
        if not nos:
            raise CommandError("--student_no 或 --all 必填其一")
        qs = SleepRecord.objects.filter(student__student_no__in=nos)
        n, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"wiped {n} records for students {nos}"))
