from django.db import models


class Week(models.Model):
    start_date = models.DateField(unique=True, db_index=True)
    weekly_goal = models.TextField(blank=True)
    weekly_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"Week starting {self.start_date}"


class DayPlan(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE, related_name="days")
    date = models.DateField(db_index=True)
    weekday_index = models.PositiveSmallIntegerField()
    main_duration_minutes = models.PositiveIntegerField(default=0)
    main_goal = models.TextField(blank=True)
    main_note = models.TextField(blank=True)
    second_duration_minutes = models.PositiveIntegerField(default=0)
    second_goal = models.TextField(blank=True)
    second_note = models.TextField(blank=True)
    learning_duration_minutes = models.PositiveIntegerField(default=0)
    learning_goal = models.TextField(blank=True)
    learning_note = models.TextField(blank=True)
    exercise_duration_minutes = models.PositiveIntegerField(default=0)
    exercise_goal = models.TextField(blank=True)
    exercise_note = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["week", "date"], name="unique_day_per_week")
        ]

    def __str__(self):
        return f"{self.date} ({self.week_id})"
