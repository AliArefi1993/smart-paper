#!/bin/sh
set -eu

if [ -z "${FINANCE_PIN_HASH:-}" ] && [ -n "${FINANCE_PIN:-}" ]; then
  FINANCE_PIN_HASH="$(
    python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup(); from django.contrib.auth.hashers import make_password; print(make_password(os.environ['FINANCE_PIN']))"
  )"
  export FINANCE_PIN_HASH
fi

python manage.py migrate
exec gunicorn config.wsgi:application --bind 0.0.0.0:8010 --workers 2
