# Backend Development Rules

This is the backend repository for Smart Paper. It has its own independent Git history. Run backend Git commands from this directory:

```bash
cd smart-paper
```

## Stack

- Python
- Django 6.0.4
- SQLite via Django ORM
- Gunicorn for the Compose startup path
- `openpyxl` for Excel export

## Architecture

- `config/`: Django project settings, URL routing, WSGI/ASGI, local CORS middleware.
- `planner/`: weekly planner models, configurable section settings, APIs, summaries, export/import.
- `finance/`: finance goal, income entries, PIN unlock, finance APIs.
- `scripts/start_backend.sh`: derives `FINANCE_PIN_HASH` from `FINANCE_PIN` when needed, runs migrations, starts Gunicorn.

## Data Model

- `planner.models.Week`: Saturday-starting week with weekly goal and note.
- `planner.models.DayPlan`: seven day records per week with stable section slot data. Slots 1-4 map to legacy `main`, `second`, `learning`, and `exercise` fields; slots 5-10 use `slot_5` through `slot_10` field groups.
- `planner.models.PlannerSectionConfig`: global single-user section labels, active/hidden state, and positions for `slot_1` through `slot_10`.
- `finance.models.FinanceState`: singleton finance goal.
- `finance.models.IncomeEntry`: dated income records.

## API Conventions

- Endpoints are regular Django views returning `JsonResponse`.
- JSON mutation endpoints currently use `csrf_exempt`.
- Planner endpoints and planner section settings are unauthenticated because Smart Paper is currently single-user/private software.
- Finance and export/import endpoints require an unlocked Django session.
- Keep the frontend API contract aligned with `smart-paper-front/src/lib/smart-paper-types.ts`.

## Commands

Install/setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Run development server:

```bash
python manage.py runserver 8010
```

Run tests:

```bash
python manage.py test
```

Run with Compose from this backend repository:

```bash
docker compose up --build
```

No backend lint or type-check command was discovered.

## Testing Requirement

- For every backend feature or bug fix, include at least one test.
- A simple happy-path test is required even for small changes.
- Do not merge backend code without a related test unless explicitly approved.

## Preferred Test Scope

- Start with straightforward, readable tests.
- Cover the main expected behavior first.
- Expand coverage for validation errors, authorization/session behavior, import/export data integrity, and regressions.

## Database And Migrations

- Use Django migrations for model changes.
- Do not edit existing applied migrations unless explicitly requested and the migration history is known to be disposable.
- Run `python manage.py makemigrations` after model changes and inspect generated migrations before keeping them.
- Do not modify or delete production data without explicit human approval.

## Engineering Constraints

- Keep business logic close to the existing app modules unless a shared helper clearly reduces duplication.
- Preserve Saturday-based week behavior unless requirements change.
- Treat finance data as sensitive.
- Do not deploy production or change production credentials without explicit human authorization.
