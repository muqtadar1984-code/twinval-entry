FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build dependencies for psycopg2 + bcrypt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Drop privileges
RUN useradd -m -u 1000 twinval && chown -R twinval /app
USER twinval

EXPOSE 8000

# Migrations are NOT run here — they're handled by:
#   - docker-compose: explicit command override that wraps alembic + uvicorn
#   - Railway:        preDeployCommand in railway.json
# This keeps container start fast and predictable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
