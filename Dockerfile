FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist
RUN python backend/manage.py collectstatic --noinput && useradd -m appuser
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180"]
