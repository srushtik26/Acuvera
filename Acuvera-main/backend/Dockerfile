FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for psycopg3 and others
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files during build. We pass a dummy secret key just to bypass the setting requirement during build (if any).
RUN DJANGO_SECRET_KEY=dummy-key-for-build python manage.py collectstatic --noinput

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=acuvera.settings

EXPOSE 8000

# Run migrations and then start gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn acuvera.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
