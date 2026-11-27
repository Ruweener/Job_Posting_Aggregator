# Container image for the API (and for running ingest or migrations with the same code).
# Build:  docker build -t jobagg-api .
# Run:    docker compose up    (starts Postgres and the API together)

# Small official Python image: Debian with only what Python needs. Pinned to 3.12 like CI.
FROM python:3.12-slim

# Don't write .pyc files (useless in a container), and print logs immediately instead of
# buffering them, so `docker logs` shows output as it happens.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies BEFORE copying the code. Docker caches each step, so editing code
# only re-runs the steps after COPY . . and the slow pip install is reused.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the code. .dockerignore keeps .env, .venv, .git and tests out of the image.
COPY . .

# Run as an ordinary user, not root, so a bug in the app can't change the container's system files.
RUN useradd --create-home appuser
USER appuser

# Documents the port the app listens on; `ports:` in docker-compose.yml actually publishes it.
EXPOSE 8000

# 0.0.0.0 = accept connections from outside the container (127.0.0.1 would only accept
# connections from inside it). No --reload: that's for development, not a running service.
# DATABASE_URL must be given at run time as an environment variable; it is never in the image.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
