"""Magic login links: headhunter-generated, candidate-only, single use, 24 hours."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.db import AsyncSessionLocal as SessionLocal
from app.models.login_link import LoginLink


def _hh_id(client, hh) -> str:
    return client.get("/api/auth/me", headers=hh).json()["id"]


def test_link_signs_in_once(client, hh, candidate):
    cand_id, _ = candidate
    resp = client.post(f"/api/users/{cand_id}/login-links", headers=hh)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    token = created["token"]
    assert created["url"].endswith(f"/auth/link#{token}")
    expires = datetime.fromisoformat(created["expires_at"].replace("Z", "+00:00"))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    assert timedelta(hours=23, minutes=59) < expires - datetime.now(UTC) <= timedelta(hours=24)

    listed = client.get(f"/api/users/{cand_id}/login-links", headers=hh).json()
    assert [link["id"] for link in listed] == [created["id"]]
    assert "token" not in listed[0]

    first = client.post("/api/auth/login-link", json={"token": token})
    assert first.status_code == 200, first.text
    session = {"Authorization": f"Bearer {first.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=session).json()["id"] == cand_id

    again = client.post("/api/auth/login-link", json={"token": token})
    assert again.status_code == 401
    assert client.get(f"/api/users/{cand_id}/login-links", headers=hh).json() == []


def test_only_the_hash_is_stored(client, hh, candidate):
    cand_id, _ = candidate
    token = client.post(f"/api/users/{cand_id}/login-links", headers=hh).json()["token"]

    async def stored() -> list[str]:
        async with SessionLocal() as db:
            return list((await db.execute(select(LoginLink.token_hash))).scalars())

    hashes = asyncio.run(stored())
    assert len(hashes) == 1 and token not in hashes[0]


def test_expired_link_is_rejected(client, hh, candidate):
    cand_id, _ = candidate
    token = client.post(f"/api/users/{cand_id}/login-links", headers=hh).json()["token"]

    async def expire() -> None:
        async with SessionLocal() as db:
            past = datetime.now(UTC) - timedelta(seconds=1)
            await db.execute(update(LoginLink).values(expires_at=past))
            await db.commit()

    asyncio.run(expire())
    assert client.post("/api/auth/login-link", json={"token": token}).status_code == 401
    assert client.get(f"/api/users/{cand_id}/login-links", headers=hh).json() == []


def test_concurrent_redemptions_only_one_wins(client, hh, candidate):
    cand_id, _ = candidate
    token = client.post(f"/api/users/{cand_id}/login-links", headers=hh).json()["token"]
    with ThreadPoolExecutor(4) as pool:
        codes = list(
            pool.map(
                lambda _: client.post("/api/auth/login-link", json={"token": token}).status_code,
                range(4),
            )
        )
    assert sorted(codes) == [200, 401, 401, 401]


def test_revoke_and_permissions(client, hh, candidate):
    cand_id, cand_headers = candidate
    # Candidates can't mint links, not even for themselves.
    assert client.post(f"/api/users/{cand_id}/login-links", headers=cand_headers).status_code == 403
    # Headhunter accounts never get links.
    resp = client.post(f"/api/users/{_hh_id(client, hh)}/login-links", headers=hh)
    assert resp.status_code == 422

    token = client.post(f"/api/users/{cand_id}/login-links", headers=hh).json()["token"]
    assert client.delete(f"/api/users/{cand_id}/login-links", headers=hh).status_code == 204
    assert client.post("/api/auth/login-link", json={"token": token}).status_code == 401
    assert client.post("/api/auth/login-link", json={"token": "x" * 43}).status_code == 401


def test_deactivated_candidate_cannot_use_link(client, hh, candidate):
    cand_id, _ = candidate
    token = client.post(f"/api/users/{cand_id}/login-links", headers=hh).json()["token"]
    client.patch(f"/api/users/{cand_id}", json={"is_active": False}, headers=hh)
    assert client.post("/api/auth/login-link", json={"token": token}).status_code == 401
    assert client.post(f"/api/users/{cand_id}/login-links", headers=hh).status_code == 422
