from django.test import TestCase
from django.urls import reverse

from .models import DayPlan, Week


class PlannerApiTests(TestCase):
    def test_weeks_list_includes_current_week(self):
        response = self.client.get(reverse("weeks-list"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        current = payload["current_week_start"]
        starts = [week["start_date"] for week in payload["weeks"]]
        self.assertIn(current, starts)

    def test_week_detail_creates_week_days(self):
        week_start = "2026-04-25"  # Saturday
        response = self.client.get(reverse("week-detail", args=[week_start]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["start_date"], week_start)
        self.assertEqual(len(payload["days"]), 7)
        self.assertEqual(Week.objects.count(), 1)
        self.assertEqual(DayPlan.objects.count(), 7)

    def test_week_update_happy_path(self):
        week_start = "2026-04-25"
        self.client.get(reverse("week-detail", args=[week_start]))

        update_payload = {
            "weekly_goal": "Finish key tasks for the week",
            "weekly_note": "Keep focus and avoid context switching",
            "days": [
                {
                    "date": "2026-04-25",
                    "sections": {
                        "main": {
                            "duration_minutes": 120,
                            "goal": "Ship backend",
                            "note": "Deep work",
                        },
                        "learning": {
                            "duration_minutes": 45,
                            "goal": "Learn APIs",
                            "note": "Django docs",
                        },
                    },
                },
                {
                    "date": "2026-04-26",
                    "sections": {
                        "exercise": {
                            "duration_minutes": 60,
                            "goal": "Cardio + strength",
                            "note": "Gym",
                        },
                    },
                },
            ]
        }

        response = self.client.put(
            reverse("week-detail", args=[week_start]),
            data=update_payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["weekly_goal"], "Finish key tasks for the week")
        self.assertEqual(
            payload["weekly_note"], "Keep focus and avoid context switching"
        )
        self.assertEqual(payload["days"][0]["sections"]["main"]["goal"], "Ship backend")
        self.assertEqual(payload["totals"]["week_total_minutes"], 225)
        self.assertEqual(payload["totals"]["by_section_minutes"]["main"], 120)
        self.assertEqual(payload["totals"]["by_section_minutes"]["learning"], 45)
        self.assertEqual(payload["totals"]["by_section_minutes"]["exercise"], 60)
