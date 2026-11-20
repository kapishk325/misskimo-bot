import pytest
from misskimo.history_buffer import ChannelHistoryManager


def test_history_buffer_rolling_limit():
    mgr = ChannelHistoryManager(max_messages=3)
    for i in range(5):
        mgr.add_message(channel_id=123, author=f"User{i}", content=f"Message {i}")

    history = mgr.get_history(channel_id=123)
    assert len(history) == 3
    assert history[0]["author"] == "User2"
    assert history[-1]["author"] == "User4"


def test_format_history_for_prompt():
    mgr = ChannelHistoryManager(max_messages=5)
    mgr.add_message(channel_id=123, author="Alex", content="Yo look at my new kicks")
    formatted = mgr.format_history_for_prompt(channel_id=123)
    assert "Alex: Yo look at my new kicks" in formatted


def test_empty_history_format():
    mgr = ChannelHistoryManager(max_messages=5)
    formatted = mgr.format_history_for_prompt(channel_id=999)
    assert formatted == "[No previous messages in conversation history]"


def test_clear_history():
    mgr = ChannelHistoryManager(max_messages=5)
    mgr.add_message(channel_id=123, author="Alice", content="Hello")
    mgr.add_message(channel_id=456, author="Bob", content="Hey")

    mgr.clear_history(channel_id=123)

    assert mgr.get_history(channel_id=123) == []
    assert mgr.format_history_for_prompt(channel_id=123) == "[No previous messages in conversation history]"
    # Channel 456 should remain untouched
    assert len(mgr.get_history(channel_id=456)) == 1
    assert "Bob: Hey" in mgr.format_history_for_prompt(channel_id=456)


def test_multi_channel_isolation():
    mgr = ChannelHistoryManager(max_messages=5)
    mgr.add_message(channel_id=101, author="User1", content="Channel 101 msg")
    mgr.add_message(channel_id=102, author="User2", content="Channel 102 msg")

    history_101 = mgr.get_history(channel_id=101)
    history_102 = mgr.get_history(channel_id=102)

    assert len(history_101) == 1
    assert history_101[0]["content"] == "Channel 101 msg"
    assert len(history_102) == 1
    assert history_102[0]["content"] == "Channel 102 msg"


def test_default_max_messages():
    mgr = ChannelHistoryManager()
    assert mgr.max_messages == 10
    for i in range(15):
        mgr.add_message(channel_id=1, author=f"User{i}", content=f"Msg {i}")
    history = mgr.get_history(channel_id=1)
    assert len(history) == 10
    assert history[0]["author"] == "User5"
    assert history[-1]["author"] == "User14"


def test_get_history_returns_copy():
    mgr = ChannelHistoryManager(max_messages=5)
    mgr.add_message(channel_id=1, author="Alice", content="Hello")
    history = mgr.get_history(channel_id=1)
    history.append({"author": "Mallory", "content": "Hacked"})

    # Internal history should not be affected
    assert len(mgr.get_history(channel_id=1)) == 1
