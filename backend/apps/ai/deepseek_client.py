"""DeepSeek AI 客户端 + Mock 兜底。

当 DEEPSEEK_API_KEY 为空或请求失败时，业务接口自动返回基于规则的模板建议，
保证学生端和老师端页面不崩溃。运维测试命令可关闭兜底，直接暴露配置或网络错误。
"""
from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class AIResult:
    text: str
    is_mock: bool
    provider: str = "mock"
    error: str = ""


class DeepSeekError(RuntimeError):
    """DeepSeek 调用失败。"""


class DeepSeekConfigError(DeepSeekError):
    """DeepSeek 配置缺失或无效。"""


class DeepSeekRequestError(DeepSeekError):
    """DeepSeek HTTP 请求失败。"""


class DeepSeekResponseError(DeepSeekError):
    """DeepSeek 返回结构不符合预期。"""


def _mock_advice(avg_quality: float, avg_duration: int, streak: int, recent_status: str) -> str:
    """基于规则生成模板建议（无需 API Key）。"""
    tips = []

    if avg_duration < 360:  # < 6h
        tips.append("您近期睡眠时长严重不足（< 6 小时），建议每晚保证至少 7-8 小时睡眠，这对记忆巩固和身体修复至关重要。")
    elif avg_duration < 420:  # < 7h
        tips.append("您近期睡眠时长略微不足，建议提前 30 分钟上床，给身体足够的恢复时间。")
    else:
        tips.append("您的睡眠时长保持良好，继续坚持规律作息。")

    if avg_quality < 50:
        tips.append("睡眠质量评分偏低，可能与入睡过晚或睡眠时间不规律有关。建议固定入睡时间，睡前 1 小时避免使用手机，有助于改善睡眠质量。")
    elif avg_quality < 70:
        tips.append("睡眠质量有提升空间。尝试在睡前进行放松活动（如阅读、轻音乐），减少咖啡因摄入，可有效提高睡眠深度。")
    elif avg_quality >= 85:
        tips.append("睡眠质量优秀！保持当前良好的作息习惯，继续坚持。")

    if recent_status in ("severe", "abnormal"):
        tips.append("近期出现睡眠异常，如持续感到疲惫或注意力下降，建议与班主任或家长沟通，必要时咨询专业人士。")

    if streak >= 7:
        tips.append(f"已连续打卡 {streak} 天，坚持记录睡眠是改善睡眠的第一步，继续保持！")
    elif streak < 3:
        tips.append("保持每日打卡习惯，有助于发现自身的睡眠规律，为科学调整提供数据支撑。")

    return "\n\n".join(f"• {t}" for t in tips)


def _mock_result(error: str = "") -> AIResult:
    return AIResult(text=_mock_advice(70, 450, 5, "normal"), is_mock=True, provider="mock", error=error)


def _chat_completions_url(base_url: str) -> str:
    """生成兼容 DeepSeek 官方 base_url 和 OpenAI 风格 /v1 base_url 的聊天接口地址。"""
    base = (base_url or "https://api.deepseek.com").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _extract_text(payload: dict) -> str:
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekResponseError("DeepSeek 返回结构异常，未找到 choices[0].message.content") from exc

    if not isinstance(text, str) or not text.strip():
        raise DeepSeekResponseError("DeepSeek 返回内容为空")
    return text.strip()


DEFAULT_SYSTEM_PROMPT = "你是一位专业的青少年睡眠健康顾问，用简洁、温暖、专业的语言给出改善建议，每次回复不超过 300 字。"


def call_deepseek(
    prompt: str,
    *,
    allow_mock: bool = True,
    system_prompt: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> AIResult:
    """调用 DeepSeek API；业务接口默认允许 Mock 兜底。"""
    api_key = getattr(settings, "DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        error = "未配置 DEEPSEEK_API_KEY"
        if allow_mock:
            return _mock_result(error)
        raise DeepSeekConfigError(error)

    try:
        import httpx

        base_url = getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = model or getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
        timeout = float(timeout if timeout is not None else getattr(settings, "DEEPSEEK_TIMEOUT_SECONDS", 60))
        max_tokens = int(max_tokens if max_tokens is not None else getattr(settings, "DEEPSEEK_MAX_TOKENS", 500))
        temperature = float(temperature if temperature is not None else getattr(settings, "DEEPSEEK_TEMPERATURE", 0.7))

        resp = httpx.post(
            _chat_completions_url(base_url),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return AIResult(text=_extract_text(resp.json()), is_mock=False, provider="deepseek")

    except Exception as exc:
        error = str(exc)
        logger.warning("DeepSeek request failed, falling back to mock advice: %s", error)
        if allow_mock:
            return _mock_result(error)
        if isinstance(exc, DeepSeekError):
            raise
        raise DeepSeekRequestError(f"DeepSeek 请求失败：{error}") from exc


def build_student_prompt(stats: dict) -> str:
    """根据学生近期数据组装 prompt。"""
    return textwrap.dedent(f"""
        学生近 7 天睡眠数据摘要：
        - 平均质量分：{stats.get('avg_quality', '—')}（满分100）
        - 平均睡眠时长：{stats.get('avg_duration_h', '—')} 小时
        - 连续打卡天数：{stats.get('streak', 0)} 天
        - 近期最差状态：{stats.get('worst_status', '—')}
        - 最近入睡时间：{stats.get('latest_bedtime', '—')}

        请根据以上数据，给出 3-5 条针对性的睡眠改善建议。
    """).strip()
