import datetime
import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import DayPlan, Week

SECTIONS = ("main", "second", "learning", "exercise")
WEEKDAY_NAMES = (
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
)
SATURDAY_WEEKDAY = 5


def saturday_start(given_date: datetime.date) -> datetime.date:
    # Python weekday: Monday=0 ... Sunday=6
    shift = (given_date.weekday() - SATURDAY_WEEKDAY) % 7
    return given_date - datetime.timedelta(days=shift)


def format_week_label(start_date: datetime.date, end_date: datetime.date) -> str:
    return f"{start_date.isoformat()} to {end_date.isoformat()}"


def build_week(week_start: datetime.date) -> Week:
    week, _ = Week.objects.get_or_create(start_date=week_start)
    existing_by_date = {day.date: day for day in week.days.all()}
    to_create = []

    for i in range(7):
        current_date = week_start + datetime.timedelta(days=i)
        if current_date in existing_by_date:
            continue
        to_create.append(
            DayPlan(
                week=week,
                date=current_date,
                weekday_index=i,
            )
        )

    if to_create:
        DayPlan.objects.bulk_create(to_create)

    return week


def serialize_day(day: DayPlan) -> dict:
    sections = {}
    for section in SECTIONS:
        sections[section] = {
            "duration_minutes": getattr(day, f"{section}_duration_minutes"),
            "goal": getattr(day, f"{section}_goal"),
            "note": getattr(day, f"{section}_note"),
        }

    return {
        "date": day.date.isoformat(),
        "weekday_index": day.weekday_index,
        "weekday_name": WEEKDAY_NAMES[day.weekday_index],
        "sections": sections,
    }


def compute_totals(days: list[DayPlan]) -> dict:
    by_section = {section: 0 for section in SECTIONS}
    for day in days:
        for section in SECTIONS:
            by_section[section] += getattr(day, f"{section}_duration_minutes")

    return {
        "by_section_minutes": by_section,
        "week_total_minutes": sum(by_section.values()),
    }


def serialize_week(week: Week) -> dict:
    days = list(week.days.all().order_by("date"))
    return {
        "start_date": week.start_date.isoformat(),
        "end_date": (week.start_date + datetime.timedelta(days=6)).isoformat(),
        "label": format_week_label(
            week.start_date, week.start_date + datetime.timedelta(days=6)
        ),
        "weekly_goal": week.weekly_goal,
        "weekly_note": week.weekly_note,
        "days": [serialize_day(day) for day in days],
        "totals": compute_totals(days),
    }


@require_http_methods(["GET"])
def weeks_list(request):
    today = datetime.date.today()
    current_week_start = saturday_start(today)
    span_raw = request.GET.get("span", "6")

    try:
        span = int(span_raw)
    except ValueError:
        return HttpResponseBadRequest("span must be a number")

    span = max(1, min(span, 26))
    weeks_data = []

    for offset in range(-span, span + 1):
        start = current_week_start + datetime.timedelta(days=offset * 7)
        end = start + datetime.timedelta(days=6)
        weeks_data.append(
            {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "label": format_week_label(start, end),
                "is_current": start == current_week_start,
            }
        )

    return JsonResponse(
        {
            "current_week_start": current_week_start.isoformat(),
            "weeks": weeks_data,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def week_detail(request, start_date: str):
    try:
        week_start = datetime.date.fromisoformat(start_date)
    except ValueError:
        return HttpResponseBadRequest("start_date must be YYYY-MM-DD")

    if week_start.weekday() != SATURDAY_WEEKDAY:
        return HttpResponseBadRequest("start_date must be a Saturday")

    week = build_week(week_start)

    if request.method == "PUT":
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

        weekly_goal = payload.get("weekly_goal")
        weekly_note = payload.get("weekly_note")
        week_changed = False
        if isinstance(weekly_goal, str):
            week.weekly_goal = weekly_goal.strip()
            week_changed = True
        if isinstance(weekly_note, str):
            week.weekly_note = weekly_note.strip()
            week_changed = True
        if week_changed:
            week.save(update_fields=["weekly_goal", "weekly_note", "updated_at"])

        days_payload = payload.get("days", [])
        if not isinstance(days_payload, list):
            return HttpResponseBadRequest("days must be an array")

        days_by_date = {day.date.isoformat(): day for day in week.days.all()}
        changed_days = []

        for item in days_payload:
            if not isinstance(item, dict):
                continue
            day = days_by_date.get(item.get("date"))
            if day is None:
                continue

            sections = item.get("sections", {})
            if not isinstance(sections, dict):
                continue

            for section in SECTIONS:
                section_payload = sections.get(section, {})
                if not isinstance(section_payload, dict):
                    continue

                duration = section_payload.get("duration_minutes")
                goal = section_payload.get("goal")
                note = section_payload.get("note")

                if isinstance(duration, int) and duration >= 0:
                    setattr(day, f"{section}_duration_minutes", duration)
                if isinstance(goal, str):
                    setattr(day, f"{section}_goal", goal.strip())
                if isinstance(note, str):
                    setattr(day, f"{section}_note", note.strip())

            changed_days.append(day)

        if changed_days:
            DayPlan.objects.bulk_update(
                changed_days,
                [
                    "main_duration_minutes",
                    "main_goal",
                    "main_note",
                    "second_duration_minutes",
                    "second_goal",
                    "second_note",
                    "learning_duration_minutes",
                    "learning_goal",
                    "learning_note",
                    "exercise_duration_minutes",
                    "exercise_goal",
                    "exercise_note",
                ],
            )

    week.refresh_from_db()
    return JsonResponse(serialize_week(week))
