from rest_framework import permissions


class RolePermission(permissions.BasePermission):
    """通用角色守卫：在 view 中设置 required_roles = ("teacher", ...)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        required = getattr(view, "required_roles", None)
        if required is None:
            return True
        return request.user.role in required


def role_required(*roles):
    class _P(permissions.BasePermission):
        def has_permission(self, request, view):
            return (
                request.user
                and request.user.is_authenticated
                and request.user.role in roles
            )
    return _P
