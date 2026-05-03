import datetime
import json
import os

from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import FinanceState, IncomeEntry

FINANCE_UNLOCK_SESSION_KEY = "finance_unlocked"
DEFAULT_UNLOCK_TTL_SECONDS = 3600


def finance_pin_hash() -> str:
    configured = getattr(settings, "FINANCE_PIN_HASH", "")
    if configured:
        return str(configured).strip()
    return os.environ.get("FINANCE_PIN_HASH", "").strip()


def finance_unlock_ttl_seconds() -> int:
    raw_ttl = getattr(
        settings,
        "FINANCE_UNLOCK_TTL_SECONDS",
        os.environ.get("FINANCE_UNLOCK_TTL_SECONDS", str(DEFAULT_UNLOCK_TTL_SECONDS)),
    )
    try:
        parsed = int(raw_ttl)
    except ValueError:
        return DEFAULT_UNLOCK_TTL_SECONDS
    return max(1, parsed)


def require_finance_unlock(request):
    if request.session.get(FINANCE_UNLOCK_SESSION_KEY):
        return None
    return JsonResponse({"detail": "Finance is locked"}, status=403)


def get_finance_state() -> FinanceState:
    state, _ = FinanceState.objects.get_or_create(id=1)
    return state


def serialize_finance() -> dict:
    state = get_finance_state()
    total_income = IncomeEntry.objects.aggregate(total=Sum("amount"))["total"] or 0
    progress_percent = 0.0
    if state.goal_amount > 0:
        progress_percent = min(100.0, (total_income / state.goal_amount) * 100)

    entries = [
        {
            "id": entry.id,
            "amount": entry.amount,
            "note": entry.note,
            "received_on": entry.received_on.isoformat(),
        }
        for entry in IncomeEntry.objects.all()
    ]

    return {
        "goal_amount": state.goal_amount,
        "total_income": total_income,
        "remaining_amount": max(0, state.goal_amount - total_income),
        "progress_percent": round(progress_percent, 2),
        "unlock_ttl_seconds": finance_unlock_ttl_seconds(),
        "entries": entries,
    }


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def finance_overview(request):
    locked_response = require_finance_unlock(request)
    if locked_response is not None:
        return locked_response

    if request.method == "GET":
        return JsonResponse(serialize_finance())

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    state = get_finance_state()
    changed_state = False

    goal_amount = payload.get("goal_amount")
    if goal_amount is not None:
        if not isinstance(goal_amount, int) or goal_amount < 0:
            return HttpResponseBadRequest("goal_amount must be a positive number")
        state.goal_amount = goal_amount
        changed_state = True

    income_amount = payload.get("income_amount")
    if income_amount is not None:
        if not isinstance(income_amount, int) or income_amount <= 0:
            return HttpResponseBadRequest("income_amount must be greater than zero")
        income_note = payload.get("income_note", "")
        if not isinstance(income_note, str):
            return HttpResponseBadRequest("income_note must be text")

        income_date_raw = payload.get("income_date")
        if income_date_raw is None:
            income_date = datetime.date.today()
        elif isinstance(income_date_raw, str):
            try:
                income_date = datetime.date.fromisoformat(income_date_raw)
            except ValueError:
                return HttpResponseBadRequest("income_date must be YYYY-MM-DD")
        else:
            return HttpResponseBadRequest("income_date must be YYYY-MM-DD")

        IncomeEntry.objects.create(
            amount=income_amount,
            note=income_note.strip(),
            received_on=income_date,
        )

    if changed_state:
        state.save(update_fields=["goal_amount", "updated_at"])

    if goal_amount is None and income_amount is None:
        return HttpResponseBadRequest("Provide goal_amount or income_amount")

    return JsonResponse(serialize_finance())


@csrf_exempt
@require_http_methods(["POST"])
def finance_unlock(request):
    pin_hash = finance_pin_hash()
    if not pin_hash:
        return JsonResponse({"detail": "Finance PIN is not configured"}, status=503)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    pin = payload.get("pin")
    if not isinstance(pin, str) or not pin:
        return HttpResponseBadRequest("pin is required")

    if not check_password(pin, pin_hash):
        return JsonResponse({"detail": "Invalid PIN"}, status=403)

    request.session[FINANCE_UNLOCK_SESSION_KEY] = True
    ttl_seconds = finance_unlock_ttl_seconds()
    request.session.set_expiry(ttl_seconds)
    return JsonResponse({"unlocked": True, "unlock_ttl_seconds": ttl_seconds})


@csrf_exempt
@require_http_methods(["DELETE", "PATCH"])
def finance_income_detail(request, entry_id: int):
    locked_response = require_finance_unlock(request)
    if locked_response is not None:
        return locked_response

    try:
        entry = IncomeEntry.objects.get(id=entry_id)
    except IncomeEntry.DoesNotExist:
        return JsonResponse({"detail": "Income entry not found"}, status=404)

    if request.method == "DELETE":
        entry.delete()
        return JsonResponse(serialize_finance())

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    amount = payload.get("income_amount")
    if amount is not None:
        if not isinstance(amount, int) or amount <= 0:
            return HttpResponseBadRequest("income_amount must be greater than zero")
        entry.amount = amount

    note = payload.get("income_note")
    if note is not None:
        if not isinstance(note, str):
            return HttpResponseBadRequest("income_note must be text")
        entry.note = note.strip()

    income_date_raw = payload.get("income_date")
    if income_date_raw is not None:
        if not isinstance(income_date_raw, str):
            return HttpResponseBadRequest("income_date must be YYYY-MM-DD")
        try:
            entry.received_on = datetime.date.fromisoformat(income_date_raw)
        except ValueError:
            return HttpResponseBadRequest("income_date must be YYYY-MM-DD")

    if amount is None and note is None and income_date_raw is None:
        return HttpResponseBadRequest(
            "Provide income_amount or income_note or income_date"
        )

    entry.save(update_fields=["amount", "note", "received_on"])
    return JsonResponse(serialize_finance())
