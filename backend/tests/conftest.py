"""Test fixtures: the real app against a throwaway SQLite database."""
from __future__ import annotations

import asyncio
import os
import tempfile

# Must be set before the app (and its settings/engine) is imported.
_DB_DIR = tempfile.mkdtemp(prefix="trove-test-")
# TROVE_TEST_DATABASE_URL runs the suite against a real Postgres instead.
os.environ["DATABASE_URL"] = os.environ.get(
    "TROVE_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{_DB_DIR}/test.db"
)
os.environ["DB_NULL_POOL"] = "true"
os.environ["BOOTSTRAP_HEADHUNTER_EMAIL"] = "hh@example.com"
os.environ["BOOTSTRAP_HEADHUNTER_PASSWORD"] = "hunter-password"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


async def _reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client():
    asyncio.run(_reset_db())
    # Entering the context runs the lifespan: bootstraps the headhunter and
    # starts the MCP session manager.
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def hh(client) -> dict[str, str]:
    """Auth headers for the bootstrapped headhunter."""
    return login(client, "hh@example.com", "hunter-password")


@pytest.fixture
def candidate(client) -> tuple[str, dict[str, str]]:
    """A registered candidate: (id, auth headers)."""
    resp = client.post(
        "/api/auth/register",
        json={"email": "cand@example.com", "password": "candidate-pw", "display_name": "Cand"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["user"]["id"], {"Authorization": f"Bearer {body['access_token']}"}
