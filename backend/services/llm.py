"""
Async Groq LLM service — with tenacity retry.

Retry policy:
  - Up to 3 attempts on RuntimeError (API errors, timeouts)
  - Exponential back-off: 2 s → 4 s → 8 s
  - Logs a warning before each retry so it's visible in logs
"""
import logging

from groq import AsyncGroq
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(RuntimeError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def groq_completion(prompt: str) -> str:
    """
    Send a prompt to the Groq chat-completion endpoint and return the
    model's text response.

    Retried automatically up to 3× on RuntimeError with exponential back-off.

    Args:
        prompt: The full prompt string to send.

    Returns:
        The model's response text.

    Raises:
        RuntimeError: After all retries are exhausted.
        EnvironmentError: If GROQ_API_KEY is not configured.
    """
    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.groq_max_tokens,
            temperature=settings.groq_temperature,
        )
    except Exception as exc:
        logger.error("Groq API call failed: %s", exc)
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    choices = response.choices
    if not choices:
        raise RuntimeError("Groq returned an empty choices list.")

    content: str = choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError("Groq returned an empty response body.")

    return content.strip()
