import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import init_db
from data.fetcher import fetch_stock_history, fetch_weekly_data, fetch_monthly_data
from data.cache import store_daily_candles, store_weekly_candles, store_monthly_candles, get_daily_candles
from data.universe import get_nifty_200_symbols
from analysis.indicators import compute_all_indicators
from analysis.signals import detect_all_signals
from analysis.scorer import compute_score, get_recommendation
from analysis.regime import detect_regime, get_regime_adjusted_weights


def run_full_scan(progress_callback=None):
    init_db()

    symbols = get_nifty_200_symbols()
    if not symbols:
        print("ERROR: Could not get stock universe")
        return []

    total = len(symbols)
    results = []

    for i, symbol in enumerate(symbols):
        if progress_callback:
            progress_callback(i + 1, total, symbol)
        else:
            print(f"  [{i+1}/{total}] Scanning {symbol}...")

        try:
            df = fetch_stock_history(symbol, period="1y", interval="1d")
            if df is None or df.empty or len(df) < 30:
                continue

            store_daily_candles(symbol, df)

            weekly_df = fetch_weekly_data(symbol, period="2y")
            if weekly_df is not None and not weekly_df.empty:
                store_weekly_candles(symbol, weekly_df)

            monthly_df = fetch_monthly_data(symbol, period="5y")
            if monthly_df is not None and not monthly_df.empty:
                store_monthly_candles(symbol, monthly_df)

            indicators = compute_all_indicators(df)
            if indicators is None:
                continue

            signals = detect_all_signals(df, indicators)
            regime = detect_regime(df, weekly_df, monthly_df)
            regime_weights = get_regime_adjusted_weights(regime)
            score = compute_score(signals, indicators, regime_weights, regime=regime.get("regime"))
            risk_reward = score.get("risk_reward", {})
            recommendation = get_recommendation(score, risk_reward, regime=regime.get("regime"))

            results.append({
                "symbol": symbol,
                "price": indicators.get("current_price", 0),
                "total_score": score["total_score"],
                "active_signals": score["signal_count"],
                "rsi": indicators.get("rsi", 50),
                "adx": indicators.get("adx", 0),
                "recommendation": recommendation,
                "signals": signals,
                "indicators": indicators,
                "regime": regime,
                "score": score,
            })

        except Exception as e:
            print(f"  ERROR scanning {symbol}: {e}")
            continue

    results.sort(key=lambda x: x["total_score"], reverse=True)
    print(f"\nProcessed {len(results)} stocks out of {total}")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("  STOCK SCREENER - NIFTY 200 SCAN")
    print("=" * 60)

    results = run_full_scan()

    if results:
        print(f"\n{'='*60}")
        print(f"  TOP {min(20, len(results))} STOCKS")
        print(f"{'='*60}")
        print(f"{'Symbol':<15} {'Price':>10} {'Score':>8} {'Signals':>8} {'RSI':>6} {'ADX':>6} {'Rec':<12}")
        print("-" * 75)

        for r in results[:20]:
            print(
                f"{r['symbol']:<15} "
                f"{r['price']:>10.2f} "
                f"{r['total_score']:>8.1f} "
                f"{r['active_signals']:>8} "
                f"{r['rsi']:>6.1f} "
                f"{r['adx']:>6.1f} "
                f"{r['recommendation']:<12}"
            )
    else:
        print("No results found!")
