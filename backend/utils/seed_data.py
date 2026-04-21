"""M8 演示种子数据生成器。

生成：
- 1 个管理员（admin/admin123）
- 1 个老师（teacher01/teacher123）+ 1 个班级
- 30 个学生（student01-30/student123）
- 30 个家长（parent01-30/parent123）
- 3 个典型案例：
  · student01 = 严重熬夜生（长期 severe）
  · student02 = 完美作息生（长期 normal）
  · student03 = 周期性异常生（normal-severe 交替）
- 其余 27 个学生：混合分布，以 normal/warning 为主
- 365 天历史睡眠记录

调用方式：
    python manage.py seed_demo_data
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone as dt_timezone

import django
from django.contrib.auth import get_user_model

User = get_user_model()

# 固定随机种子保证可重现
random.seed(42)

# 演示起始日期（生成到昨天，共 365 个历史归属日）
TODAY = date.today()
START_DATE = TODAY - timedelta(days=365)


def _dt(d: date, hour: int, minute: int = 0) -> datetime:
    """构造 UTC+8 naive datetime（Django 存 UTC，需转换）。"""
    from django.utils import timezone
    import pytz
    tz_cn = pytz.timezone("Asia/Shanghai")
    naive = datetime(d.year, d.month, d.day, hour, minute)
    return tz_cn.localize(naive)


def _make_record_params(case: str, d: date) -> dict | None:
    """根据案例类型生成该日的打卡参数，返回 None 表示跳过（missed）。"""
    weekday = d.weekday()
    is_weekend = weekday >= 5

    if case == "night_owl":
        # 严重熬夜生：入睡 01:00-04:00，起床 07:00-09:00，偶尔 missed
        if random.random() < 0.1:
            return None
        sleep_hour = random.randint(1, 4)
        sleep_min = random.randint(0, 59)
        wake_hour = random.randint(7, 9)
        wake_min = random.randint(0, 59)

    elif case == "perfect":
        # 完美作息生：入睡 22:30-23:00，起床 06:30-07:00，极少 missed
        if random.random() < 0.02:
            return None
        sleep_hour = 22
        sleep_min = random.randint(30, 59)
        wake_hour = random.choice([6, 7])
        wake_min = random.randint(0 if wake_hour == 7 else 30, 59 if wake_hour == 6 else 0)

    elif case == "periodic":
        # 周期性异常：以 14 天为周期，7 天正常 + 7 天熬夜
        day_in_cycle = (d - START_DATE).days % 14
        if random.random() < 0.08:
            return None
        if day_in_cycle < 7:
            sleep_hour = 23
            sleep_min = random.randint(0, 30)
            wake_hour = 7
            wake_min = random.randint(0, 30)
        else:
            sleep_hour = random.randint(0, 2)
            sleep_min = random.randint(0, 59)
            wake_hour = random.randint(6, 8)
            wake_min = random.randint(0, 59)

    else:
        # 普通学生：混合
        if random.random() < 0.08:
            return None
        weights = {"early": 0.3, "normal": 0.4, "late": 0.2, "very_late": 0.1}
        pattern = random.choices(list(weights.keys()), list(weights.values()))[0]
        if pattern == "early":
            sleep_hour = 22
            sleep_min = random.randint(30, 59)
        elif pattern == "normal":
            sleep_hour = 23
            sleep_min = random.randint(0, 29)
        elif pattern == "late":
            sleep_hour = 23
            sleep_min = random.randint(30, 59)
        else:
            sleep_hour = random.randint(0, 1)
            sleep_min = random.randint(0, 59)
        wake_hour = random.randint(6, 8)
        wake_min = random.randint(0, 59)

        if is_weekend:
            sleep_hour = min(sleep_hour + 1, 3)

    return {
        "sleep_hour": sleep_hour,
        "sleep_min": sleep_min,
        "wake_hour": wake_hour,
        "wake_min": wake_min,
    }


def run(stdout=None) -> None:
    from django.db import transaction
    from apps.users.models import ClassRoom, StudentProfile, TeacherProfile, ParentProfile
    from apps.sleep.models import SleepRecord
    from utils.score_engine import compute_score

    def log(msg):
        if stdout:
            stdout.write(msg + "\n")
        else:
            print(msg)

    with transaction.atomic():
        # ── 管理员 ──
        admin, created = User.objects.get_or_create(username="admin", defaults={
            "role": User.Role.ADMIN,
            "email": "admin@sleep-system.example",
            "is_staff": True,
            "is_superuser": True,
        })
        if created or not admin.check_password("admin123"):
            admin.set_password("admin123")
            admin.save()
        log(f"{'创建' if created else '已有'} 管理员: admin / admin123")

        # ── 老师 ──
        teacher_user, created = User.objects.get_or_create(username="teacher01", defaults={
            "role": User.Role.TEACHER,
            "email": "teacher01@sleep-system.example",
        })
        if created or not teacher_user.check_password("teacher123"):
            teacher_user.set_password("teacher123")
            teacher_user.save()
        teacher_profile, _ = TeacherProfile.objects.get_or_create(
            user=teacher_user,
            defaults={"teacher_no": "T0001", "real_name": "张老师"},
        )

        classroom, _ = ClassRoom.objects.get_or_create(
            name="高三(1)班",
            defaults={"teacher": teacher_user},
        )
        log(f"班级: {classroom.name}  邀请码: {classroom.invite_code}")

        # ── 科普文章（预置 10 篇）──
        _seed_articles(admin, log)

        # ── 学生 + 家长 + 睡眠记录 ──
        cases = {
            "student01": "night_owl",
            "student02": "perfect",
            "student03": "periodic",
        }
        real_names = [
            "李明", "王芳", "张伟", "刘洋", "陈静",
            "赵磊", "孙敏", "周强", "吴丽", "郑涛",
            "林晓", "何超", "徐慧", "马杰", "朱燕",
            "胡峰", "高雪", "曹阳", "彭思", "梁博",
            "谢凤", "段勇", "宋梅", "蒋昊", "韩玉",
            "杨宁", "冯华", "程军", "秦月", "许建",
        ]

        for i in range(1, 31):
            username = f"student{i:02d}"
            real_name = real_names[i - 1]
            case = cases.get(username, "normal")

            # 创建学生用户
            stu_user, created = User.objects.get_or_create(username=username, defaults={
                "role": User.Role.STUDENT,
                "email": f"{username}@sleep-system.example",
            })
            if created or not stu_user.check_password("student123"):
                stu_user.set_password("student123")
                stu_user.save()

            stu_profile, _ = StudentProfile.objects.get_or_create(
                user=stu_user,
                defaults={
                    "classroom": classroom,
                    "student_no": f"DEMO2024{i:03d}",
                    "real_name": real_name,
                    "gender": random.choice(["M", "F"]),
                    "grade": "高三",
                    "target_sleep_hours": 8,
                },
            )
            if stu_profile.classroom is None:
                stu_profile.classroom = classroom
                stu_profile.save()

            # 创建家长
            parent_username = f"parent{i:02d}"
            parent_user, created = User.objects.get_or_create(username=parent_username, defaults={
                "role": User.Role.PARENT,
                "email": f"{parent_username}@sleep-system.example",
            })
            if created or not parent_user.check_password("parent123"):
                parent_user.set_password("parent123")
                parent_user.save()
            ParentProfile.objects.get_or_create(
                user=parent_user,
                defaults={"real_name": f"{real_name}家长", "child": stu_profile},
            )

            # 生成 365 天记录
            _generate_records(stu_profile, case, compute_score, log if i <= 3 else None, real_name)

        log("种子数据生成完毕")


def _generate_records(student, case, compute_score, log_fn, name):
    from apps.sleep.models import SleepRecord
    import pytz
    tz_cn = pytz.timezone("Asia/Shanghai")

    created_count = 0
    for day_offset in range(365):
        d = START_DATE + timedelta(days=day_offset)
        # 今天晚上的睡眠尚未发生，演示数据只生成到昨天
        if d >= TODAY:
            break

        # 已有记录则跳过
        if SleepRecord.objects.filter(student=student, date=d).exists():
            continue

        params = _make_record_params(case, d)
        if params is None:
            # missed 打桩
            SleepRecord.objects.create(
                student=student,
                date=d,
                status=SleepRecord.Status.MISSED,
                quality_score=0,
                duration_minutes=0,
            )
            continue

        # d 是"那晚所属日期"；凌晨入睡的真实日期是 d+1。
        sh, sm = params["sleep_hour"], params["sleep_min"]
        wh, wm = params["wake_hour"], params["wake_min"]

        if sh < 5:
            bedtime_date = d + timedelta(days=1)
            wake_date = d + timedelta(days=1)
        else:
            bedtime_date = d
            wake_date = d + timedelta(days=1)

        bedtime = tz_cn.localize(datetime(bedtime_date.year, bedtime_date.month, bedtime_date.day, sh, sm))
        wake_time = tz_cn.localize(datetime(wake_date.year, wake_date.month, wake_date.day, wh, wm))
        if wake_time <= bedtime:
            wake_time = bedtime + timedelta(hours=7)

        try:
            result = compute_score(bedtime, wake_time, random.randint(2, 5))
        except Exception:
            continue

        # 加入一些随机日记（约 20% 概率）
        diary = ""
        if random.random() < 0.2:
            diary = random.choice([
                "今天睡得不错，精神很好！",
                "昨晚有点兴奋睡不着…",
                "考试压力大，失眠了",
                "早睡早起，状态满分",
                "熬夜刷题，明天要早点休息",
                "周末睡到自然醒，舒服",
                "梦到了考试，好累",
            ])

        SleepRecord.objects.create(
            student=student,
            date=result.date,
            bedtime=bedtime,
            wake_time=wake_time,
            duration_minutes=result.duration_minutes,
            subjective_score=random.randint(2, 5),
            quality_score=result.quality_score,
            status=result.status,
            mood_tag=random.choice(["great", "good", "normal", "tired", "bad", ""]),
            diary=diary,
        )
        created_count += 1

    if log_fn:
        log_fn(f"  [{name}({case})] 生成 {created_count} 条记录")


def _seed_articles(admin_user, log):
    from apps.articles.models import Article

    articles = [
        ("青少年需要多少睡眠？", '中学生每晚应保证 8-10 小时睡眠。研究表明，睡眠不足会影响记忆巩固、情绪调节和免疫功能。大脑在深度睡眠期间完成白天学习内容的"归档"，因此保证充足睡眠对学习效果至关重要。建议同学们每晚 22:30 前上床，尽量在固定时间入睡。'),
        ("如何快速入睡？5个科学方法", "1. 保持卧室阴暗凉爽（18-20℃最佳）\n2. 睡前 1 小时远离手机和蓝光\n3. 尝试 4-7-8 呼吸法（吸气4秒，屏息7秒，呼气8秒）\n4. 睡前温水泡脚，促进血液循环\n5. 建立固定的睡前仪式（阅读、听轻音乐）"),
        ("熬夜的危害你知多少", "长期熬夜会导致：免疫力下降、记忆力减退、情绪不稳定、肥胖风险增加、青春痘加重。研究发现，连续一周每晚睡眠少于6小时，认知能力下降相当于连续24小时不睡觉。"),
        ("周末补觉有用吗？", '很多同学平时睡不够，指望周末补觉。科学研究表明，"补觉"能缓解部分疲劳，但无法完全恢复。更重要的是，周末过度睡懒觉会打乱生物钟，导致周一"社交时差"更严重。建议周末比平时晚起不超过 1 小时。'),
        ("睡眠与学习成绩的关系", '斯坦福大学研究发现，每晚睡够8小时的学生，考试成绩比睡眠不足的学生平均高出 20-30 分（百分制）。睡眠中大脑会将短期记忆转化为长期记忆，所以"睡前背单词"是有科学依据的。'),
        ("手机蓝光与睡眠的关系", "手机屏幕发出的蓝光会抑制褪黑素（睡眠激素）的分泌。实验发现，睡前看手机 1 小时会使入睡时间延迟约 30 分钟，深度睡眠减少 23%。建议睡前开启手机夜间模式，或使用防蓝光眼镜。"),
        ("什么是睡眠周期？", "人的睡眠由多个 90 分钟的周期组成，每个周期包含浅睡眠、深睡眠和 REM（快速眼动）睡眠。理想情况下，一晚应完成 4-6 个完整周期。按照90分钟倍数规划起床时间（如睡着后90/180/270/360分钟），会感觉更清醒。"),
        ("考前如何调整睡眠？", "考前熬夜是最坏的策略！建议：考前一周开始固定作息；考前一晚保证正常睡眠，不要过度复习；考试当天早餐后可小睡 20 分钟（权威能量睡眠法）；避免考前喝过多咖啡因饮料。"),
        ("运动与睡眠的关系", "规律运动能显著改善睡眠质量。研究表明，每天 30 分钟有氧运动可使入睡时间缩短 50%，深度睡眠增加 15%。但注意：睡前 3 小时内剧烈运动会使体温和肾上腺素升高，反而难以入睡。"),
        ("压力大睡不着怎么办？", '1. 写「烦恼清单」：睡前将担忧事项写下来并"打包"，告诉自己明天再处理\n2. 渐进式肌肉放松：从脚趾到头顶逐步放松各肌肉群\n3. 正念冥想：专注于呼吸，观察念头不随之起伏\n4. 如果躺下 20 分钟仍无睡意，起床做轻松活动，有睡意再回床\n5. 长期高压请寻求学校心理咨询'),
    ]

    for title, content in articles:
        from apps.articles.models import Article
        Article.objects.get_or_create(title=title, defaults={
            "content": content,
            "author": admin_user,
        })
    log(f"科普文章：确保 {len(articles)} 篇已存在")
