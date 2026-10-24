# Trove

A centralized job-search portal shared by **candidates** and the **headhunters**
working for them. A headhunter is usually an AI tool (Claude, ChatGPT, …) talking
to Trove over **MCP** or the **REST API**, but people can do everything from the
web UI too.

- **Candidates** upload one detailed *base* resume, say what they're looking for
  (titles, categories, employment types, locations, work arrangement, salary
  range), and track every job the headhunter finds through to an offer.
- **Headhunters** read those preferences, download the base resume, post
  matching jobs with a 1–5 fit score, and attach a resume rewritten for each
  specific posting.

The UI is built for phones first: bottom tab bar, large touch targets, and no
zooming into form fields.

## Concepts

| Thing | What it holds |
|---|---|
| **Candidate profile** | Headline, desired titles, job categories, employment types, locations, work modes (on-site / hybrid / remote), relocation, salary min/max + currency + period, free-form notes |
| **Base resume** | One file per candidate (PDF, DOCX, DOC, ODT, RTF, TXT, MD or HTML). Text is extracted on upload so AI tools can read it |
| **Job** | Role name / job title, company, apply link, status, job category, employment type, location, work mode, compensation, date found, shift / schedule, job-fit score (1–5), notes |
| **Optimized resume** | One file per job: the base resume tailored to that posting |

**Job status** covers both sides: candidates track `new → interested → applied →
interviewing → offer` (or `rejected` / `not_interested`), and headhunters mark
postings `expired` or `unavailable` when they close.

## Personas & permissions

- **Candidate** — sees only their own profile, resume and jobs. On a job they can
  change the **status** and **notes**, open the apply link and download the
  tailored resume. Candidates can register themselves
  (`ALLOW_CANDIDATE_REGISTRATION`), or a headhunter can add them.
- **Headhunter** — sees and acts for **every** candidate: posts, edits and
  deletes jobs, uploads optimized resumes, manages accounts and API keys. The
  first headhunter is created on startup from `BOOTSTRAP_HEADHUNTER_*`.

Anyone can also **sign in with Google** once it is configured (see
[Google sign-in](#google-sign-in)).

## Connecting an AI headhunter (MCP)

1. Sign in as a headhunter, open **Settings → API keys**, and create a key
   (shown once; Trove stores only a hash).
2. Point your MCP client at `https://<your-trove>/mcp` (streamable HTTP) with the
   header `Authorization: Bearer <key>`. For example, in Claude Code:

   ```bash
   claude mcp add --transport http trove https://trove.example.com/mcp \
     --header "Authorization: Bearer trove_…"
   ```

   or in a JSON MCP config:

   ```json
   { "mcpServers": { "trove": {
       "type": "http", "url": "https://trove.example.com/mcp",
       "headers": { "Authorization": "Bearer trove_…" } } } }
   ```

### MCP tools

Each tool calls the same code as the REST operation with the same `operationId`,
so behaviour and permissions are identical. Full schemas:
[`docs/mcp-tools.json`](docs/mcp-tools.json).

| Tool | REST twin | Purpose |
|---|---|---|
| `whoami` | `GET /api/auth/me` | The authenticated headhunter |
| `list_candidates` | `GET /api/candidates` | Candidates with resume status and job counts |
| `get_candidate` | `GET /api/candidates/{id}` | Search preferences + base-resume metadata |
| `get_base_resume` | `GET /api/candidates/{id}/resume/content` | Base resume as text (optionally the file as base64) |
| `get_job_options` | `GET /api/jobs/options` | Allowed statuses / employment types / work modes, categories in use |
| `list_jobs` | `GET /api/jobs` | Jobs, filterable by candidate, status and search text |
| `get_job` | `GET /api/jobs/{id}` | One job |
| `create_job` | `POST /api/jobs` | Post a job for a candidate (rejects a duplicate apply link) |
| `update_job` | `PATCH /api/jobs/{id}` | Change any field, e.g. mark it `expired` |
| `upload_optimized_resume` | `PUT /api/jobs/{id}/resume/content` | Attach the tailored resume (Markdown text or base64 file) |
| `get_optimized_resume` | `GET /api/jobs/{id}/resume/content` | Read it back |

The server also sends instructions describing the intended workflow: read
preferences and the base resume, find matching openings, `create_job` with a fit
score and reasoning, then upload a tailored resume for each.

## REST API

Interactive docs at `/docs` (Swagger UI) and `/redoc`; the spec at
`/openapi.json`. The same spec is committed at
[`docs/openapi.json`](docs/openapi.json) and attached to every GitHub release.

- Auth: `Authorization: Bearer <token>` — a session token from
  `POST /api/auth/login`, or a headhunter API key.
- `me` works anywhere a `candidate_id` is expected.
- Resume uploads are `multipart/form-data` (`file` field) on
  `PUT /api/candidates/{id}/resume` and `PUT /api/jobs/{id}/resume`; downloads
  are `GET` on the same paths. `PUT /api/jobs/{id}/resume/content` takes JSON
  (`content_text` or `content_base64`) instead.

```bash
TROVE=https://trove.example.com KEY=trove_…
# Read a candidate's preferences and resume text
curl -H "Authorization: Bearer $KEY" $TROVE/api/candidates
curl -H "Authorization: Bearer $KEY" $TROVE/api/candidates/<id>/resume/content
# Post a job
curl -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' $TROVE/api/jobs -d '{
  "candidate_id": "<id>", "title": "Staff SRE", "company": "Globex",
  "apply_url": "https://jobs.example.com/123", "employment_type": "permanent",
  "location": "Denver, CO", "work_mode": "hybrid", "compensation": "$180k-$210k",
  "fit_score": 4, "notes": "Strong Kubernetes overlap; on-call is 1 week in 6."}'
# Attach a tailored resume
curl -H "Authorization: Bearer $KEY" -X PUT -F file=@tailored.pdf $TROVE/api/jobs/<job-id>/resume
```

## Architecture

```
            ┌──────────── browser (React SPA) ───────────┐
            │                                             │
 AI tool ──►│  nginx (frontend image)                     │
  (MCP /    │   /           → SPA                         │
   REST)    │   /api, /mcp, /docs, /openapi.json ─┐      │
            └─────────────────────────────────────┼──────┘
                                                  ▼
                               FastAPI (backend image)
                               ├─ REST  /api/*   ─┐
                               └─ MCP   /mcp     ─┴─► services ─► Postgres
                                                     (one code path)   (incl. resume files)
```

- **backend** — FastAPI, SQLAlchemy 2 (async), Alembic, the official `mcp`
  Python SDK (stateless streamable HTTP, so it scales horizontally).
- **frontend** — React + Vite + TypeScript, served by nginx, which also proxies
  the API and MCP paths so everything is same-origin.
- **Postgres** — the only stateful piece; resumes are stored in it, so there is
  no file volume to manage or back up separately.

## Quick start (Docker)

```bash
make up          # copies .env.example to .env if missing, then docker compose up --build
```

Open http://localhost:8080 and sign in as `headhunter@example.com` /
`change-me-please` (from `.env`), or register a candidate account. The API is
also on http://localhost:8000 (`/docs`).

`docker compose -f docker-compose.yml up --build` runs the production images
without the dev override (hot reload).

## Local development without Docker

```bash
# Postgres somewhere reachable, then:
cd backend
pip install ".[dev]"
export POSTGRES_HOST=localhost
alembic upgrade head
uvicorn app.main:app --reload            # http://localhost:8000

cd ../frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev   # http://localhost:5173
```

## Testing

```bash
cd backend
ruff check .
pytest -q                                   # runs on SQLite, no services needed
TROVE_TEST_DATABASE_URL=postgresql+asyncpg://trove:trove@localhost:5432/trove pytest -q

cd ../frontend
npm run build && npm test
```

The backend suite drives the real app end to end, including an MCP session that
plays the AI-headhunter workflow.

## Configuration

All settings are environment variables; see [`.env.example`](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `change-me` | Signs session tokens. **Set a long random value**; with `TROVE_ENV=production` the backend refuses to start on a placeholder. |
| `POSTGRES_*` / `DATABASE_URL` | `trove` / derived | Database connection |
| `CORS_ORIGINS` | `http://localhost:5173` | Browser origins allowed to call the API cross-origin |
| `TROVE_PUBLIC_URL` | `http://localhost:8080` | Public URL, shown in Settings for MCP/API setup |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Web session lifetime (API keys don't expire; revoke them) |
| `ALLOW_CANDIDATE_REGISTRATION` | `true` | Show self-service sign-up for candidates |
| `BOOTSTRAP_HEADHUNTER_EMAIL` / `_PASSWORD` | `headhunter@example.com` / generated | First headhunter, created if missing. With no password set, a random one is printed in the backend log on first start. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | empty | Google OAuth client. Google sign-in is **off** unless both are set. |
| `GOOGLE_REDIRECT_URI` | `$TROVE_PUBLIC_URL/auth/google/callback` | Override only if Trove is reached on a different URL than `TROVE_PUBLIC_URL` |
| `MAX_UPLOAD_MB` | `10` | Resume size limit |

## Google sign-in

With a Google OAuth client configured, the sign-in and sign-up pages show
**Sign in with Google**, and every user gets a **Google sign-in** card (Profile
for candidates, Settings for headhunters) to link or unlink their Google account.

How accounts are matched:

- A Google account that is **linked** signs straight into its Trove account
  (candidate or headhunter).
- A Google account that is **not linked** and whose email is **new** to Trove
  creates a candidate account, if `ALLOW_CANDIDATE_REGISTRATION` is on and
  Google has verified the email. These accounts have no password.
- If the Google email **already belongs** to a Trove account, sign-in is
  refused: the owner signs in with their password once and links Google from
  Profile/Settings. Trove never merges accounts by email alone, so an existing
  account can't be taken over through a Google account with the same address.
- Unlinking requires a password, so nobody locks themselves out. A headhunter
  can set one for a Google-only user from Settings → People.

### Setting up the Google Cloud OAuth client

1. In the [Google Cloud console](https://console.cloud.google.com/), create or
   pick a project.
2. **Google Auth Platform → Branding** (formerly *OAuth consent screen*): set
   the app name (e.g. Trove), support email and, under *Authorized domains*,
   your Trove domain (e.g. `example.com`).
3. **Audience**: choose *External* (any Google account) or *Internal* (only
   your Google Workspace). An External app in *Testing* only lets listed test
   users sign in; click **Publish app** to open it up. Trove only asks for the
   `openid`, `email` and `profile` scopes, which need no Google verification.
4. **Clients → Create client** → *Web application*:
   - *Authorized JavaScript origins*: your public URL, e.g.
     `https://trove.example.com`.
   - *Authorized redirect URIs*: `https://trove.example.com/auth/google/callback`
     (the `TROVE_PUBLIC_URL` plus `/auth/google/callback`, exactly).
5. Copy the **Client ID** and **Client secret** into `GOOGLE_CLIENT_ID` and
   `GOOGLE_CLIENT_SECRET` and restart the backend. The login page picks the
   change up automatically.

Google only accepts `https://` redirect URIs on a public domain, plus
`http://localhost` for development. A LAN URL such as
`http://truenas.local:30081` won't work; put Trove behind HTTPS on a real
domain (a reverse proxy or tunnel) to use Google sign-in there. For local
development add `http://localhost:8080/auth/google/callback` (Docker) or
`http://localhost:5173/auth/google/callback` (Vite, with
`TROVE_PUBLIC_URL=http://localhost:5173`).

Under the hood this is the OpenID Connect authorization-code flow with PKCE,
handled by the backend (`app/services/google_auth.py`) so the client secret
never reaches the browser. The flow is stateless (a signed, 10-minute `state`),
so it works with any number of backend replicas.

## Deploying to TrueNAS SCALE

[`deploy/truenas/`](deploy/truenas/) has a compose file that uses the published
GHCR images, publishes a single port (30081) for the UI, API and MCP endpoint,
and keeps Postgres on a host dataset for snapshots. See
[deploy/truenas/README.md](deploy/truenas/README.md).

## Deploying to Kubernetes

The Helm chart in `charts/trove` deploys the backend (with an
`alembic upgrade head` init container), the frontend, Postgres (StatefulSet +
PVC) and an Ingress that sends `/api`, `/mcp`, `/docs`, `/redoc` and
`/openapi.json` to the backend and everything else to the SPA. Every release
publishes it to GHCR with the same version as the images:

```bash
kubectl create namespace trove
kubectl -n trove create secret generic trove-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=BOOTSTRAP_HEADHUNTER_PASSWORD="$(openssl rand -hex 12)"
  # optional, enables Google sign-in together with config.GOOGLE_CLIENT_ID:
  # --from-literal=GOOGLE_CLIENT_SECRET=...

helm install trove oci://ghcr.io/zollo/charts/trove -n trove \
  --set existingSecret=trove-secrets \
  --set ingress.enabled=true --set ingress.hosts[0]=trove.example.com \
  --set config.CORS_ORIGINS=https://trove.example.com \
  --set config.TROVE_PUBLIC_URL=https://trove.example.com
  # --set config.GOOGLE_CLIENT_ID=1234-abc.apps.googleusercontent.com
```

See `charts/trove/values.yaml` for external Postgres, resources, and
`postgresql.backup` (a nightly `pg_dump` CronJob to its own PVC).

## CI / releases

`.github/workflows/ci.yml` runs on every PR and every push to `main`:

1. **backend** — ruff, pytest (SQLite), and a check that `docs/openapi.json` and
   `docs/mcp-tools.json` match the code
2. **backend-postgres** — `alembic upgrade head`, `alembic check`, pytest on Postgres
3. **frontend** — type-check, build, vitest
4. **smoke** — boots the whole compose stack and checks health, the nginx
   proxy, `/openapi.json`, and that `/mcp` refuses anonymous callers
5. **chart-lint** — `helm lint` + `helm template`

On a **merge to `main`** (after the above pass):

6. **version** — computes the next **semantic version** from the squash commit
   (Conventional Commits: `feat:` → minor, `fix:` → patch, `!` / `BREAKING
   CHANGE` → major; default patch; first release is `v1.0.0`), tags it and
   creates a GitHub release. PR titles drive this (see
   [CONTRIBUTING.md](CONTRIBUTING.md)).
7. **api-spec** — attaches `trove-openapi-X.Y.Z.json` and
   `trove-mcp-tools-X.Y.Z.json` to the release.
8. **images** — builds `ghcr.io/zollo/trove-backend` and `-frontend` tagged
   `latest`, `X.Y.Z`, `X.Y`, `sha-<short>`, signs them with cosign (keyless) and
   pushes build-provenance attestations.
9. **chart** — packages the Helm chart at the release version and pushes it to
   `oci://ghcr.io/zollo/charts/trove`.

### Verifying an image

```bash
IMAGE=ghcr.io/zollo/trove-backend:latest
cosign verify "$IMAGE" \
  --certificate-identity-regexp "https://github.com/zollo/trove/.github/workflows/ci.yml@.*" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
gh attestation verify "oci://$IMAGE" --repo zollo/trove
```

## Project layout

```
backend/            FastAPI app + MCP server, Alembic migrations
  app/
    api/routes/      auth, users, api-keys, candidates, jobs, health
    core/            security (JWT, passwords, API keys), errors, resume text extraction
    models/          SQLAlchemy models
    schemas/         Pydantic schemas
    services/        candidate, job, document and user services (shared by REST + MCP)
    mcp_server.py    MCP tools at /mcp
    openapi_export.py writes docs/openapi.json + docs/mcp-tools.json
    migrations/      Alembic
frontend/           React + Vite SPA (mobile-first)
  src/
    api/             typed fetch client (JSON, uploads, downloads)
    components/      layout + tab bar, job list, file box, chip inputs
    pages/           candidate pages; headhunter/* pages
charts/trove/       Helm chart (published to oci://ghcr.io/zollo/charts/trove)
deploy/truenas/     TrueNAS SCALE compose
docs/               Published API contract (OpenAPI spec, MCP tool definitions)
```

## License

Provided as-is for personal use. Add a license here if you share it.
