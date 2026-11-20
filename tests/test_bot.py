"""Tests for Misskimo Discord bot client and autonomous trigger logic."""

import time
from unittest.mock import AsyncMock, MagicMock, patch
import discord
import pytest

from misskimo.bot import MisskimoBot
from misskimo.config import Config
from misskimo.engine import GroqRoastEngine
from misskimo.history_buffer import ChannelHistoryManager


def make_bot(
    allowed_channel_ids: list[int] | None = None,
    chime_chance: float = 0.5,
    cooldown_seconds: int = 30,
) -> MisskimoBot:
    """Helper to create a configured MisskimoBot with mock dependencies."""
    if allowed_channel_ids is None:
        allowed_channel_ids = [100, 200]

    config = Config(
        discord_token="fake_token",
        groq_api_key="gsk_fake_key",
        allowed_channel_ids=allowed_channel_ids,
        chime_chance=chime_chance,
        cooldown_seconds=cooldown_seconds,
    )
    history = ChannelHistoryManager()
    engine = MagicMock(spec=GroqRoastEngine)
    bot = MisskimoBot(config=config, history=history, engine=engine)

    mock_user = MagicMock()
    mock_user.id = 9999
    mock_user.mentioned_in = MagicMock(return_value=False)
    bot._user = mock_user

    return bot


def make_message(
    content: str = "Hello world",
    author_name: str = "Alice",
    channel_id: int = 100,
    is_bot: bool = False,
    mentions: list[MagicMock] | None = None,
) -> MagicMock:
    """Helper to create a mock Discord message with channel and author."""
    msg = MagicMock(spec=discord.Message)
    msg.content = content
    msg.author = MagicMock()
    msg.author.display_name = author_name
    msg.author.name = author_name
    msg.author.bot = is_bot
    msg.channel = MagicMock()
    msg.channel.id = channel_id

    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)
    msg.channel.typing = MagicMock(return_value=typing_cm)

    msg.channel.send = AsyncMock()
    msg.reply = AsyncMock()
    msg.mentions = mentions if mentions is not None else []
    return msg


# --- Initialization & Event Tests ---


def test_bot_initialization_defaults():
    """Verify MisskimoBot sets expected intents, state, and dependencies."""
    bot = make_bot()
    assert bot.intents.messages is True
    assert bot.intents.message_content is True
    assert bot.intents.guilds is True
    assert bot.last_chime_times == {}
    assert isinstance(bot.history, ChannelHistoryManager)


def test_bot_initialization_custom_intents():
    """Verify custom intents are preserved if provided."""
    custom_intents = discord.Intents.none()
    custom_intents.messages = True
    config = Config(discord_token="fake", groq_api_key="fake")
    history = ChannelHistoryManager()
    engine = MagicMock(spec=GroqRoastEngine)

    bot = MisskimoBot(
        config=config, history=history, engine=engine, intents=custom_intents
    )
    assert bot.intents.messages is True
    assert bot.intents.guilds is False


@pytest.mark.asyncio
async def test_on_ready_sets_presence():
    """Verify on_ready sets Tokyo rain listening activity."""
    bot = make_bot()
    bot.change_presence = AsyncMock()

    await bot.on_ready()

    bot.change_presence.assert_awaited_once()
    activity = bot.change_presence.call_args.kwargs.get("activity")
    assert activity is not None
    assert activity.type == discord.ActivityType.listening
    assert activity.name == "Tokyo rain | don't"


# --- Trigger & Filter Tests (should_respond) ---


def test_should_respond_ignores_bots():
    """Bot authors should always be ignored."""
    bot = make_bot()
    msg = make_message(is_bot=True)

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is False
    assert is_mention is False


def test_should_respond_ignores_self_user():
    """Messages from the bot itself should be ignored."""
    bot = make_bot()
    msg = make_message()
    msg.author = bot.user

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is False
    assert is_mention is False


def test_should_respond_disallowed_channel_ignored():
    """Messages in channels outside allowed_channel_ids should be ignored."""
    bot = make_bot(allowed_channel_ids=[100, 200])
    msg = make_message(channel_id=999)

    should_resp, _ = bot.should_respond(msg)
    assert should_resp is False


def test_should_respond_disallowed_channel_ignores_even_with_mention():
    """Mentions in disallowed channels should still be ignored."""
    bot = make_bot(allowed_channel_ids=[100, 200])
    msg = make_message(channel_id=999, mentions=[bot.user])

    should_resp, _ = bot.should_respond(msg)
    assert should_resp is False


def test_should_respond_empty_allowed_channels_allows_any():
    """When allowed_channel_ids is empty, any channel should be evaluated."""
    bot = make_bot(allowed_channel_ids=[])
    msg = make_message(channel_id=999, mentions=[bot.user])

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is True
    assert is_mention is True


def test_should_respond_direct_mention_in_mentions_list():
    """Direct mention in message.mentions triggers response immediately."""
    bot = make_bot()
    msg = make_message(channel_id=100, mentions=[bot.user])

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is True
    assert is_mention is True


def test_should_respond_direct_mention_via_mentioned_in():
    """Direct mention detected via user.mentioned_in triggers response."""
    bot = make_bot()
    bot.user.mentioned_in.return_value = True
    msg = make_message(channel_id=100, mentions=[])

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is True
    assert is_mention is True


def test_should_respond_direct_mention_bypasses_cooldown():
    """Direct mentions bypass channel cooldown."""
    bot = make_bot(cooldown_seconds=60)
    bot.last_chime_times[100] = time.time()  # Active cooldown
    msg = make_message(channel_id=100, mentions=[bot.user])

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is True
    assert is_mention is True


def test_should_respond_direct_mention_bypasses_zero_chime_chance():
    """Direct mentions bypass 0% chime chance."""
    bot = make_bot(chime_chance=0.0)
    msg = make_message(channel_id=100, mentions=[bot.user])

    should_resp, is_mention = bot.should_respond(msg)
    assert should_resp is True
    assert is_mention is True


def test_cooldown_prevents_autonomous_chime():
    """Active cooldown suppresses autonomous chime even if random chance passes."""
    bot = make_bot(cooldown_seconds=30)
    bot.last_chime_times[100] = time.time() - 10  # 10s ago < 30s
    msg = make_message(channel_id=100, mentions=[])

    with patch("random.random", return_value=0.01):
        should_resp, is_mention = bot.should_respond(msg)

    assert should_resp is False
    assert is_mention is False


def test_autonomous_chime_succeeds_when_cooldown_expired_and_chance_passes():
    """Autonomous chime triggers when cooldown has passed and probability check succeeds."""
    bot = make_bot(chime_chance=0.5, cooldown_seconds=30)
    bot.last_chime_times[100] = time.time() - 35  # Cooldown passed
    msg = make_message(channel_id=100, mentions=[])

    with patch("random.random", return_value=0.3):  # 0.3 < 0.5
        should_resp, is_mention = bot.should_respond(msg)

    assert should_resp is True
    assert is_mention is False


def test_autonomous_chime_fails_when_probability_fails():
    """Autonomous chime does not trigger when random check is greater than chime_chance."""
    bot = make_bot(chime_chance=0.5, cooldown_seconds=30)
    bot.last_chime_times[100] = time.time() - 35  # Cooldown passed
    msg = make_message(channel_id=100, mentions=[])

    with patch("random.random", return_value=0.8):  # 0.8 >= 0.5
        should_resp, is_mention = bot.should_respond(msg)

    assert should_resp is False
    assert is_mention is False


# --- Message Handler Tests (on_message) ---


@pytest.mark.asyncio
async def test_on_message_adds_incoming_message_to_history():
    """All incoming valid messages are recorded into history, even if unresponded."""
    bot = make_bot()
    msg = make_message(
        content="Random banter", author_name="Bob", channel_id=100
    )

    with patch.object(bot, "should_respond", return_value=(False, False)):
        await bot.on_message(msg)

    history = bot.history.get_history(100)
    assert len(history) == 1
    assert history[0] == {"author": "Bob", "content": "Random banter"}


@pytest.mark.asyncio
async def test_on_message_ignores_self_message():
    """Messages from the bot itself are ignored and not recorded."""
    bot = make_bot()
    msg = make_message(content="I am speaking", author_name="Misskimo")
    msg.author = bot.user

    await bot.on_message(msg)

    assert len(bot.history.get_history(100)) == 0


@pytest.mark.asyncio
async def test_on_message_direct_mention_flow():
    """Direct mention triggers typing, reply without author ping, and updates history & cooldown."""
    bot = make_bot()
    bot.engine.generate_roast = AsyncMock(
        return_value="You talk too much for someone saying nothing."
    )
    msg = make_message(
        content="@Misskimo roast me",
        author_name="Charlie",
        channel_id=100,
        mentions=[bot.user],
    )

    before_time = time.time()
    await bot.on_message(msg)
    after_time = time.time()

    msg.channel.typing.assert_called_once()
    bot.engine.generate_roast.assert_awaited_once()
    msg.reply.assert_awaited_once_with(
        "You talk too much for someone saying nothing.", mention_author=False
    )
    msg.channel.send.assert_not_called()

    history = bot.history.get_history(100)
    assert len(history) == 2
    assert history[0] == {"author": "Charlie", "content": "@Misskimo roast me"}
    assert history[1] == {
        "author": "Misskimo",
        "content": "You talk too much for someone saying nothing.",
    }

    assert before_time <= bot.last_chime_times[100] <= after_time


@pytest.mark.asyncio
async def test_on_message_autonomous_chime_flow():
    """Autonomous chime triggers typing, channel.send, and updates history & cooldown."""
    bot = make_bot()
    bot.engine.generate_roast = AsyncMock(
        return_value="Your confidence is wild."
    )
    msg = make_message(
        content="I think web3 will fix everything",
        author_name="Dave",
        channel_id=100,
    )

    with patch.object(bot, "should_respond", return_value=(True, False)):
        await bot.on_message(msg)

    msg.channel.typing.assert_called_once()
    bot.engine.generate_roast.assert_awaited_once()
    msg.channel.send.assert_awaited_once_with("Your confidence is wild.")
    msg.reply.assert_not_called()

    history = bot.history.get_history(100)
    assert len(history) == 2
    assert history[1] == {
        "author": "Misskimo",
        "content": "Your confidence is wild.",
    }


@pytest.mark.asyncio
async def test_on_message_truncates_long_roast():
    """Roasts exceeding Discord 2000 character limit are truncated to 2000 chars."""
    bot = make_bot()
    long_roast = "X" * 2500
    bot.engine.generate_roast = AsyncMock(return_value=long_roast)
    msg = make_message(
        content="Roast me big time",
        author_name="Eve",
        channel_id=100,
        mentions=[bot.user],
    )

    await bot.on_message(msg)

    msg.reply.assert_awaited_once_with("X" * 2000, mention_author=False)
    history = bot.history.get_history(100)
    assert len(history[1]["content"]) == 2000


@pytest.mark.asyncio
async def test_on_message_engine_returns_none():
    """When engine fails and returns None, no message is sent and bot history is not updated."""
    bot = make_bot()
    bot.engine.generate_roast = AsyncMock(return_value=None)
    msg = make_message(
        content="@Misskimo hello",
        author_name="Frank",
        channel_id=100,
        mentions=[bot.user],
    )

    await bot.on_message(msg)

    bot.engine.generate_roast.assert_awaited_once()
    msg.reply.assert_not_called()
    msg.channel.send.assert_not_called()

    history = bot.history.get_history(100)
    assert len(history) == 1
    assert history[0]["author"] == "Frank"


@pytest.mark.asyncio
async def test_on_message_handles_exception_gracefully():
    """Exceptions during roast generation are handled without crashing."""
    bot = make_bot()
    bot.engine.generate_roast = AsyncMock(
        side_effect=RuntimeError("Groq service failure")
    )
    msg = make_message(
        content="@Misskimo hello",
        author_name="Grace",
        channel_id=100,
        mentions=[bot.user],
    )

    # Should not raise
    await bot.on_message(msg)

    msg.reply.assert_not_called()
    msg.channel.send.assert_not_called()
