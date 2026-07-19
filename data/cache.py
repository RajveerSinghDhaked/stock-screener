import pandas as pd
import json
from datetime import datetime
from db.connection import get_cursor
from config import (
    CACHE_DAILY_MAX_AGE_HOURS, CACHE_WEEKLY_MAX_AGE_HOURS,
    CACHE_MONTHLY_MAX_AGE_HOURS, CACHE_QUOTE_MAX_AGE_MINUTES,
)


# ═══════════════════════════════════════════════════════════════
# CANDLE STORAGE
# ═══════════════════════════════════════════════════════════════

def store_daily_candles(symbol, df):
    rows = [(symbol, row["date"], row["open"], row["high"], row["low"],
             row["close"], int(row["volume"])) for _, row in df.iterrows()]
    with get_cursor() as cur:
        cur.executemany(
            """INSERT OR REPLACE INTO daily_candles (symbol, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def store_weekly_candles(symbol, df):
    rows = [(symbol, row["date"], row["open"], row["high"], row["low"],
             row["close"], int(row["volume"])) for _, row in df.iterrows()]
    with get_cursor() as cur:
        cur.executemany(
            """INSERT OR REPLACE INTO weekly_candles (symbol, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def store_monthly_candles(symbol, df):
    rows = [(symbol, row["date"], row["open"], row["high"], row["low"],
             row["close"], int(row["volume"])) for _, row in df.iterrows()]
    with get_cursor() as cur:
        cur.executemany(
            """INSERT OR REPLACE INTO monthly_candles (symbol, date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def store_intraday_candles(symbol, df):
    with get_cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(
                """INSERT OR REPLACE INTO intraday_candles (symbol, timestamp, open, high, low, close, volume)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (symbol, row["timestamp"], row["open"], row["high"],
                 row["low"], row["close"], int(row["volume"])),
            )


def store_live_quote(quote):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO live_quotes (symbol, ltp, change_pct, volume, fetched_at)
               VALUES (?, ?, ?, ?, ?)""",
            (quote["symbol"], quote["ltp"], quote["change_pct"],
             quote["volume"], datetime.now().isoformat()),
        )


# ═══════════════════════════════════════════════════════════════
# CANDLE RETRIEVAL
# ═══════════════════════════════════════════════════════════════

def get_daily_candles(symbol, limit=300):
    with get_cursor() as cur:
        cur.execute(
            """SELECT date, open, high, low, close, volume
               FROM daily_candles WHERE symbol = ? ORDER BY date DESC LIMIT ?""",
            (symbol, limit),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def get_weekly_candles(symbol, limit=104):
    with get_cursor() as cur:
        cur.execute(
            """SELECT date, open, high, low, close, volume
               FROM weekly_candles WHERE symbol = ? ORDER BY date DESC LIMIT ?""",
            (symbol, limit),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def get_monthly_candles(symbol, limit=60):
    with get_cursor() as cur:
        cur.execute(
            """SELECT date, open, high, low, close, volume
               FROM monthly_candles WHERE symbol = ? ORDER BY date DESC LIMIT ?""",
            (symbol, limit),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def get_intraday_candles(symbol, limit=200):
    with get_cursor() as cur:
        cur.execute(
            """SELECT timestamp, open, high, low, close, volume
               FROM intraday_candles WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?""",
            (symbol, limit),
        )
        rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def get_live_quote(symbol):
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM live_quotes WHERE symbol = ? ORDER BY fetched_at DESC LIMIT 1",
            (symbol,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════
# FRESHNESS CHECKS
# ═══════════════════════════════════════════════════════════════

def _get_last_date(table, symbol):
    with get_cursor() as cur:
        cur.execute(f"SELECT MAX(date) as last_date FROM {table} WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
    if row and row["last_date"]:
        return row["last_date"]
    return None


def _get_last_fetched(table, symbol, date_col="fetched_at"):
    with get_cursor() as cur:
        cur.execute(f"SELECT MAX({date_col}) as last FROM {table} WHERE symbol = ?", (symbol,))
        row = cur.fetchone()
    if row and row["last"]:
        return row["last"]
    return None


def _is_fresh(last_date_str, max_age_hours):
    if last_date_str is None:
        return False
    try:
        if "T" in str(last_date_str) or " " in str(last_date_str):
            last_dt = datetime.fromisoformat(str(last_date_str).replace("Z", "+00:00").split("+")[0])
        else:
            last_dt = datetime.strptime(str(last_date_str), "%Y-%m-%d")
        age = datetime.now() - last_dt
        return age.total_seconds() < max_age_hours * 3600
    except Exception:
        return False


def is_daily_fresh(symbol):
    return _is_fresh(_get_last_date("daily_candles", symbol), CACHE_DAILY_MAX_AGE_HOURS)


def is_weekly_fresh(symbol):
    return _is_fresh(_get_last_date("weekly_candles", symbol), CACHE_WEEKLY_MAX_AGE_HOURS)


def is_monthly_fresh(symbol):
    return _is_fresh(_get_last_date("monthly_candles", symbol), CACHE_MONTHLY_MAX_AGE_HOURS)


def is_quote_fresh(symbol):
    last = _get_last_fetched("live_quotes", symbol)
    return _is_fresh(last, CACHE_QUOTE_MAX_AGE_MINUTES / 60.0)


def get_cache_age(table, symbol):
    last = _get_last_date(table, symbol)
    if last is None:
        return "No data"
    try:
        if "T" in str(last) or " " in str(last):
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00").split("+")[0])
        else:
            last_dt = datetime.strptime(str(last), "%Y-%m-%d")
        diff = datetime.now() - last_dt
        hours = diff.total_seconds() / 3600
        if hours < 1:
            return f"{int(hours * 60)} min ago"
        elif hours < 24:
            return f"{int(hours)} hours ago"
        else:
            return f"{int(hours / 24)} days ago"
    except Exception:
        return "Unknown"


# ═══════════════════════════════════════════════════════════════
# STOCKS
# ═══════════════════════════════════════════════════════════════

def get_all_stocks():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM stocks WHERE is_active = 1 ORDER BY symbol")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def store_stock_info(symbol, name="", exchange="NSE", sector="", market_cap_category=""):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO stocks (symbol, name, exchange, sector, market_cap_category, last_updated)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (symbol, name, exchange, sector, market_cap_category,
             datetime.now().isoformat()),
        )


# ═══════════════════════════════════════════════════════════════
# WATCHLIST
# ═══════════════════════════════════════════════════════════════

def get_watchlist():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def add_to_watchlist(symbol, notes="", target_price=None, stop_loss=None):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO watchlist (symbol, notes, target_price, stop_loss)
               VALUES (?, ?, ?, ?)""",
            (symbol, notes, target_price, stop_loss),
        )


def remove_from_watchlist(symbol):
    with get_cursor() as cur:
        cur.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


# ═══════════════════════════════════════════════════════════════
# SCAN STATUS (for frontend-backend communication)
# ═══════════════════════════════════════════════════════════════

def save_scan_status(status):
    val = {"idle": 0, "running": 1, "complete": 2}.get(status, 0)
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO cache_metadata (table_name, last_refresh, record_count)
               VALUES ('scan_status', ?, ?)""",
            (datetime.now().isoformat(), val),
        )


def get_scan_status():
    with get_cursor() as cur:
        cur.execute("SELECT record_count FROM cache_metadata WHERE table_name = 'scan_status'")
        row = cur.fetchone()
        if not row:
            return None
        return {0: "idle", 1: "running", 2: "complete"}.get(row["record_count"])


def save_scan_progress(current, total, stock, batch_time):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO cache_metadata (table_name, last_refresh, record_count)
               VALUES ('scan_progress', ?, 0)""",
            (json.dumps({
                "current": current, "total": total,
                "stock": stock, "batch_time": batch_time,
            }),),
        )


def get_scan_progress():
    with get_cursor() as cur:
        cur.execute("SELECT last_refresh FROM cache_metadata WHERE table_name = 'scan_progress'")
        row = cur.fetchone()
        if row and row["last_refresh"]:
            return json.loads(row["last_refresh"])
        return None


def clear_scan_progress():
    with get_cursor() as cur:
        cur.execute("DELETE FROM cache_metadata WHERE table_name = 'scan_progress'")


# ═══════════════════════════════════════════════════════════════
# SCAN RESULTS (loaded by frontend)
# ═══════════════════════════════════════════════════════════════

def load_fresh_scan_results():
    with get_cursor() as cur:
        cur.execute(
            """SELECT * FROM scan_results
               WHERE scan_date = (SELECT MAX(scan_date) FROM scan_results)
               ORDER BY total_score DESC"""
        )
        rows = cur.fetchall()

    results = []
    for row in rows:
        r = dict(row)
        signals = json.loads(r.get("signals", "[]")) if r.get("signals") else []
        analysis = json.loads(r.get("ai_analysis", "{}")) if r.get("ai_analysis") else {}

        analysis.setdefault("regime", r.get("regime", "unknown"))
        analysis.setdefault("confidence_level", 0)
        analysis.setdefault("recommendation", r.get("recommendation", "HOLD"))
        analysis.setdefault("narrative", "")
        analysis.setdefault("warnings", [])
        analysis.setdefault("key_factors", [])

        factor_scores = {}
        for s in signals:
            name = s.get("name", "")
            factor_scores[name] = {
                "score": s.get("strength", 1.0),
                "weight": 1.0,
                "strength": s.get("strength", 1.0),
                "description": s.get("description", ""),
                "action": s.get("action", ""),
                "level": s.get("level"),
            }

        score = {
            "total_score": r.get("total_score", 0),
            "signal_count": len(signals),
            "entry": analysis.get("entry", {"price": 0, "method": "cached"}),
            "factor_scores": factor_scores,
            "active_signals": [s.get("name", "") for s in signals],
        }

        results.append({
            "symbol": r["symbol"],
            "analysis": analysis,
            "score": score,
            "signals": signals,
            "regime": {"regime": r.get("regime", "unknown")},
            "indicators": {},
            "daily_df": None,
            "weekly_df": None,
            "monthly_df": None,
        })

    return results


def get_stock_analysis(symbol):
    with get_cursor() as cur:
        cur.execute(
            """SELECT ai_analysis FROM scan_results
               WHERE symbol = ? AND scan_date = (SELECT MAX(scan_date) FROM scan_results)
               LIMIT 1""",
            (symbol,),
        )
        row = cur.fetchone()
        if row and row["ai_analysis"]:
            return json.loads(row["ai_analysis"])
        return None


# ═══════════════════════════════════════════════════════════════
# HISTORY (7-day recommendations)
# ═══════════════════════════════════════════════════════════════

def load_scan_history(days=7):
    with get_cursor() as cur:
        cur.execute(
            """SELECT symbol, scan_date, total_score, recommendation
               FROM scan_results
               WHERE scan_date >= datetime(?, '-' || ? || ' days')
               ORDER BY symbol, scan_date DESC""",
            (datetime.now().isoformat(), days),
        )
        rows = cur.fetchall()

    history = {}
    for row in rows:
        r = dict(row)
        sym = r["symbol"]
        if sym not in history:
            history[sym] = []
        history[sym].append({
            "date": r["scan_date"][:10] if r["scan_date"] else "",
            "score": r["total_score"],
            "recommendation": r["recommendation"],
        })
    return history


def get_stock_history(symbol, days=7):
    with get_cursor() as cur:
        cur.execute(
            """SELECT scan_date, total_score, recommendation
               FROM scan_results
               WHERE symbol = ? AND scan_date >= datetime(?, '-' || ? || ' days')
               ORDER BY scan_date DESC""",
            (symbol, datetime.now().isoformat(), days),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════

def store_pattern(pattern_name, description, market_context, outcome,
                  return_pct, success_rate, timeframe_days, examples_count):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO pattern_memory
               (pattern_name, description, market_context, outcome,
                return_pct, success_rate, timeframe_days, examples_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pattern_name, description, market_context, outcome,
             return_pct, success_rate, timeframe_days, examples_count),
        )


def get_all_patterns():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM pattern_memory ORDER BY success_rate DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def find_matching_patterns(indicators_summary):
    patterns = get_all_patterns()
    matched = []
    for p in patterns:
        score = 0
        name_lower = p["pattern_name"].lower()
        if "ema" in name_lower and indicators_summary.get("ema_bullish"):
            score += 3
        if "rsi" in name_lower and indicators_summary.get("rsi_oversold_recovery"):
            score += 3
        if "macd" in name_lower and indicators_summary.get("macd_bullish"):
            score += 3
        if "volume" in name_lower and indicators_summary.get("volume_surge"):
            score += 2
        if "bollinger" in name_lower and indicators_summary.get("bb_squeeze"):
            score += 3
        if "ichimoku" in name_lower and indicators_summary.get("ichimoku_break"):
            score += 3
        if "supertrend" in name_lower and indicators_summary.get("supertrend_buy"):
            score += 3
        if "death cross" in name_lower and indicators_summary.get("death_cross"):
            score += 5
        if score >= 2:
            matched.append({**p, "match_score": score})
    matched.sort(key=lambda x: x["match_score"], reverse=True)
    return matched[:3]


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION HISTORY
# ═══════════════════════════════════════════════════════════════

def store_recommendation(symbol, recommendation, score, entry_price, target_price, stop_loss):
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO recommendation_history
               (symbol, recommendation, score, entry_price, target_price, stop_loss)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (symbol, recommendation, score, entry_price, target_price, stop_loss),
        )


def get_recommendation_history(symbol=None, limit=50):
    with get_cursor() as cur:
        if symbol:
            cur.execute(
                "SELECT * FROM recommendation_history WHERE symbol = ? ORDER BY created_at DESC LIMIT ?",
                (symbol, limit),
            )
        else:
            cur.execute(
                "SELECT * FROM recommendation_history ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_recommended_count():
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM recommendation_history")
        row = cur.fetchone()
    return row["cnt"] if row else 0


def get_latest_scan_results(limit=50):
    with get_cursor() as cur:
        cur.execute(
            """SELECT * FROM scan_results
               WHERE scan_date = (SELECT MAX(scan_date) FROM scan_results)
               ORDER BY total_score DESC LIMIT ?""",
            (limit,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]
