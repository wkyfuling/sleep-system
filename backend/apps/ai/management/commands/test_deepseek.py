from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ai.deepseek_client import DeepSeekError, call_deepseek


class Command(BaseCommand):
    help = "Test the configured DeepSeek API key with a real request."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prompt",
            default="请用一句中文回复：DeepSeek API 已经接入成功。",
            help="Prompt to send to DeepSeek.",
        )

    def handle(self, *args, **options):
        model = getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
        base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.stdout.write(f"Testing DeepSeek API: model={model}, base_url={base_url}")

        try:
            result = call_deepseek(options["prompt"], allow_mock=False)
        except DeepSeekError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("DeepSeek API OK"))
        self.stdout.write(result.text)
