"""Configuration loader and schema for Misskimo Discord bot."""

from dataclasses import dataclass, field
import os
from typing import Optional
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Misskimo bot runtime configuration."""

    discord_token: str
    groq_api_key: str
    groq_model: str = "qwen/qwen3.8-27b"
    allowed_channel_ids: list[int] = field(default_factory=list)
    chime_chance: float = 0.12
    cooldown_seconds: int = 45
    max_history_messages: int = 10
    allow_bot_replies: bool = True
    max_consecutive_bot_replies: int = 5


def _parse_channel_ids(raw_value: str) -> list[int]:
    """Parse comma-separated channel IDs into a list of integers."""
    if not raw_value or not raw_value.strip():
        return []

    channel_ids: list[int] = []
    for item in raw_value.split(","):
        cleaned = item.strip()
        if cleaned:
            channel_ids.append(int(cleaned))
    return channel_ids


def load_config(env_path: Optional[str] = None) -> Config:
    """Load configuration from environment variables or a .env file.

    Args:
        env_path: Optional path to a specific .env file to load.

    Returns:
        Config: Populated configuration instance.

    Raises:
        ValueError: If required environment variables (DISCORD_TOKEN or GROQ_API_KEY) are missing.
    """
    if env_path is not None:
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        raise ValueError("DISCORD_TOKEN environment variable is required")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required")

    groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    raw_channels = os.getenv("ALLOWED_CHANNEL_IDS", "")
    allowed_channel_ids = _parse_channel_ids(raw_channels)

    chime_chance = float(os.getenv("CHIME_CHANCE", "0.12"))
    cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", "45"))
    max_history_messages = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

    raw_allow_bot = os.getenv("ALLOW_BOT_REPLIES", "true").strip().lower()
    allow_bot_replies = raw_allow_bot in ("true", "1", "yes", "on")
    max_consecutive_bot_replies = int(os.getenv("MAX_CONSECUTIVE_BOT_REPLIES", "5"))

    return Config(
        discord_token=discord_token,
        groq_api_key=groq_api_key,
        groq_model=groq_model,
        allowed_channel_ids=allowed_channel_ids,
        chime_chance=chime_chance,
        cooldown_seconds=cooldown_seconds,
        max_history_messages=max_history_messages,
        allow_bot_replies=allow_bot_replies,
        max_consecutive_bot_replies=max_consecutive_bot_replies,
    )
