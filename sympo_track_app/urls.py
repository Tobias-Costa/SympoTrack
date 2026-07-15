from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
    path("edit/event/<int:event_id>", views.edit_event, name="edit_event"),
    path("register/event/language", views.register_language, name="register_language"),
    path("register/event/stage", views.register_stage_type, name="register_stage_type"),
    path("manage/groups", views.management_groups, name="management_groups"),
    path("detail/event/<int:event_id>", views.event_detail, name="event_detail"),
    path("subscriptions/list", views.subscriptions_list, name="subscriptions_list"),
    path("subscribe/event/<int:event_id>", views.subscribe_event, name="subscribe_event"),
    path("unsubscribe/event/<int:event_id>", views.unsubscribe_event, name="unsubscribe_event"),
]