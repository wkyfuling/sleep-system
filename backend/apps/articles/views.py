"""文章视图：公开列表 + 详情 + 管理员 CRUD。"""
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User
from apps.users.permissions import role_required

from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "title", "content", "cover_image", "author", "author_name", "views", "created_at"]
        read_only_fields = ["id", "author", "author_name", "views", "created_at"]

    def get_author_name(self, obj):
        if not obj.author:
            return "系统"
        profile = getattr(obj.author, "teacher_profile", None) or getattr(obj.author, "student_profile", None)
        return profile.real_name if profile else obj.author.username


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), role_required(User.Role.ADMIN)()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Article.objects.filter(pk=instance.pk).update(views=instance.views + 1)
        instance.refresh_from_db()
        ser = self.get_serializer(instance)
        return Response(ser.data)
