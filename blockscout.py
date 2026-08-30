"""
Discovers every token contract deployed on Robinhood Chain via the free
explorer API (Blockscout) - no key required. This does NOT give us
reliable volume data (see dexscreener.py for that) - it just gives us
the full list of token addresses to check, since Blockscout indexes
every deployed contract regardless of whether it has trading activity.
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


async def get_all_token_addresses() -> list[dict]:
    """
    Returns [{"address": str, "symbol": str, "name": str}, ...] for every
    token the explorer returns, up to the page cap. No volume data here -
    Blockscout's own volume figures are unreliable for brand-new tokens
    without integrated price feeds, which is most memecoins on this chain.
    """
    tokens = []
    params = {}

    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        for _ in range(MAX_TOKEN_PAGES):
            resp = await client.get(f"{BLOCKSCOUT_BASE_URL}/tokens", params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                address = item.get("address")
                if address:
                    tokens.append({
                        "address": address,
                        "symbol": item.get("symbol"),
                        "name": item.get("name"),
                    })

            next_page = data.get("next_page_params")
            if not next_page:
                break
            params = next_page

    return tokens
