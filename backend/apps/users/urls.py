from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from . import teacher_views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", views.me, name="me"),
    path("profile/preferences/", views.profile_preferences, name="profile-preferences"),
    path("generate-parent-code/", views.generate_parent_code, name="generate_parent_code"),
    # 管理员端
    path("admin/users/", views.admin_users, name="admin-users"),
    path("admin/users/<int:pk>/", views.admin_user_detail, name="admin-user-detail"),
    path("admin/global-stats/", views.admin_global_stats, name="admin-global-stats"),
    path("admin/seed-demo/", views.admin_seed_demo, name="admin-seed-demo"),
    # 家长端
    path("parent/child/overview/", views.parent_child_overview, name="parent-child-overview"),
    # 老师端
    path("teacher/classroom/", teacher_views.create_classroom, name="teacher-create-classroom"),
    path("teacher/class-overview/", teacher_views.class_overview, name="teacher-class-overview"),
    path("teacher/students/", teacher_views.student_list, name="teacher-student-list"),
    path("teacher/students/<int:student_id>/trend/", teacher_views.student_trend, name="teacher-student-trend"),
]
