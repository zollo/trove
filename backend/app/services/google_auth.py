"""Google sign-in (OpenID Connect authorization-code flow with PKCE) and account linking.

The flow is stateless so any replica can serve any step:

1. `authorize` returns Google's consent URL plus a signed `state` (a short-lived
   JWT holding the intent, a nonce, the PKCE challenge and, for linking, the
   caller's id) and the PKCE `code_verifier`. The web UI keeps both in
   sessionStorage and sends the browser to Google.
2. Google redirects back to the web UI (`/auth/google/callback`), which checks
   that `state` is the one it stored and posts `code`, `state` and
   `code_verifier` to `login` or `link`.
3. We verify the state, redeem the code with Google (client secret + verifier)
   and read the identity from the returned ID token.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.models.user import User, UserRole
from app.services import user_service

logger = logging.getLogger("trove.google")

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
STATE_PURPOSE = "google_oauth"
STATE_TTL = timedelta(minutes=10)


@dataclass
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str


def _require_enabled() -> None:
    if not settings.google_enabled:
        raise NotFound("Google sign-in is not enabled")


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorize(intent: str, user: User | None) -> tuple[str, str, str]:
    """Return (authorization_url, state, code_verifier) for a new sign-in attempt."""
    _require_enabled()
    if intent == "link" and user is None:
        raise Forbidden("Sign in before linking a Google account")
    verifier = secrets.token_urlsafe(48)
    nonce = secrets.token_urlsafe(16)
    now = datetime.now(UTC)
    claims = {
        "purpose": STATE_PURPOSE,
        "intent": intent,
        "nonce": nonce,
        "cc": _challenge(verifier),
        "iat": now,
        "exp": now + STATE_TTL,
    }
    if intent == "link" and user is not None:
        claims["uid"] = str(user.id)
    state = jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": _challenge(verifier),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}", state, verifier


def _read_state(state: str, verifier: str, intent: str) -> dict:
    try:
        claims = jwt.decode(state, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise Invalid("Google sign-in expired or was tampered with; try again") from exc
    if claims.get("purpose") != STATE_PURPOSE or claims.get("intent") != intent:
        raise Invalid("Google sign-in expired or was tampered with; try again")
    if not secrets.compare_digest(claims.get("cc", ""), _challenge(verifier)):
        raise Invalid("Google sign-in expired or was tampered with; try again")
    return claims


async def exchange_code(code: str, verifier: str) -> dict:
    """Redeem an authorization code at Google's token endpoint; returns the ID token claims.

    The ID token comes straight from Google over TLS, so (per OpenID Connect
    Core 3.1.3.7) its signature need not be checked; audience, issuer and
    expiry still are.
    """
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_callback_url,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(TOKEN_URL, data=data)
    except httpx.HTTPError as exc:
        logger.warning("Google token request failed: %s", exc)
        raise Invalid("Could not reach Google; try again") from exc
    if resp.status_code != 200:
        logger.warning("Google token exchange rejected (%s): %s", resp.status_code, resp.text)
        raise Invalid("Google rejected the sign-in; try again")
    id_token = resp.json().get("id_token")
    if not id_token:
        raise Invalid("Google did not return an identity")
    try:
        return jwt.decode(
            id_token,
            # Skipping the signature turns the other checks off unless re-enabled.
            options={
                "verify_signature": False,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "require": ["sub", "aud", "iss", "exp"],
            },
            audience=settings.google_client_id,
            issuer=list(ISSUERS),
        )
    except jwt.PyJWTError as exc:
        raise Invalid("Google returned an invalid identity") from exc


async def _identity(code: str, verifier: str, nonce: str) -> GoogleIdentity:
    claims = await exchange_code(code, verifier)
    if claims.get("nonce") != nonce:
        raise Invalid("Google sign-in expired or was tampered with; try again")
    email = str(claims.get("email") or "").lower()
    if not email:
        raise Invalid("Your Google account did not share an email address")
    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=email,
        email_verified=bool(claims.get("email_verified")),
        name=str(claims.get("name") or ""),
    )


async def _by_sub(db: AsyncSession, sub: str) -> User | None:
    result = await db.execute(select(User).where(User.google_sub == sub))
    return result.scalar_one_or_none()


async def login(db: AsyncSession, code: str, state: str, verifier: str) -> User:
    """Sign in with Google; creates a candidate account if registration is open."""
    _require_enabled()
    claims = _read_state(state, verifier, "login")
    ident = await _identity(code, verifier, claims["nonce"])

    user = await _by_sub(db, ident.sub)
    if user is not None:
        if not user.is_active:
            raise Forbidden("This account is deactivated")
        return user

    # An existing account is never taken over by email alone: its owner proves
    # the password first and links Google from their settings.
    if await user_service.get_by_email(db, ident.email):
        raise Conflict(
            "A Trove account already uses this email. Sign in with your password, "
            "then link Google from your profile or settings."
        )
    if not settings.allow_candidate_registration:
        raise Forbidden("No Trove account is linked to this Google account")
    if not ident.email_verified:
        raise Forbidden("Verify your Google account's email address first")
    return await user_service.create_user(
        db,
        email=ident.email,
        password=None,
        display_name=ident.name,
        role=UserRole.candidate,
        google_sub=ident.sub,
    )


async def link(db: AsyncSession, user: User, code: str, state: str, verifier: str) -> User:
    """Attach a Google account to the signed-in user."""
    _require_enabled()
    claims = _read_state(state, verifier, "link")
    if claims.get("uid") != str(user.id):
        raise Forbidden("This Google link was started by a different account")
    ident = await _identity(code, verifier, claims["nonce"])
    owner = await _by_sub(db, ident.sub)
    if owner is not None and owner.id != user.id:
        raise Conflict("That Google account is already linked to another Trove account")
    user.google_sub = ident.sub
    user.google_email = ident.email
    await db.commit()
    await db.refresh(user)
    return user


async def unlink(db: AsyncSession, user: User) -> User:
    if user.google_sub is None:
        raise NotFound("No Google account is linked")
    if not user.has_password:
        raise Invalid("Your account has no password; set one before unlinking Google")
    user.google_sub = None
    user.google_email = None
    await db.commit()
    await db.refresh(user)
    return user

