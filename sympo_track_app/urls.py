from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
]