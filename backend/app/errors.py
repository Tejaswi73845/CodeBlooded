from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Domain error that is rendered as a consistent JSON envelope."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(404, "not_found", f"{resource} was not found.", {"id": str(identifier)})


class UnsupportedMediaError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(415, "unsupported_media_type", message, details)


class FileTooLargeError(AppError):
    def __init__(self, limit_mb: int):
        super().__init__(413, "file_too_large", f"File exceeds the {limit_mb} MB upload limit.")


class ProcessingError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(422, "processing_error", message, details)


class AIServiceError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(503, "ai_service_unavailable", message, details)


class AIServiceUnavailable(AIServiceError):
    """Transport failure, timeout, 429 or 5xx after retries. Fallback is allowed."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details)
        self.code = "ai_unavailable"


class AINotConfigured(AIServiceUnavailable):
    def __init__(self, message: str = "Gemini is not configured. Set GEMINI_API_KEY to enable AI analysis."):
        super().__init__(message)
        self.code = "ai_not_configured"


class AIConfigurationError(AIServiceError):
    """Invalid key, model or request configuration. Never silently degrade."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details)
        self.code = "ai_misconfigured"


class AIInvalidRequest(AIServiceError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details)
        self.status_code = 502
        self.code = "ai_invalid_request"


class AIInvalidResponse(AIServiceError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details)
        self.status_code = 502
        self.code = "ai_invalid_response"


class AISafetyBlocked(AIServiceError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details)
        self.status_code = 422
        self.code = "ai_safety_blocked"


class IntegrityError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(409, "integrity_error", message, details)
