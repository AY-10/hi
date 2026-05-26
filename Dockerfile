FROM node:20-bookworm AS frontend-build

WORKDIR /app

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

COPY frontend ./frontend
COPY backend ./backend
RUN cd frontend && npm run build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=frontend-build /app/backend ./backend
COPY --from=frontend-build /app/frontend ./frontend

WORKDIR /app/backend

RUN python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_demo && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]