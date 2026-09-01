"""
Compares each token's volume THIS cycle to its own recent average, and
flags anything that jumped by SPIKE_MULTIPLIER or more. Works the same
way for a coin that's existed for months or one that appeared an hour
ago - it just uses however much history it has so far (as little as a
single prior reading), rather than requiring a fixed warm-up period.

Each token only ever alerts once (see state.is_alerted /
state.mark_alerted) - after that it's skipped for good.
"""
import time
from config import SPIKE_MULTIPLIER, MIN_BASELINE_VOLUME_USD, NEW_ACTIVITY_THRESHOLD_USD
from state import record_reading, is_alerted, mark_alerted


def check_for_spikes(state: dict, tokens_snapshot: list[dict]) -> list[dict]:
    """
    Updates state's token_history with this snapshot, and returns a list
    of NEW spikes found (tokens that haven't already alerted before):
    [{"address", "symbol", "name", "cycle_volume", "baseline_avg", "multiplier"}, ...]
    "multiplier" is None when the token had no real baseline to compare
    against (brand-new activity, flagged on absolute volume instead).
    """
    now = int(time.time())
    spikes = []

    for token in tokens_snapshot:
        address = token["address"]
        if not address:
            continue

        if is_alerted(state, address):
            record_reading(state, address, now, token["volume_h1"])
            continue

        history = state["token_history"].get(address, [])

        if len(history) >= 1:
            previous_volume = history[-1].get("volume_h1", 0.0)
            cycle_volume = max(token["volume_h1"] - previous_volume, 0.0)

            # Baseline = average of whatever past cycle-over-cycle deltas
            # we've seen so far - even just one. No minimum wait required,
            # so this works the same for a token we just discovered as
            # for one we've tracked for days.
            past_deltas = []
            for i in range(1, len(history)):
                delta = max(history[i].get("volume_h1", 0.0) - history[i - 1].get("volume_h1", 0.0), 0.0)
                past_deltas.append(delta)
            baseline_avg = sum(past_deltas) / len(past_deltas) if past_deltas else 0.0

            spike = None
            if baseline_avg >= MIN_BASELINE_VOLUME_USD:
                if cycle_volume >= baseline_avg * SPIKE_MULTIPLIER:
                    spike = {
                        "address": address,
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "cycle_volume": round(cycle_volume, 2),
                        "baseline_avg": round(baseline_avg, 2),
                        "multiplier": round(cycle_volume / baseline_avg, 1),
                    }
            else:
                if cycle_volume >= NEW_ACTIVITY_THRESHOLD_USD:
                    spike = {
                        "address": address,
                        "symbol": token["symbol"],
                        "name": token["name"],
                        "cycle_volume": round(cycle_volume, 2),
                        "baseline_avg": round(baseline_avg, 2),
                        "multiplier": None,
                    }

            if spike:
                spikes.append(spike)
                mark_alerted(state, address)

        record_reading(state, address, now, token["volume_h1"])

    return spikes
