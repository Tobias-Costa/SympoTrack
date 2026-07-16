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
    path("edit/group/<int:group_id>", views.edit_management_group, name="edit_management_group"),
    path("group/events/<int:group_id>", views.management_group_events, name="management_group_events"),
    path("group/<int:group_id>/members/list", views.management_group_members, name="management_group_members"),
    path("register/group/<int:group_id>/member", views.register_group_member, name="register_group_member"),
    path("remove/group/<int:group_id>/member/<int:member_id>", views.remove_group_member, name="remove_group_member"),
    path("edit/group/<int:group_id>/member/<int:member_id>", views.edit_group_member, name="edit_group_member"),
]