"""M4.1 评分引擎单元测试 — 纯函数，不依赖 Django。

运行：venv/Scripts/python.exe -m pytest tests/test_score_engine.py -v
或：venv/Scripts/python.exe tests/test_score_engine.py
"""
from __future__ import annotations

import sys
from datetime import datetime

import pytest

# 允许从 backend/ 目录直接运行
sys.path.insert(0, ".")

from utils.score_engine import (  # noqa: E402
    STATUS_ABNORMAL,
    STATUS_NORMAL,
    STATUS_SEVERE,
    STATUS_WARNING,
    compute_score,
)


def dt(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute)


class TestCrossDayBelonging:
    def test_bedtime_2am_belongs_previous_day(self):
        """2026-04-20 02:10 入睡、06:00 起床 → date 应为 04-19"""
        r = compute_score(dt(2026, 4, 20, 2, 10), dt(2026, 4, 20, 6, 0))
        assert r.date.isoformat() == "2026-04-19"

    def test_bedtime_2310_belongs_same_day(self):
        """2026-04-20 23:10 入睡 → date = 04-20"""
        r = compute_score(dt(2026, 4, 20, 23, 10), dt(2026, 4, 21, 6, 30))
        assert r.date.isoformat() == "2026-04-20"

    def test_bedtime_5am_belongs_same_day(self):
        """5:00 已不算凌晨跨天 → date = 当天"""
        r = compute_score(dt(2026, 4, 20, 5, 0), dt(2026, 4, 20, 12, 0))
        assert r.date.isoformat() == "2026-04-20"


class TestWeekdayBoundary:
    """工作日入睡阈值 23:30 的边界。"""

    def test_exactly_2330_is_normal(self):
        """4-20 周一 23:30 入睡 + 8h → 480min → 满分 100 → normal"""
        r = compute_score(dt(2026, 4, 20, 23, 30), dt(2026, 4, 21, 7, 30), subjective=3)
        assert r.duration_minutes == 480
        assert r.quality_score == 50 + 30 + 12  # duration + bedtime + subjective
        assert r.status == STATUS_NORMAL

    def test_2331_drops_to_warning(self):
        """23:31 超 1 分钟 → bedtime 分降到 20 → 总分 82 → warning"""
        r = compute_score(dt(2026, 4, 20, 23, 31), dt(2026, 4, 21, 7, 31), subjective=3)
        assert r.quality_score == 50 + 20 + 12
        assert r.status == STATUS_WARNING


class TestWeekendRelaxation:
    """周末放宽：周五 / 周六晚健康线 = 00:00。belong_date.weekday() ∈ {4, 5}。"""

    def test_friday_night_2345_still_normal(self):
        """2026-04-24 是周五。23:45 入睡，belong_date=04-24 (周五，weekday=4) → 放宽阈值"""
        r = compute_score(dt(2026, 4, 24, 23, 45), dt(2026, 4, 25, 7, 45), subjective=3)
        assert r.date.isoformat() == "2026-04-24"
        assert r.status == STATUS_NORMAL

    def test_saturday_night_midnight_still_normal(self):
        """周六晚 00:00 入睡（凌晨归 04-25 周六 → 放宽阈值命中 → bedtime 满分）"""
        r = compute_score(dt(2026, 4, 26, 0, 0), dt(2026, 4, 26, 8, 0), subjective=3)
        assert r.date.isoformat() == "2026-04-25"
        assert r.date.weekday() == 5  # 周六
        # 周六晚 00:00 = 健康线 → bedtime 满 30 分
        assert r.quality_score >= 85
        assert r.status == STATUS_NORMAL

    def test_weekday_midnight_drops(self):
        """同样 00:00 入睡，工作日（belong_date 周四）→ 过健康线 30min 档 → warning"""
        # 4-23 周四晚 00:00 入睡 = 4-24 周五 00:00 → belong_date=周四(weekday=3)
        r = compute_score(dt(2026, 4, 24, 0, 0), dt(2026, 4, 24, 8, 0), subjective=3)
        assert r.date.weekday() == 3  # 周四
        assert r.status == STATUS_WARNING


class TestSevereCase:
    def test_0130_wake_0700_severe(self):
        """典型熬夜：01:30 入睡（归前一晚）、07:00 起床 → 5.5h → severe"""
        r = compute_score(dt(2026, 4, 21, 1, 30), dt(2026, 4, 21, 7, 0), subjective=3)
        assert r.duration_minutes == 330
        assert r.status == STATUS_SEVERE


class TestDurationEdgeCases:
    def test_wake_before_bedtime_raises(self):
        with pytest.raises(ValueError):
            compute_score(dt(2026, 4, 20, 8, 0), dt(2026, 4, 20, 7, 0))

    def test_very_short_sleep(self):
        """2h 睡眠 → 最低档 10 分 + bedtime 满 30 + subjective 12 = 52 → abnormal"""
        r = compute_score(dt(2026, 4, 20, 23, 0), dt(2026, 4, 21, 1, 0), subjective=3)
        assert r.duration_minutes == 120
        assert r.status == STATUS_ABNORMAL


class TestSubjectiveInfluence:
    def test_subjective_1_lowers_score(self):
        r1 = compute_score(dt(2026, 4, 20, 23, 0), dt(2026, 4, 21, 7, 0), subjective=5)
        r2 = compute_score(dt(2026, 4, 20, 23, 0), dt(2026, 4, 21, 7, 0), subjective=1)
        assert r1.quality_score - r2.quality_score == 16  # 20-4


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
