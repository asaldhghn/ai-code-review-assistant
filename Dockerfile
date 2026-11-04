# Public-demo image: builds the UI, then serves UI + API from one FastAPI process.
# Live AI reviews are DISABLED by default here, so a hosted copy can never spend money.
FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENABLE_LIVE_REVIEW=false \
    FRONTEND_DIST=/app/static
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/code_review ./code_review
COPY --from=ui /ui/dist ./static
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn code_review.api:app_factory --factory --host 0.0.0.0 --port ${PORT:-8000}"]
