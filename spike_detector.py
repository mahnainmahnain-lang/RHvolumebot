"""
Takes a fresh snapshot of every token's 1-hour volume (from Dexscreener),
works out how much NEW volume happened just in this cycle (current
reading minus last reading), compares that to the token's recent
average, and flags anything that jumped by SPIKE_MULTIPLIER or more.
"""
import time
from config import SPIKE_MULTIPLIER, ROLLING_HISTORY_LENGTH, MIN_BASELINE_VOLUME_USD, NEW_ACTIVITY_THRESHOLD_USD
from state import record_reading


def check_for_spikes(state: dict, tokens_snapshot: list[dict]) -> list[dict]:
    """
    Updates state's token_history with this snapshot, and returns a list
    of spikes found: [{"address", "symbol", "name", "cycle_volume",
    "baseline_avg", "multiplier"}, ...]. "multiplier" is None for tokens
    that had no meaningful baseline (brand-new activity, not a relative jump).
    """
    now = int(time.time())
    spikes = []

    for token in tokens_snapshot:
        address = token["address"]
        if not address:
            continue

        history = state["token_history"].get(address, [])

        if len(history) >= 1:
            previous_volume = history[-1].get("volume_h1", 0.0)
            cycle_volume = max(token["volume_h1"] - previous_volume, 0.0)

            # Build the baseline from prior cycle-over-cycle deltas
            past_deltas = []
            for i in range(1, len(history)):
                delta = max(history[i].get("volume_h1", 0.0) - history[i - 1].get("volume_h1", 0.0), 0.0)
                past_deltas.append(delta)

            if len(past_deltas) >= ROLLING_HISTORY_LENGTH:
                baseline_avg = sum(past_deltas) / len(past_deltas)

                if baseline_avg >= MIN_BASELINE_VOLUME_USD:
                    # Established token - flag if this cycle is a big
                    # multiple of its own normal volume
                    if cycle_volume >= baseline_avg * SPIKE_MULTIPLIER:
                        spikes.append({
                            "address": address,
                            "symbol": token["symbol"],
                            "name": token["name"],
                            "cycle_volume": round(cycle_volume, 2),
                            "baseline_avg": round(baseline_avg, 2),
                            "multiplier": round(cycle_volume / baseline_avg, 1),
                        })
                else:
                    # Little/no prior volume - a multiplier is meaningless
                    # here, so flag on absolute fresh volume instead. This
                    # is what catches a dead/new token suddenly trading.
                    if cycle_volume >= NEW_ACTIVITY_THRESHOLD_USD:
                        spikes.append({
                            "address": address,
                            "symbol": token["symbol"],
                            "name": token["name"],
                            "cycle_volume": round(cycle_volume, 2),
                            "baseline_avg": round(baseline_avg, 2),
                            "multiplier": None,
                        })

        record_reading(state, address, now, token["volume_h1"])

    return spikes
