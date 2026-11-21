"""Discord bot client, autonomous message handler, and event loop for Misskimo."""

import logging
import random
import time
from typing import Any, Optional

import discord
from discord import app_commands

from misskimo.config import Config
from misskimo.engine import GroqRoastEngine
from misskimo.history_buffer import ChannelHistoryManager
from misskimo.prompt import build_chat_messages, build_group_talk_messages
from misskimo.user_memory import UserMemoryManager

logger = logging.getLogger("misskimo.bot")


class MisskimoBot(discord.Client):
    """Discord bot client running Misskimo persona with autonomous triggers."""

    def __init__(
        self,
        config: Config,
        history: ChannelHistoryManager,
        engine: GroqRoastEngine,
        memory: Optional[UserMemoryManager] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Misskimo bot client with intents, slash commands, and runtime state."""
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
        self.memory = memory if memory is not None else UserMemoryManager()
        self.last_chime_times: dict[int, float] = {}
        self.consecutive_bot_replies: dict[int, int] = {}
        self._user: Optional[Any] = None
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self) -> None:
        """Register application slash commands."""

        @self.tree.command(
            name="grouptalk",
            description="Initiate a group discussion or roast circle with Milk.",
        )
        @app_commands.describe(
            topic="Optional topic or question for the channel (e.g. 'who has the worst sleep schedule?')"
        )
        async def grouptalk_slash(
            interaction: discord.Interaction, topic: Optional[str] = None
        ) -> None:
            await self._handle_grouptalk_interaction(interaction, topic)

    async def _handle_grouptalk_interaction(
        self, interaction: discord.Interaction, topic: Optional[str] = None
    ) -> None:
        """Handle execution of the /grouptalk slash command."""
        try:
            await interaction.response.defer(thinking=True)
        except Exception:
            pass

        channel_id = interaction.channel_id
        caller_name = (
            getattr(interaction.user, "display_name", getattr(interaction.user, "name", "Someone"))
            if interaction.user
            else "Someone"
        )

        history_context = (
            self.history.format_history_for_prompt(channel_id)
            if channel_id
            else "[No history]"
        )

        history_items = self.history.get_history(channel_id) if channel_id else []
        seen_names = set()
        participants_list = []
        for item in history_items:
            name = item.get("author", "Someone")
            if name not in ("Milk", "Misskimo") and name not in seen_names:
                seen_names.add(name)
                participants_list.append(name)

        participants_summary = (
            ", ".join(participants_list) if participants_list else caller_name
        )

        chat_messages = build_group_talk_messages(
            history_context=history_context,
            caller_name=caller_name,
            topic=topic,
            participants_summary=participants_summary,
        )

        try:
            roast = await self.engine.generate_roast(chat_messages)
            if not roast:
                roast = "..."
            if len(roast) > 2000:
                roast = roast[:2000]

            await interaction.followup.send(roast)
            if channel_id:
                self.history.add_message(channel_id, "Milk", roast)
        except Exception as exc:
            logger.error("Error executing /grouptalk slash command: %s", exc, exc_info=True)
            try:
                await interaction.followup.send("Failed to speak right now. Try again.")
            except Exception:
                pass

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
        """Handle gateway ready event, sync slash commands, and set bot presence."""
        logger.info("Milk logged in as %s", self.user)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="Tokyo rain | don't",
            )
        )
        try:
            synced = await self.tree.sync()
            logger.info("Synced %d global application slash commands.", len(synced))
        except Exception as exc:
            logger.warning("Could not sync global application slash commands: %s", exc)

        for guild in getattr(self, "guilds", []):
            try:
                self.tree.copy_global_to(guild=guild)
                synced_guild = await self.tree.sync(guild=guild)
                logger.info(
                    "Synced %d slash commands to guild %s (%s).",
                    len(synced_guild),
                    getattr(guild, "name", "unknown"),
                    getattr(guild, "id", "unknown"),
                )
            except Exception as exc:
                logger.warning("Could not sync slash commands to guild %s: %s", getattr(guild, "id", None), exc)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Sync slash commands immediately when joining a new guild."""
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(
                "Synced slash commands to newly joined guild %s (%s).",
                getattr(guild, "name", "unknown"),
                getattr(guild, "id", "unknown"),
            )
        except Exception as exc:
            logger.warning("Could not sync slash commands to new guild %s: %s", getattr(guild, "id", None), exc)


    def should_respond(self, message: discord.Message) -> tuple[bool, bool]:
        """Determine whether Misskimo should respond to a Discord message.

        Args:
            message: Incoming Discord message to evaluate.

        Returns:
            tuple[bool, bool]: (should_respond, is_direct_mention)
        """
        bot_user = self.user
        is_self = bot_user is not None and (
            message.author == bot_user
            or getattr(message.author, "id", None) == getattr(bot_user, "id", None)
        )
        if is_self:
            return (False, False)

        is_bot = getattr(message.author, "bot", False)
        if is_bot and not self.config.allow_bot_replies:
            return (False, False)

        channel_id = getattr(message.channel, "id", None)
        if (
            self.config.allowed_channel_ids
            and channel_id not in self.config.allowed_channel_ids
        ):
            return (False, False)

        # Loop protection: if replying to another bot and limit reached, do not respond
        if is_bot and channel_id is not None:
            if self.consecutive_bot_replies.get(channel_id, 0) >= self.config.max_consecutive_bot_replies:
                logger.info(
                    "Bot reply loop limit (%d) reached in channel %s; suppressing bot reply.",
                    self.config.max_consecutive_bot_replies,
                    channel_id,
                )
                return (False, False)

        if self._is_direct_mention(message, bot_user):
            return (True, True)

        # Do NOT autonomously chime in on background chatter from other bots
        if is_bot:
            return (False, False)

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

    def _parse_group_talk_command(self, content: str) -> tuple[bool, Optional[str]]:
        """Check if message content triggers a group talk command.

        Returns:
            tuple[bool, Optional[str]]: (is_grouptalk, optional_topic)
        """
        text = content.strip()
        if not text:
            return (False, None)

        # Strip bot mentions / names from start
        prefixes = ["@milk", "milk", "@misskimo", "misskimo"]
        bot_user = self.user
        if bot_user and hasattr(bot_user, "id"):
            prefixes.extend([f"<@{bot_user.id}>", f"<@!{bot_user.id}>"])

        # Strip matching bot name prefixes with word boundaries
        matched_prefix = True
        while matched_prefix:
            matched_prefix = False
            for p in prefixes:
                if text.lower().startswith(p.lower()):
                    rest = text[len(p):]
                    if not rest or rest[0] in " \t:,!/.-":
                        text = rest.lstrip(" \t:,!/.-")
                        matched_prefix = True
                        break

        # Known variations of group discussion commands
        known_commands = (
            "group talk",
            "grouptalk",
            "group-talk",
            "group_talk",
            "round table",
            "roundtable",
            "vibe check",
            "vibecheck",
        )

        cleaned = text.lstrip("!/?. ")
        for cmd in known_commands:
            if cleaned.lower().startswith(cmd):
                after_cmd = cleaned[len(cmd):]
                if not after_cmd or after_cmd[0] in " \t:,!?-":
                    topic_part = after_cmd.lstrip(" \t:,!?-")
                    for t_prefix in ("topic:", "topic=", "about:", "about="):
                        if topic_part.lower().startswith(t_prefix):
                            topic_part = topic_part[len(t_prefix):].strip()
                    return (True, topic_part if topic_part else None)

        return (False, None)

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming Discord message, buffer history, and dispatch response."""
        bot_user = self.user
        if bot_user is not None and (
            message.author == bot_user
            or getattr(message.author, "id", None) == getattr(bot_user, "id", None)
        ):
            return

        channel_id = getattr(message.channel, "id", None)
        if channel_id is None:
            return

        is_bot = getattr(message.author, "bot", False)
        if is_bot and not self.config.allow_bot_replies:
            return

        if (
            self.config.allowed_channel_ids
            and channel_id not in self.config.allowed_channel_ids
        ):
            return

        # Human message resets consecutive bot replies counter for this channel
        if not is_bot:
            self.consecutive_bot_replies[channel_id] = 0

        # Loop protection check for bot authors
        if is_bot and self.consecutive_bot_replies.get(channel_id, 0) >= self.config.max_consecutive_bot_replies:
            logger.info(
                "Bot reply loop limit (%d) reached in channel %s; suppressing bot message from %s.",
                self.config.max_consecutive_bot_replies,
                channel_id,
                getattr(message.author, "display_name", getattr(message.author, "name", "bot")),
            )
            return

        author_name = getattr(
            message.author, "display_name", getattr(message.author, "name", "Unknown")
        )
        author_id = getattr(message.author, "id", 0)
        self.history.add_message(channel_id, author_name, message.content)

        # Check for group talk command (!grouptalk [topic])
        is_grouptalk, topic = self._parse_group_talk_command(message.content)
        if is_grouptalk:
            self.last_chime_times[channel_id] = time.time()
            history_context = self.history.format_history_for_prompt(channel_id)
            
            # Extract unique active participants from channel history
            history_items = self.history.get_history(channel_id)
            seen_names = set()
            participants_list = []
            for item in history_items:
                name = item.get("author", "Someone")
                if name not in ("Milk", "Misskimo") and name not in seen_names:
                    seen_names.add(name)
                    participants_list.append(name)

            participants_summary = ", ".join(participants_list) if participants_list else author_name
            chat_messages = build_group_talk_messages(
                history_context=history_context,
                caller_name=author_name,
                topic=topic,
                participants_summary=participants_summary,
            )

            await self._generate_and_send_roast(
                message=message,
                channel_id=channel_id,
                author_id=author_id,
                author_name=author_name,
                chat_messages=chat_messages,
                is_direct_mention=False,
            )
            return

        should_respond, is_direct_mention = self.should_respond(message)
        if not should_respond:
            return

        self.last_chime_times[channel_id] = time.time()
        history_context = self.history.format_history_for_prompt(channel_id)
        user_memory = self.memory.format_memory_for_prompt(author_id, author_name)
        chat_messages = build_chat_messages(
            history_context,
            author_name,
            message.content,
            is_direct_mention,
            user_memory=user_memory,
            is_speaker_bot=is_bot,
        )

        await self._generate_and_send_roast(
            message=message,
            channel_id=channel_id,
            author_id=author_id,
            author_name=author_name,
            chat_messages=chat_messages,
            is_direct_mention=is_direct_mention,
        )

    async def _generate_and_send_roast(
        self,
        message: discord.Message,
        channel_id: int,
        author_id: int,
        author_name: str,
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
                    is_bot_author = getattr(message.author, "bot", False)
                    await message.reply(roast, mention_author=is_bot_author)
                except Exception:
                    # Fallback to standard channel message if original message was deleted
                    await message.channel.send(roast)
            else:
                await message.channel.send(roast)

            self.history.add_message(channel_id, "Milk", roast)

            # Update loop protection tracking
            is_bot = getattr(message.author, "bot", False)
            if is_bot:
                self.consecutive_bot_replies[channel_id] = (
                    self.consecutive_bot_replies.get(channel_id, 0) + 1
                )
            else:
                self.consecutive_bot_replies[channel_id] = 0

            # Record memory of this interaction
            if author_id:
                self.memory.record_interaction(author_id, author_name, message.content, roast)

        except Exception as exc:
            logger.error(
                "Error processing roast in channel %s: %s",
                channel_id,
                exc,
                exc_info=True,
            )
