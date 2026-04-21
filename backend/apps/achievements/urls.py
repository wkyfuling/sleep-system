from django.urls import path
from . import views

urlpatterns = [
    path("me/", views.my_achievements, name="achievements-me"),
]
