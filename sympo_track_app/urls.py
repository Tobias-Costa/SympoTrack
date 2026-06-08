from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
    path("register/language", views.register_language, name="register_language"),
    path("register/address", views.register_address, name="register_address"),
    path("register/address/city", views.register_city, name="register_city"),
]