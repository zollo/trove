"""Aggregate API router, mounted at /api."""
from fastapi import APIRouter

from app.api.routes import api_keys, auth, candidates, health, jobs, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
