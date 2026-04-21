from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import ClassRoom, ParentProfile, StudentProfile, TeacherProfile

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "role", "role_display", "email", "phone",
            "avatar", "email_alert_enabled", "is_active", "profile",
        )

    def get_profile(self, obj: User):
        if obj.role == User.Role.STUDENT and hasattr(obj, "student_profile"):
            sp = obj.student_profile
            return {
                "student_no": sp.student_no,
                "real_name": sp.real_name,
                "gender": sp.gender,
                "grade": sp.grade,
                "target_sleep_hours": str(sp.target_sleep_hours),
                "target_bedtime": sp.target_bedtime.strftime("%H:%M"),
                "risk_level": sp.risk_level,
                "share_diary_to_teacher": sp.share_diary_to_teacher,
                "classroom": (
                    {"id": sp.classroom.id, "name": sp.classroom.name, "invite_code": sp.classroom.invite_code}
                    if sp.classroom else None
                ),
            }
        if obj.role == User.Role.TEACHER and hasattr(obj, "teacher_profile"):
            tp = obj.teacher_profile
            classrooms = [
                {"id": c.id, "name": c.name, "invite_code": c.invite_code}
                for c in ClassRoom.objects.filter(teacher=obj)
            ]
            return {
                "teacher_no": tp.teacher_no,
                "real_name": tp.real_name,
                "classrooms": classrooms,
            }
        if obj.role == User.Role.PARENT and hasattr(obj, "parent_profile"):
            pp = obj.parent_profile
            return {
                "real_name": pp.real_name,
                "child": (
                    {
                        "id": pp.child.id,
                        "student_no": pp.child.student_no,
                        "real_name": pp.child.real_name,
                        "gender": pp.child.gender,
                        "grade": pp.child.grade,
                        "target_sleep_hours": str(pp.child.target_sleep_hours),
                        "target_bedtime": pp.child.target_bedtime.strftime("%H:%M"),
                        "risk_level": pp.child.risk_level,
                        "classroom": pp.child.classroom.name if pp.child.classroom else None,
                        "classroom_name": pp.child.classroom.name if pp.child.classroom else None,
                    }
                    if pp.child else None
                ),
            }
        return None


class AdminUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, min_length=6)

    class Meta:
        model = User
        fields = (
            "username", "password", "role", "email", "phone",
            "email_alert_enabled", "is_active",
        )
        extra_kwargs = {
            "username": {"required": False},
            "role": {"required": False},
            "email": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
            "email_alert_enabled": {"required": False},
            "is_active": {"required": False},
        }

    def validate_username(self, value: str) -> str:
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate(self, attrs):
        if not self.instance:
            if not attrs.get("username"):
                raise serializers.ValidationError({"username": "用户名必填"})
            if not attrs.get("password"):
                raise serializers.ValidationError({"password": "初始密码必填"})
            attrs.setdefault("role", User.Role.STUDENT)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "")
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ---------- Register ----------
class _BaseRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=32)
    password = serializers.CharField(min_length=6, max_length=64, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value


class StudentRegisterSerializer(_BaseRegisterSerializer):
    student_no = serializers.CharField(max_length=32)
    real_name = serializers.CharField(max_length=32)
    gender = serializers.ChoiceField(choices=StudentProfile.Gender.choices, default=StudentProfile.Gender.OTHER)
    grade = serializers.CharField(required=False, allow_blank=True, max_length=16)
    classroom_invite_code = serializers.CharField(max_length=8)

    def validate_student_no(self, value: str) -> str:
        if StudentProfile.objects.filter(student_no=value).exists():
            raise serializers.ValidationError("该学号已被注册")
        return value

    def validate_classroom_invite_code(self, value: str) -> str:
        try:
            self._classroom = ClassRoom.objects.get(invite_code=value.upper())
        except ClassRoom.DoesNotExist:
            raise serializers.ValidationError("班级邀请码无效")
        return value

    @transaction.atomic
    def create(self, validated_data):
        classroom = getattr(self, "_classroom", None)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=User.Role.STUDENT,
            phone=validated_data.get("phone", ""),
        )
        StudentProfile.objects.create(
            user=user,
            classroom=classroom,
            student_no=validated_data["student_no"],
            real_name=validated_data["real_name"],
            gender=validated_data.get("gender", StudentProfile.Gender.OTHER),
            grade=validated_data.get("grade", ""),
        )
        return user


class TeacherRegisterSerializer(_BaseRegisterSerializer):
    teacher_no = serializers.CharField(max_length=32)
    real_name = serializers.CharField(max_length=32)
    classroom_name = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_teacher_no(self, value: str) -> str:
        if TeacherProfile.objects.filter(teacher_no=value).exists():
            raise serializers.ValidationError("该工号已被注册")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=User.Role.TEACHER,
            phone=validated_data.get("phone", ""),
        )
        TeacherProfile.objects.create(
            user=user,
            teacher_no=validated_data["teacher_no"],
            real_name=validated_data["real_name"],
        )
        cname = validated_data.get("classroom_name", "").strip()
        if cname:
            ClassRoom.objects.create(name=cname, teacher=user)
        return user


class ParentRegisterSerializer(_BaseRegisterSerializer):
    real_name = serializers.CharField(max_length=32)
    parent_invite_code = serializers.CharField(max_length=8)

    def validate_parent_invite_code(self, value: str) -> str:
        try:
            student = StudentProfile.objects.get(parent_invite_code=value.upper())
        except StudentProfile.DoesNotExist:
            raise serializers.ValidationError("邀请码无效")
        if not student.invite_is_valid():
            raise serializers.ValidationError("邀请码已过期")
        if hasattr(student, "parent_profile"):
            raise serializers.ValidationError("该学生已绑定家长")
        self._student = student
        return value

    @transaction.atomic
    def create(self, validated_data):
        student = self._student
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=User.Role.PARENT,
            phone=validated_data.get("phone", ""),
        )
        ParentProfile.objects.create(
            user=user,
            real_name=validated_data["real_name"],
            child=student,
        )
        # 清掉一次性邀请码
        student.parent_invite_code = ""
        student.invite_expires_at = None
        student.save(update_fields=["parent_invite_code", "invite_expires_at"])
        return user


class ParentInviteSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
