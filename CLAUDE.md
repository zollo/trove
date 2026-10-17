# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Trove is a job-search portal. **Candidates** upload a detailed base resume and their search preferences; **headhunters** (people in the web UI, or AI tools over the REST API / MCP) post job openings for them, score the fit 1–5, and attach a resume optimized for each posting. Candidates track their applications through each job's status.

## Commands

Full stack (Docker; `docker-compose.override.yml` is auto-merged for hot reload):
```bash
make up                      # creates .env from .env.example if missing, then compose up --build
docker compose -f docker-compose.yml up --build   # prod-like, no dev override
```

Backend (`cd backend`):
```bash
pip install ".[dev]"
ruff check .
pytest -q                                        # SQLite; no services needed
TROVE_TEST_DATABASE_URL=postgresql+asyncpg://trove:trove@localhost:5432/trove pytest -q   # same suite on Postgres
pytest tests/test_mcp.py::test_mcp_headhunter_workflow
alembic upgrade head && alembic check            # migrations apply and match the models
python -m app.openapi_export ../docs/openapi.json --mcp-tools ../docs/mcp-tools.json   # or `make openapi`
uvicorn app.main:app --reload
```

Frontend (`cd frontend`):
```bash
npm install
npm run dev          # Vite on :5173; set VITE_API_BASE_URL=http://localhost:8000
npm run build        # tsc (strict, noUnused*) + vite build
npm test             # vitest
```

## Architecture

**Services:** `backend` (FastAPI: REST at `/api`, MCP at `/mcp`), `frontend` (React/Vite SPA served by nginx), Postgres. No queue/worker: everything is request/response.

**One service layer, two interfaces.** `app/services/*` hold all logic and permission checks and raise `core/errors.TroveError` subclasses. REST routes (`app/api/routes/*`) map those to HTTP via an exception handler in `main.py`; MCP tools (`app/mcp_server.py`) turn them into tool errors. Every MCP tool name equals the `operationId` of its REST twin — `tests/test_app_smoke.py` enforces it — and `docs/openapi.json` + `docs/mcp-tools.json` are the published contract (CI fails if stale; `make openapi`).

**Permissions:** two roles. Headhunters see and act for **every** candidate (no assignment table). Candidates see only their own data; on their jobs they may change only `status` and `notes` (`job_service.CANDIDATE_EDITABLE`). Anywhere a `candidate_id` is accepted, `me` means the caller (`candidate_service.resolve_candidate`).

**Auth:** `Authorization: Bearer` with either a session JWT (`/api/auth/login`, stored in localStorage by the SPA) or a headhunter API key (`trove_…`, SHA-256 hashed in `api_keys`, shown once). `user_service.resolve_token` handles both. Candidates can self-register (`ALLOW_CANDIDATE_REGISTRATION`); a bootstrap headhunter is created on startup from `BOOTSTRAP_HEADHUNTER_*`; headhunters add other accounts in Settings.

**MCP** (`app/mcp_server.py`): official `mcp` SDK v2 (`MCPServer`, the renamed FastMCP), **stateless** streamable HTTP with JSON responses so any replica can serve any request. `MCPEndpoint` is a plain Starlette route (kept out of OpenAPI) that rejects non-headhunter bearer tokens with 401 before the SDK sees the request; tools re-resolve the caller from `ctx.headers`. The SDK's session manager can only `run()` once, so a fresh `streamable_http_app()` is built inside each app lifespan. DNS-rebinding protection is off because bearer auth is mandatory.

**Resumes** (`models/document.py`, `services/document_service.py`): bytes live in Postgres (`documents.data`, deferred column) so the API is stateless — no shared volume. One `base_resume` per candidate; one `optimized_resume` per job (`job_id` unique). Text is extracted on upload (`core/resume_text.py`: PDF via pypdf, DOCX via python-docx, TXT/MD/HTML) so AI tools can read and rewrite it. JSON uploads (`content_text` → saved as `.md`, or `content_base64`) exist for AI clients; the UI uses multipart.

**Enums** are stored as VARCHAR (`models/base.str_enum`, `native_enum=False`), so adding a status or employment type needs no migration — just update the enum and the frontend's `lib/format.ts` labels.

**Frontend ↔ API is same-origin:** the SPA calls relative `/api`; nginx proxies `/api`, `/mcp` (unbuffered), `/docs`, `/redoc`, `/openapi.json` to `backend:8000` via Docker's resolver so nginx boots even when the backend is down. In k8s the ingress routes those paths to the backend instead. Mobile-first CSS: a bottom tab bar under 760px, 44px touch targets, 16px inputs (prevents iOS zoom).

**Build info:** `APP_VERSION`/`GIT_COMMIT`/`BUILD_TIME` build-args are baked into both images (backend `TROVE_*` env, frontend `VITE_*`), surfaced by `GET /api/build-info` and the About page. Keep these ARGs late in the Dockerfiles.

## Gotchas

- **Tests** run the real app on SQLite with `NullPool` (`DB_NULL_POOL`): async DB connections are bound to the loop that opened them, and `TestClient` runs the app on its own loop. Set `TROVE_TEST_DATABASE_URL` to run the same suite on Postgres (CI does).
- After `commit()`, `await db.refresh(obj)` before returning ORM rows: `updated_at` is server-side and would otherwise lazy-load outside the async greenlet.
- Don't annotate 204 routes with `-> None`; return `Response(status_code=204)`.
- bcrypt ≥ 5 raises on passwords > 72 bytes; `core/security.py` truncates explicitly.
- SQLAlchemy relationship forward refs stay quoted with `TYPE_CHECKING` imports; ruff `UP037` is intentionally ignored.
- **TypeScript:** import `type FormEvent` / `type ReactNode` from `react`; don't use the `React.*` namespace.
- **Healthchecks:** frontend checks must hit `127.0.0.1`, not `localhost` (busybox wget tries `::1`; nginx listens IPv4-only).

## CI, releases & conventions

`.github/workflows/ci.yml`: backend (ruff, pytest on SQLite, `docs/` drift check), backend-postgres (migrations + `alembic check` + pytest on Postgres), frontend (build + vitest), smoke (base compose boots the whole stack; checks health, the nginx proxy, `/openapi.json`, and that `/mcp` rejects anonymous calls), chart-lint. **Only on push to `main`:** `version` computes the next semver (seeded at `v1.0.0`; `mathieudutour/github-tag-action` thereafter) and creates a GitHub release; `api-spec` attaches the versioned OpenAPI spec and MCP tool list; `images` builds both images tagged `latest`/`X.Y.Z`/`X.Y`/`sha-<short>`, signs them with cosign and attests provenance; `chart` publishes the Helm chart.

The repo is **squash-merge only**, with the squash commit title = PR title. The PR title drives the version bump and must be a Conventional Commit (enforced by `.github/workflows/pr-title.yml`): `feat:` → minor, `fix:`/other types → patch, `!` or a `BREAKING CHANGE` footer → major. See `CONTRIBUTING.md`.

## Deployments

- `docker-compose.yml` (+ dev override) — local/dev; builds images from source.
- `deploy/truenas/` — TrueNAS SCALE compose using the published GHCR images; only the frontend port (default 30081) is published.
- `charts/trove/` — Helm chart, published by CI to `oci://ghcr.io/zollo/charts/trove` (version = release). The backend runs `alembic upgrade head` in an init container and can scale horizontally.
- Documentation lives in this repo (README, this file, `docs/`).
