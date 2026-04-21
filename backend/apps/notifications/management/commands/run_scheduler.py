"""以独立进程运行 APScheduler 定时任务。

    python manage.py run_scheduler

会阻塞前台；可放到 Docker 里作为单独容器/服务。
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "以阻塞方式运行 APScheduler（每天 10:00 执行 mark_missed_yesterday）"

    def handle(self, *args, **options):
        from utils.scheduler import run
        run()
