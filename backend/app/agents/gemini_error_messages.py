from google.genai.errors import APIError, ClientError


def describe_gemini_failure(task: str, exc: Exception) -> str:
    message = str(exc).lower()

    if isinstance(exc, ClientError) and exc.code == 429:
        return (
            f"Gemini {task} failed with HTTP 429 (rate limited) after automatic backoff retries. "
            "Wait several minutes, reduce parallel uploads, or check quota and billing in Google AI Studio."
        )

    if isinstance(exc, APIError):
        status = (getattr(exc, "status", None) or "").upper()
        if status in {"RESOURCE_EXHAUSTED", "UNAVAILABLE"} or "resource exhausted" in message:
            return (
                f"Gemini {task} failed because the API quota or concurrency limit was hit. "
                "Check billing and limits in Google AI Studio, then restart the backend after "
                "updating backend/.env."
            )

    if "quota" in message or ("exceeded" in message and "limit" in message):
        return (
            f"Gemini {task} may have failed due to quota or usage limits. "
            "Verify API key restrictions and Gemini API availability for your project."
        )

    return f"Gemini {task} failed: {exc.__class__.__name__}: {exc}"
