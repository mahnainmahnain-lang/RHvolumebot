"""
Simple JSON-file persistence - no database needed for this scale.

Stores:
- subscribers: list of Telegram chat_ids who get alerts
- token_history: {token_address: [{"time": unix_ts, "volume_h1": float}, ...]}
- alerted_tokens: list of addresses that already got a spike alert, so
  the same coin never pings twice
"""
import json
import os
from config import STATE_FILE_PATH, ROLLING_HISTORY_LENGTH


def load_state() -> dict:
    if not os.path.exists(STATE_FILE_PATH):
        return {"subscribers": [], "token_history": {}, "alerted_tokens": []}

    with open(STATE_FILE_PATH, "r") as f:
        state = json.load(f)
        state.setdefault("alerted_tokens", [])
        return state


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
    # Keep a bounded window of past readings so this file doesn't grow forever
    max_len = ROLLING_HISTORY_LENGTH + 1
    if len(history) > max_len:
        state["token_history"][token_address] = history[-max_len:]


def is_alerted(state: dict, token_address: str) -> bool:
    return token_address in state.get("alerted_tokens", [])


def mark_alerted(state: dict, token_address: str) -> None:
    if token_address not in state["alerted_tokens"]:
        state["alerted_tokens"].append(token_address)
