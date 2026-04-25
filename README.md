# smart-paper
it should act like a mart paper of me so i can put data there and it save me and give me the real progress.

## Run Backend (Django)

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
