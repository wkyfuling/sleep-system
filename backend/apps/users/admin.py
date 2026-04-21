from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, ClassRoom, StudentProfile, TeacherProfile, ParentProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "role", "email", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        ("业务字段", {"fields": ("role", "phone", "avatar", "email_alert_enabled")}),
    )


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "invite_code", "created_at")
    search_fields = ("name", "invite_code")
    readonly_fields = ("invite_code", "created_at")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("real_name", "student_no", "classroom", "risk_level")
    list_filter = ("classroom", "risk_level", "gender")
    search_fields = ("real_name", "student_no", "user__username")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("real_name", "teacher_no")
    search_fields = ("real_name", "teacher_no")


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("real_name", "child")
    search_fields = ("real_name", "child__real_name")
