from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import SessionLocal
from app.services import auth_service
from app.utils.http import bearer_token


def _is_public(path: str) -> bool:
    if not path.startswith(settings.api_prefix):
        return True
    public = {
        f"{settings.api_prefix}/auth/login",
        f"{settings.api_prefix}/auth/register",
        f"{settings.api_prefix}/health",
    }
    return path in public or path.startswith(f"{settings.api_prefix}/health")


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Attach the signed-in user and, when enabled, require authentication."""

    async def dispatch(self, request, call_next):
        request.state.user = None
        token = bearer_token(request)
        if token:
            db = SessionLocal()
            try:
                request.state.user = auth_service.user_for_token(db, token)
            finally:
                db.close()
        if settings.auth_required and request.state.user is None and not _is_public(request.url.path):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "not_authenticated",
                        "message": "Please sign in to continue.",
                        "details": None,
                    }
                },
            )
        return await call_next(request)
