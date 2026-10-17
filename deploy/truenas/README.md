# Trove on TrueNAS SCALE

A Docker Compose deployment tuned for **TrueNAS SCALE (Electric Eel 24.10+)**,
which runs Docker natively.

## Why this compose is TrueNAS-friendly

- **Prebuilt images** from GHCR — TrueNAS pulls, it doesn't build.
- **One published port.** The frontend reverse-proxies `/api` and `/mcp` to the
  backend, so the UI, the REST API and the MCP endpoint are all on
  `http://<truenas>:30081` with no CORS and no baked API URL. Postgres and the
  API stay on the internal network. (30081 rather than 30080 so it can sit next
  to Azuregos.)
- **Data on a dataset.** Postgres (the source of truth, including uploaded
  resumes) is bind-mounted to a host dataset you can snapshot and replicate.

## 1. Create the dataset

In the TrueNAS UI: **Datasets → Add Dataset**, e.g. `tank/apps/trove` (swap
`tank` for your pool). The Postgres data lands in a `postgres` subfolder created
automatically on first run.

## 2. Configure

Every setting — **including all secrets** (`SECRET_KEY`, `POSTGRES_PASSWORD`,
`BOOTSTRAP_HEADHUNTER_PASSWORD`) — is a plain environment variable: a `.env`
file next to `docker-compose.yml` (Dockge / `docker compose`), the shell, or the
TrueNAS Custom App *Environment Variables* section.

`SECRET_KEY` is required: the stack refuses to start without it. If you leave
`BOOTSTRAP_HEADHUNTER_PASSWORD` blank, a random password is generated on first
start and printed in the backend log (`docker logs trove-backend`).

```bash
cp .env.example .env
openssl rand -hex 32        # SECRET_KEY
openssl rand -hex 16        # POSTGRES_PASSWORD
openssl rand -hex 12        # BOOTSTRAP_HEADHUNTER_PASSWORD
```

Also set `TROVE_DATA` to your dataset path, `TROVE_PORT` to the host port, and
`TROVE_PUBLIC_URL` to how people (and AI tools) will reach it.

> Changing `POSTGRES_PASSWORD` after the first run won't update an
> already-initialized database. Set it before the first `up`.

## 3. Install

**Option A — Dockge / docker compose (recommended).** Put `docker-compose.yml`
and `.env` in a folder on a dataset and run `docker compose up -d`.

**Option B — TrueNAS "Custom App".** Apps → Discover Apps → **Custom App** →
*Install via YAML*. Paste `docker-compose.yml` and either replace the `${...}`
placeholders with literal values or add the variables in the app's environment
section.

## 4. First login

Open `http://<truenas-ip>:30081` and sign in with `BOOTSTRAP_HEADHUNTER_EMAIL` and
`BOOTSTRAP_HEADHUNTER_PASSWORD` (or the generated password from the backend log). Candidates can register themselves from the
login page (turn that off with `ALLOW_CANDIDATE_REGISTRATION=false`). Create an
API key under **Settings** to connect an AI headhunter over MCP.

## 5. Backups

Snapshot (and optionally replicate) the `TROVE_DATA` dataset — it holds the full
Postgres database: accounts, search preferences, jobs and every resume.
