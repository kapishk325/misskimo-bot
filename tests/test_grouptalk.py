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
    
    is_gt, topic = bot._parse_group_talk_command("!grouptalk who has bad taste?")
    assert is_gt is True
    assert topic == "who has bad taste?"

    is_gt2, topic2 = bot._parse_group_talk_command("!grouptalk")
    assert is_gt2 is True
    assert topic2 is None

    is_gt3, topic3 = bot._parse_group_talk_command("just chatting normally")
    assert is_gt3 is False
    assert topic3 is None


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
