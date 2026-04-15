# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Django 5.2 app ("4digit" / Fourdigit) for managing *Freistellungsanträge* (student leave-of-absence requests) at Landesgymnasium Sankt Afra. German-language domain: students submit an Antrag, teachers/mentors/principal/secretariat respond via tokenized email links, secretariat confirms parent approval where required.

## Commands

Local dev uses SQLite (auto when `DEBUG=True`); production uses MySQL (configured via `.env`).

```bash
# Local dev server (SQLite)
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests — whole suite / single app / single test
python manage.py test
python manage.py test antraege
python manage.py test antraege.test_workflow.WorkflowTests.test_name

# Static files (collected at image build; usually not needed locally)
python manage.py collectstatic --noinput
```

Deployment is Podman Compose (`sql` MySQL 8.4 + `backend` Django/Gunicorn). `entrypoint.sh` waits for the DB and runs `migrate` automatically on container start. Backend is exposed on port 10200; see README.md.

## Architecture

Three Django apps under project `fourdigit/`:

- **`antraege/`** — core domain. Models: `Antrag` (the request), `Anfrage` (per-teacher sub-request tied to one Antrag), `Lehrer` (teacher, with `principal` / `secretariat` / `is_im` / `is_gm` flags), `Fach` (subject), `Zaehler` (per-student/teacher/subject counter), `AntragSubmission`. URL root `/`.
- **`users/`** — custom `AUTH_USER_MODEL = users.CustomUser` (extends `AbstractUser`); `save()` forces `username = email`. URL root `/users/`.
- **`adminview/`** — admin-facing dashboard (separate from Django admin). URL root `/adminview/`.

### Approval workflow (critical)

State transitions live in **`antraege/workflow.py`** and MUST go through `transition_antrag` / `transition_anfrage`. The `ALLOWED_TRANSITIONS` maps enforce a forward-only flow:
- `Antrag.status`: `in_progress → accepted | declined` (terminal).
- `Anfrage.response`: `not_responded → accepted | declined` (terminal).

Do not mutate `status`/`response` directly — use the transition helpers so `responded_at` and `update_fields` stay consistent. `all_requests_responded(antrag)` is how views check whether the Antrag can be finalized.

### Token-based approval links

Teachers/principal/secretariat approve via emailed URL (`antrag_bestaetigen/<token>/`). Tokens are stored on `Anfrage.token` and expire after `ANFRAGE_TOKEN_MAX_AGE_SECONDS` (default 7 days, env-overridable). Token generation/validation is in `antraege/tokens.py`. Which form a link shows is role-driven by the `Anfrage` flags (`is_principle`, `is_secretariat`, `gm_boolean`, `im_boolean`) — see recent commits for precedents.

### Email

`antraege/mailer.py` exposes `send_mail_logged`; all outbound mail flows through it and is logged to the `emails/` directory (one `.log` file per message). Message composition lives in `antraege/functions.py` (`send_email`, `send_email_gm`, `send_email_im`, `send_email_schulleiter`, `send_email_sekretariat`, `send_eltern_bestaetigung`, plus student notifications). SMTP is configured by `EMAIL_*` env vars.

### Settings notes

- `FORCE_SCRIPT_NAME` defaults to `/freistellung` in production (the app is mounted under a subpath; root domain belongs to a separate service). `STATIC_URL` is derived from it — keep this in mind when adding URLs.
- In production, HSTS + secure-cookie hardening is enabled; DEBUG disables all of it so local dev works.
- Upload/field caps are tightened in `settings.py` (CWE-770 mitigation): `DATA_UPLOAD_MAX_MEMORY_SIZE = 2 MB`, `DATA_UPLOAD_MAX_NUMBER_FIELDS = 200`. Don't relax these without reason.
- `django.request` logger is ERROR-only on purpose — URLs may contain approval tokens that must not leak into logs.
