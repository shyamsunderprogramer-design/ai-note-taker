FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements-cloud.txt /app/requirements-cloud.txt
RUN pip install --no-cache-dir -r /app/requirements-cloud.txt

# Copy backend code
COPY backend/ /app/backend/

# Create all data directories the app needs at runtime
# Single source of truth: /app/backend/data/ — all persistent state lives here.
# These dirs hold user data, generated audio, logs, etc. They are VOLUMEs in
# production so they survive container restarts. Do NOT add /app/backend/core/data/
# — that path was a legacy duplicate and has been removed.
RUN mkdir -p /app/backend/data \
            /app/backend/data/temp_audio \
            /app/backend/data/voice_models \
            /app/backend/data/conversations \
            /app/backend/data/audit_logs \
            /app/backend/data/user_keys \
            /app/backend/data/meeting_templates \
            /app/backend/security/data \
            /app/backend/modules/ai/data \
            /app/backend/modules/ai/embeddings \
            /app/backend/modules/crm/data \
            /app/backend/modules/platform/data \
            /app/backend/modules/platform/data/documents \
            /app/backend/modules/platform/data/vectors

# Mark persistent directories as volumes so they aren't baked into image layers
# (and can be mounted to host storage in production)
VOLUME ["/app/backend/data", "/app/backend/modules/platform/data/documents", "/app/backend/modules/platform/data/vectors"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the app with memory optimization for cloud (512MB RAM limit)
ENV CLOUD_MODE=true
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app/backend
CMD uvicorn core.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log