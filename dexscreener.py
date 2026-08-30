"""
Gets REAL trading volume for tokens from Dexscreener, which actually
tracks live DEX activity (unlike Blockscout's generic token list, which
mostly reflects tokens with recognized price feeds - not the flood of
brand-new memecoins that matter most here).

No API key needed - Dexscreener's core endpoints are free and public.
Batches lookups 30 addresses at a time (their max per call) to stay
well within the free rate limit.
"""
import httpx
from config import DEXSCREENER_BASE_URL, DEXSCREENER_CHAIN_ID

BATCH_SIZE = 30


async def enrich_with_volume(tokens: list[dict]) -> list[dict]:
    """
    Takes [{"address", "symbol", "name"}, ...] from blockscout.py and
    adds "volume_h1" (that token's total 1-hour trading volume in USD,
    summed across all its trading pairs, 0.0 if it has none).

    NOTE: this hasn't been run against live Dexscreener responses yet.
    If the response shape differs from what's parsed below, send me the
    raw JSON and I'll fix the parsing immediately.
    """
    by_address = {t["address"].lower(): t for t in tokens if t.get("address")}
    addresses = list(by_address.keys())

    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, len(addresses), BATCH_SIZE):
            batch = addresses[i:i + BATCH_SIZE]
            url = f"{DEXSCREENER_BASE_URL}/tokens/v1/{DEXSCREENER_CHAIN_ID}/{','.join(batch)}"

            resp = await client.get(url)
            if resp.status_code != 200:
                continue  # skip this batch, keep going with the rest

            pairs = resp.json()
            if not isinstance(pairs, list):
                continue

            for pair in pairs:
                base_address = (pair.get("baseToken", {}) or {}).get("address", "").lower()
                token = by_address.get(base_address)
                if not token:
                    continue

                volume_h1 = (pair.get("volume", {}) or {}).get("h1", 0) or 0
                token["volume_h1"] = token.get("volume_h1", 0.0) + float(volume_h1)

    # Any token with no matching pair on Dexscreener just has no trading activity
    for t in tokens:
        t.setdefault("volume_h1", 0.0)

    return tokens
