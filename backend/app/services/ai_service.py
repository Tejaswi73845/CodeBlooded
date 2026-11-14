from __future__ import annotations

import base64
import json
import math
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings
from app.errors import (
    AIConfigurationError,
    AIInvalidRequest,
    AIInvalidResponse,
    AINotConfigured,
    AISafetyBlocked,
    AIServiceUnavailable,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class AIResult:
    text: str
    model: str
    raw: dict[str, Any]


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimensions: int
    task_type: str
    meta: dict[str, Any] = field(default_factory=dict)


class AIService:
    def __init__(self) -> None:
        self.provider = settings.ai_provider
        if self.provider == "opencode":
            self.api_key = settings.opencode_api_key
            self.model = settings.opencode_model
            root = settings.opencode_chat_base.rstrip("/")
            # The gateway mirrors both APIs; pick the shape from the model family.
            self.api_style = "gemini" if self.model.startswith("gemini") else "openai"
            self.base_url = f"{root}/google/v1beta" if self.api_style == "gemini" else f"{root}/openai/v1"
        else:
            self.api_key = settings.gemini_api_key
            self.base_url = settings.gemini_api_base.rstrip("/")
            self.model = settings.gemini_model
            self.api_style = "gemini"
        self.embedding_model = settings.gemini_embedding_model
        # The gateway serves no embedding models, so embeddings always use the
        # Google Gemini API (or are skipped when no Google key is configured).
        self.embedding_api_key = settings.gemini_api_key
        self.embedding_base_url = settings.gemini_api_base.rstrip("/")
        # OpenCode expects a stable session header per conversation plus a
        # self-identifying user agent. We keep one session per process.
        self.session_id = uuid.uuid4().hex

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @property
    def embeddings_configured(self) -> bool:
        return bool(self.embedding_api_key)

    # ── transport ────────────────────────────────────────────────────────────
    def _error_message(self, response: httpx.Response) -> str:
        try:
            return str(response.json().get("error", {}).get("message") or f"Gemini returned {response.status_code}.")
        except ValueError:
            return f"Gemini returned {response.status_code}."

    def _headers(self, *, embedding: bool = False) -> dict[str, str]:
        # Google's native API authenticates with x-goog-api-key; OpenCode Go
        # uses a Bearer token on its Gemini-compatible endpoint and expects a
        # stable session header plus a self-identifying user agent.
        if embedding or self.provider != "opencode":
            key = self.embedding_api_key if embedding else self.api_key
            return {"x-goog-api-key": key, "Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "tracevault-backend/1.0",
            "x-opencode-session": self.session_id,
        }

    def _post_json(
        self,
        url: str,
        body: dict[str, Any],
        *,
        attempts: int = 3,
        embedding: bool = False,
    ) -> dict[str, Any]:
        if not (self.embedding_api_key if embedding else self.api_key):
            raise AINotConfigured()
        headers = self._headers(embedding=embedding)
        last_error: str | None = None
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
                    response = client.post(url, headers=headers, json=body)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt + 1 < attempts:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise AIServiceUnavailable(
                    "Could not connect to Gemini. The API may be unavailable.",
                    {"error": last_error, "attempts": attempts},
                ) from exc

            if response.status_code in RETRYABLE_STATUS:
                last_error = self._error_message(response)
                if attempt + 1 < attempts:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise AIServiceUnavailable(
                    "Gemini is temporarily unavailable.",
                    {"status": response.status_code, "error": last_error, "attempts": attempts},
                )

            if response.status_code in {401, 403}:
                raise AIConfigurationError(
                    "The AI provider rejected the API key. "
                    "Check OPENCODE_API_KEY (opencode provider) or GEMINI_API_KEY.",
                    {"status": response.status_code},
                )
            if response.status_code == 404:
                raise AIConfigurationError(
                    "The configured AI model was not found for this API key.",
                    {"status": response.status_code},
                )
            if response.status_code >= 400:
                raise AIInvalidRequest(
                    self._error_message(response),
                    {"status": response.status_code},
                )

            try:
                return response.json()
            except ValueError as exc:
                raise AIInvalidResponse("Gemini returned a non-JSON HTTP body.") from exc

        raise AIServiceUnavailable("Gemini is unavailable.", {"error": last_error})

    def _generate_url(self) -> str:
        return f"{self.base_url}/models/{self.model}:generateContent"

    def _chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _embedding_url(self) -> str:
        return f"{self.embedding_base_url}/models/{self.embedding_model}:batchEmbedContents"

    # ── generation ───────────────────────────────────────────────────────────
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> AIResult:
        if self.api_style == "openai":
            return self._generate_openai(
                prompt,
                system=system,
                temperature=temperature,
                json_mode=json_mode,
                image_bytes=image_bytes,
                image_mime=image_mime,
            )
        parts: list[dict[str, Any]] = [{"text": prompt}]
        if image_bytes:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": image_mime or "image/png",
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                }
            )
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": temperature, "topP": 0.9, "maxOutputTokens": 8192},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        payload = self._post_json(self._generate_url(), body)
        candidates = payload.get("candidates", [])
        block_reason = payload.get("promptFeedback", {}).get("blockReason")
        if not candidates:
            if block_reason:
                raise AISafetyBlocked(
                    "Gemini blocked this request for safety reasons.",
                    {"reason": block_reason},
                )
            raise AIInvalidResponse("Gemini returned no answer candidates.")
        candidate = candidates[0]
        finish_reason = str(candidate.get("finishReason") or "")
        content = candidate.get("content", {})
        text = "\n".join(part.get("text", "") for part in content.get("parts", []) if "text" in part).strip()
        if not text:
            if finish_reason in {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"} or block_reason:
                raise AISafetyBlocked(
                    "Gemini blocked this response for safety reasons.",
                    {"finishReason": finish_reason, "reason": block_reason},
                )
            raise AIInvalidResponse(
                "Gemini returned an empty response.",
                {"finishReason": finish_reason},
            )
        return AIResult(text=text, model=self.model, raw=payload)

    def _generate_openai(
        self,
        prompt: str,
        *,
        system: str | None,
        temperature: float,
        json_mode: bool,
        image_bytes: bytes | None,
        image_mime: str | None,
    ) -> AIResult:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        if image_bytes:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime or 'image/png'};base64,"
                                + base64.b64encode(image_bytes).decode("ascii")
                            },
                        },
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": prompt})
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        payload = self._post_json(self._chat_completions_url(), body)
        choices = payload.get("choices") or []
        if not choices:
            raise AIInvalidResponse("The AI provider returned no answer candidates.")
        choice = choices[0]
        finish_reason = str(choice.get("finish_reason") or "")
        message = choice.get("message") or {}
        text = str(message.get("content") or "").strip()
        if not text:
            if finish_reason == "content_filter":
                raise AISafetyBlocked(
                    "The AI provider blocked this response for safety reasons.",
                    {"finishReason": finish_reason},
                )
            raise AIInvalidResponse(
                "The AI provider returned an empty response.",
                {"finishReason": finish_reason},
            )
        return AIResult(text=text, model=self.model, raw=payload)

    def generate_json(self, prompt: str, *, system: str | None = None, temperature: float = 0.1) -> dict[str, Any]:
        last_error: Exception | None = None
        retry_prompt = prompt
        for attempt in range(2):
            result = self.generate(retry_prompt, system=system, temperature=temperature, json_mode=True)
            try:
                return parse_json_object(result.text)
            except AIInvalidResponse as exc:
                last_error = exc
                logger.warning("Gemini returned invalid JSON (attempt %s/2)", attempt + 1)
                retry_prompt = (
                    prompt
                    + "\n\nYour previous response was not valid JSON. Return one complete, valid JSON object "
                    "only. Do not truncate it, do not use markdown fences, and escape all newlines inside strings."
                )
        raise AIInvalidResponse(
            "Gemini did not return valid JSON after two attempts.",
            {"error": str(last_error)},
        )

    # ── embeddings ───────────────────────────────────────────────────────────
    def embed_texts(
        self,
        texts: list[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], model=self.embedding_model, dimensions=0, task_type=task_type)
        if not self.embedding_api_key:
            raise AINotConfigured()

        prepared = [text[:8000].strip() or " " for text in texts]
        batch_size = max(1, min(settings.gemini_embedding_batch_size, 100))
        vectors: list[list[float]] = []
        actual_dimensions = 0
        use_dimensions = settings.gemini_embedding_dimensions > 0

        for start in range(0, len(prepared), batch_size):
            batch = prepared[start : start + batch_size]
            body: dict[str, Any] = {
                "requests": [
                    {
                        "model": f"models/{self.embedding_model}",
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                    }
                    for text in batch
                ]
            }
            if use_dimensions:
                body["requests"] = [
                    {**request, "outputDimensionality": settings.gemini_embedding_dimensions}
                    for request in body["requests"]
                ]
            try:
                payload = self._post_json(self._embedding_url(), body, embedding=True)
            except AIInvalidRequest as exc:
                # Older embedding models may reject outputDimensionality. Retry without it once.
                if use_dimensions and "outputdimensionality" in str(exc).lower():
                    use_dimensions = False
                    body["requests"] = [
                        {key: value for key, value in request.items() if key != "outputDimensionality"}
                        for request in body["requests"]
                    ]
                    payload = self._post_json(self._embedding_url(), body, embedding=True)
                else:
                    raise

            embeddings = payload.get("embeddings", [])
            if len(embeddings) != len(batch):
                raise AIInvalidResponse(
                    "Gemini returned an unexpected number of embeddings.",
                    {"expected": len(batch), "received": len(embeddings)},
                )
            for embedding in embeddings:
                values = embedding.get("values", [])
                if not values:
                    raise AIInvalidResponse("Gemini returned an empty embedding vector.")
                vector = [float(value) for value in values]
                actual_dimensions = len(vector)
                vectors.append(_normalize(vector))

        return EmbeddingResult(
            vectors=vectors,
            model=self.embedding_model,
            dimensions=actual_dimensions,
            task_type=task_type,
            meta={"batches": math.ceil(len(prepared) / batch_size), "outputDimensionality": use_dimensions},
        )

    def embed_query(self, question: str) -> list[float]:
        result = self.embed_texts([question], task_type="RETRIEVAL_QUERY")
        return result.vectors[0] if result.vectors else []

    def extract_text_from_image(self, image_bytes: bytes, mime: str) -> str:
        system = (
            "You are an OCR engine for digital evidence. Transcribe every visible character verbatim, "
            "including timestamps and phone numbers. Preserve line breaks. Do not summarize, translate, "
            "explain or invent anything. If no text is visible, return an empty string."
        )
        result = self.generate(
            "Transcribe all visible text in this image exactly as it appears.",
            system=system,
            temperature=0.0,
            image_bytes=image_bytes,
            image_mime=mime,
        )
        return result.text.strip()


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                value = json.loads(repaired)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
    raise AIInvalidResponse("AI response was not valid JSON.")


ai_service = AIService()
