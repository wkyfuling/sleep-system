"""APScheduler 入口：独立进程每天 10:00 执行 mark_missed_yesterday。

部署/答辩时单独运行：
    python manage.py run_scheduler
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings


logger = logging.getLogger(__name__)


def build_scheduler() -> BlockingScheduler:
    from apps.notifications.tasks import mark_missed_yesterday

    scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_job(
        mark_missed_yesterday,
        trigger=CronTrigger(hour=10, minute=0, timezone=settings.TIME_ZONE),
        id="mark_missed_yesterday",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler


def run():
    logger.info("启动 APScheduler，每天 10:00 (本地时区) 运行 mark_missed_yesterday")
    scheduler = build_scheduler()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
