"""
Simple JSON-file persistence - no database needed for this scale.

Stores:
- subscribers: list of Telegram chat_ids who get alerts
- token_history: {token_address: [{"time": unix_ts, "volume_h1": float}, ...]}
  (kept trimmed to ROLLING_HISTORY_LENGTH + 1 entries per token)
"""
import json
import os
from config import STATE_FILE_PATH, ROLLING_HISTORY_LENGTH


def load_state() -> dict:
    if not os.path.exists(STATE_FILE_PATH):
        return {"subscribers": [], "token_history": {}}

    with open(STATE_FILE_PATH, "r") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_FILE_PATH, "w") as f:
        json.dump(state, f)


def add_subscriber(state: dict, chat_id: int) -> bool:
    """Returns True if newly added, False if already subscribed."""
    if chat_id in state["subscribers"]:
        return False
    state["subscribers"].append(chat_id)
    save_state(state)
    return True


def remove_subscriber(state: dict, chat_id: int) -> bool:
    if chat_id not in state["subscribers"]:
        return False
    state["subscribers"].remove(chat_id)
    save_state(state)
    return True


def record_reading(state: dict, token_address: str, timestamp: int, volume_h1: float) -> None:
    history = state["token_history"].setdefault(token_address, [])
    history.append({"time": timestamp, "volume_h1": volume_h1})
    # Keep only what we need: enough past cycles for the baseline, plus this one
    max_len = ROLLING_HISTORY_LENGTH + 1
    if len(history) > max_len:
        state["token_history"][token_address] = history[-max_len:]
