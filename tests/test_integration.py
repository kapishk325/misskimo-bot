"""Integration smoke tests for Misskimo Discord bot pipeline and entrypoint."""

import signal
from unittest.mock import MagicMock, patch
import pytest

from misskimo.bot import MisskimoBot
from misskimo.config import Config
from misskimo.engine import GroqRoastEngine
from misskimo.history_buffer import ChannelHistoryManager
import main


def test_full_pipeline_instantiation():
    """Verify that all core components instantiate and wire together cleanly."""
    config = Config(
        discord_token="fake_token",
        groq_api_key="gsk_fake",
        allowed_channel_ids=[],
        chime_chance=0.15,
        cooldown_seconds=45,
    )
    history = ChannelHistoryManager(max_messages=config.max_history_messages)
    engine = GroqRoastEngine(api_key=config.groq_api_key, model=config.groq_model)
    bot = MisskimoBot(config=config, history=history, engine=engine)
    assert bot is not None
    assert bot.config == config
    assert bot.history == history
    assert bot.engine == engine


def test_setup_logging():
    """Verify that logging configuration executes without errors."""
    main.setup_logging()


def test_setup_signal_handlers():
    """Verify that signal handlers are registered for SIGINT and SIGTERM."""
    with patch("signal.signal") as mock_signal:
        main.setup_signal_handlers()
        assert mock_signal.call_count == 2
        calls = [c[0][0] for c in mock_signal.call_args_list]
        assert signal.SIGINT in calls
        assert signal.SIGTERM in calls


def test_signal_handler_raises_keyboard_interrupt():
    """Verify that invoking the registered signal handler raises KeyboardInterrupt."""
    handler_holder = {}

    def capture_signal(sig, handler):
        handler_holder[sig] = handler

    with patch("signal.signal", side_effect=capture_signal):
        main.setup_signal_handlers()
        sigint_handler = handler_holder[signal.SIGINT]
        with pytest.raises(KeyboardInterrupt):
            sigint_handler(signal.SIGINT, None)


def test_main_successful_startup_and_run():
    """Verify main entrypoint correctly wires and starts the bot."""
    fake_config = Config(
        discord_token="fake_discord_token",
        groq_api_key="gsk_fake_key",
    )
    with patch("main.load_config", return_value=fake_config), \
         patch("main.setup_signal_handlers") as mock_signals, \
         patch.object(MisskimoBot, "run") as mock_run:
        main.main()
        mock_signals.assert_called_once()
        mock_run.assert_called_once_with("fake_discord_token", log_handler=None)


def test_main_config_load_failure_exits():
    """Verify main exits with status code 1 when configuration loading fails."""
    with patch("main.load_config", side_effect=ValueError("Missing DISCORD_TOKEN")), \
         patch("sys.exit") as mock_exit:
        main.main()
        mock_exit.assert_called_once_with(1)


def test_main_handles_keyboard_interrupt():
    """Verify main catches KeyboardInterrupt and shuts down cleanly."""
    fake_config = Config(
        discord_token="fake_token",
        groq_api_key="gsk_key",
    )
    with patch("main.load_config", return_value=fake_config), \
         patch("main.setup_signal_handlers"), \
         patch.object(MisskimoBot, "run", side_effect=KeyboardInterrupt):
        main.main()


def test_main_fatal_exception_exits():
    """Verify main exits with status code 1 on fatal unexpected runtime error."""
    fake_config = Config(
        discord_token="fake_token",
        groq_api_key="gsk_key",
    )
    with patch("main.load_config", return_value=fake_config), \
         patch("main.setup_signal_handlers"), \
         patch.object(MisskimoBot, "run", side_effect=RuntimeError("Fatal network crash")), \
         patch("sys.exit") as mock_exit:
        main.main()
        mock_exit.assert_called_once_with(1)
