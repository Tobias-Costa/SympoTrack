from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
    path("register/event/language", views.register_language, name="register_language"),
    # path("register/event/category", views.register_category, name="register_category"),
]
