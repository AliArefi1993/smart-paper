from django.db import models


class FinanceState(models.Model):
    goal_amount = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Finance goal: {self.goal_amount}"


class IncomeEntry(models.Model):
    amount = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    received_on = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_on", "-id"]

    def __str__(self):
        return f"Income {self.amount} on {self.received_on}"
