from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notification-list"),
    path("<int:pk>/read/", views.mark_read, name="notification-read"),
    path("read-all/", views.mark_all_read, name="notification-read-all"),
    path("unread-count/", views.unread_count, name="notification-unread-count"),
    path("send/", views.send_message, name="notification-send"),
    path("messages/", views.message_center, name="notification-messages"),
    path("recipients/", views.recipients, name="notification-recipients"),
    path("broadcast/", views.broadcast, name="notification-broadcast"),
    path("alerts/", views.alerts, name="notification-alerts"),
]
