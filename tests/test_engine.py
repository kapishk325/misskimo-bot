"""Tests for Groq LLM inference client."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from groq import AsyncGroq
from misskimo.engine import GroqRoastEngine


def test_engine_initialization_defaults():
    """Verify default engine configuration."""
    engine = GroqRoastEngine(api_key="gsk_test_key")
    assert engine.api_key == "gsk_test_key"
    assert engine.model == "qwen/qwen3.8-27b"
    assert engine.timeout == 10.0
    assert isinstance(engine.client, AsyncGroq)


def test_engine_initialization_custom():
    """Verify custom parameters for model and timeout."""
    engine = GroqRoastEngine(
        api_key="gsk_custom_key",
        model="custom-model-id",
        timeout=25.0,
    )
    assert engine.api_key == "gsk_custom_key"
    assert engine.model == "custom-model-id"
    assert engine.timeout == 25.0


def test_engine_custom_client_injection():
    """Verify passing a pre-configured AsyncGroq client."""
    mock_client = MagicMock(spec=AsyncGroq)
    engine = GroqRoastEngine(api_key="gsk_test", client=mock_client)
    assert engine.client is mock_client


@pytest.mark.asyncio
async def test_generate_roast_success():
    """Verify standard roast generation returns expected text."""
    engine = GroqRoastEngine(api_key="gsk_test")
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Sit down, you talk like a spam call."))
    ]

    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result == "Sit down, you talk like a spam call."
        mock_create.assert_awaited_once_with(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=150,
            temperature=0.9,
        )


@pytest.mark.asyncio
async def test_generate_roast_custom_parameters():
    """Verify custom max_tokens and temperature are passed to API."""
    engine = GroqRoastEngine(api_key="gsk_test", model="llama-3.3-70b-versatile")
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Cold burn."))
    ]

    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await engine.generate_roast(
            [{"role": "user", "content": "hello"}],
            max_tokens=220,
            temperature=0.7,
        )
        assert result == "Cold burn."
        mock_create.assert_awaited_once_with(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "hello"}],
            max_tokens=220,
            temperature=0.7,
        )


@pytest.mark.asyncio
async def test_generate_roast_strips_surrounding_quotes_and_whitespace():
    """Verify leading/trailing whitespace and enclosing quotes are removed."""
    engine = GroqRoastEngine(api_key="gsk_test")
    mock_response_double_quotes = MagicMock()
    mock_response_double_quotes.choices = [
        MagicMock(message=MagicMock(content='  "You dress like a laundry basket."  \n'))
    ]

    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response_double_quotes
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result == "You dress like a laundry basket."

    mock_response_single_quotes = MagicMock()
    mock_response_single_quotes.choices = [
        MagicMock(message=MagicMock(content="  'Rudeness is my border wall.'  "))
    ]
    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response_single_quotes
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result == "Rudeness is my border wall."


@pytest.mark.asyncio
async def test_generate_roast_handles_api_exception():
    """Verify exceptions during API call log and return None without crashing."""
    engine = GroqRoastEngine(api_key="gsk_test")
    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("Rate limit hit")
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result is None


@pytest.mark.asyncio
async def test_generate_roast_handles_empty_choices():
    """Verify empty choices list returns None."""
    engine = GroqRoastEngine(api_key="gsk_test")
    mock_response = MagicMock()
    mock_response.choices = []

    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result is None


@pytest.mark.asyncio
async def test_generate_roast_handles_empty_or_none_content():
    """Verify empty content string or None returns None."""
    engine = GroqRoastEngine(api_key="gsk_test")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]

    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result is None

    mock_response_blank = MagicMock()
    mock_response_blank.choices = [MagicMock(message=MagicMock(content="   \n  "))]
    with patch.object(engine.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response_blank
        result = await engine.generate_roast([{"role": "user", "content": "hi"}])
        assert result is None
