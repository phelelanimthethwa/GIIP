"""
Exchange Rate Service

Fetches live USD → ZAR conversion rates from exchangerate-api.com and caches
the result for one hour to avoid hammering the API on every payment request.

Environment variable required:
    EXCHANGE_RATE_API_KEY  –  your exchangerate-api.com API key
"""

import logging
import time
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache  (rate, fetched_at_epoch)
# ---------------------------------------------------------------------------
_cache: dict = {
    "rate": None,
    "fetched_at": 0.0,
}
CACHE_TTL_SECONDS = 3600  # refresh rate every hour
FALLBACK_USD_TO_ZAR = 18.5  # conservative fallback if the API is unreachable


def get_usd_to_zar_rate(api_key: str) -> Tuple[float, bool]:
    """
    Return the current USD → ZAR exchange rate.

    Returns:
        (rate, is_live)  –  rate as a float; is_live=False when using the fallback.
    """
    now = time.time()

    # Serve from cache if still fresh
    if _cache["rate"] and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        logger.debug(f"[FX] Serving cached USD/ZAR rate: {_cache['rate']}")
        return _cache["rate"], True

    if not api_key:
        logger.warning("[FX] EXCHANGE_RATE_API_KEY not set – using fallback rate.")
        return FALLBACK_USD_TO_ZAR, False

    try:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/USD/ZAR"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("result") == "success":
            rate = float(data["conversion_rate"])
            _cache["rate"] = rate
            _cache["fetched_at"] = now
            logger.info(f"[FX] Fetched live USD/ZAR rate: {rate}")
            return rate, True
        else:
            error_type = data.get("error-type", "unknown")
            logger.error(f"[FX] exchangerate-api error: {error_type}")
            return FALLBACK_USD_TO_ZAR, False

    except requests.RequestException as exc:
        logger.error(f"[FX] Could not reach exchangerate-api.com: {exc}")
        return FALLBACK_USD_TO_ZAR, False
    except Exception as exc:
        logger.error(f"[FX] Unexpected error fetching exchange rate: {exc}")
        return FALLBACK_USD_TO_ZAR, False


def convert_usd_to_zar(usd_amount: float, api_key: str) -> Tuple[float, float, bool]:
    """
    Convert a USD amount to ZAR.

    Args:
        usd_amount: Amount in US dollars.
        api_key:    exchangerate-api.com API key.

    Returns:
        (zar_amount, rate_used, is_live_rate)
    """
    rate, is_live = get_usd_to_zar_rate(api_key)
    zar_amount = round(usd_amount * rate, 2)
    logger.info(
        f"[FX] ${usd_amount:.2f} USD → R{zar_amount:.2f} ZAR "
        f"(rate={rate}, live={is_live})"
    )
    return zar_amount, rate, is_live
