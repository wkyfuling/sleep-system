"""手动触发"昨日未打卡→missed"任务。

用法：
    python manage.py mark_missed                     # 处理昨天
    python manage.py mark_missed --date 2026-04-20   # 处理指定日期
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.notifications.tasks import mark_missed_for_date


class Command(BaseCommand):
    help = "为指定日期（默认昨天）没打卡的学生生成 missed 记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", dest="target_date", default=None,
            help="ISO 日期 YYYY-MM-DD，默认昨天",
        )

    def handle(self, *args, **options):
        raw = options.get("target_date")
        if raw:
            try:
                target = date.fromisoformat(raw)
            except ValueError as e:
                raise CommandError(f"--date 参数格式错误：{raw} ({e})")
        else:
            target = timezone.localdate() - timedelta(days=1)

        result = mark_missed_for_date(target)
        self.stdout.write(self.style.SUCCESS(
            f"[mark_missed] date={result['date']} created={result['created']} "
            f"existing={result['existing']}"
        ))
