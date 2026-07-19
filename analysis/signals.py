import pandas as pd
import numpy as np
from config import MIN_SIGNALS_REQUIRED


def detect_all_signals(df, indicators=None):
    if df is None or df.empty or len(df) < 5:
        return []

    if indicators is None:
        indicators = {}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    signals = []

    if _detect_ema_bullish_alignment(indicators):
        signals.append({
            "type": "trend",
            "name": "EMA Bullish Alignment",
            "action": "buy",
            "strength": 1.5,
            "description": "Price above EMA20 > EMA50 > EMA200 — strong uptrend structure",
            "level": indicators.get("ema20"),
        })

    if _detect_ema_bearish_alignment(indicators):
        signals.append({
            "type": "trend",
            "name": "EMA Bearish Alignment",
            "action": "sell",
            "strength": 1.5,
            "description": "Price below EMA20 < EMA50 < EMA200 — downtrend structure",
            "level": indicators.get("ema20"),
        })

    if _detect_macd_bullish(indicators, prev, df):
        signals.append({
            "type": "momentum",
            "name": "MACD Bullish Crossover",
            "action": "buy",
            "strength": 1.2,
            "description": "MACD crossed above signal line — momentum turning positive",
        })

    if _detect_macd_bearish(indicators, prev, df):
        signals.append({
            "type": "momentum",
            "name": "MACD Bearish Crossover",
            "action": "sell",
            "strength": 1.2,
            "description": "MACD crossed below signal line — momentum turning negative",
        })

    if _detect_bb_squeeze_breakout(indicators, df):
        breakout_dir = "up" if indicators.get("current_price", 0) > (indicators.get("bb_upper") or 0) else "down"
        signals.append({
            "type": "volatility",
            "name": f"BB Squeeze Breakout ({breakout_dir})",
            "action": "buy" if breakout_dir == "up" else "sell",
            "strength": 1.3,
            "description": f"Bollinger squeeze followed by breakout to the {breakout_dir}",
        })

    if _detect_supertrend_buy(indicators, df):
        signals.append({
            "type": "supertrend",
            "name": "Supertrend Buy",
            "action": "buy",
            "strength": 1.4,
            "description": "Supertrend flipped to buy — trend following signal active",
            "level": indicators.get("supertrend"),
        })

    if _detect_supertrend_sell(indicators, df):
        signals.append({
            "type": "supertrend",
            "name": "Supertrend Sell",
            "action": "sell",
            "strength": 1.4,
            "description": "Supertrend flipped to sell — trend turned bearish",
            "level": indicators.get("supertrend"),
        })

    if _detect_ichimoku_cloud_break(indicators, df):
        signals.append({
            "type": "ichimoku",
            "name": "Ichimoku Cloud Break",
            "action": "buy",
            "strength": 1.3,
            "description": "Price broke above Ichimoku cloud — bullish confirmation",
        })

    if _detect_volume_surge(indicators):
        vol_ratio = indicators.get("volume_ratio", 1)
        signals.append({
            "type": "volume",
            "name": "Volume Surge",
            "action": "buy",
            "strength": min(2.0, vol_ratio / 2),
            "description": f"Volume {vol_ratio:.1f}x average — strong institutional interest",
        })

    if _detect_adx_strong_trend(indicators):
        signals.append({
            "type": "trend",
            "name": "ADX Strong Trend",
            "action": "buy",
            "strength": 1.1,
            "description": f"ADX at {indicators.get('adx', 0):.0f} with +DI > -DI — trend strengthening",
        })

    if _detect_stoch_rsi_recovery(indicators, df):
        signals.append({
            "type": "rsi",
            "name": "StochRSI Oversold Recovery",
            "action": "buy",
            "strength": 1.2,
            "description": "StochRSI recovering from oversold — potential reversal",
        })

    if _detect_sar_flip_bullish(indicators, df):
        signals.append({
            "type": "pattern",
            "name": "SAR Flip Bullish",
            "action": "buy",
            "strength": 1.0,
            "description": "Parabolic SAR flipped below price — bullish trend confirmed",
        })

    if _detect_rsi_oversold(indicators):
        signals.append({
            "type": "rsi",
            "name": "RSI Oversold",
            "action": "buy",
            "strength": 1.0,
            "description": f"RSI at {indicators.get('rsi', 50):.0f} — oversold territory, watch for reversal",
        })

    if _detect_rsi_overbought(indicators):
        signals.append({
            "type": "rsi",
            "name": "RSI Overbought",
            "action": "sell",
            "strength": 1.0,
            "description": f"RSI at {indicators.get('rsi', 50):.0f} — overbought, consider booking profits",
        })

    if _detect_death_cross(df):
        signals.append({
            "type": "trend",
            "name": "Death Cross",
            "action": "sell",
            "strength": 1.8,
            "description": "EMA50 crossed below EMA200 — major bearish signal",
        })

    if _detect_golden_cross(df):
        signals.append({
            "type": "trend",
            "name": "Golden Cross",
            "action": "buy",
            "strength": 1.8,
            "description": "EMA50 crossed above EMA200 — major bullish signal",
        })

    return signals


def _detect_ema_bullish_alignment(ind):
    ema20 = ind.get("ema20")
    ema50 = ind.get("ema50")
    ema200 = ind.get("ema200")
    price = ind.get("current_price", 0)
    if ema20 is None or ema50 is None or ema200 is None:
        return False
    return price > ema20 > ema50 > ema200


def _detect_ema_bearish_alignment(ind):
    ema20 = ind.get("ema20")
    ema50 = ind.get("ema50")
    ema200 = ind.get("ema200")
    price = ind.get("current_price", 0)
    if ema20 is None or ema50 is None or ema200 is None:
        return False
    return price < ema20 < ema50 < ema200


def _detect_macd_bullish(ind, prev_row, df):
    if df is None or len(df) < 2:
        return False

    curr_macd = ind.get("macd", 0)
    curr_signal = ind.get("macd_signal", 0)

    close = df["close"]
    macd_series = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal_series = macd_series.ewm(span=9, adjust=False).mean()

    if len(macd_series) < 2:
        return False
    prev_macd = macd_series.iloc[-2]
    prev_signal = signal_series.iloc[-2]
    return prev_macd <= prev_signal and curr_macd > curr_signal


def _detect_macd_bearish(ind, prev_row, df):
    if df is None or len(df) < 2:
        return False

    curr_macd = ind.get("macd", 0)
    curr_signal = ind.get("macd_signal", 0)

    close = df["close"]
    macd_series = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal_series = macd_series.ewm(span=9, adjust=False).mean()

    if len(macd_series) < 2:
        return False
    prev_macd = macd_series.iloc[-2]
    prev_signal = signal_series.iloc[-2]
    return prev_macd >= prev_signal and curr_macd < curr_signal


def _detect_bb_squeeze_breakout(ind, df, window=20):
    bb_width = ind.get("bb_width")
    if bb_width is None or bb_width == 0:
        return False
    if len(df) < window:
        return False
    close = df["close"]
    sma = close.rolling(20).mean()
    std = close.rolling(20).std()
    bw = (2 * std) / sma
    recent_bw = bw.tail(window).dropna()
    if recent_bw.empty:
        return False
    min_bw = recent_bw.min()
    if min_bw == 0:
        return False
    if bb_width > min_bw * 1.2:
        price = ind.get("current_price", 0)
        bb_upper = ind.get("bb_upper")
        bb_lower = ind.get("bb_lower")
        if bb_upper and price > bb_upper:
            return True
        if bb_lower and price < bb_lower:
            return True
    return False


def _detect_supertrend_buy(ind, df):
    if df is None or len(df) < 12:
        return False

    high = df["high"]
    low = df["low"]
    close = df["close"]

    atr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1).rolling(window=10).mean()

    hl2 = (high + low) / 2
    upper_band = hl2 + (3.0 * atr)
    lower_band = hl2 - (3.0 * atr)

    direction = pd.Series(index=close.index, dtype=float)
    direction.iloc[0] = 1
    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    if len(direction) < 2:
        return False
    return direction.iloc[-2] == -1 and direction.iloc[-1] == 1


def _detect_supertrend_sell(ind, df):
    if df is None or len(df) < 12:
        return False

    high = df["high"]
    low = df["low"]
    close = df["close"]

    atr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1).rolling(window=10).mean()

    hl2 = (high + low) / 2
    upper_band = hl2 + (3.0 * atr)
    lower_band = hl2 - (3.0 * atr)

    direction = pd.Series(index=close.index, dtype=float)
    direction.iloc[0] = 1
    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    if len(direction) < 2:
        return False
    return direction.iloc[-2] == 1 and direction.iloc[-1] == -1


def _detect_ichimoku_cloud_break(ind, df):
    if df is None or len(df) < 35:
        return False

    high = df["high"]
    low = df["low"]
    close = df["close"]

    tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
    kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)

    if len(senkou_a.dropna()) < 2 or len(senkou_b.dropna()) < 2:
        return False

    curr_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    curr_cloud_top = max(senkou_a.iloc[-1], senkou_b.iloc[-1])
    prev_cloud_top = max(senkou_a.iloc[-2], senkou_b.iloc[-2])

    return prev_price <= prev_cloud_top and curr_price > curr_cloud_top


def _detect_volume_surge(ind):
    vol_ratio = ind.get("volume_ratio", 1)
    return vol_ratio > 1.5


def _detect_adx_strong_trend(ind):
    adx = ind.get("adx", 0)
    plus_di = ind.get("plus_di", 0)
    minus_di = ind.get("minus_di", 0)
    return adx > 25 and plus_di > minus_di


def _detect_stoch_rsi_recovery(ind, df):
    k = ind.get("stochrsi_k", 50)
    if k > 30:
        return False
    if len(df) < 20:
        return False

    close = df["close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi_min = rsi.rolling(window=14).min()
    rsi_max = rsi.rolling(window=14).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
    k_series = stoch_rsi.rolling(window=14).mean() * 100

    if len(k_series) < 3:
        return False
    prev_k = k_series.iloc[-2]
    curr_k = k_series.iloc[-1]
    return prev_k < 25 and curr_k > prev_k


def _detect_sar_flip_bullish(ind, df):
    sar_signal = ind.get("sar_signal")
    if sar_signal != "buy":
        return False
    if len(df) < 2:
        return False
    return True


def _detect_rsi_oversold(ind):
    rsi = ind.get("rsi", 50)
    return rsi < 30


def _detect_rsi_overbought(ind):
    rsi = ind.get("rsi", 50)
    return rsi > 70


def _detect_death_cross(df):
    if len(df) < 200:
        return False
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    ema200 = df["close"].ewm(span=200, adjust=False).mean()
    if len(ema50) < 2 or len(ema200) < 2:
        return False
    prev_diff = ema50.iloc[-2] - ema200.iloc[-2]
    curr_diff = ema50.iloc[-1] - ema200.iloc[-1]
    return prev_diff >= 0 and curr_diff < 0


def _detect_golden_cross(df):
    if len(df) < 200:
        return False
    ema50 = df["close"].ewm(span=50, adjust=False).mean()
    ema200 = df["close"].ewm(span=200, adjust=False).mean()
    if len(ema50) < 2 or len(ema200) < 2:
        return False
    prev_diff = ema50.iloc[-2] - ema200.iloc[-2]
    curr_diff = ema50.iloc[-1] - ema200.iloc[-1]
    return prev_diff <= 0 and curr_diff > 0


def filter_qualified_stocks(all_signals, min_signals=MIN_SIGNALS_REQUIRED):
    qualified = {}
    for symbol, signals in all_signals.items():
        active_count = len(signals)
        if active_count >= min_signals:
            qualified[symbol] = {
                "signals": signals,
                "active_count": active_count,
            }
    return qualified
