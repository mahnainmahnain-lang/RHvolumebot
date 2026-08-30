"""
Takes a fresh snapshot of every token's volume_24h, works out how much
volume happened just in THIS cycle (current reading minus last
reading), compares that to the token's recent average, and flags
anything that jumped by SPIKE_MULTIPLIER or more.
"""
import time
from config import SPIKE_MULTIPLIER, ROLLING_HISTORY_LENGTH, MIN_BASELINE_VOLUME_USD
from state import record_reading


def check_for_spikes(state: dict, tokens_snapshot: list[dict]) -> list[dict]:
    """
    Updates state's token_history with this snapshot, and returns a list
    of spikes found: [{"address", "symbol", "name", "cycle_volume",
    "baseline_avg", "multiplier"}, ...]
    """
    now = int(time.time())
    spikes = []

    for token in tokens_snapshot:
        address = token["address"]
        if not address:
            continue

        history = state["token_history"].get(address, [])

        if len(history) >= 1:
            previous_volume = history[-1]["volume_24h"]
            cycle_volume = max(token["volume_24h"] - previous_volume, 0.0)

            # Build the baseline from prior cycle-over-cycle deltas
            past_deltas = []
            for i in range(1, len(history)):
                delta = max(history[i]["volume_24h"] - history[i - 1]["volume_24h"], 0.0)
                past_deltas.append(delta)

            if len(past_deltas) >= ROLLING_HISTORY_LENGTH:
                baseline_avg = sum(past_deltas) / len(past_deltas)

                if baseline_avg >= MIN_BASELINE_VOLUME_USD and cycle_volume >= baseline_avg * SPIKE_MULTIPLIER:
                    spikes.append({
                        "address": address,
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "cycle_volume": round(cycle_volume, 2),
                        "baseline_avg": round(baseline_avg, 2),
                        "multiplier": round(cycle_volume / baseline_avg, 1) if baseline_avg else None,
                    })

        record_reading(state, address, now, token["volume_24h"])

    return spikes
