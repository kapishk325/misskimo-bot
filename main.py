"""Main entrypoint for Misskimo Discord Bot."""

import logging
import signal
import sys
from typing import Any

from misskimo.bot import MisskimoBot
from misskimo.config import load_config
from misskimo.engine import GroqRoastEngine
from misskimo.history_buffer import ChannelHistoryManager

logger = logging.getLogger("misskimo")


def setup_logging() -> None:
    """Configure structured logging for stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_signal_handlers() -> None:
    """Register termination signal handlers for graceful shutdown."""

    def handle_signal(signum: int, _frame: Any) -> None:
        signame = (
            signal.Signals(signum).name
            if hasattr(signal, "Signals")
            else str(signum)
        )
        logger.info(
            "Received termination signal %s (%d). Shutting down...",
            signame,
            signum,
        )
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main() -> None:
    """Initialize dependencies and run Misskimo bot client."""
    setup_logging()
    logger.info("Starting Misskimo Discord Bot...")

    try:
        config = load_config()
    except Exception as exc:
        logger.critical("Failed to load configuration: %s", exc)
        sys.exit(1)
        return

    setup_signal_handlers()

    history = ChannelHistoryManager(max_messages=config.max_history_messages)
    engine = GroqRoastEngine(api_key=config.groq_api_key, model=config.groq_model)
    bot = MisskimoBot(config=config, history=history, engine=engine)

    try:
        bot.run(config.discord_token, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Misskimo bot shutdown completed gracefully.")
    except Exception as exc:
        logger.critical(
            "Fatal error encountered in bot execution: %s", exc, exc_info=True
        )
        sys.exit(1)
        return


if __name__ == "__main__":
    main()
