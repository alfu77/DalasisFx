import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from config import DATABASE_PATH

def get_connection(db_path=None):
    """Returns a SQLite connection with row factory enabled."""
    path = Path(db_path or DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes tables for rate cache, rate history snapshots, and user conversions."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Table for full rates cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_cache (
            base_currency TEXT PRIMARY KEY,
            rates_json TEXT NOT NULL,
            provider_update_time TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for tracking rate changes over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_currency TEXT NOT NULL,
            target_currency TEXT NOT NULL,
            rate REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table for recent user conversions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            amount REAL NOT NULL,
            result REAL NOT NULL,
            rate REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def save_rates_to_cache(base_currency, rates_dict, provider_time, db_path=None):
    """Save exchange rates payload to SQLite cache."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO rate_cache (base_currency, rates_json, provider_update_time, cached_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(base_currency) DO UPDATE SET
            rates_json = excluded.rates_json,
            provider_update_time = excluded.provider_update_time,
            cached_at = excluded.cached_at
    """, (base_currency.upper(), json.dumps(rates_dict), provider_time, now_iso))
    conn.commit()
    conn.close()

def get_rates_from_cache(base_currency, db_path=None):
    """Retrieve exchange rates payload from SQLite cache."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rates_json, provider_update_time, cached_at 
        FROM rate_cache 
        WHERE base_currency = ?
    """, (base_currency.upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "rates": json.loads(row["rates_json"]),
            "provider_update_time": row["provider_update_time"],
            "cached_at": row["cached_at"]
        }
    return None

def log_conversion(from_curr, to_curr, amount, result, rate, db_path=None):
    """Record an individual conversion transaction in SQLite."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversion_history (from_currency, to_currency, amount, result, rate, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (from_curr.upper(), to_curr.upper(), float(amount), float(result), float(rate), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def get_recent_conversions(limit=10, db_path=None):
    """Retrieve recent user conversions."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, from_currency, to_currency, amount, result, rate, created_at
        FROM conversion_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def record_rate_snapshot(base_currency, target_currency, rate, db_path=None):
    """Record a snapshot of a rate for historical tracking."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rate_snapshots (base_currency, target_currency, rate, timestamp)
        VALUES (?, ?, ?, ?)
    """, (base_currency.upper(), target_currency.upper(), float(rate), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def get_historical_snapshots(base_currency, target_currency, limit=30, db_path=None):
    """Get snapshot history for a specific currency pair."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rate, timestamp
        FROM rate_snapshots
        WHERE base_currency = ? AND target_currency = ?
        ORDER BY id DESC
        LIMIT ?
    """, (base_currency.upper(), target_currency.upper(), limit))
    rows = cursor.fetchall()
    conn.close()
    # return in chronological order
    return [dict(r) for r in reversed(rows)]
