"""M3 冒烟测试：完整走一遍注册→登录→me→邀请码流程。
单独运行：venv/Scripts/python.exe tests/test_auth_smoke.py
前提：Django server 已在 :8000 启动。
"""
import sys
import time
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


def main():
    s = requests.Session()
    suffix = str(int(time.time() * 1000))
    teacher_username = f"teacher_{suffix}"
    teacher2_username = f"teacher2_{suffix}"
    student_username = f"student_{suffix}"
    student2_username = f"student2_{suffix}"
    parent_username = f"parent_{suffix}"
    teacher_no = f"T{suffix[-6:]}"
    teacher2_no = f"T2{suffix[-5:]}"
    student_no = f"S{suffix[-6:]}"

    # 1. admin 登录
    r = s.post(f"{BASE}/auth/login/", json={"username": "admin", "password": "admin123"})
    must(r.status_code == 200, "admin 登录返回 200")
    admin_token = r.json()["access"]

    # 2. 老师注册 + 建班
    r = s.post(f"{BASE}/auth/register/", json={
        "role": "teacher", "username": teacher_username, "password": "pass1234",
        "teacher_no": teacher_no, "real_name": "王老师", "classroom_name": "高三(5)班"
    })
    must(r.status_code == 201, f"老师注册返回 201 (got {r.status_code}: {r.text[:200]})")
    teacher_data = r.json()
    classrooms = teacher_data["user"]["profile"]["classrooms"]
    must(len(classrooms) == 1, f"老师档案包含 1 个班级 (got {classrooms})")
    invite_code = classrooms[0]["invite_code"]
    print(f"   → 班级邀请码：{invite_code}")

    # 3. 学生用邀请码注册
    r = s.post(f"{BASE}/auth/register/", json={
        "role": "student", "username": student_username, "password": "pass1234",
        "student_no": student_no, "real_name": "张三", "gender": "M",
        "grade": "高三", "classroom_invite_code": invite_code
    })
    must(r.status_code == 201, f"学生注册返回 201 (got {r.status_code}: {r.text[:200]})")
    student_data = r.json()
    must(student_data["user"]["profile"]["classroom"]["name"] == "高三(5)班",
         "学生已加入高三(5)班")
    student_token = student_data["access"]

    # 4. 学生生成家长邀请码
    r = s.post(f"{BASE}/auth/generate-parent-code/",
               headers={"Authorization": f"Bearer {student_token}"})
    must(r.status_code == 200, f"生成家长邀请码返回 200 (got {r.status_code})")
    parent_code = r.json()["code"]
    print(f"   → 家长邀请码：{parent_code}")

    # 5. 家长注册
    r = s.post(f"{BASE}/auth/register/", json={
        "role": "parent", "username": parent_username, "password": "pass1234",
        "real_name": "张父", "parent_invite_code": parent_code
    })
    must(r.status_code == 201, f"家长注册返回 201 (got {r.status_code}: {r.text[:200]})")
    parent_data = r.json()
    must(parent_data["user"]["profile"]["child"]["real_name"] == "张三",
         "家长已绑定学生张三")

    # 6. /me 测试（用老师 token）
    r = s.get(f"{BASE}/auth/me/",
              headers={"Authorization": f"Bearer {teacher_data['access']}"})
    must(r.status_code == 200 and r.json()["user"]["username"] == teacher_username,
         "/me 返回当前老师用户")

    # 7. 重复注册同学号应失败
    r = s.post(f"{BASE}/auth/register/", json={
        "role": "student", "username": student2_username, "password": "pass1234",
        "student_no": student_no, "real_name": "李四",
        "classroom_invite_code": invite_code
    })
    must(r.status_code == 400, f"重复学号应返回 400 (got {r.status_code})")

    # 8. 无邀请码的老师可以不建班
    r = s.post(f"{BASE}/auth/register/", json={
        "role": "teacher", "username": teacher2_username, "password": "pass1234",
        "teacher_no": teacher2_no, "real_name": "李老师"
    })
    must(r.status_code == 201, "老师注册（不建班）返回 201")

    # 9. 错误密码登录
    r = s.post(f"{BASE}/auth/login/", json={"username": student_username, "password": "wrong"})
    must(r.status_code == 401, "错误密码返回 401")

    print("\n🎉 M3a 后端认证冒烟测试全部通过")


if __name__ == "__main__":
    main()
