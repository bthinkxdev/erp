#!/bin/bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$#" -eq 0 ]; then
  set -- gunicorn erp.wsgi:application --bind 0.0.0.0:8000
fi
exec "$@"
