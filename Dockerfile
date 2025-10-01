FROM python:3.11-alpine AS builder

# Aggiorna sistema e installa dipendenze di sistema necessarie
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    jpeg-dev \
    zlib-dev \
    libmagic

WORKDIR /app
RUN python3 -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt --no-cache-dir

FROM python:3.11-alpine AS runner

# Aggiorna sistema e installa runtime dependencies
RUN apk update && apk add --no-cache \
    libpq \
    libmagic \
    jpeg \
    zlib

WORKDIR /app
COPY --from=builder /app/venv venv
COPY app/ ./app/
COPY alembic.ini .
COPY migrations/ ./migrations/
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn --host 0.0.0.0 app.main:app"] 