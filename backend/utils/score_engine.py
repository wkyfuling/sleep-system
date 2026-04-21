"""睡眠质量评分引擎 — 纯函数模块。

设计目标（答辩可讲分层思想）：
- 无任何 Django ORM 依赖，便于单元测试
- 规则集中一处，调整权重/阈值只改本文件
- 输入 = (bedtime, wake_time, subjective_score)，输出 = (date, duration_minutes, quality_score, status)

评分结构（满分 100）：
- 时长分 50 分：7-9h 满分 / 6-7h 或 9-10h 35 分 / 5-6h 20 分 / <5h 10 分 / =0 0 分
- 入睡时间分 30 分：≤健康线 30 / 健康线+30min 20 / +60min 10 / 更晚 0
  - 健康线：周日-周四晚 23:30；周五周六晚 00:00（周末放宽）
- 主观分 20 分：1→4 / 2→8 / 3→12 / 4→16 / 5→20

状态分档：
- ≥85 normal / 70-84 warning / 50-69 abnormal / <50 severe

跨天归属（"那晚所属日期"）：
- 若 bedtime 小时 ∈ [0, 4]：视为凌晨入睡，`date = bedtime.date() - 1 day`
- 否则：`date = bedtime.date()`
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls, datetime, time as time_cls, timedelta
from typing import Optional


STATUS_NORMAL = "normal"
STATUS_WARNING = "warning"
STATUS_ABNORMAL = "abnormal"
STATUS_SEVERE = "severe"
STATUS_MISSED = "missed"


@dataclass
class ScoreResult:
    date: date_cls
    duration_minutes: int
    quality_score: int
    status: str
    is_weekend_night: bool


def _belongs_to_date(bedtime: datetime) -> date_cls:
    """跨天归属：凌晨 00:00-04:59 入睡算前一晚。"""
    if 0 <= bedtime.hour < 5:
        return (bedtime - timedelta(days=1)).date()
    return bedtime.date()


def _is_weekend_night(belong_date: date_cls) -> bool:
    """belong_date 是周五或周六 → 属于"周末晚"，放宽入睡阈值。

    belong_date.weekday(): Mon=0 ... Fri=4, Sat=5, Sun=6
    """
    return belong_date.weekday() in (4, 5)


def _compute_duration_score(duration_minutes: int) -> int:
    if duration_minutes <= 0:
        return 0
    if 420 <= duration_minutes <= 540:  # 7-9h
        return 50
    if 360 <= duration_minutes < 420 or 540 < duration_minutes <= 600:  # 6-7h / 9-10h
        return 35
    if 300 <= duration_minutes < 360:  # 5-6h
        return 20
    return 10  # <5h（但有打卡），给基础分


def _compute_bedtime_score(bedtime: datetime, belong_date: date_cls) -> int:
    """入睡时间分 30 分；健康线工作日 23:30、周末 00:00。"""
    weekend = _is_weekend_night(belong_date)
    # 把 bedtime 转换为"相对 belong_date 23:00 的分钟偏移"
    base = datetime.combine(belong_date, time_cls(23, 0), tzinfo=bedtime.tzinfo)
    offset_min = int((bedtime - base).total_seconds() // 60)
    # 健康线 offset = 30min（工作日）或 60min（周末）
    healthy_threshold = 60 if weekend else 30
    if offset_min <= healthy_threshold:
        return 30
    if offset_min <= healthy_threshold + 30:
        return 20
    if offset_min <= healthy_threshold + 60:
        return 10
    return 0


def _compute_subjective_score(subjective: int) -> int:
    # 1→4 / 2→8 / 3→12 / 4→16 / 5→20
    s = max(1, min(5, int(subjective)))
    return s * 4


def _status_from_quality(q: int) -> str:
    if q >= 85:
        return STATUS_NORMAL
    if q >= 70:
        return STATUS_WARNING
    if q >= 50:
        return STATUS_ABNORMAL
    return STATUS_SEVERE


def compute_score(
    bedtime: datetime,
    wake_time: datetime,
    subjective: int = 3,
) -> ScoreResult:
    """核心入口：返回评分结果。

    参数：
        bedtime: 入睡时间（aware 或 naive；两者需一致，内部只做差值计算）
        wake_time: 起床时间（必须晚于 bedtime）
        subjective: 主观评分 1-5

    异常：
        ValueError — wake_time <= bedtime 时抛出
    """
    if wake_time <= bedtime:
        raise ValueError("wake_time 必须晚于 bedtime")

    duration_minutes = int((wake_time - bedtime).total_seconds() // 60)
    belong_date = _belongs_to_date(bedtime)

    ds = _compute_duration_score(duration_minutes)
    bs = _compute_bedtime_score(bedtime, belong_date)
    ss = _compute_subjective_score(subjective)

    quality = ds + bs + ss
    status = _status_from_quality(quality)

    return ScoreResult(
        date=belong_date,
        duration_minutes=duration_minutes,
        quality_score=quality,
        status=status,
        is_weekend_night=_is_weekend_night(belong_date),
    )


def make_missed_stub(for_date: date_cls) -> dict:
    """为给定日期生成一条"未打卡"占位数据（dict 形式，便于模型 bulk_create）。"""
    return {
        "date": for_date,
        "bedtime": None,
        "wake_time": None,
        "duration_minutes": 0,
        "subjective_score": 0,
        "quality_score": 0,
        "status": STATUS_MISSED,
    }
