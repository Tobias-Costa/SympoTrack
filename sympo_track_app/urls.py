from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
    path("register/event/language", views.register_language, name="register_language"),
    path("register/event/stage", views.register_stage_type, name="register_stage_type"),
    path("manage/groups", views.management_groups, name="management_groups"),
]