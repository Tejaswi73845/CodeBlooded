from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import bearer_token, current_user
from app.errors import AppError
from app.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut
from app.services import auth_service, workspace_service
from app.services.audit_service import record_audit
from app.utils.http import actor_name, client_ip, user_agent

router = APIRouter(prefix="/auth", tags=["Auth"])


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.display_name, role=user.role)


def _default_workspace_id(db: Session):
    return workspace_service.get_default(db).id


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise AppError(400, "invalid_email", "Enter a valid email address.")
    if len(payload.password) < 6:
        raise AppError(400, "weak_password", "Password must be at least 6 characters.")
    if auth_service.find_user(db, email):
        raise AppError(409, "email_taken", "An account with this email already exists.")

    user = auth_service.register(db, name=payload.name, email=email, password=payload.password)
    token = auth_service.create_session(db, user)
    record_audit(
        db,
        actor=user.display_name,
        action="Account created",
        target_type="user",
        target_id=str(user.id),
        details={"email": user.email},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=_default_workspace_id(db),
    )
    return AuthResponse(token=token, user=_out(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    if not user:
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    token = auth_service.create_session(db, user)
    record_audit(
        db,
        actor=user.display_name,
        action="Signed in",
        target_type="user",
        target_id=str(user.id),
        details={"email": user.email},
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=_default_workspace_id(db),
    )
    return AuthResponse(token=token, user=_out(user))


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token = bearer_token(request)
    user = getattr(request.state, "user", None)
    if token:
        auth_service.revoke_session(db, token)
    record_audit(
        db,
        actor=user.display_name if user else actor_name(request),
        action="Signed out",
        target_type="user",
        target_id=str(user.id) if user else None,
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        workspace_id=_default_workspace_id(db) if user else None,
    )
    return {"signedOut": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return _out(user)
