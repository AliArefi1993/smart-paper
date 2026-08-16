import datetime
import json

from django.http import HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import DayPlan, PlannerSectionConfig, Week

SLOT_IDS = tuple(f"slot_{index}" for index in range(1, 11))
LEGACY_SECTION_TO_SLOT = {
    "main": "slot_1",
    "second": "slot_2",
    "learning": "slot_3",
    "exercise": "slot_4",
}
SLOT_TO_FIELD_PREFIX = {
    "slot_1": "main",
    "slot_2": "second",
    "slot_3": "learning",
    "slot_4": "exercise",
    **{f"slot_{index}": f"slot_{index}" for index in range(5, 11)},
}
SECTION_FIELD_NAMES = [
    f"{field_prefix}_{field}"
    for field_prefix in SLOT_TO_FIELD_PREFIX.values()
    for field in ("duration_minutes", "goal", "note")
]
DEFAULT_PLANNER_SECTIONS = tuple(
    {
        "slot_id": f"slot_{index}",
        "label": label,
        "active": index <= 4,
        "position": index,
    }
    for index, label in enumerate(
        (
            "Main",
            "Second",
            "Learning",
            "Exercise",
            "Section 5",
            "Section 6",
            "Section 7",
            "Section 8",
            "Section 9",
            "Section 10",
        ),
        start=1,
    )
)
# Backward-compatible alias for older import/export call sites.
SECTIONS = SLOT_IDS
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


def normalize_section_key(section_key: str) -> str | None:
    if section_key in SLOT_IDS:
        return section_key
    return LEGACY_SECTION_TO_SLOT.get(section_key)


def field_prefix_for_slot(slot_id: str) -> str:
    return SLOT_TO_FIELD_PREFIX[slot_id]


def ensure_planner_sections() -> list[PlannerSectionConfig]:
    existing_by_slot = {
        section.slot_id: section for section in PlannerSectionConfig.objects.all()
    }
    to_create = []
    for default in DEFAULT_PLANNER_SECTIONS:
        if default["slot_id"] in existing_by_slot:
            continue
        to_create.append(PlannerSectionConfig(**default))
    if to_create:
        PlannerSectionConfig.objects.bulk_create(to_create)
    return list(PlannerSectionConfig.objects.filter(slot_id__in=SLOT_IDS))


def serialize_planner_section(section: PlannerSectionConfig) -> dict:
    return {
        "slot_id": section.slot_id,
        "label": section.label,
        "active": section.active,
        "position": section.position,
    }


def serialize_planner_sections() -> list[dict]:
    sections_by_slot = {
        section.slot_id: section for section in ensure_planner_sections()
    }
    return [
        serialize_planner_section(sections_by_slot[slot_id])
        for slot_id in SLOT_IDS
        if slot_id in sections_by_slot
    ]


def active_slot_ids(planner_sections: list[dict] | None = None) -> tuple[str, ...]:
    if planner_sections is None:
        planner_sections = serialize_planner_sections()
    return tuple(
        section["slot_id"] for section in planner_sections if section.get("active")
    )


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
    for slot_id in SLOT_IDS:
        field_prefix = field_prefix_for_slot(slot_id)
        sections[slot_id] = {
            "duration_minutes": getattr(day, f"{field_prefix}_duration_minutes"),
            "goal": getattr(day, f"{field_prefix}_goal"),
            "note": getattr(day, f"{field_prefix}_note"),
        }

    return {
        "date": day.date.isoformat(),
        "weekday_index": day.weekday_index,
        "weekday_name": WEEKDAY_NAMES[day.weekday_index],
        "sections": sections,
    }


def compute_totals(days: list[DayPlan], section_ids: tuple[str, ...] | None = None) -> dict:
    if section_ids is None:
        section_ids = active_slot_ids()
    by_section = {section: 0 for section in section_ids}
    for day in days:
        for section in section_ids:
            field_prefix = field_prefix_for_slot(section)
            by_section[section] += getattr(day, f"{field_prefix}_duration_minutes")

    return {
        "by_section_minutes": by_section,
        "week_total_minutes": sum(by_section.values()),
    }


def serialize_week(week: Week) -> dict:
    days = list(week.days.all().order_by("date"))
    planner_sections = serialize_planner_sections()
    return {
        "start_date": week.start_date.isoformat(),
        "end_date": (week.start_date + datetime.timedelta(days=6)).isoformat(),
        "label": format_week_label(
            week.start_date, week.start_date + datetime.timedelta(days=6)
        ),
        "weekly_goal": week.weekly_goal,
        "weekly_note": week.weekly_note,
        "planner_sections": planner_sections,
        "days": [serialize_day(day) for day in days],
        "totals": compute_totals(days, active_slot_ids(planner_sections)),
    }


def serialize_week_summary(week: Week) -> dict:
    days = list(week.days.all().order_by("date"))
    planner_sections = serialize_planner_sections()
    section_ids = active_slot_ids(planner_sections)
    by_section_notes: dict[str, list[str]] = {section: [] for section in section_ids}
    details_by_section: dict[str, list[dict]] = {section: [] for section in section_ids}

    for day in days:
        for section in section_ids:
            field_prefix = field_prefix_for_slot(section)
            duration_minutes = getattr(day, f"{field_prefix}_duration_minutes")
            goal = getattr(day, f"{field_prefix}_goal").strip()
            note = getattr(day, f"{field_prefix}_note").strip()
            if not duration_minutes and not goal and not note:
                continue
            if note:
                by_section_notes[section].append(
                    f"{WEEKDAY_NAMES[day.weekday_index]}: {note}"
                )
            details_by_section[section].append(
                {
                    "date": day.date.isoformat(),
                    "weekday_name": WEEKDAY_NAMES[day.weekday_index],
                    "duration_minutes": duration_minutes,
                    "goal": goal,
                    "note": note,
                }
            )

    return {
        "start_date": week.start_date.isoformat(),
        "end_date": (week.start_date + datetime.timedelta(days=6)).isoformat(),
        "label": format_week_label(
            week.start_date, week.start_date + datetime.timedelta(days=6)
        ),
        "weekly_goal": week.weekly_goal,
        "weekly_note": week.weekly_note,
        "planner_sections": planner_sections,
        "totals": compute_totals(days, section_ids),
        "notes_by_section": by_section_notes,
        "details_by_section": details_by_section,
    }


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def planner_sections(request):
    if request.method == "GET":
        return JsonResponse({"planner_sections": serialize_planner_sections()})

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    sections_payload = payload.get("planner_sections")
    if not isinstance(sections_payload, list):
        return HttpResponseBadRequest("planner_sections must be an array")

    sections_by_slot = {section.slot_id: section for section in ensure_planner_sections()}
    changed = []
    now = timezone.now()
    for item in sections_payload:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        if slot_id not in SLOT_IDS:
            return HttpResponseBadRequest("planner_sections contains an invalid slot_id")
        section = sections_by_slot[slot_id]
        did_change = False

        label = item.get("label")
        if label is not None:
            if not isinstance(label, str):
                return HttpResponseBadRequest("planner section label must be text")
            section.label = label.strip() or next(
                default["label"]
                for default in DEFAULT_PLANNER_SECTIONS
                if default["slot_id"] == slot_id
            )
            did_change = True

        active = item.get("active")
        if active is not None:
            if not isinstance(active, bool):
                return HttpResponseBadRequest("planner section active must be boolean")
            section.active = active
            did_change = True

        if did_change:
            section.updated_at = now
            changed.append(section)

    if changed:
        next_active_by_slot = {
            slot_id: section.active for slot_id, section in sections_by_slot.items()
        }
        for section in changed:
            next_active_by_slot[section.slot_id] = section.active
        if not any(next_active_by_slot.values()):
            return HttpResponseBadRequest("at least one planner section must be active")
        PlannerSectionConfig.objects.bulk_update(changed, ["label", "active", "updated_at"])

    return JsonResponse({"planner_sections": serialize_planner_sections()})


@require_http_methods(["GET"])
def weeks_list(request):
    today = datetime.date.today()
    current_week_start = saturday_start(today)
    span_raw = request.GET.get("span", "6")

    try:
        span = int(span_raw)
    except ValueError:
        return HttpResponseBadRequest("span must be a number")
    span = max(1, min(span, 104))
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


@require_http_methods(["GET"])
def week_summaries(request):
    today = datetime.date.today()
    current_week_start = saturday_start(today)
    span_raw = request.GET.get("span", "8")

    try:
        span = int(span_raw)
    except ValueError:
        return HttpResponseBadRequest("span must be a number")
    span = max(1, min(span, 104))
    starts = [
        current_week_start + datetime.timedelta(days=offset * 7)
        for offset in range(-span, span + 1)
    ]

    for start in starts:
        build_week(start)

    weeks_by_start = {
        week.start_date: week
        for week in Week.objects.filter(start_date__in=starts).prefetch_related("days")
    }
    summaries = []
    for start in starts:
        week = weeks_by_start.get(start)
        if week is None:
            continue
        summaries.append(
            {
                **serialize_week_summary(week),
                "is_current": start == current_week_start,
            }
        )

    return JsonResponse(
        {
            "current_week_start": current_week_start.isoformat(),
            "summaries": summaries,
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

            changed = False
            for raw_section, section_payload in sections.items():
                section = normalize_section_key(raw_section)
                if section is None:
                    continue
                if not isinstance(section_payload, dict):
                    continue
                field_prefix = field_prefix_for_slot(section)

                duration = section_payload.get("duration_minutes")
                goal = section_payload.get("goal")
                note = section_payload.get("note")

                if isinstance(duration, int) and duration >= 0:
                    setattr(day, f"{field_prefix}_duration_minutes", duration)
                    changed = True
                if isinstance(goal, str):
                    setattr(day, f"{field_prefix}_goal", goal.strip())
                    changed = True
                if isinstance(note, str):
                    setattr(day, f"{field_prefix}_note", note.strip())
                    changed = True

            if changed:
                changed_days.append(day)

        if changed_days:
            DayPlan.objects.bulk_update(changed_days, SECTION_FIELD_NAMES)

    week.refresh_from_db()
    return JsonResponse(serialize_week(week))
