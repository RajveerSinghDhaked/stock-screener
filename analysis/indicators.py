import pandas as pd
import numpy as np
from config import (
    EMA_SHORT, EMA_MID, EMA_LONG, RSI_PERIOD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, ATR_PERIOD,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER,
    ADX_PERIOD, ICHIMOKU_TENKAN, ICHIMOKU_KIJUN, ICHIMOKU_SENKOU,
    SAR_AF, SAR_MAX, STOCH_RSI_K, STOCH_RSI_D, STOCH_RSI_SMOOTH,
)


def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(close, period=RSI_PERIOD):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(close):
    ema_fast = calculate_ema(close, MACD_FAST)
    ema_slow = calculate_ema(close, MACD_SLOW)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, MACD_SIGNAL)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(close):
    sma = close.rolling(window=BB_PERIOD).mean()
    std = close.rolling(window=BB_PERIOD).std()
    upper = sma + (BB_STD * std)
    lower = sma - (BB_STD * std)
    pct_b = (close - lower) / (upper - lower)
    bandwidth = (upper - lower) / sma
    return upper, sma, lower, pct_b, bandwidth


def calculate_atr(high, low, close, period=ATR_PERIOD):
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_supertrend(high, low, close, period=SUPERTREND_PERIOD, multiplier=SUPERTREND_MULTIPLIER):
    atr = calculate_atr(high, low, close, period)
    hl2 = (high + low) / 2

    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            supertrend.iloc[i] = upper_band.iloc[i]

    return supertrend, direction


def calculate_ichimoku(high, low, close):
    tenkan = (high.rolling(window=ICHIMOKU_TENKAN).max() +
              low.rolling(window=ICHIMOKU_TENKAN).min()) / 2

    kijun = (high.rolling(window=ICHIMOKU_KIJUN).max() +
             low.rolling(window=ICHIMOKU_KIJUN).min()) / 2

    senkou_a = ((tenkan + kijun) / 2).shift(ICHIMOKU_KIJUN)
    senkou_b = ((high.rolling(window=ICHIMOKU_SENKOU).max() +
                 low.rolling(window=ICHIMOKU_SENKOU).min()) / 2).shift(ICHIMOKU_KIJUN)

    chikou = close.shift(-ICHIMOKU_KIJUN)

    return tenkan, kijun, senkou_a, senkou_b, chikou


def calculate_fibonacci_levels(high, low, lookback=60):
    recent_high = high.tail(lookback).max()
    recent_low = low.tail(lookback).min()
    diff = recent_high - recent_low

    levels = {
        "0.0": recent_high,
        "0.236": recent_high - diff * 0.236,
        "0.382": recent_high - diff * 0.382,
        "0.5": recent_high - diff * 0.5,
        "0.618": recent_high - diff * 0.618,
        "0.786": recent_high - diff * 0.786,
        "1.0": recent_low,
    }
    return levels, recent_high, recent_low


def calculate_adx(high, low, close, period=ADX_PERIOD):
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr = calculate_atr(high, low, close, period)

    plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period).mean() / atr)

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.ewm(alpha=1 / period).mean()

    return adx, plus_di, minus_di


def calculate_parabolic_sar(high, low, close, af=SAR_AF, max_af=SAR_MAX):
    length = len(close)
    sar = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    ep = pd.Series(index=close.index, dtype=float)
    af_series = pd.Series(index=close.index, dtype=float)

    is_long = True
    sar_val = low.iloc[0]
    ep_val = high.iloc[0]
    af_val = af

    sar.iloc[0] = sar_val
    direction.iloc[0] = 1
    ep.iloc[0] = ep_val
    af_series.iloc[0] = af_val

    for i in range(1, length):
        if is_long:
            sar_val = sar_val + af_val * (ep_val - sar_val)
            sar_val = min(sar_val, low.iloc[i - 1])
            if i >= 2:
                sar_val = min(sar_val, low.iloc[i - 2])

            if low.iloc[i] < sar_val:
                is_long = False
                sar_val = ep_val
                ep_val = low.iloc[i]
                af_val = af
            else:
                if high.iloc[i] > ep_val:
                    ep_val = high.iloc[i]
                    af_val = min(af_val + af, max_af)
        else:
            sar_val = sar_val + af_val * (ep_val - sar_val)
            sar_val = max(sar_val, high.iloc[i - 1])
            if i >= 2:
                sar_val = max(sar_val, high.iloc[i - 2])

            if high.iloc[i] > sar_val:
                is_long = True
                sar_val = ep_val
                ep_val = high.iloc[i]
                af_val = af
            else:
                if low.iloc[i] < ep_val:
                    ep_val = low.iloc[i]
                    af_val = min(af_val + af, max_af)

        sar.iloc[i] = sar_val
        direction.iloc[i] = 1 if is_long else -1
        ep.iloc[i] = ep_val
        af_series.iloc[i] = af_val

    return sar, direction


def calculate_stoch_rsi(close, rsi_period=RSI_PERIOD, k_period=STOCH_RSI_K,
                        d_period=STOCH_RSI_D, smooth=STOCH_RSI_SMOOTH):
    rsi = calculate_rsi(close, rsi_period)
    stoch_rsi = (rsi - rsi.rolling(window=k_period).min()) / \
                (rsi.rolling(window=k_period).max() - rsi.rolling(window=k_period).min())
    k = stoch_rsi.rolling(window=smooth).mean() * 100
    d = k.rolling(window=d_period).mean()
    return k, d


def calculate_volume_ma(volume, period=20):
    return volume.rolling(window=period).mean()


def compute_all_indicators(df):
    if df is None or len(df) < EMA_LONG:
        return None

    result = df.copy()

    result["ema20"] = calculate_ema(result["close"], EMA_SHORT)
    result["ema50"] = calculate_ema(result["close"], EMA_MID)
    result["ema200"] = calculate_ema(result["close"], EMA_LONG)

    result["rsi"] = calculate_rsi(result["close"])

    macd_line, signal_line, histogram = calculate_macd(result["close"])
    result["macd"] = macd_line
    result["macd_signal"] = signal_line
    result["macd_hist"] = histogram

    bb_upper, bb_mid, bb_lower, pct_b, bandwidth = calculate_bollinger_bands(result["close"])
    result["bb_upper"] = bb_upper
    result["bb_mid"] = bb_mid
    result["bb_lower"] = bb_lower
    result["bb_pct_b"] = pct_b
    result["bb_bandwidth"] = bandwidth

    result["atr"] = calculate_atr(result["high"], result["low"], result["close"])

    st, st_dir = calculate_supertrend(result["high"], result["low"], result["close"])
    result["supertrend"] = st
    result["supertrend_dir"] = st_dir

    tenkan, kijun, senkou_a, senkou_b, chikou = calculate_ichimoku(
        result["high"], result["low"], result["close"]
    )
    result["ichimoku_tenkan"] = tenkan
    result["ichimoku_kijun"] = kijun
    result["ichimoku_senkou_a"] = senkou_a
    result["ichimoku_senkou_b"] = senkou_b

    fib_levels, fib_high, fib_low = calculate_fibonacci_levels(
        result["high"], result["low"]
    )
    result["fib_high"] = fib_high
    result["fib_low"] = fib_low
    for level, price in fib_levels.items():
        result[f"fib_{level}"] = price

    adx, plus_di, minus_di = calculate_adx(result["high"], result["low"], result["close"])
    result["adx"] = adx
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di

    sar, sar_dir = calculate_parabolic_sar(result["high"], result["low"], result["close"])
    result["sar"] = sar
    result["sar_dir"] = sar_dir

    k, d = calculate_stoch_rsi(result["close"])
    result["stoch_rsi_k"] = k
    result["stoch_rsi_d"] = d

    result["volume_ma"] = calculate_volume_ma(result["volume"])

    latest = result.iloc[-1]
    volume_ratio = latest["volume"] / latest["volume_ma"] if latest["volume_ma"] > 0 else 1.0

    return {
        "current_price": float(latest["close"]),
        "ema20": float(latest["ema20"]) if not pd.isna(latest["ema20"]) else None,
        "ema50": float(latest["ema50"]) if not pd.isna(latest["ema50"]) else None,
        "ema200": float(latest["ema200"]) if not pd.isna(latest["ema200"]) else None,
        "rsi": float(latest["rsi"]) if not pd.isna(latest["rsi"]) else 50.0,
        "macd": float(latest["macd"]) if not pd.isna(latest["macd"]) else 0.0,
        "macd_signal": float(latest["macd_signal"]) if not pd.isna(latest["macd_signal"]) else 0.0,
        "macd_hist": float(latest["macd_hist"]) if not pd.isna(latest["macd_hist"]) else 0.0,
        "bb_upper": float(latest["bb_upper"]) if not pd.isna(latest["bb_upper"]) else None,
        "bb_mid": float(latest["bb_mid"]) if not pd.isna(latest["bb_mid"]) else None,
        "bb_lower": float(latest["bb_lower"]) if not pd.isna(latest["bb_lower"]) else None,
        "bb_width": float(latest["bb_bandwidth"]) if not pd.isna(latest["bb_bandwidth"]) else None,
        "atr": float(latest["atr"]) if not pd.isna(latest["atr"]) else 0.0,
        "supertrend": float(latest["supertrend"]) if not pd.isna(latest["supertrend"]) else None,
        "supertrend_signal": "buy" if latest.get("supertrend_dir") == 1 else "sell",
        "adx": float(latest["adx"]) if not pd.isna(latest["adx"]) else 0.0,
        "plus_di": float(latest["plus_di"]) if not pd.isna(latest["plus_di"]) else 0.0,
        "minus_di": float(latest["minus_di"]) if not pd.isna(latest["minus_di"]) else 0.0,
        "ichimoku_tenkan": float(latest["ichimoku_tenkan"]) if not pd.isna(latest["ichimoku_tenkan"]) else None,
        "ichimoku_kijun": float(latest["ichimoku_kijun"]) if not pd.isna(latest["ichimoku_kijun"]) else None,
        "ichimoku_senkou_a": float(latest["ichimoku_senkou_a"]) if not pd.isna(latest["ichimoku_senkou_a"]) else None,
        "ichimoku_senkou_b": float(latest["ichimoku_senkou_b"]) if not pd.isna(latest["ichimoku_senkou_b"]) else None,
        "price_above_cloud": float(latest["close"]) > max(
            float(latest["ichimoku_senkou_a"]) if not pd.isna(latest["ichimoku_senkou_a"]) else 0,
            float(latest["ichimoku_senkou_b"]) if not pd.isna(latest["ichimoku_senkou_b"]) else 0,
        ),
        "stochrsi_k": float(latest["stoch_rsi_k"]) if not pd.isna(latest["stoch_rsi_k"]) else 50.0,
        "stochrsi_d": float(latest["stoch_rsi_d"]) if not pd.isna(latest["stoch_rsi_d"]) else 50.0,
        "volume_ratio": round(volume_ratio, 2),
        "obv_trend": 1 if volume_ratio > 1.0 else -1,
        "sar": float(latest["sar"]) if not pd.isna(latest["sar"]) else None,
        "sar_signal": "buy" if latest.get("sar_dir") == 1 else "sell",
        "fib_high": float(latest["fib_high"]) if not pd.isna(latest.get("fib_high")) else None,
        "fib_low": float(latest["fib_low"]) if not pd.isna(latest.get("fib_low")) else None,
    }
