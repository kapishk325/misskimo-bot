"""Sliding window message history buffer per channel."""

from collections import defaultdict, deque
from typing import Final

EMPTY_HISTORY_PLACEHOLDER: Final[str] = (
    "[No previous messages in conversation history]"
)


class ChannelHistoryManager:
    """Manages sliding window message history per Discord channel."""

    def __init__(self, max_messages: int = 10) -> None:
        self.max_messages = max_messages
        self._channels: dict[int, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=self.max_messages)
        )

    def add_message(self, channel_id: int, author: str, content: str) -> None:
        """Add a message to the specified channel's history."""
        self._channels[channel_id].append({"author": author, "content": content})

    def get_history(self, channel_id: int) -> list[dict[str, str]]:
        """Return a copy of message history for the given channel."""
        if channel_id not in self._channels:
            return []
        return [dict(msg) for msg in self._channels[channel_id]]

    def format_history_for_prompt(self, channel_id: int) -> str:
        """Format channel history as a prompt context block."""
        history = self.get_history(channel_id)
        if not history:
            return EMPTY_HISTORY_PLACEHOLDER
        return "\n".join(f"{msg['author']}: {msg['content']}" for msg in history)

    def clear_history(self, channel_id: int) -> None:
        """Clear the history for the specified channel."""
        if channel_id in self._channels:
            del self._channels[channel_id]
