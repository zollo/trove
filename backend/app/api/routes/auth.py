"""Authentication: local login, Google sign-in/linking and candidate self-registration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.config import settings
from app.core.security import create_access_token
from app.db import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    AuthConfig,
    GoogleAuthorization,
    GoogleAuthorizeRequest,
    GoogleCallback,
    LoginRequest,
    RegisterRequest,
    Token,
    UserRead,
)
from app.services import google_auth, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(user: User) -> Token:
    access = create_access_token(user.id, extra={"role": user.role.value})
    return Token(access_token=access, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token, operation_id="login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange email + password for a bearer token."""
    user = await user_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return _token_for(user)


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    operation_id="register_candidate",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Self-service candidate registration (if enabled)."""
    if not settings.allow_candidate_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    user = await user_service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        role=UserRole.candidate,
    )
    return _token_for(user)


@router.get("/me", response_model=UserRead, operation_id="whoami")
async def me(user: User = Depends(get_current_user)) -> User:
    """The authenticated user."""
    return user


@router.get("/config", response_model=AuthConfig, operation_id="auth_config")
async def auth_config() -> AuthConfig:
    """Tells the login page which options to render."""
    return AuthConfig(
        registration_enabled=settings.allow_candidate_registration,
        google_enabled=settings.google_enabled,
    )


@router.post(
    "/google/authorize",
    response_model=GoogleAuthorization,
    operation_id="google_authorize",
    # The bearer token is optional here: only the `link` intent needs one.
    openapi_extra={"security": [{"HTTPBearer": []}, {}]},
)
async def google_authorize(
    payload: GoogleAuthorizeRequest, user: User | None = Depends(get_optional_user)
) -> GoogleAuthorization:
    """Start Google sign-in. `link` requires a session; send the browser to the returned URL."""
    url, state, verifier = google_auth.authorize(payload.intent, user)
    return GoogleAuthorization(authorization_url=url, state=state, code_verifier=verifier)


@router.post("/google/login", response_model=Token, operation_id="google_login")
async def google_login(payload: GoogleCallback, db: AsyncSession = Depends(get_db)) -> Token:
    """Finish Google sign-in with the code from Google's redirect; returns a session token."""
    user = await google_auth.login(db, payload.code, payload.state, payload.code_verifier)
    return _token_for(user)


@router.post("/google/link", response_model=UserRead, operation_id="google_link")
async def google_link(
    payload: GoogleCallback,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Link the Google account from Google's redirect to the signed-in user."""
    return await google_auth.link(db, user, payload.code, payload.state, payload.code_verifier)


@router.delete("/google/link", response_model=UserRead, operation_id="google_unlink")
async def google_unlink(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> User:
    """Unlink Google from the signed-in user (they must have a password)."""
    return await google_auth.unlink(db, user)
