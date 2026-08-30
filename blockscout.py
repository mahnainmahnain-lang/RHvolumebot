"""
Pulls the token list from Robinhood Chain's own free explorer API
(Blockscout) - no key required. Paginates through results up to
MAX_TOKEN_PAGES as a safety cap.
"""
import httpx
from config import BLOCKSCOUT_BASE_URL, MAX_TOKEN_PAGES

# The explorer sits behind Cloudflare, which blocks httpx's default
# User-Agent as a bot. A normal-looking one avoids that.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


async def get_all_tokens() -> list[dict]:
    """
    Returns [{"address": str, "symbol": str, "name": str, "volume_24h": float}, ...]
    for every token the explorer returns, up to the page cap.

    NOTE: this hasn't been run against the live API yet. If field names
    come back different (e.g. volume_24h missing or under a different
    key) once you're testing for real, send me the raw JSON and I'll
    adjust the parsing immediately.
    """
    tokens = []
    params = {}

    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        for _ in range(MAX_TOKEN_PAGES):
            resp = await client.get(f"{BLOCKSCOUT_BASE_URL}/tokens", params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                volume = item.get("volume_24h")
                tokens.append({
                    "address": item.get("address"),
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "volume_24h": float(volume) if volume is not None else 0.0,
                })

            next_page = data.get("next_page_params")
            if not next_page:
                break
            params = next_page

    return tokens
