from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "sender", "sender_name", "receiver",
            "type", "title", "content", "is_read", "created_at",
        ]
        read_only_fields = ["id", "sender", "sender_name", "receiver", "created_at", "is_read"]

    def get_sender_name(self, obj):
        if not obj.sender:
            return "系统"
        profile = (
            getattr(obj.sender, "teacher_profile", None)
            or getattr(obj.sender, "student_profile", None)
            or getattr(obj.sender, "parent_profile", None)
        )
        if profile:
            return profile.real_name
        return obj.sender.username


class SendMessageSerializer(serializers.Serializer):
    """老师/家长/学生发消息。"""
    receiver_id = serializers.IntegerField()
    title = serializers.CharField(max_length=128)
    content = serializers.CharField()
    type = serializers.ChoiceField(choices=Notification.Type.choices, default=Notification.Type.TEACHER_MSG)


class BroadcastSerializer(serializers.Serializer):
    """老师发班级公告，群发给全班学生（及其家长）。"""
    title = serializers.CharField(max_length=128)
    content = serializers.CharField()
    include_parents = serializers.BooleanField(default=False)
