"""管理命令：python manage.py seed_demo_data

生成演示种子数据（30 学生 + 365 天记录 + 科普文章）。
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "生成演示种子数据（30 名学生 + 365 天睡眠记录 + 预置文章）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="跳过确认提示，直接运行",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            self.stdout.write(
                self.style.WARNING(
                    "此命令将向数据库写入大量演示数据（30 学生 + ~10000 条睡眠记录）。\n"
                    "已有数据不会删除，但会跳过冲突记录。\n"
                    "确认继续？输入 yes 回车："
                )
            )
            confirm = input().strip().lower()
            if confirm != "yes":
                self.stdout.write("已取消。")
                return

        self.stdout.write("开始生成种子数据…")

        import sys, os
        # 确保 utils 在路径上
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        from utils.seed_data import run
        run(stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS("种子数据生成完毕！"))
