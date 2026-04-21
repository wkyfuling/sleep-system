from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from . import export_views


router = DefaultRouter()
router.register(r"records", views.SleepRecordViewSet, basename="sleep-record")

urlpatterns = [
    path("", include(router.urls)),
    path("teacher/records/<int:pk>/", views.teacher_edit_record, name="teacher-edit-record"),
    path("statistics/week/", views.week_statistics, name="sleep-week-stats"),
    path("heatmap/", views.heatmap_data, name="sleep-heatmap"),
    path("ranking/", views.class_ranking, name="sleep-ranking"),
    # 导出
    path("export/class-month/", export_views.export_class_month, name="export-class-month"),
    path("export/day-overview/", export_views.export_day_overview, name="export-day-overview"),
    path("export/student-pdf/", export_views.export_student_pdf, name="export-student-pdf"),
]
