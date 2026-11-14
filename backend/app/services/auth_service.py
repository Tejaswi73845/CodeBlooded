from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuthSession, User
from app.utils.time import utcnow

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def register(db: Session, *, name: str, email: str, password: str) -> User:
    user = User(
        email=email.strip().lower(),
        display_name=name.strip()[:160],
        role="analyst",
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User | None:
    user = find_user(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(days=max(1, settings.auth_session_days))
    db.add(
        AuthSession(
            token_hash=_token_hash(token),
            user_id=user.id,
            expires_at=expires_at,
            last_used_at=utcnow(),
        )
    )
    db.commit()
    return token


def revoke_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    db.commit()


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    if not session:
        return None
    if session.expires_at <= utcnow():
        db.delete(session)
        db.commit()
        return None
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        return None
    session.last_used_at = utcnow()
    db.add(session)
    db.commit()
    return user


def ensure_default_credentials(db: Session) -> User:
    """Give the seeded analyst a working password so sign-in works out of the box."""
    user = find_user(db, settings.default_actor_email)
    if not user:
        user = User(
            email=settings.default_actor_email.strip().lower(),
            display_name=settings.default_actor,
            role="analyst",
            password_hash=hash_password(settings.default_password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    if not user.password_hash:
        user.password_hash = hash_password(settings.default_password)
        db.add(user)
        db.commit()
    return user
