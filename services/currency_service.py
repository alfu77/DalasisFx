import requests
import time
import math
from datetime import datetime, timezone
from config import API_BASE_URL, CACHE_DURATION_SECONDS, POPULAR_CURRENCIES, ALL_CURRENCY_METADATA
import database

# In-memory cache dictionary: { 'USD': { 'rates': {...}, 'fetched_at': float, 'provider_time': '...' } }
_MEMORY_CACHE = {}

def get_currency_list():
    """Return the list of popular currencies with rich metadata."""
    return POPULAR_CURRENCIES

def validate_currency_code(code: str) -> bool:
    """Check if the currency code is valid uppercase 3-letter alphanumeric code."""
    if not code or not isinstance(code, str):
        return False
    code = code.strip().upper()
    return len(code) == 3 and code.isalpha()

def fetch_exchange_rates(base_currency: str = "USD", force_refresh: bool = False, db_path=None):
    """
    Fetch exchange rates for base_currency.
    Uses in-memory cache, falls back to SQLite cache, or queries live API.
    If the network call fails, falls back to SQLite cached data regardless of age.
    """
    base = base_currency.strip().upper()
    now_ts = time.time()

    # 1. Check in-memory cache
    if not force_refresh and base in _MEMORY_CACHE:
        cache_entry = _MEMORY_CACHE[base]
        if now_ts - cache_entry["fetched_at"] < CACHE_DURATION_SECONDS:
            return {
                "base": base,
                "rates": cache_entry["rates"],
                "provider_update_time": cache_entry["provider_time"],
                "source": "memory_cache"
            }

    # 2. Check SQLite cache
    if not force_refresh:
        cached_db = database.get_rates_from_cache(base, db_path=db_path)
        if cached_db:
            try:
                cached_at_dt = datetime.fromisoformat(cached_db["cached_at"])
                if cached_at_dt.tzinfo is None:
                    cached_at_dt = cached_at_dt.replace(tzinfo=timezone.utc)
                age_seconds = (datetime.now(timezone.utc) - cached_at_dt).total_seconds()
                if age_seconds < CACHE_DURATION_SECONDS:
                    _MEMORY_CACHE[base] = {
                        "rates": cached_db["rates"],
                        "fetched_at": now_ts - age_seconds,
                        "provider_time": cached_db["provider_update_time"]
                    }
                    return {
                        "base": base,
                        "rates": cached_db["rates"],
                        "provider_update_time": cached_db["provider_update_time"],
                        "source": "sqlite_cache"
                    }
            except Exception:
                pass

    # 3. Query External API
    api_url = f"{API_BASE_URL}/{base}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("result") == "error":
            raise ValueError(data.get("error-type", "API returned an error"))

        rates = data.get("rates")
        if not isinstance(rates, dict) or not rates:
            raise ValueError("Exchange-rate provider returned an invalid rates payload")
        # Reject malformed provider values before caching them.
        clean_rates = {}
        for code, value in rates.items():
            if isinstance(code, str) and validate_currency_code(code):
                try:
                    numeric_rate = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(numeric_rate) and numeric_rate > 0:
                    clean_rates[code.upper()] = numeric_rate
        rates = clean_rates
        if base not in rates:
            # Some providers include the base rate; normalize it for same-base consistency.
            rates[base] = 1.0
        if not rates:
            raise ValueError("Exchange-rate provider returned no usable rates")
        provider_time = data.get("time_last_update_utc", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC"))

        # Save to SQLite and memory
        database.save_rates_to_cache(base, rates, provider_time, db_path=db_path)
        _MEMORY_CACHE[base] = {
            "rates": rates,
            "fetched_at": now_ts,
            "provider_time": provider_time
        }

        # Snapshot key currencies for history charts (especially GMD, EUR, GBP, XOF)
        for target in ["GMD", "EUR", "GBP", "XOF"]:
            if target in rates:
                database.record_rate_snapshot(base, target, rates[target], db_path=db_path)

        return {
            "base": base,
            "rates": rates,
            "provider_update_time": provider_time,
            "source": "live_api"
        }

    except Exception as e:
        # Fallback to SQLite cache even if expired
        stale = database.get_rates_from_cache(base, db_path=db_path)
        if stale:
            return {
                "base": base,
                "rates": stale["rates"],
                "provider_update_time": stale["provider_update_time"] + " (Offline Mode)",
                "source": "stale_fallback",
                "warning": f"Network fetch failed ({str(e)}). Using cached rates."
            }
        raise RuntimeError(f"Failed to fetch exchange rates for {base}: {str(e)}")

def convert_currency(from_currency: str, to_currency: str, amount: float, db_path=None):
    """
    Perform conversion from one currency to another.
    Logs conversion to database.
    """
    if amount is None or not math.isfinite(float(amount)) or amount < 0:
        raise ValueError("Amount must be a finite, non-negative number")

    from_c = from_currency.strip().upper()
    to_c = to_currency.strip().upper()

    if not validate_currency_code(from_c) or not validate_currency_code(to_c):
        raise ValueError("Invalid currency code provided")

    if from_c == to_c:
        result = amount
        rate = 1.0
        provider_time = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")
    else:
        # Fetch rates with base = from_c
        rates_data = fetch_exchange_rates(from_c, db_path=db_path)
        rates = rates_data["rates"]

        if to_c not in rates:
            raise ValueError(f"Exchange rate for currency '{to_c}' is not available")

        rate = float(rates[to_c])
        result = amount * rate
        provider_time = rates_data.get("provider_update_time", "")

    # Record conversion in history
    database.log_conversion(from_c, to_c, amount, result, rate, db_path=db_path)

    # Return conversion details
    return {
        "from": from_c,
        "to": to_c,
        "amount": round(amount, 4),
        "result": round(result, 4),
        "rate": rate,
        "inverse_rate": round(1 / rate, 6) if rate > 0 else 0,
        "provider_update_time": provider_time,
        "from_meta": ALL_CURRENCY_METADATA.get(from_c, {"code": from_c, "name": from_c, "symbol": "", "flag": "🌐"}),
        "to_meta": ALL_CURRENCY_METADATA.get(to_c, {"code": to_c, "name": to_c, "symbol": "", "flag": "🌐"}),
    }

def get_popular_rates(base_currency: str = "USD", db_path=None):
    """
    Returns exchange rates for Gambian-relevant currencies against the specified base.
    """
    base = base_currency.strip().upper()
    rates_data = fetch_exchange_rates(base, db_path=db_path)
    rates = rates_data["rates"]

    target_codes = ["GMD", "USD", "EUR", "GBP", "XOF", "GNF", "SLE", "NGN", "CAD", "CNY", "GHS"]
    popular_list = []

    for code in target_codes:
        if code == base:
            continue
        if code in rates:
            meta = ALL_CURRENCY_METADATA.get(code, {"code": code, "name": code, "symbol": code, "flag": "🌐"})
            popular_list.append({
                "code": code,
                "name": meta["name"],
                "symbol": meta["symbol"],
                "flag": meta["flag"],
                "rate": round(rates[code], 4),
                "inverse_rate": round(1 / rates[code], 6) if rates[code] > 0 else 0
            })

    return {
        "base": base,
        "provider_update_time": rates_data.get("provider_update_time"),
        "popular_rates": popular_list
    }
