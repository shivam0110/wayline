.PHONY: install dev build serve test
-include .env
export

install:
	python3 -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm ci

# Vite handles hot reload; stop both processes with Ctrl+C.
dev:
	@.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 & api_pid=$$!; \
	trap 'kill $$api_pid 2>/dev/null || true' INT TERM EXIT; cd frontend && npm run dev

build:
	cd frontend && npm run build
	.venv/bin/python backend/manage.py collectstatic --noinput

serve: build
	.venv/bin/gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$${PORT:-8000} --workers 1 --threads 4 --timeout 180

test:
	.venv/bin/python backend/manage.py test planner.tests
	cd frontend && npm run build
