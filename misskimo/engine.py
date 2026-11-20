"""Groq LLM inference client for Misskimo Discord bot."""

import logging
from typing import Optional
from groq import AsyncGroq

logger = logging.getLogger(__name__)


class GroqRoastEngine:
    """Asynchronous Groq inference engine with robust error handling."""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen/qwen3.8-27b",
        timeout: float = 10.0,
        client: Optional[AsyncGroq] = None,
    ) -> None:
        """Initialize the Groq roast inference engine.

        Args:
            api_key: Groq API key for authentication.
            model: Model identifier on Groq (default: 'qwen/qwen3.8-27b').
            timeout: Request timeout in seconds (default: 10.0).
            client: Optional pre-configured AsyncGroq client instance.
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = client if client is not None else AsyncGroq(api_key=api_key, timeout=timeout)

    async def generate_roast(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 150,
        temperature: float = 0.9,
    ) -> Optional[str]:
        """Generate a roast response asynchronously using Groq Chat Completions.

        Args:
            messages: OpenAI-compatible list of message dicts (role and content).
            max_tokens: Maximum tokens in generated completion (default: 150).
            temperature: Sampling temperature (default: 0.9).

        Returns:
            Cleaned response string, or None if the request failed or response was empty.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            if not response or not getattr(response, "choices", None):
                logger.warning("Groq API returned an empty response or choices list")
                return None

            raw_content = response.choices[0].message.content
            if not raw_content:
                logger.warning("Groq API choice message content was empty or None")
                return None

            return self._clean_output(raw_content)

        except Exception as exc:
            logger.error("Failed to generate roast with Groq: %s", exc, exc_info=True)
            return None

    @staticmethod
    def _clean_output(text: str) -> Optional[str]:
        """Clean output by stripping leading/trailing whitespace and enclosing quotes.

        Args:
            text: Raw model generation string.

        Returns:
            Sanitized string or None if blank after cleaning.
        """
        cleaned = text.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("'") and cleaned.endswith("'")
        ):
            cleaned = cleaned[1:-1].strip()

        return cleaned if cleaned else None
