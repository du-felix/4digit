# ── Base image ───────────────────────────────────────────────────────────────
# Pin to a specific minor release so Dependabot can propose image upgrades.
FROM python:3.12-slim

# ── Environment ──────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Prevent pip from caching and reduce image size
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (security hardening) ───────────────────────────────────────
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first so this layer is cached unless deps change.
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
COPY . /app/

# Drop root privileges before running the app.
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# NOTE: manage.py runserver is for development only.
# For production, replace with gunicorn or uvicorn, e.g.:
#   CMD ["gunicorn", "fourdigit.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
