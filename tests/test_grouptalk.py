import pytest
from unittest.mock import AsyncMock, MagicMock
from misskimo.prompt import build_group_talk_messages, build_chat_messages
from misskimo.bot import MisskimoBot
from misskimo.config import Config
from misskimo.history_buffer import ChannelHistoryManager
from misskimo.engine import GroqRoastEngine
from misskimo.user_memory import UserMemoryManager


def test_build_group_talk_messages_with_topic():
    messages = build_group_talk_messages(
        history_context="Alex: I sleep at 4am\nBob: same",
        caller_name="Maya",
        topic="who has the worst sleep schedule?",
        participants_summary="Alex (homie), Bob (stranger)",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    content = messages[1]["content"]
    assert "Maya" in content
    assert "worst sleep schedule" in content
    assert "Alex (homie)" in content


def test_build_group_talk_messages_without_topic():
    messages = build_group_talk_messages(
        history_context="Alex: hello\nBob: hey",
        caller_name="Alex",
        topic=None,
        participants_summary="Alex, Bob",
    )
    content = messages[1]["content"]
    assert "general room vibe" in content.lower() or "current conversation" in content.lower()


def make_bot(tmp_path):
    config = Config(
        discord_token="fake_token",
        groq_api_key="gsk_fake",
        allowed_channel_ids=[],
        chime_chance=0.12,
        cooldown_seconds=45,
    )
    history = ChannelHistoryManager()
    engine = MagicMock(spec=GroqRoastEngine)
    memory = UserMemoryManager(storage_path=str(tmp_path / "memory.json"))
    bot = MisskimoBot(config=config, history=history, engine=engine, memory=memory)
    bot.user = MagicMock()
    bot.user.id = 9999
    bot.user.name = "misskimo"
    bot.user.mentioned_in = MagicMock(return_value=False)
    return bot


def test_is_group_talk_command(tmp_path):
    bot = make_bot(tmp_path)
    
    # Standard prefix commands
    is_gt, topic = bot._parse_group_talk_command("!grouptalk who has bad taste?")
    assert is_gt is True
    assert topic == "who has bad taste?"

    is_gt2, topic2 = bot._parse_group_talk_command("!grouptalk")
    assert is_gt2 is True
    assert topic2 is None

    # Variations with space ("group talk")
    is_gt_space, topic_space = bot._parse_group_talk_command("group talk")
    assert is_gt_space is True
    assert topic_space is None

    is_gt_space_excl, topic_space_excl = bot._parse_group_talk_command("!group talk who's asleep?")
    assert is_gt_space_excl is True
    assert topic_space_excl == "who's asleep?"

    is_gt_slash, topic_slash = bot._parse_group_talk_command("/group talk")
    assert is_gt_slash is True
    assert topic_slash is None

    # Milk prefixes and topic specifiers
    is_gt_milk, topic_milk = bot._parse_group_talk_command("Milk group talk who has the worst fits?")
    assert is_gt_milk is True
    assert topic_milk == "who has the worst fits?"

    is_gt_colon, topic_colon = bot._parse_group_talk_command("Milk: group talk topic: weekend plans")
    assert is_gt_colon is True
    assert topic_colon == "weekend plans"

    is_gt_at, topic_at = bot._parse_group_talk_command("@milk grouptalk")
    assert is_gt_at is True

    # Other aliases
    is_gt_vibe, _ = bot._parse_group_talk_command("vibe check")
    assert is_gt_vibe is True

    is_gt_round, _ = bot._parse_group_talk_command("!round table")
    assert is_gt_round is True

    # Non-command chatter
    is_gt3, topic3 = bot._parse_group_talk_command("just chatting normally")
    assert is_gt3 is False
    assert topic3 is None

    is_gt4, topic4 = bot._parse_group_talk_command("milk is good for bones")
    assert is_gt4 is False
    assert topic4 is None


@pytest.mark.asyncio
async def test_on_message_handles_grouptalk_command(tmp_path):
    bot = make_bot(tmp_path)
    bot.engine.generate_roast = AsyncMock(return_value="Listen up everyone, let's talk about this room.")

    msg = MagicMock()
    msg.author.bot = False
    msg.author.id = 1234
    msg.author.display_name = "Maya"
    msg.channel.id = 100
    msg.content = "!grouptalk who is the biggest clown here?"
    msg.mentions = []
    msg.channel.typing = MagicMock()
    msg.channel.send = AsyncMock()
    msg.reply = AsyncMock()

    await bot.on_message(msg)

    bot.engine.generate_roast.assert_awaited_once()
    msg.channel.send.assert_awaited_once_with("Listen up everyone, let's talk about this room.")


def test_grouptalk_slash_command_registered(tmp_path):
    bot = make_bot(tmp_path)
    cmd = bot.tree.get_command("grouptalk")
    assert cmd is not None
    assert cmd.name == "grouptalk"
    assert "group discussion" in cmd.description.lower()


@pytest.mark.asyncio
async def test_handle_grouptalk_interaction(tmp_path):
    bot = make_bot(tmp_path)
    bot.engine.generate_roast = AsyncMock(return_value="Misskimo addressing the room.")

    interaction = MagicMock()
    interaction.channel_id = 200
    interaction.user.display_name = "Alex"
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()

    await bot._handle_grouptalk_interaction(interaction, topic="who has the worst fits?")

    interaction.response.defer.assert_awaited_once_with(thinking=True)
    bot.engine.generate_roast.assert_awaited_once()
    interaction.followup.send.assert_awaited_once_with("Misskimo addressing the room.")
    history = bot.history.get_history(200)
    assert history[-1]["content"] == "Misskimo addressing the room."

