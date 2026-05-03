# smart-paper
it should act like a mart paper of me so i can put data there and it save me and give me the real progress.

## Run with Docker Compose (Backend + Frontend)

This repository includes Docker Compose configuration to run both projects together in production mode:
- Backend (`smart-paper`) with `gunicorn` on port `8010`
- Frontend (`../smart-paper-front`) with `next build` + `next start` on port `3000`

```bash
cd /home/aliarefi/Documents/programming/playground/smart-paper
docker compose up --build
```

Access:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8010`

To stop:
```bash
docker compose down
```

## Run Backend Locally (Without Docker)

```bash
cd /home/aliarefi/Documents/programming/playground/smart-paper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8010
```

## API Endpoints
- `GET /api/weeks/?span=8` -> list weeks around current week
- `GET /api/weeks/<saturday-date>/` -> week details and totals
- `PUT /api/weeks/<saturday-date>/` -> save all day section data for that week
- `POST /api/finance/unlock/` -> unlock finance session with PIN (`pin`)
- `GET /api/finance/` -> finance goal, total income, progress, unlock TTL, and entries (requires unlocked session)
- `PUT /api/finance/` -> update goal and/or add income entry (`goal_amount`, `income_amount`, `income_note`, `income_date`) (requires unlocked session)
- `PATCH /api/finance/incomes/<entry_id>/` -> edit saved income record (amount, note, date) (requires unlocked session)
- `DELETE /api/finance/incomes/<entry_id>/` -> delete saved income record (requires unlocked session)

## Finance PIN Setup
Finance API is protected by a PIN and uses session unlock.

1. Put your PIN in `.env`:
```bash
cd /home/aliarefi/Documents/programming/playground/smart-paper
echo "FINANCE_PIN=1234" >> .env
```
2. Set unlock TTL in `.env` (example 5 minutes):
```bash
echo "FINANCE_UNLOCK_TTL_SECONDS=300" >> .env
```
3. Start with Docker Compose. Backend hashes `FINANCE_PIN` automatically on each startup.

Notes:
- `FINANCE_UNLOCK_TTL_SECONDS` default is `3600` if not set.
- Frontend auto-locks and hides finance data when session expires.
