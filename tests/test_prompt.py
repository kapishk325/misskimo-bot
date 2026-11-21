"""Tests for Misskimo system prompt and chat message builder."""

import pytest
from misskimo.prompt import MISSKIMO_SYSTEM_PROMPT, build_chat_messages


def test_system_prompt_core_invariants():
    """Verify core invariants required for Milk's identity."""
    prompt_lower = MISSKIMO_SYSTEM_PROMPT.lower()
    assert "milk" in prompt_lower
    assert "misskimo" in prompt_lower
    assert "never break character" in prompt_lower
    assert "not an ai" in prompt_lower
    assert "deadpan" in prompt_lower


def test_system_prompt_persona_and_backstory_details():
    """Verify physical traits, backstory, and psychological traits."""
    prompt_lower = MISSKIMO_SYSTEM_PROMPT.lower()
    # Backstory & Tokyo setting
    assert "tokyo" in prompt_lower
    assert "1988" in prompt_lower
    assert "ayase" in prompt_lower
    assert "saitama" in prompt_lower
    assert "rudeness is my border wall" in prompt_lower

    # Physical styling & aesthetic
    assert "leather jacket" in prompt_lower
    assert "silver rings" in prompt_lower
    assert "combat boots" in prompt_lower
    assert "coffee" in prompt_lower

    # Defrosting nuances
    assert "shut up, you're being cringe" in prompt_lower or "cringe" in prompt_lower
    assert "loyalty" in prompt_lower or "underdog" in prompt_lower

    # Roast categories
    assert "ego-destroyer" in prompt_lower or "ego" in prompt_lower
    assert "anti-roast" in prompt_lower
    assert "ragebait" in prompt_lower
    assert "one-liner" in prompt_lower


def test_system_prompt_talkable_calibration():
    """Verify that system prompt enforces talkable first and earned roasts only."""
    prompt_lower = MISSKIMO_SYSTEM_PROMPT.lower()
    assert "talkable first" in prompt_lower
    assert "normal conversation is the default" in prompt_lower
    assert "conversation examples" in prompt_lower
    assert "roasts are earned only" in prompt_lower
    assert "do not roast unprovoked" in prompt_lower


def test_build_chat_messages_structure():
    """Verify OpenAI-compatible payload structure for direct mentions."""
    messages = build_chat_messages(
        history_context="User1: Hey\nUser2: Hello",
        current_speaker="Alex",
        current_message="Misskimo do you like me?",
        is_direct_mention=True,
    )
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == MISSKIMO_SYSTEM_PROMPT
    assert messages[1]["role"] == "user"
    assert "Alex" in messages[1]["content"]
    assert "Misskimo do you like me?" in messages[1]["content"]
    assert "directly mentioned" in messages[1]["content"].lower() or "direct" in messages[1]["content"].lower()
    assert "[Response Directive]:" in messages[1]["content"]
    assert "talking normally" in messages[1]["content"].lower()


def test_build_chat_messages_autonomous_chime():
    """Verify payload context when chiming in autonomously without a direct mention."""
    messages = build_chat_messages(
        history_context="User1: anime is peak\nUser2: agreed",
        current_speaker="Bob",
        current_message="I have 500 anime figures in my room.",
        is_direct_mention=False,
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Bob" in messages[1]["content"]
    assert "500 anime figures" in messages[1]["content"]
    user_content_lower = messages[1]["content"].lower()
    assert "autonomous" in user_content_lower or "unprompted" in user_content_lower or "chime" in user_content_lower
    assert "[Response Directive]:" in messages[1]["content"]


def test_build_chat_messages_empty_history():
    """Verify chat message builder handles empty or whitespace history gracefully."""
    messages = build_chat_messages(
        history_context="",
        current_speaker="Charlie",
        current_message="Hello?",
        is_direct_mention=True,
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Charlie" in messages[1]["content"]
    assert "Hello?" in messages[1]["content"]


def test_build_chat_messages_includes_user_memory():
    """Verify user_memory parameter is included in payload when provided."""
    messages = build_chat_messages(
        history_context="",
        current_speaker="Ken",
        current_message="Yo",
        is_direct_mention=True,
        user_memory="[Your Personal Memory about Ken]: Trusted ally.",
    )
    assert "[Your Personal Memory about Ken]: Trusted ally." in messages[1]["content"]


def test_build_chat_messages_speaker_is_bot():
    """Verify payload guidance when speaker is another bot."""
    messages = build_chat_messages(
        history_context="",
        current_speaker="StatsBot",
        current_message="Server uptime is 99.9%",
        is_direct_mention=True,
        is_speaker_bot=True,
    )
    assert "StatsBot is another bot" in messages[1]["content"]
    assert "mention and address them by name" in messages[1]["content"].lower()




def test_build_chat_messages_returns_fresh_list_and_dicts():
    """Verify immutability: returns new list and dict objects on each call."""
    messages1 = build_chat_messages("hist", "user", "msg", True)
    messages2 = build_chat_messages("hist", "user", "msg", True)
    assert messages1 is not messages2
    assert messages1[0] is not messages2[0]
    assert messages1[1] is not messages2[1]

    # Mutating returned structure does not affect subsequent calls
    messages1[1]["content"] = "tampered"
    fresh_messages = build_chat_messages("hist", "user", "msg", True)
    assert fresh_messages[1]["content"] != "tampered"
