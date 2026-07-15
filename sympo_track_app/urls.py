from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/event", views.register_event, name="register_event"),
    path("edit/event/<int:event_id>", views.edit_event, name="edit_event"),
    path("register/event/language", views.register_language, name="register_language"),
    path("register/event/stage", views.register_stage_type, name="register_stage_type"),
    path("detail/event/<int:event_id>", views.event_detail, name="event_detail"),
    path("subscriptions/list", views.subscriptions_list, name="subscriptions_list"),
    path("detail/subscription/<int:subscription_id>", views.subscription_detail, name="subscription_detail"),
    path("confirm/stage/<int:requirement_id>", views.confirm_stage, name="confirm_stage"),
    path("subscribe/event/<int:event_id>", views.subscribe_event, name="subscribe_event"),
    path("unsubscribe/event/<int:event_id>", views.unsubscribe_event, name="unsubscribe_event"),
    path("groups/list", views.management_groups, name="management_groups"),
    path("register/group", views.register_management_group, name="register_management_group"),
]