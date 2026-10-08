FROM node:24-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
ARG VITE_API_BASE_URL=/api
ARG VITE_STREAMLIT_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_STREAMLIT_URL=${VITE_STREAMLIT_URL}
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY alembic.ini ./
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

RUN mkdir -p /data

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
