#!/usr/bin/env python3
"""Persistent background scan worker — runs independently of Streamlit."""
import sys
import os
import json
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


from datetime import datetime
from db.connection import init_db, get_cursor
from data.universe import get_nifty_200_symbols
from data.fetcher import fetch_stock_history, fetch_weekly_data, fetch_monthly_data
from data.cache import (
    store_daily_candles, store_weekly_candles, store_monthly_candles,
    is_daily_fresh, is_weekly_fresh, is_monthly_fresh,
    get_daily_candles, get_weekly_candles, get_monthly_candles,
)
from analysis.indicators import compute_all_indicators
from analysis.signals import detect_all_signals
from analysis.regime import detect_regime, get_regime_adjusted_weights
from analysis.scorer import compute_score
from analysis.suggestions import generate_veteran_analysis

SLEEP_SECONDS = 15 * 60


def main():
    init_db()
    while True:
        run_scan()
        time.sleep(SLEEP_SECONDS)


def run_scan():
    symbols = get_nifty_200_symbols()
    total = len(symbols)
    batch_time = datetime.now().isoformat()

    with get_cursor() as cur:
        cur.execute("DELETE FROM scan_results")
        cur.execute(
            "INSERT OR REPLACE INTO cache_metadata (table_name, last_refresh, record_count) "
            "VALUES (?, ?, ?)",
            ("worker_pid", datetime.now().isoformat(), os.getpid()),
        )

    _set_status("running")
    _set_progress(0, total, "", batch_time)

    for i, symbol in enumerate(symbols):
        try:
            daily_df = _load_or_fetch(symbol, "daily")
            weekly_df = _load_or_fetch(symbol, "weekly")
            monthly_df = _load_or_fetch(symbol, "monthly")

            if daily_df is None or len(daily_df) < 30:
                continue

            indicators = compute_all_indicators(daily_df)
            if indicators is None:
                continue

            signals = detect_all_signals(daily_df, indicators)
            regime = detect_regime(daily_df, weekly_df, monthly_df)
            regime_weights = get_regime_adjusted_weights(regime)
            score = compute_score(signals, indicators, regime_weights,
                                  regime=regime.get("regime"))

            weekly_ind = (compute_all_indicators(weekly_df)
                          if weekly_df is not None and len(weekly_df) > 20
                          else None)
            monthly_ind = (compute_all_indicators(monthly_df)
                           if monthly_df is not None and len(monthly_df) > 12
                           else None)

            analysis = generate_veteran_analysis(
                symbol, score, regime, indicators, signals,
                weekly_ind, monthly_ind,
            )

            _save_result(batch_time, symbol, score, regime, signals,
                         analysis, indicators)

        except Exception as e:
            print(f"Error {symbol}: {e}")

        _set_progress(i + 1, total, symbol, batch_time)

    _set_status("complete")
    _set_progress(total, total, "Done", batch_time)


def _load_or_fetch(symbol, tf):
    is_fresh_fn = {
        "daily": is_daily_fresh,
        "weekly": is_weekly_fresh,
        "monthly": is_monthly_fresh,
    }[tf]
    store_fn = {
        "daily": store_daily_candles,
        "weekly": store_weekly_candles,
        "monthly": store_monthly_candles,
    }[tf]
    get_fn = {
        "daily": get_daily_candles,
        "weekly": get_weekly_candles,
        "monthly": get_monthly_candles,
    }[tf]
    fetch_fn = {
        "daily": fetch_stock_history,
        "weekly": fetch_weekly_data,
        "monthly": fetch_monthly_data,
    }[tf]
    fetch_args = {
        "daily": ("1y", "1d"),
        "weekly": ("2y",),
        "monthly": ("5y",),
    }[tf]

    if is_fresh_fn(symbol):
        return get_fn(symbol)

    df = fetch_fn(symbol, *fetch_args)
    if df is not None and not df.empty:
        store_fn(symbol, df)
        return df
    return get_fn(symbol)


def _save_result(batch_time, symbol, score, regime, signals, analysis, indicators):
    comprehensive = {
        **analysis,
        "indicators": indicators,
        "regime_data": regime,
        "factor_scores": score.get("factor_scores", {}),
        "entry": score.get("entry", {}),
        "risk_reward": score.get("risk_reward", {}),
        "signal_count": score.get("signal_count", 0),
    }
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO scan_results
               (scan_date, symbol, total_score, regime, signals,
                indicator_values, recommendation, ai_analysis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                batch_time,
                symbol,
                score.get("total_score", 0),
                regime.get("regime", "unknown"),
                json.dumps(signals, cls=NumpyEncoder),
                json.dumps(indicators, cls=NumpyEncoder),
                analysis.get("recommendation", "HOLD"),
                json.dumps(comprehensive, cls=NumpyEncoder),
            ),
        )


def _set_status(status):
    val = {"idle": 0, "running": 1, "complete": 2}.get(status, 0)
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO cache_metadata (table_name, last_refresh, record_count)
               VALUES ('scan_status', ?, ?)""",
            (datetime.now().isoformat(), val),
        )


def _set_progress(current, total, stock, batch_time):
    with get_cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO cache_metadata (table_name, last_refresh, record_count)
               VALUES ('scan_progress', ?, 0)""",
            (json.dumps({
                "current": current,
                "total": total,
                "stock": stock,
                "batch_time": batch_time,
            }, cls=NumpyEncoder),),
        )


if __name__ == "__main__":
    main()
