
from django.db import models


class Task(models.Model):
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
