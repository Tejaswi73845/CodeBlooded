from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=False,
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "TraceVault"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # Local-dev default is SQLite so the service starts with zero infrastructure.
    # Set DATABASE_URL to PostgreSQL in production (see .env.example).
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'tracevault.db').as_posix()}"
    auto_create_tables: bool = True

    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: int = 2048
    allowed_extensions: str = (
        "pdf,png,jpg,jpeg,mp3,wav,m4a,aac,flac,ogg,opus,aiff,aif,wma,amr,"
        "mp4,m4v,mov,mkv,webm,avi,wmv,flv,mpg,mpeg,3gp,ogv,"
        "txt,json,csv,eml"
    )
    read_only_originals: bool = True

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173,"
        "http://localhost:3000"
    )

    default_actor: str = "Aarav Shah"
    default_actor_email: str = "aarav.shah@kestrel.legal"

    # Authentication (frontend sign-in). Enforcement is opt-in so local Swagger
    # keeps working; set AUTH_REQUIRED=true to protect the API.
    auth_required: bool = False
    auth_session_days: int = 7
    default_password: str = "tracevault"

    # Gemini (never hardcode a key; leave empty to use deterministic fallbacks)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_timeout_seconds: int = 90
    gemini_vision_fallback: bool = True
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    gemini_embedding_batch_size: int = 50

    # Alternative chat provider: OpenCode inference gateway.
    # Set AI_PROVIDER=opencode + OPENCODE_API_KEY to route chat through OpenCode.
    # The base is the provider root; the API shape is picked from the model:
    # Gemini models use /google/v1beta, everything else uses /openai/v1.
    # Embeddings are not served by the gateway, so they always use GEMINI_API_KEY.
    ai_provider: str = "google"  # "google" | "opencode"
    opencode_api_key: str | None = None
    opencode_model: str = "deepseek-v4.1-flash"
    opencode_chat_base: str = "https://opencode.ai/inference/go"

    # Retrieval-augmented generation
    rag_enabled: bool = True
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 150
    rag_max_chunks: int = 5000
    rag_vector_weight: float = 0.7
    rag_lexical_weight: float = 0.2
    rag_entity_weight: float = 0.1
    rag_min_score: float = 0.12
    rag_min_vector_match: float = 0.52

    # OCR / ASR
    ocr_engine: str = "auto"  # auto | easyocr | paddleocr | tesseract | gemini | none
    ocr_languages: str = "en"
    ocr_gpu: bool = False
    max_pdf_ocr_pages: int = 40
    whisper_model: str = "small"
    whisper_language: str | None = None
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    video_frame_interval_seconds: int = 8
    max_video_frames: int = 12
    demo_audio_model: bool = False  # when true, tiny model is used for demo

    # Limits
    max_text_chars_for_ai: int = 24_000
    assistant_max_sources: int = 8

    audit_genesis_hash: str = "0" * 64
    timezone: str = "Asia/Kolkata"

    @model_validator(mode="after")
    def _fallbacks(self):
        # An explicitly empty environment variable must be able to disable a
        # value loaded from the dotenv file (notably in isolated test runs).
        if "GEMINI_API_KEY" in os.environ:
            self.gemini_api_key = os.environ["GEMINI_API_KEY"] or None
        elif not self.gemini_api_key:
            self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or None
        if self.demo_audio_model:
            self.whisper_model = "tiny"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {ext.strip().lower().lstrip(".") for ext in self.allowed_extensions.split(",") if ext.strip()}

    @property
    def upload_root(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
