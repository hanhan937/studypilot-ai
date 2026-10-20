
from django.urls import path

from . import views
from .chat_view import chat

urlpatterns = [
    path("health/", views.health, name="health"),
    path("config/", views.config, name="config"),
    path("csrf/", views.csrf_token, name="csrf_token"),
    path("chat/", chat, name="chat"),
    path("tasks/", views.tasks, name="tasks"),
    path("plans/", views.plans, name="plans"),
    path(
        "plans/generate/",
        views.generate_plan,
        name="generate_plan",
    ),
    path(
        "plans/<int:plan_id>/reschedule/",
        views.reschedule_plan,
        name="reschedule_plan",
    ),
]
