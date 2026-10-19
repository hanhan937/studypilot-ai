
from django.db import models


class StudyPlan(models.Model):
    goal = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    daily_minutes = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.goal[:50]


class Task(models.Model):
    plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=100, blank=True)
    scheduled_date = models.DateField(
        null=True,
        blank=True
    )
    estimated_minutes = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
