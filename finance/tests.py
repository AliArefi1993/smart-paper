import datetime
from unittest.mock import patch

from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.hashers import make_password

from .models import FinanceUnlockAttempt, IncomeEntry


class FinanceApiTests(TestCase):
    def setUp(self):
        FinanceUnlockAttempt.objects.all().delete()

    def tearDown(self):
        FinanceUnlockAttempt.objects.all().delete()

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

    def test_finance_unlock_invalid_pin_before_threshold(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=3,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["detail"], "Invalid PIN")

    def test_finance_unlock_throttles_after_too_many_invalid_pins(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=2,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            first_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
            )
            second_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
            )
            correct_pin_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )

            self.assertEqual(first_response.status_code, 403)
            self.assertEqual(second_response.status_code, 429)
            self.assertEqual(second_response.json()["retry_after_seconds"], 60)
            self.assertEqual(correct_pin_response.status_code, 429)

    def test_finance_unlock_throttle_survives_fresh_session(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=1,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            first_client_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
                REMOTE_ADDR="203.0.113.10",
            )
            fresh_client = Client()
            fresh_client_response = fresh_client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
                REMOTE_ADDR="203.0.113.10",
            )

            self.assertEqual(first_client_response.status_code, 429)
            self.assertEqual(fresh_client_response.status_code, 429)

    def test_finance_unlock_throttle_ignores_spoofed_forwarded_for(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=1,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            first_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
                REMOTE_ADDR="203.0.113.20",
                HTTP_X_FORWARDED_FOR="198.51.100.1",
            )
            fresh_client = Client()
            spoofed_response = fresh_client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
                REMOTE_ADDR="203.0.113.20",
                HTTP_X_FORWARDED_FOR="198.51.100.2",
            )

            self.assertEqual(first_response.status_code, 429)
            self.assertEqual(spoofed_response.status_code, 429)

    def test_finance_unlock_allows_retry_after_cooldown(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=1,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            locked_time = datetime.datetime(
                2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC
            )
            unlocked_time = locked_time + datetime.timedelta(seconds=61)

            with patch("finance.views.timezone.now", return_value=locked_time):
                throttled_response = self.client.post(
                    reverse("finance-unlock"),
                    data={"pin": "9999"},
                    content_type="application/json",
                )
            self.assertEqual(throttled_response.status_code, 429)

            with patch("finance.views.timezone.now", return_value=unlocked_time):
                unlock_response = self.client.post(
                    reverse("finance-unlock"),
                    data={"pin": "1234"},
                    content_type="application/json",
                )

            self.assertEqual(unlock_response.status_code, 200)
            self.assertEqual(unlock_response.json()["unlocked"], True)

    def test_finance_unlock_success_clears_failed_attempts(self):
        with self.settings(
            FINANCE_PIN_HASH=make_password("1234"),
            FINANCE_UNLOCK_MAX_ATTEMPTS=2,
            FINANCE_UNLOCK_COOLDOWN_SECONDS=60,
        ):
            invalid_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
            )
            unlock_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "1234"},
                content_type="application/json",
            )
            self.assertEqual(invalid_response.status_code, 403)
            self.assertEqual(unlock_response.status_code, 200)

            session = self.client.session
            session.pop("finance_unlocked", None)
            session.save()

            next_invalid_response = self.client.post(
                reverse("finance-unlock"),
                data={"pin": "9999"},
                content_type="application/json",
            )

            self.assertEqual(next_invalid_response.status_code, 403)

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
