# ── Base image ───────────────────────────────────────────────────────────────
FROM python:3.14-slim

# ── Environment ──────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    fonts-dejavu-core \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (security hardening) ───────────────────────────────────────
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
COPY . /app/

# ── Static files (collected at build time; served by WhiteNoise at runtime) ──
RUN DEBUG=True SECRET_KEY=build-time-dummy-key-not-used-in-production \
    python manage.py collectstatic --noinput

# ── Entrypoint: waits for DB, runs migrations, then starts gunicorn ───────────
RUN chmod +x /app/entrypoint.sh

# Drop root privileges before running the app.
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "fourdigit.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
