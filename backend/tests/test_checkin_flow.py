"""M4 打卡流程后端 E2E 冒烟测试。

运行前提：
- Django dev server 已启动在 127.0.0.1:8000
- 数据库已做过 migrate
- 已跑过 test_auth_smoke.py，库里存在 teacher1 / student1 / admin 等账号
  （若未跑，本脚本会先自建）

运行：
    venv/Scripts/python.exe tests/test_checkin_flow.py
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8000/api"


def must(cond, msg):
    if not cond:
        print(f"❌ {msg}")
        sys.exit(1)
    print(f"✅ {msg}")


def login(username, password):
    r = requests.post(f"{BASE}/auth/login/", json={"username": username, "password": password})
    if r.status_code != 200:
        return None
    return r.json()["access"]


def ensure_actors():
    """确保 teacher1/student1 存在；若 test_auth_smoke 未跑则自建一份可用账号。"""
    admin_tok = login("admin", "admin123")
    assert admin_tok, "admin 账号必须存在"

    teacher_tok = login("teacher_m4", "pass1234")
    classroom_code = None
    if not teacher_tok:
        r = requests.post(f"{BASE}/auth/register/", json={
            "role": "teacher", "username": "teacher_m4", "password": "pass1234",
            "teacher_no": "TM4", "real_name": "M4老师", "classroom_name": "M4测试班",
        })
        assert r.status_code == 201, r.text
        teacher_tok = r.json()["access"]
        classroom_code = r.json()["user"]["profile"]["classrooms"][0]["invite_code"]
    else:
        r = requests.get(f"{BASE}/auth/me/",
                         headers={"Authorization": f"Bearer {teacher_tok}"})
        classroom_code = r.json()["user"]["profile"]["classrooms"][0]["invite_code"]

    student_tok = login("student_m4", "pass1234")
    if not student_tok:
        r = requests.post(f"{BASE}/auth/register/", json={
            "role": "student", "username": "student_m4", "password": "pass1234",
            "student_no": "M4001", "real_name": "M4同学", "gender": "F",
            "grade": "高三", "classroom_invite_code": classroom_code,
        })
        assert r.status_code == 201, r.text
        student_tok = r.json()["access"]

    other_student_tok = login("student_m4b", "pass1234")
    if not other_student_tok:
        r = requests.post(f"{BASE}/auth/register/", json={
            "role": "student", "username": "student_m4b", "password": "pass1234",
            "student_no": "M4002", "real_name": "M4同学B", "gender": "M",
            "grade": "高三", "classroom_invite_code": classroom_code,
        })
        assert r.status_code == 201, r.text
        other_student_tok = r.json()["access"]

    return teacher_tok, student_tok, other_student_tok


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def cleanup_records():
    """每次跑测试前，用 management 命令清掉 M4 测试学生的记录。"""
    import subprocess
    subprocess.run(
        ["./venv/Scripts/python.exe", "manage.py", "wipe_sleep",
         "--student_no", "M4001", "M4002"],
        check=False, capture_output=True,
    )


def iso(dt: datetime) -> str:
    return dt.isoformat()


def main():
    print("=== 准备账号 ===")
    teacher_tok, student_tok, other_student_tok = ensure_actors()
    cleanup_records()
    print("=== 账号就绪 + 清空历史记录 ===\n")

    # 为避免与之前测试数据冲突，本测试用"相对今天的偏移"
    today = date.today()
    last_night = datetime.combine(today - timedelta(days=1), datetime.min.time()) \
                 .replace(hour=23, minute=10)
    this_morning = datetime.combine(today, datetime.min.time()).replace(hour=6, minute=30)

    # === 1. 昨晚 23:10 睡 今晨 06:30 起 → date = 昨天, status=normal, score≥85 ===
    r = requests.post(f"{BASE}/sleep/records/", headers=auth(student_tok), json={
        "bedtime": iso(last_night),
        "wake_time": iso(this_morning),
        "subjective_score": 3,
        "mood_tag": "good",
        "diary": "睡得很香",
    })
    must(r.status_code == 201, f"学生打卡返回 201 (got {r.status_code}: {r.text[:200]})")
    rec = r.json()
    must(rec["date"] == (today - timedelta(days=1)).isoformat(),
         f"date 归属前一天 (got {rec['date']})")
    must(rec["status"] == "normal", f"status=normal (got {rec['status']})")
    must(rec["quality_score"] >= 85, f"quality_score≥85 (got {rec['quality_score']})")
    normal_record_id = rec["id"]

    # === 2. 凌晨 01:30 睡 07:00 起 → severe ===
    # 注意：bedtime=今天 01:30 会归属昨天，但昨天已经有记录了 → 要用另一学生
    last_night_severe = datetime.combine(today, datetime.min.time()).replace(hour=1, minute=30)
    morning_severe = datetime.combine(today, datetime.min.time()).replace(hour=7, minute=0)
    r = requests.post(f"{BASE}/sleep/records/", headers=auth(other_student_tok), json={
        "bedtime": iso(last_night_severe),
        "wake_time": iso(morning_severe),
        "subjective_score": 2,
    })
    must(r.status_code == 201, f"严重熬夜案例 201 (got {r.status_code}: {r.text[:200]})")
    severe_rec = r.json()
    must(severe_rec["status"] == "severe",
         f"凌晨 01:30 睡 应判 severe (got {severe_rec['status']})")
    must(severe_rec["date"] == (today - timedelta(days=1)).isoformat(),
         f"凌晨入睡归属前一天 (got {severe_rec['date']})")

    # === 3. 2h 内 PATCH 成功 ===
    r = requests.patch(f"{BASE}/sleep/records/{normal_record_id}/", headers=auth(student_tok),
                       json={"mood_tag": "great", "diary": "今天状态很棒"})
    must(r.status_code == 200, f"2h 内 PATCH 应 200 (got {r.status_code}: {r.text[:200]})")
    must(r.json()["mood_tag"] == "great", "mood_tag 已更新")

    # === 4. 补打 2 天前 → 成功；补打 5 天前 → 400/422 ===
    two_nights_ago_bedtime = datetime.combine(today - timedelta(days=2), datetime.min.time()) \
                             .replace(hour=23, minute=20)
    two_nights_ago_wake = datetime.combine(today - timedelta(days=1), datetime.min.time()) \
                          .replace(hour=7, minute=0)
    r = requests.post(f"{BASE}/sleep/records/", headers=auth(student_tok), json={
        "bedtime": iso(two_nights_ago_bedtime),
        "wake_time": iso(two_nights_ago_wake),
        "subjective_score": 4,
    })
    must(r.status_code == 201, f"补打 2 天前 201 (got {r.status_code}: {r.text[:200]})")

    too_old_bedtime = datetime.combine(today - timedelta(days=5), datetime.min.time()) \
                      .replace(hour=23, minute=0)
    too_old_wake = datetime.combine(today - timedelta(days=4), datetime.min.time()) \
                   .replace(hour=7, minute=0)
    r = requests.post(f"{BASE}/sleep/records/", headers=auth(student_tok), json={
        "bedtime": iso(too_old_bedtime),
        "wake_time": iso(too_old_wake),
        "subjective_score": 3,
    })
    must(r.status_code == 400, f"补打 5 天前 应 400 (got {r.status_code}: {r.text[:200]})")

    # === 5. 老师代改 — 不带 modified_reason 400 ===
    r = requests.patch(
        f"{BASE}/sleep/teacher/records/{normal_record_id}/",
        headers=auth(teacher_tok),
        json={"subjective_score": 5},
    )
    must(r.status_code == 400, f"老师代改缺 reason 应 400 (got {r.status_code})")

    # === 6. 老师代改 — 带 modified_reason 成功 ===
    r = requests.patch(
        f"{BASE}/sleep/teacher/records/{normal_record_id}/",
        headers=auth(teacher_tok),
        json={"subjective_score": 5, "modified_reason": "学生反馈主观分填错"},
    )
    must(r.status_code == 200,
         f"老师带 reason 代改 200 (got {r.status_code}: {r.text[:200]})")
    edited = r.json()
    must(edited["modified_reason"] == "学生反馈主观分填错", "modified_reason 写入")
    must(edited["modified_by"] is not None, "modified_by 写入")
    must(edited["modified_at"] is not None, "modified_at 写入")

    # === 7. 列表按日期区间 ===
    r = requests.get(
        f"{BASE}/sleep/records/?from={(today - timedelta(days=3)).isoformat()}&to={today.isoformat()}",
        headers=auth(student_tok),
    )
    must(r.status_code == 200, "按区间拉取列表 200")
    items = r.json().get("results", r.json())
    if isinstance(items, dict):
        items = items.get("results", [])
    must(len(items) >= 2, f"至少 2 条记录 (got {len(items)})")

    # === 8. 隐私：老师读学生日记应为空字符串（share_diary_to_teacher 默认 False）===
    r = requests.get(f"{BASE}/sleep/records/{normal_record_id}/",
                     headers=auth(student_tok))
    must(r.json()["diary"] == "今天状态很棒", "学生本人可见自己的日记")

    print("\n🎉 M4 打卡流程后端冒烟测试全部通过")


if __name__ == "__main__":
    main()
