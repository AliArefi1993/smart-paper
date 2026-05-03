from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password

from .models import IncomeEntry


class FinanceApiTests(TestCase):
    def test_finance_overview_requires_unlock(self):
        response = self.client.get(reverse("finance-overview"))
        self.assertEqual(response.status_code, 403)

    def test_finance_unlock_then_overview_happy_path(self):
        with self.settings(FINANCE_PIN_HASH=make_password("1234")):
            unlock_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )
            self.assertEqual(unlock_response.status_code, 200)
            self.assertEqual(unlock_response.json()["unlocked"], True)

            response = self.client.get(reverse("finance-overview"))
            self.assertEqual(response.status_code, 200)

    def test_finance_overview_update_and_totals_happy_path(self):
        with self.settings(FINANCE_PIN_HASH=make_password("1234")):
            self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )

            response = self.client.put(
                reverse("finance-overview"),
                data={
                    "goal_amount": 10000,
                    "income_amount": 2500,
                    "income_note": "Salary",
                    "income_date": "2026-05-03",
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()

            self.assertEqual(payload["goal_amount"], 10000)
            self.assertEqual(payload["total_income"], 2500)
            self.assertEqual(payload["remaining_amount"], 7500)
            self.assertEqual(payload["progress_percent"], 25.0)
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["note"], "Salary")
            self.assertEqual(IncomeEntry.objects.count(), 1)

    def test_finance_income_delete_happy_path(self):
        with self.settings(FINANCE_PIN_HASH=make_password("1234")):
            self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )
            create_response = self.client.put(
                reverse("finance-overview"),
                data={
                    "goal_amount": 10000,
                    "income_amount": 2500,
                    "income_note": "Salary",
                    "income_date": "2026-05-03",
                },
                content_type="application/json",
            )
            self.assertEqual(create_response.status_code, 200)
            created_entry_id = create_response.json()["entries"][0]["id"]

            delete_response = self.client.delete(
                reverse("finance-income-detail", args=[created_entry_id])
            )
            self.assertEqual(delete_response.status_code, 200)
            payload = delete_response.json()
            self.assertEqual(payload["total_income"], 0)
            self.assertEqual(len(payload["entries"]), 0)
            self.assertEqual(IncomeEntry.objects.count(), 0)

    def test_finance_income_edit_happy_path(self):
        with self.settings(FINANCE_PIN_HASH=make_password("1234")):
            self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )
            create_response = self.client.put(
                reverse("finance-overview"),
                data={
                    "goal_amount": 10000,
                    "income_amount": 2500,
                    "income_note": "Salary",
                    "income_date": "2026-05-03",
                },
                content_type="application/json",
            )
            self.assertEqual(create_response.status_code, 200)
            created_entry_id = create_response.json()["entries"][0]["id"]

            edit_response = self.client.patch(
                reverse("finance-income-detail", args=[created_entry_id]),
                data={
                    "income_amount": 3000,
                    "income_note": "Updated salary",
                    "income_date": "2026-05-04",
                },
                content_type="application/json",
            )
            self.assertEqual(edit_response.status_code, 200)
            payload = edit_response.json()
            self.assertEqual(payload["total_income"], 3000)
            self.assertEqual(payload["entries"][0]["amount"], 3000)
            self.assertEqual(payload["entries"][0]["note"], "Updated salary")
            self.assertEqual(payload["entries"][0]["received_on"], "2026-05-04")
