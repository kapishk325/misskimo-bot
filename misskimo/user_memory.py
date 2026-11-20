"""Per-user memory and relationship tracking engine for Misskimo."""

from dataclasses import asdict, dataclass, field
import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger("misskimo.memory")

# Rapport tiers
TIER_STRANGER = "stranger"
TIER_ACQUAINTANCE = "acquaintance"
TIER_HOMIE = "homie"
TIER_CLOWN = "clown"
TIER_SOFT_SPOT = "soft_spot"


@dataclass(frozen=True)
class UserProfile:
    """Immutable snapshot of Misskimo's memory and rapport with a user."""

    user_id: int
    name: str
    interaction_count: int = 0
    rapport_tier: str = TIER_STRANGER
    notes: list[str] = field(default_factory=list)
    last_seen: float = 0.0


class UserMemoryManager:
    """Manages persistent per-user rapport and memory profiles."""

    def __init__(self, storage_path: str = "data/user_memory.json") -> None:
        self.storage_path = storage_path
        self._profiles: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load profiles from JSON file if available."""
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                self._profiles = {int(k): v for k, v in raw_data.items()}
        except Exception as exc:
            logger.warning("Could not read user memory from %s: %s", self.storage_path, exc)

    def _save(self) -> None:
        """Save profiles to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to persist user memory to %s: %s", self.storage_path, exc)

    def get_profile(self, user_id: int, name: Optional[str] = None) -> UserProfile:
        """Get or create the user's relationship profile."""
        data = self._profiles.get(user_id)
        if not data:
            return UserProfile(
                user_id=user_id,
                name=name or f"User_{user_id}",
                interaction_count=0,
                rapport_tier=TIER_STRANGER,
                notes=[],
                last_seen=0.0,
            )
        return UserProfile(
            user_id=user_id,
            name=name or data.get("name", f"User_{user_id}"),
            interaction_count=data.get("interaction_count", 0),
            rapport_tier=data.get("rapport_tier", TIER_STRANGER),
            notes=list(data.get("notes", [])),
            last_seen=data.get("last_seen", 0.0),
        )

    def record_interaction(
        self, user_id: int, name: str, user_msg: str, bot_reply: str
    ) -> None:
        """Record an interaction, update rapport, and extract memory notes."""
        profile = self.get_profile(user_id, name)
        count = profile.interaction_count + 1
        notes = list(profile.notes)
        tier = profile.rapport_tier

        user_lower = user_msg.lower()

        # Check for clown / flexer / hostile behavior
        clown_triggers = ["crypto", "rolex", "flex", "bot", "ai", "dumb", "ugly", "bitch", "loser", "poor"]
        if any(trig in user_lower for trig in clown_triggers):
            tier = TIER_CLOWN
            notes.append(f"Acted cocky/hostile or called you a bot ('{user_msg[:40]}...')")

        # Check for warmth / caring / food / coffee / genuine kindness
        warmth_triggers = ["coffee", "tea", "eat", "hungry", "care", "safe", "warmth", "kind", "drink", "rest"]
        if any(trig in user_lower for trig in warmth_triggers):
            if tier != TIER_CLOWN:
                tier = TIER_SOFT_SPOT
                notes.append(f"Showed quiet kindness or care ('{user_msg[:40]}...')")

        # Normal relationship progression
        if tier == TIER_STRANGER and count >= 3:
            tier = TIER_ACQUAINTANCE
        elif tier == TIER_ACQUAINTANCE and count >= 7:
            tier = TIER_HOMIE

        # Keep max 5 most recent notes
        if len(notes) > 5:
            notes = notes[-5:]

        self._profiles[user_id] = {
            "user_id": user_id,
            "name": name,
            "interaction_count": count,
            "rapport_tier": tier,
            "notes": notes,
            "last_seen": time.time(),
        }
        self._save()

    def format_memory_for_prompt(self, user_id: int, name: Optional[str] = None) -> str:
        """Format a concise memory blurb for prompt injection."""
        profile = self.get_profile(user_id, name)
        display_name = profile.name or (name if name else f"User_{user_id}")

        if profile.interaction_count == 0:
            return (
                f"[Your Memory of {display_name}]: You haven't spoken before. "
                "They are a stranger—be cool, observant, and talkable, don't roast unless they provoke you."
            )

        notes_str = "; ".join(profile.notes) if profile.notes else "No specific incidents noted"
        tier_guidance = {
            TIER_STRANGER: "Stranger. Talkable, cool, and dry.",
            TIER_ACQUAINTANCE: "Familiar regular. You recognize them; casual easy banter.",
            TIER_HOMIE: "Trusted regular / homie. You talk openly and have relaxed mutual respect.",
            TIER_CLOWN: "Clown / flexer. On your roast radar. Drop heavy attitude if they start slipping.",
            TIER_SOFT_SPOT: (
                "Secret soft spot. They've shown unbothered warmth or kindness. "
                "You act flustered and defensive ('shut up, cringe'), but you secretly appreciate them."
            ),
        }.get(profile.rapport_tier, "Cool and neutral.")

        return (
            f"[Your Memory of {display_name}]\n"
            f"- Rapport: {profile.rapport_tier.upper()} ({profile.interaction_count} past interactions)\n"
            f"- Attitude toward them: {tier_guidance}\n"
            f"- Specific Memories: {notes_str}"
        )
