import json
import pytest
from misskimo.user_memory import UserMemoryManager, UserProfile


def test_get_profile_new_user(tmp_path):
    storage = tmp_path / "memory.json"
    mgr = UserMemoryManager(storage_path=str(storage))

    profile = mgr.get_profile(12345, "Alex")
    assert profile.user_id == 12345
    assert profile.name == "Alex"
    assert profile.interaction_count == 0
    assert profile.rapport_tier == "stranger"
    assert profile.notes == []


def test_record_interaction_updates_profile(tmp_path):
    storage = tmp_path / "memory.json"
    mgr = UserMemoryManager(storage_path=str(storage))

    mgr.record_interaction(
        user_id=12345,
        name="Alex",
        user_msg="hey Misskimo, I brought you some black coffee",
        bot_reply="...shut up, who told you to be nice? thanks though.",
    )

    profile = mgr.get_profile(12345, "Alex")
    assert profile.interaction_count == 1
    assert profile.rapport_tier in ["soft_spot", "homie", "regular"]
    assert len(profile.notes) > 0


def test_record_interaction_detects_clown(tmp_path):
    storage = tmp_path / "memory.json"
    mgr = UserMemoryManager(storage_path=str(storage))

    mgr.record_interaction(
        user_id=67890,
        name="Chad",
        user_msg="yo look at my crypto gains and rolex, you're just an ai bot",
        bot_reply="your confidence has the depth of a parking lot puddle.",
    )

    profile = mgr.get_profile(67890, "Chad")
    assert profile.interaction_count == 1
    assert profile.rapport_tier == "clown"


def test_format_memory_for_prompt_stranger(tmp_path):
    storage = tmp_path / "memory.json"
    mgr = UserMemoryManager(storage_path=str(storage))

    blurb = mgr.format_memory_for_prompt(99999, "NewGuy")
    assert "NewGuy" in blurb
    assert "stranger" in blurb.lower() or "first time" in blurb.lower()


def test_format_memory_for_prompt_existing(tmp_path):
    storage = tmp_path / "memory.json"
    mgr = UserMemoryManager(storage_path=str(storage))

    mgr.record_interaction(
        user_id=111,
        name="Maya",
        user_msg="good evening misskimo, hope you ate",
        bot_reply="don't baby me.",
    )

    blurb = mgr.format_memory_for_prompt(111, "Maya")
    assert "Maya" in blurb
    assert "interactions" in blurb.lower()


def test_persistence_save_and_reload(tmp_path):
    storage = tmp_path / "memory.json"
    mgr1 = UserMemoryManager(storage_path=str(storage))
    mgr1.record_interaction(123, "Sam", "hello", "sup")

    # Load in new manager instance from same file
    mgr2 = UserMemoryManager(storage_path=str(storage))
    profile = mgr2.get_profile(123, "Sam")
    assert profile.interaction_count == 1
    assert profile.name == "Sam"
