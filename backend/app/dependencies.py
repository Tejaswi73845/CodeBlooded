from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import AppError
from app.models import User, Workspace
from app.services import auth_service, workspace_service
from app.utils.http import bearer_token

WORKSPACE_HEADER = "X-Workspace-Id"


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    state_user = getattr(request.state, "user", None)
    if state_user is not None:
        return state_user
    return auth_service.user_for_token(db, bearer_token(request))


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = optional_user(request, db)
    if not user:
        raise AppError(401, "not_authenticated", "Please sign in to continue.")
    return user


def current_workspace(request: Request, db: Session = Depends(get_db)) -> Workspace:
    """Resolve the workspace selected by the client (defaults safely)."""
    return workspace_service.resolve(db, request.headers.get(WORKSPACE_HEADER))
