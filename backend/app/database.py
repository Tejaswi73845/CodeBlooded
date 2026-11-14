from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine, event, inspect, select, text, update
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


connect_args = {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
    future=True,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models  # noqa: F401  (register mappings)

    Base.metadata.create_all(bind=engine)


def ensure_workspace_schema() -> None:
    """Add workspace columns to pre-existing tables, create the default workspace and backfill."""
    import app.models  # noqa: F401
    from app.models import AuditLog, Evidence, Report
    from app.models.workspace import Workspace
    from app.services.workspace_service import DEFAULT_WORKSPACE_NAME

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "workspaces" not in tables:
        Base.metadata.create_all(bind=engine)
        tables = set(inspect(engine).get_table_names())

    column_type = "CHAR(32)" if engine.dialect.name == "sqlite" else "UUID"
    with engine.begin() as conn:
        for table in ("evidence", "reports", "audit_logs"):
            if table not in tables:
                continue
            columns = {column["name"] for column in inspect(engine).get_columns(table)}
            if "workspace_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN workspace_id {column_type}"))

    db = SessionLocal()
    try:
        default = db.scalar(select(Workspace).where(Workspace.is_default.is_(True)))
        if default is None:
            default = db.scalar(select(Workspace).order_by(Workspace.created_at.asc()).limit(1))
            if default is None:
                default = Workspace(name=DEFAULT_WORKSPACE_NAME, is_default=True)
                db.add(default)
            else:
                default.is_default = True
                db.add(default)
            db.commit()
            db.refresh(default)
        for model in (Evidence, Report, AuditLog):
            db.execute(
                update(model).where(model.workspace_id.is_(None)).values(workspace_id=default.id)
            )
        db.commit()
    finally:
        db.close()


def ensure_auth_schema() -> None:
    """Add auth columns/tables to pre-existing databases."""
    import app.models  # noqa: F401

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables or "auth_sessions" not in tables:
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
    if "users" not in tables:
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    bool_default = "BOOLEAN DEFAULT 1" if engine.dialect.name == "sqlite" else "BOOLEAN DEFAULT TRUE"
    with engine.begin() as conn:
        if "password_hash" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)"))
        if "is_active" not in columns:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN is_active {bool_default}"))
