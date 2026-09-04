# ================================
# Stage 1: Build dependencies
# ================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY backend/requirements.txt .

RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt


# ================================
# Stage 2: Production image
# ================================
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install only runtime dependencies
COPY --from=builder /install /usr/local

# Copy application
COPY backend/app ./backend/app

# Create persistent data directory
RUN mkdir -p /app/data && \
    useradd --create-home --shell /usr/sbin/nologin appuser && \
    chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 8000

# Container health check
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=10s \
            --retries=3 \
            CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]