
from django.urls import path
from . import views

urlpatterns = [
    # Existing APIs
    path("health/", views.health, name="health"),
    path("chat/", views.chat, name="chat"),
    path("tasks/", views.tasks, name="tasks"),

    # Module 5: Study Plan APIs
    path("plans/", views.plans, name="plans"),
    path("plans/generate/", views.generate_plan, name="generate_plan"),
    path(
        "plans/<int:plan_id>/reschedule/",
        views.reschedule_plan,
        name="reschedule_plan",
    ),
]
