"""Discord bot client and autonomous trigger engine for Misskimo."""

import logging
import random
import time
from typing import Any, Optional
import discord

from misskimo.config import Config
from misskimo.engine import GroqRoastEngine
from misskimo.history_buffer import ChannelHistoryManager
from misskimo.prompt import build_chat_messages

logger = logging.getLogger(__name__)


class MisskimoBot(discord.Client):
    """Misskimo Discord bot client with autonomous trigger and roast generation."""

    def __init__(
        self,
        config: Config,
        history: ChannelHistoryManager,
        engine: GroqRoastEngine,
        **kwargs: Any,
    ) -> None:
        """Initialize Misskimo bot client with intents and runtime state."""
        intents = kwargs.pop("intents", None)
        if intents is None:
            intents = discord.Intents.default()
            intents.messages = True
            intents.message_content = True
            intents.guilds = True

        super().__init__(intents=intents, **kwargs)
        self.config = config
        self.history = history
        self.engine = engine
        self.last_chime_times: dict[int, float] = {}
        self._user: Optional[Any] = None

    @property
    def user(self) -> Optional[Any]:
        """Return the connected client user, or overridden test user."""
        if hasattr(self, "_user") and self._user is not None:
            return self._user
        return super().user

    @user.setter
    def user(self, value: Optional[Any]) -> None:
        """Set the user property (supports testing mocks)."""
        self._user = value

    async def on_ready(self) -> None:
        """Handle gateway ready event and set bot presence."""
        logger.info("Misskimo logged in as %s", self.user)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="Tokyo rain | don't",
            )
        )

    def should_respond(self, message: discord.Message) -> tuple[bool, bool]:
        """Determine whether Misskimo should respond to a Discord message.

        Args:
            message: Incoming Discord message to evaluate.

        Returns:
            tuple[bool, bool]: (should_respond, is_direct_mention)
        """
        bot_user = self.user
        if getattr(message.author, "bot", False) or (
            bot_user is not None and message.author == bot_user
        ):
            return (False, False)

        channel_id = getattr(message.channel, "id", None)
        if (
            self.config.allowed_channel_ids
            and channel_id not in self.config.allowed_channel_ids
        ):
            return (False, False)

        if self._is_direct_mention(message, bot_user):
            return (True, True)

        return self._should_autonomous_chime(channel_id)

    def _is_direct_mention(
        self, message: discord.Message, bot_user: Optional[Any]
    ) -> bool:
        """Check if the bot user was directly mentioned or replied to in the message."""
        if bot_user is None:
            return False

        mentions = getattr(message, "mentions", None) or []
        if bot_user in mentions:
            return True

        if hasattr(bot_user, "mentioned_in") and callable(bot_user.mentioned_in):
            try:
                if bot_user.mentioned_in(message):
                    return True
            except Exception:
                pass

        # Check if message is a Discord reply to Misskimo (even if author disabled @ping)
        ref = getattr(message, "reference", None)
        if ref is not None:
            resolved = getattr(ref, "resolved", None)
            if resolved is not None and getattr(resolved, "author", None) == bot_user:
                return True

        return False

    def _should_autonomous_chime(self, channel_id: Optional[int]) -> tuple[bool, bool]:
        """Evaluate channel cooldown and probability for autonomous chime-in."""
        if channel_id is None:
            return (False, False)

        last_chime = self.last_chime_times.get(channel_id, 0.0)
        if time.time() - last_chime < self.config.cooldown_seconds:
            return (False, False)

        if random.random() < self.config.chime_chance:
            return (True, False)

        return (False, False)

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming Discord message, buffer history, and dispatch response."""
        bot_user = self.user
        if bot_user is not None and message.author == bot_user:
            return

        channel_id = getattr(message.channel, "id", None)
        if channel_id is None:
            return

        if getattr(message.author, "bot", False):
            return

        if (
            self.config.allowed_channel_ids
            and channel_id not in self.config.allowed_channel_ids
        ):
            return

        author_name = getattr(
            message.author, "display_name", getattr(message.author, "name", "Unknown")
        )
        self.history.add_message(channel_id, author_name, message.content)

        should_respond, is_direct_mention = self.should_respond(message)
        if not should_respond:
            return

        self.last_chime_times[channel_id] = time.time()
        history_context = self.history.format_history_for_prompt(channel_id)
        chat_messages = build_chat_messages(
            history_context, author_name, message.content, is_direct_mention
        )

        await self._generate_and_send_roast(
            message=message,
            channel_id=channel_id,
            chat_messages=chat_messages,
            is_direct_mention=is_direct_mention,
        )

    async def _generate_and_send_roast(
        self,
        message: discord.Message,
        channel_id: int,
        chat_messages: list[dict[str, str]],
        is_direct_mention: bool,
    ) -> None:
        """Invoke Groq engine and send the formatted roast to Discord."""
        try:
            async with message.channel.typing():
                roast = await self.engine.generate_roast(chat_messages)

            if not roast:
                return

            if len(roast) > 2000:
                roast = roast[:2000]

            if is_direct_mention:
                try:
                    await message.reply(roast, mention_author=False)
                except Exception:
                    # Fallback to standard channel message if original message was deleted
                    await message.channel.send(roast)
            else:
                await message.channel.send(roast)

            self.history.add_message(channel_id, "Misskimo", roast)

        except Exception as exc:
            logger.error(
                "Error processing roast in channel %s: %s",
                channel_id,
                exc,
                exc_info=True,
            )
