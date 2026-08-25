import uuid

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
    slot_5_duration_minutes = models.PositiveIntegerField(default=0)
    slot_5_goal = models.TextField(blank=True)
    slot_5_note = models.TextField(blank=True)
    slot_6_duration_minutes = models.PositiveIntegerField(default=0)
    slot_6_goal = models.TextField(blank=True)
    slot_6_note = models.TextField(blank=True)
    slot_7_duration_minutes = models.PositiveIntegerField(default=0)
    slot_7_goal = models.TextField(blank=True)
    slot_7_note = models.TextField(blank=True)
    slot_8_duration_minutes = models.PositiveIntegerField(default=0)
    slot_8_goal = models.TextField(blank=True)
    slot_8_note = models.TextField(blank=True)
    slot_9_duration_minutes = models.PositiveIntegerField(default=0)
    slot_9_goal = models.TextField(blank=True)
    slot_9_note = models.TextField(blank=True)
    slot_10_duration_minutes = models.PositiveIntegerField(default=0)
    slot_10_goal = models.TextField(blank=True)
    slot_10_note = models.TextField(blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["week", "date"], name="unique_day_per_week")
        ]

    def __str__(self):
        return f"{self.date} ({self.week_id})"


class DayScheduleEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    day = models.ForeignKey(
        DayPlan, on_delete=models.CASCADE, related_name="schedule_entries"
    )
    start_minutes = models.PositiveSmallIntegerField()
    end_minutes = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    note = models.TextField(blank=True)
    section_id = models.CharField(max_length=16, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_minutes", "end_minutes", "order", "title"]
        indexes = [
            models.Index(fields=["day", "start_minutes"]),
        ]

    def __str__(self):
        return f"{self.day.date} {self.start_minutes}-{self.end_minutes}: {self.title}"


class PlannerSectionConfig(models.Model):
    slot_id = models.CharField(max_length=16, unique=True)
    label = models.CharField(max_length=80)
    active = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.slot_id}: {self.label}"
