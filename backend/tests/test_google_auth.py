"""Google sign-in and account linking, with Google's token endpoint faked."""
from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest

from app.config import settings
from app.services import google_auth


@pytest.fixture
def google(monkeypatch):
    """Enable Google sign-in; `google[code] = claims` defines what each code redeems to."""
    monkeypatch.setattr(settings, "google_client_id", "client-123.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "shh")
    codes: dict[str, dict] = {}

    async def fake_exchange(code: str, verifier: str) -> dict:
        if code not in codes:
            raise google_auth.Invalid("Google rejected the sign-in; try again")
        return codes[code]

    monkeypatch.setattr(google_auth, "exchange_code", fake_exchange)
    return codes


def _start(client, intent="login", headers=None) -> tuple[dict, str]:
    """Begin a flow; returns (callback payload minus code, nonce sent to Google)."""
    resp = client.post("/api/auth/google/authorize", json={"intent": intent}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    query = parse_qs(urlparse(body["authorization_url"]).query)
    assert query["redirect_uri"] == ["http://localhost:8080/auth/google/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [body["state"]]
    return {"state": body["state"], "code_verifier": body["code_verifier"]}, query["nonce"][0]


def _identity(nonce, sub="g-1", email="gina@gmail.com", verified=True, name="Gina"):
    return {"sub": sub, "email": email, "email_verified": verified, "name": name, "nonce": nonce}


def test_disabled_by_default(client):
    assert client.get("/api/auth/config").json()["google_enabled"] is False
    resp = client.post("/api/auth/google/authorize", json={"intent": "login"})
    assert resp.status_code == 404


def test_sign_up_then_sign_in(client, google):
    assert client.get("/api/auth/config").json()["google_enabled"] is True

    payload, nonce = _start(client)
    google["c1"] = _identity(nonce)
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c1"})
    assert resp.status_code == 200, resp.text
    user = resp.json()["user"]
    assert user["role"] == "candidate"
    assert user["email"] == "gina@gmail.com"
    assert user["google_email"] == "gina@gmail.com"
    assert user["has_password"] is False
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    assert client.get("/api/candidates/me", headers=headers).status_code == 200

    # Second sign-in finds the same account.
    payload, nonce = _start(client)
    google["c2"] = _identity(nonce)
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c2"})
    assert resp.json()["user"]["id"] == user["id"]

    # A Google-only account can't unlink (it would be locked out).
    resp = client.delete("/api/auth/google/link", headers=headers)
    assert resp.status_code == 422


def test_existing_email_must_link_explicitly(client, google, candidate):
    payload, nonce = _start(client)
    google["c"] = _identity(nonce, email="cand@example.com")
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c"})
    assert resp.status_code == 409
    assert "link Google" in resp.json()["detail"]


def test_link_and_unlink(client, google, hh):
    payload, nonce = _start(client, "link", hh)
    google["c"] = _identity(nonce, sub="g-hh", email="boss@gmail.com")
    resp = client.post("/api/auth/google/link", json={**payload, "code": "c"}, headers=hh)
    assert resp.status_code == 200, resp.text
    assert resp.json()["google_email"] == "boss@gmail.com"
    assert resp.json()["email"] == "hh@example.com"

    # Now Google signs the headhunter in.
    payload, nonce = _start(client)
    google["c2"] = _identity(nonce, sub="g-hh", email="boss@gmail.com")
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c2"})
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "headhunter"

    resp = client.delete("/api/auth/google/link", headers=hh)
    assert resp.status_code == 200
    assert resp.json()["google_email"] is None
    payload, nonce = _start(client)
    google["c3"] = _identity(nonce, sub="g-hh", email="boss@gmail.com")
    # Unlinked: the Google email is new, so this signs up a fresh candidate instead.
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c3"})
    assert resp.json()["user"]["role"] == "candidate"


def test_link_requires_session_and_unique_google_account(client, google, hh, candidate):
    resp = client.post("/api/auth/google/authorize", json={"intent": "link"})
    assert resp.status_code == 403

    _, cand_headers = candidate
    payload, nonce = _start(client, "link", cand_headers)
    google["c"] = _identity(nonce, sub="shared")
    assert (
        client.post("/api/auth/google/link", json={**payload, "code": "c"}, headers=cand_headers)
    ).status_code == 200

    payload, nonce = _start(client, "link", hh)
    google["c2"] = _identity(nonce, sub="shared")
    resp = client.post("/api/auth/google/link", json={**payload, "code": "c2"}, headers=hh)
    assert resp.status_code == 409


def test_link_state_is_bound_to_the_user(client, google, hh, candidate):
    _, cand_headers = candidate
    payload, nonce = _start(client, "link", cand_headers)
    google["c"] = _identity(nonce)
    # The headhunter can't finish a link the candidate started.
    resp = client.post("/api/auth/google/link", json={**payload, "code": "c"}, headers=hh)
    assert resp.status_code == 403
    # Nor can a link state be used to sign in.
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c"})
    assert resp.status_code == 422


def test_rejects_tampering(client, google):
    payload, nonce = _start(client)
    google["c"] = _identity(nonce)
    wrong_verifier = {**payload, "code": "c", "code_verifier": "x" * 64}
    assert client.post("/api/auth/google/login", json=wrong_verifier).status_code == 422
    forged = jwt.encode({"purpose": "google_oauth", "intent": "login"}, "wrong-key" * 4)
    resp = client.post("/api/auth/google/login", json={**payload, "code": "c", "state": forged})
    assert resp.status_code == 422
    google["c2"] = _identity("some-other-nonce")
    assert client.post("/api/auth/google/login", json={**payload, "code": "c2"}).status_code == 422
    # A session token is not a valid state, and a state is not a valid session token.
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {payload['state']}"})
    assert resp.status_code == 401


def test_sign_up_respects_registration_and_verification(client, google, monkeypatch):
    payload, nonce = _start(client)
    google["c"] = _identity(nonce, verified=False)
    assert client.post("/api/auth/google/login", json={**payload, "code": "c"}).status_code == 403

    monkeypatch.setattr(settings, "allow_candidate_registration", False)
    payload, nonce = _start(client)
    google["c2"] = _identity(nonce)
    assert client.post("/api/auth/google/login", json={**payload, "code": "c2"}).status_code == 403


def test_deactivated_user_cannot_sign_in(client, google, hh):
    payload, nonce = _start(client)
    google["c"] = _identity(nonce)
    user = client.post("/api/auth/google/login", json={**payload, "code": "c"}).json()["user"]
    client.patch(f"/api/users/{user['id']}", json={"is_active": False}, headers=hh)
    payload, nonce = _start(client)
    google["c2"] = _identity(nonce)
    assert client.post("/api/auth/google/login", json={**payload, "code": "c2"}).status_code == 403


def test_password_login_ignores_google_only_accounts(client, google):
    payload, nonce = _start(client)
    google["c"] = _identity(nonce)
    client.post("/api/auth/google/login", json={**payload, "code": "c"})
    resp = client.post("/api/auth/login", json={"email": "gina@gmail.com", "password": ""})
    assert resp.status_code == 401


def test_exchange_code_validates_the_id_token(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-123")
    monkeypatch.setattr(settings, "google_client_secret", "shh")
    sent: dict = {}

    def id_token(**overrides) -> str:
        claims = {"iss": "https://accounts.google.com", "aud": "client-123", "sub": "1",
                  "exp": 4_000_000_000, "email": "a@b.co", **overrides}
        return jwt.encode(claims, "google-signs-with-rsa-but-we-trust-tls-instead")

    def handler_for(token: str):
        def handler(request: httpx.Request) -> httpx.Response:
            sent["form"] = parse_qs(request.content.decode())
            return httpx.Response(200, json={"id_token": token})
        return handler

    real_client = httpx.AsyncClient

    def use(token: str) -> None:
        transport = httpx.MockTransport(handler_for(token))
        monkeypatch.setattr(
            google_auth.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw)
        )

    use(id_token())
    claims = asyncio.run(google_auth.exchange_code("the-code", "the-verifier"))
    assert claims["sub"] == "1"
    assert sent["form"]["code_verifier"] == ["the-verifier"]
    assert sent["form"]["client_secret"] == ["shh"]

    for bad in (
        id_token(aud="someone-else"),
        id_token(iss="https://evil.example"),
        id_token(exp=1_000_000_000),
    ):
        use(bad)
        with pytest.raises(google_auth.Invalid):
            asyncio.run(google_auth.exchange_code("the-code", "the-verifier"))
