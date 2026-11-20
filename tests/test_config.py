from dataclasses import FrozenInstanceError
from dotenv import load_dotenv as real_load_dotenv
import pytest
from misskimo.config import Config, load_config


@pytest.fixture(autouse=True)
def isolate_ambient_dotenv(monkeypatch):
    """Ensure test suite remains hermetic and does not read local .env files unless explicitly requested."""
    def patched_load_dotenv(dotenv_path=None, **kwargs):
        if dotenv_path is not None:
            return real_load_dotenv(dotenv_path=dotenv_path, **kwargs)
        return False

    monkeypatch.setattr("misskimo.config.load_dotenv", patched_load_dotenv)



def test_load_config_defaults(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake_discord_token")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake_key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("ALLOWED_CHANNEL_IDS", raising=False)
    monkeypatch.delenv("CHIME_CHANCE", raising=False)
    monkeypatch.delenv("COOLDOWN_SECONDS", raising=False)
    monkeypatch.delenv("MAX_HISTORY_MESSAGES", raising=False)

    config = load_config()
    assert config.discord_token == "fake_discord_token"
    assert config.groq_api_key == "gsk_fake_key"
    assert config.groq_model == "qwen/qwen3.8-27b"
    assert config.chime_chance == 0.12
    assert config.cooldown_seconds == 45
    assert config.max_history_messages == 10
    assert config.allowed_channel_ids == []


def test_load_config_custom_values(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "custom_token")
    monkeypatch.setenv("GROQ_API_KEY", "custom_key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("ALLOWED_CHANNEL_IDS", "123456789, 987654321")
    monkeypatch.setenv("CHIME_CHANCE", "0.25")
    monkeypatch.setenv("COOLDOWN_SECONDS", "30")
    monkeypatch.setenv("MAX_HISTORY_MESSAGES", "15")

    config = load_config()
    assert config.discord_token == "custom_token"
    assert config.groq_api_key == "custom_key"
    assert config.groq_model == "openai/gpt-oss-120b"
    assert config.allowed_channel_ids == [123456789, 987654321]
    assert config.chime_chance == 0.25
    assert config.cooldown_seconds == 30
    assert config.max_history_messages == 15


def test_load_config_channel_ids_formatting(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake_token")
    monkeypatch.setenv("GROQ_API_KEY", "fake_key")
    monkeypatch.setenv("ALLOWED_CHANNEL_IDS", "  1001 ,  1002, 1003, ")

    config = load_config()
    assert config.allowed_channel_ids == [1001, 1002, 1003]


def test_load_config_missing_discord_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake_key")
    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        load_config()


def test_load_config_missing_groq_api_key(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake_discord_token")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        load_config()


def test_load_config_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ALLOWED_CHANNEL_IDS", raising=False)

    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "DISCORD_TOKEN=file_token\n"
        "GROQ_API_KEY=file_key\n"
        "ALLOWED_CHANNEL_IDS=111,222\n"
    )

    config = load_config(env_path=str(env_file))
    assert config.discord_token == "file_token"
    assert config.groq_api_key == "file_key"
    assert config.allowed_channel_ids == [111, 222]


def test_config_immutability():
    config = Config(
        discord_token="token",
        groq_api_key="key",
    )
    with pytest.raises(FrozenInstanceError):
        config.discord_token = "new_token"  # type: ignore
