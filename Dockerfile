# syntax=docker/dockerfile:1

FROM node:20-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/web/dist \
    PORT=8080 \
    DATABASE_PATH=/data/app.db \
    PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY scripts/ scripts/
COPY --from=web /build/web/dist web/dist

RUN mkdir -p /data

EXPOSE 8080
CMD ["sh", "-c", "python scripts/init_db.py && uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
