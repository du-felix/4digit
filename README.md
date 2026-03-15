# 4digit

## Deployment with Podman (2 containers)

This repository is set up for a 2-service deployment:

1. `sql` (MySQL 8.4)
2. `backend` (Django + Gunicorn)

### 1. Prepare environment file

```bash
cp .env.example .env
```

Then edit `.env` and set secure values, especially:

1. `SECRET_KEY`
2. `DB_PASSWORD`
3. `DB_ROOT_PASSWORD`
4. `ALLOWED_HOSTS`
5. `CSRF_TRUSTED_ORIGINS`

### 2. Build and start containers

```bash
podman compose up -d --build
```

Backend is exposed on `http://<server>:10200`.

### 3. Check service status

```bash
podman compose ps
podman compose logs -f backend
```

The backend container runs migrations automatically on startup via `entrypoint.sh`.

### 4. Update deployment after `git pull`

```bash
git pull
podman compose up -d --build
```

### 5. Stop deployment

```bash
podman compose down
```

To also delete DB data volume:

```bash
podman compose down -v
```
