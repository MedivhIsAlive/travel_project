app_name := "travel_planner"

default:
    @just --justfile /app/justfile --list

dev:
    python manage.py runserver 0.0.0.0:8000

security-check:
    bandit -r {{app_name}}
    python manage.py check --deploy

serve:
    gunicorn {{app_name}}.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -

serve-asgi:
    uvicorn {{app_name}}.asgi.application \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4


migrate:
    python manage.py migrate

test:
    python manage.py test

# Wait for DB (useful for entrypoints)
wait-for-db:
    while ! nc -z db 5432; do sleep 1; done;
