"""
Central configuration. Tune these numbers any time - no other code
needs to change.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Robinhood Chain's own free block explorer API - no key needed
BLOCKSCOUT_BASE_URL = "https://robinhoodchain.blockscout.com/api/v2"

# --- Scan behavior ---

# How often to check for spikes, in minutes
CHECK_INTERVAL_MINUTES = 20

# A token's volume this cycle must be at least this many times its
# recent average to count as a "sudden" spike
SPIKE_MULTIPLIER = 5

# How many past cycles to average over when building each token's
# "normal" baseline (6 cycles x 20 min = 2 hours of history)
ROLLING_HISTORY_LENGTH = 6

# Ignore tokens whose recent average volume is below this - otherwise a
# token going from $2 to $20 in volume technically "spikes 10x" but is
# meaningless noise. Only applies to tokens that DO have some baseline -
# see NEW_ACTIVITY_THRESHOLD_USD below for tokens with none.
MIN_BASELINE_VOLUME_USD = 50

# For tokens with little/no prior volume, a relative multiplier doesn't
# mean much (5x of $1 is still nothing). Instead, flag them if a single
# cycle brings in at least this much fresh volume - this is what catches
# a coin going from dead/new straight to actively trading.
NEW_ACTIVITY_THRESHOLD_USD = 500

# Safety cap on how many pages of tokens to pull from the explorer per
# check, so this stays fast even if the chain grows a lot. Each page is
# usually 50 tokens, so 10 pages = up to 500 tokens checked per cycle.
MAX_TOKEN_PAGES = 10

STATE_FILE_PATH = "bot_state.json"
