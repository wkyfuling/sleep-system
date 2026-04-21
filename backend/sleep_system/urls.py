from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from apps.ai import views as ai_views
from apps.notifications import views as notification_views
from apps.sleep import export_views, views as sleep_views
from apps.users import teacher_views, views as user_views


def healthz(_request):
    return JsonResponse({"status": "ok", "service": "sleep-system"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/healthz/", healthz, name="healthz"),
    path("api/auth/", include("apps.users.urls")),
    path("api/sleep/", include("apps.sleep.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/articles/", include("apps.articles.urls")),
    path("api/achievements/", include("apps.achievements.urls")),
    path("api/ai/", include("apps.ai.urls")),
    # 设计文档中的角色化入口别名，保留已有模块化入口以兼容前端。
    path("api/teacher/classroom/", teacher_views.create_classroom, name="teacher-classroom"),
    path("api/teacher/class/overview/", teacher_views.class_overview, name="teacher-class-overview-alias"),
    path("api/teacher/students/", teacher_views.student_list, name="teacher-students-alias"),
    path("api/teacher/students/<int:student_id>/trend/", teacher_views.student_trend, name="teacher-student-trend-alias"),
    path("api/teacher/records/<int:pk>/", sleep_views.teacher_edit_record, name="teacher-record-edit-alias"),
    path("api/teacher/alerts/", notification_views.alerts, name="teacher-alerts-alias"),
    path("api/teacher/notifications/", notification_views.broadcast, name="teacher-notifications-alias"),
    path("api/teacher/export/month_excel/", export_views.export_class_month, name="teacher-export-month-excel"),
    path("api/teacher/export/day_overview_excel/", export_views.export_day_overview, name="teacher-export-day-overview"),
    path("api/teacher/export/semester_pdf/", export_views.export_student_pdf, name="teacher-export-semester-pdf"),
    path("api/teacher/ai/class-diagnosis/", ai_views.class_diagnosis, name="teacher-ai-class-diagnosis"),
    path("api/parent/child/overview/", user_views.parent_child_overview, name="parent-child-overview-alias"),
    path("api/parent/alerts/", notification_views.alerts, name="parent-alerts-alias"),
    path("api/parent/messages/", notification_views.message_center, name="parent-messages-alias"),
    path("api/admin/users/", user_views.admin_users, name="admin-users-alias"),
    path("api/admin/users/<int:pk>/", user_views.admin_user_detail, name="admin-user-detail-alias"),
    path("api/admin/articles/", include("apps.articles.urls")),
    path("api/admin/seed-demo-data/", user_views.admin_seed_demo, name="admin-seed-demo-data"),
    path("api/admin/global-stats/", user_views.admin_global_stats, name="admin-global-stats-alias"),
]
