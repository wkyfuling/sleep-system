"""M8 报表导出视图。

端点：
- GET /api/sleep/export/class-month/?year=YYYY&month=MM    班级月报 Excel
- GET /api/sleep/export/day-overview/?date=YYYY-MM-DD      单日概览 Excel
- GET /api/sleep/export/student-pdf/?student_id=N&year=YYYY&semester=1  个人学期 PDF
"""
from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User
from apps.users.permissions import role_required


def _get_teacher_classroom(user, classroom_id: str | None = None):
    """返回老师有权限访问的班级。未指定时返回第一个班级。"""
    classrooms = user.classrooms.all()
    if classroom_id:
        try:
            return classrooms.get(id=int(classroom_id))
        except (TypeError, ValueError, classrooms.model.DoesNotExist):
            return None
    return classrooms.first()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def export_class_month(request):
    classroom = _get_teacher_classroom(request.user, request.query_params.get("classroom_id"))
    if not classroom:
        return Response({"detail": "未找到班级"}, status=status.HTTP_404_NOT_FOUND)

    try:
        year = int(request.query_params.get("year", date.today().year))
        month = int(request.query_params.get("month", date.today().month))
    except ValueError:
        return Response({"detail": "年份/月份格式错误"}, status=status.HTTP_400_BAD_REQUEST)

    from utils.exporters import export_class_month_excel
    data = export_class_month_excel(classroom, year, month)

    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="class_{year}{month:02d}.xlsx"'
    return resp


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def export_day_overview(request):
    classroom = _get_teacher_classroom(request.user, request.query_params.get("classroom_id"))
    if not classroom:
        return Response({"detail": "未找到班级"}, status=status.HTTP_404_NOT_FOUND)

    date_str = request.query_params.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return Response({"detail": "日期格式错误"}, status=status.HTTP_400_BAD_REQUEST)

    from utils.exporters import export_day_overview_excel
    data = export_day_overview_excel(classroom, target_date)

    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="day_{date_str}.xlsx"'
    return resp


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, role_required(User.Role.TEACHER)])
def export_student_pdf(request):
    from apps.users.models import StudentProfile
    from utils.exporters import export_student_semester_pdf

    try:
        student_id = int(request.query_params.get("student_id", 0))
        year = int(request.query_params.get("year", date.today().year))
        semester = int(request.query_params.get("semester", 1))
    except ValueError:
        return Response({"detail": "参数格式错误"}, status=status.HTTP_400_BAD_REQUEST)

    student = StudentProfile.objects.filter(id=student_id, classroom__teacher=request.user).first()
    if not student:
        return Response({"detail": "学生不在本班"}, status=status.HTTP_404_NOT_FOUND)

    data = export_student_semester_pdf(student, year, semester)

    resp = HttpResponse(data, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="student_{student.student_no}_{year}_s{semester}.pdf"'
    return resp
