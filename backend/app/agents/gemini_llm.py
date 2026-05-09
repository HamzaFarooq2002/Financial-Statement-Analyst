import logging
import random
import time
from typing import Any, TypeVar

from google import genai
from google.genai import types
from google.genai.errors import APIError, ServerError
from pydantic import BaseModel

from app.agents.gemini_error_messages import describe_gemini_failure
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class GeminiGenerationError(Exception):
    """Raised when a Gemini structured generation request fails validation or transport."""


def create_gemini_client() -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key or "",
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(attempts=settings.gemini_http_sdk_retries),
        ),
    )


def _retry_after_seconds(exc: Exception) -> float | None:
    if not isinstance(exc, APIError):
        return None
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _is_retryable_gemini_transport_error(exc: Exception) -> bool:
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        if code == 429:
            return True
        if isinstance(exc, ServerError):
            return True if code is None else code >= 500
        status = (exc.status or "").upper()
        return status in {
            "RESOURCE_EXHAUSTED",
            "UNAVAILABLE",
            "INTERNAL",
            "DEADLINE_EXCEEDED",
        }
    lowered = str(exc).lower()
    return (
        "429" in lowered
        or "resource exhausted" in lowered
        or "too many requests" in lowered
        or "unavailable" in lowered
    )


def _summarize_transport_error(exc: Exception) -> str:
    """Human-readable detail for logs (helps distinguish 429 vs 403 vs bad model)."""
    if isinstance(exc, APIError):
        parts: list[str] = [exc.__class__.__name__]
        code = getattr(exc, "code", None)
        if code is not None:
            parts.append(f"http={code}")
        status = getattr(exc, "status", None)
        if status:
            parts.append(f"rpc={status}")
        msg = getattr(exc, "message", None)
        if msg:
            parts.append(str(msg).strip().replace("\n", " ")[:180])
        ra = _retry_after_seconds(exc)
        if ra is not None:
            parts.append(f"Retry-After={ra}s")
        return " | ".join(parts) if len(parts) > 1 else parts[0]
    return f"{exc.__class__.__name__}: {str(exc)[:200]}"


def _backoff_sleep_seconds(attempt_index: int, exc: Exception) -> float:
    """attempt_index is 0 after first failure (sleep before retry #2)."""
    retry_after = _retry_after_seconds(exc)
    cap = settings.gemini_retry_max_delay_seconds
    if retry_after is not None:
        return max(0.5, min(retry_after, cap))

    base = settings.gemini_retry_base_seconds * (2**attempt_index)
    jitter = random.uniform(0, base * 0.25)
    return max(0.5, min(base + jitter, cap))


def generate_parsed(
    client: genai.Client,
    model: str,
    system_instruction: str,
    user_text: str,
    response_model: type[T],
    *,
    task_label: str,
) -> T:
    response_schema = _sanitize_json_schema(response_model.model_json_schema())
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_json_schema=response_schema,
    )

    max_attempts = settings.gemini_max_retries + 1
    response = None
    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_text,
                config=config,
            )
            break
        except Exception as exc:
            last_exc = exc
            remains = max_attempts - attempt - 1
            if remains <= 0 or not _is_retryable_gemini_transport_error(exc):
                raise GeminiGenerationError(describe_gemini_failure(task_label, exc)) from exc

            delay = _backoff_sleep_seconds(attempt, exc)
            logger.warning(
                "%s: retryable Gemini error [%s]; sleeping %.1fs (%s attempts left before giving up)",
                task_label,
                _summarize_transport_error(exc),
                delay,
                remains,
            )
            time.sleep(delay)

    if response is None:
        assert last_exc is not None
        raise GeminiGenerationError(describe_gemini_failure(task_label, last_exc)) from last_exc

    if response.prompt_feedback and response.prompt_feedback.block_reason:
        raise GeminiGenerationError(
            f"Gemini blocked {task_label}: {response.prompt_feedback.block_reason}"
        )

    parsed = response.parsed
    if parsed is None:
        raw = response.text
        if raw:
            try:
                parsed = response_model.model_validate_json(raw)
            except Exception as exc:
                raise GeminiGenerationError(
                    f"Gemini returned JSON that could not be parsed as "
                    f"{response_model.__name__}: {exc}"
                ) from exc
        else:
            raise GeminiGenerationError(
                f"Gemini response did not include structured output for {response_model.__name__}."
            )

    if isinstance(parsed, dict):
        parsed = response_model.model_validate(parsed)

    return parsed


def _sanitize_json_schema(schema: Any) -> Any:
    """Remove schema fields Gemini API rejects."""
    if isinstance(schema, dict):
        cleaned: dict[str, Any] = {}
        for key, value in schema.items():
            if key in {"additionalProperties", "additional_properties"}:
                continue
            cleaned[key] = _sanitize_json_schema(value)
        return cleaned
    if isinstance(schema, list):
        return [_sanitize_json_schema(item) for item in schema]
    return schema
