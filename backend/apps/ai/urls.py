from django.urls import path
from . import views

urlpatterns = [
    path("advice/", views.get_advice, name="ai-advice"),
    path("advice/history/", views.advice_history, name="ai-advice-history"),
    path("class-diagnosis/", views.class_diagnosis, name="ai-class-diagnosis"),
    path("chat/", views.chat, name="ai-chat"),
]
