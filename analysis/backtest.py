import pandas as pd
import numpy as np
from datetime import datetime


def backtest_strategy(df, entry_signals=None, exit_signals=None, params=None, regime=None):
    if df is None or len(df) < 50:
        return {"error": "Insufficient data for backtesting"}

    params = params or {}
    take_profit_pct = params.get("take_profit_pct", 0.08)
    stop_loss_pct = params.get("stop_loss_pct", 0.04)
    max_hold_days = params.get("max_hold_days", 20)

    if entry_signals is None:
        entry_signals = _default_entry_signals
    if exit_signals is None:
        exit_signals = _default_exit_signals

    trades = []
    position = None

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        recent = df.iloc[max(0, i - 50):i + 1]

        if position is None:
            signal = entry_signals(df, i, regime=regime)
            if signal:
                position = {
                    "entry_date": row["date"],
                    "entry_price": row["close"],
                    "signal": signal,
                    "hold_days": 0,
                }
        else:
            position["hold_days"] += 1
            current_return = (row["close"] - position["entry_price"]) / position["entry_price"]

            exit_reason = None
            if current_return >= take_profit_pct:
                exit_reason = "take_profit"
            elif current_return <= -stop_loss_pct:
                exit_reason = "stop_loss"
            elif position["hold_days"] >= max_hold_days:
                exit_reason = "max_hold"
            elif exit_signals(df, i):
                exit_reason = "signal_exit"

            if exit_reason:
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": row["date"],
                    "entry_price": position["entry_price"],
                    "exit_price": row["close"],
                    "return_pct": round(current_return * 100, 2),
                    "hold_days": position["hold_days"],
                    "exit_reason": exit_reason,
                })
                position = None

    return _compute_stats(trades, df)


def _default_entry_signals(df, idx, regime=None):
    if idx < 20:
        return None

    if regime in ("strong_downtrend", "downtrend"):
        return None
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]

    price = row["close"]
    ema20 = df["close"].ewm(span=20).mean().iloc[idx]
    ema50 = df["close"].ewm(span=50).mean().iloc[idx]
    rsi = _compute_rsi(df["close"], 14).iloc[idx]
    volume = row["volume"]
    avg_vol = df["volume"].iloc[max(0, idx - 20):idx].mean()

    if (prev["close"] <= ema20 and price > ema20 and
            ema20 > ema50 and 30 < rsi < 55 and
            volume > avg_vol * 1.2):
        return "ema_crossover"

    if rsi < 32 and price > ema50:
        return "rsi_oversold"

    if idx >= 3:
        macd = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        if macd.iloc[idx - 1] < signal.iloc[idx - 1] and macd.iloc[idx] > signal.iloc[idx]:
            return "macd_cross"

    return None


def _default_exit_signals(df, idx):
    if idx < 20:
        return False
    price = df["close"].iloc[idx]
    ema20 = df["close"].ewm(span=20).mean().iloc[idx]
    rsi = _compute_rsi(df["close"], 14).iloc[idx]

    if price < ema20 * 0.98:
        return True
    if rsi > 75:
        return True
    return False


def _compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def _compute_stats(trades, df):
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "total_return": 0,
            "max_drawdown": 0,
            "profit_factor": 0,
            "sharpe_ratio": 0,
            "trades": [],
        }

    returns = [t["return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(returns) * 100 if returns else 0
    avg_return = np.mean(returns) if returns else 0
    total_return = np.sum(returns)

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.01
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    cumulative = np.cumsum(returns)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = peak - cumulative
    max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0

    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252 / np.mean([t["hold_days"] for t in trades]))
    else:
        sharpe = 0

    avg_hold = np.mean([t["hold_days"] for t in trades])
    best_trade = max(returns)
    worst_trade = min(returns)

    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    return {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_return": round(avg_return, 2),
        "total_return": round(total_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_hold_days": round(avg_hold, 1),
        "best_trade": round(best_trade, 2),
        "worst_trade": round(worst_trade, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "trades": trades,
    }


def backtest_period(df, start_date=None, end_date=None, params=None):
    if df is None or df.empty:
        return {"error": "No data"}

    if start_date:
        df = df[df["date"] >= start_date].reset_index(drop=True)
    if end_date:
        df = df[df["date"] <= end_date].reset_index(drop=True)

    return backtest_strategy(df, params=params)


def monte_carlo_backtest(df, n_simulations=100, params=None):
    if df is None or len(df) < 100:
        return {"error": "Insufficient data"}

    block_size = min(20, len(df) // 5)
    n_blocks = len(df) // block_size

    results = []
    for _ in range(n_simulations):
        blocks = []
        for _ in range(n_blocks):
            start = np.random.randint(0, len(df) - block_size)
            blocks.append(df.iloc[start:start + block_size])
        shuffled = pd.concat(blocks, ignore_index=True)
        result = backtest_strategy(shuffled, params=params)
        results.append(result)

    win_rates = [r["win_rate"] for r in results if "win_rate" in r]
    returns = [r["total_return"] for r in results if "total_return" in r]

    return {
        "simulations": n_simulations,
        "avg_win_rate": round(np.mean(win_rates), 1) if win_rates else 0,
        "avg_return": round(np.mean(returns), 2) if returns else 0,
        "worst_return": round(np.min(returns), 2) if returns else 0,
        "best_return": round(np.max(returns), 2) if returns else 0,
        "percentile_5": round(np.percentile(returns, 5), 2) if returns else 0,
        "percentile_95": round(np.percentile(returns, 95), 2) if returns else 0,
    }
