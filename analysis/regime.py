import pandas as pd
import numpy as np
from config import REGIME_DETECTION_LOOKBACK, REGIME_WEIGHTS


def detect_regime(df, weekly_df=None, monthly_df=None):
    if df is None or len(df) < 30:
        return {"regime": "unknown", "confidence": 0, "details": {}}

    daily_regime = _detect_daily_regime(df)
    weekly_regime = _detect_weekly_regime(weekly_df) if weekly_df is not None and len(weekly_df) > 20 else None
    monthly_regime = _detect_monthly_regime(monthly_df) if monthly_df is not None and len(monthly_df) > 12 else None

    regime_votes = []
    regime_votes.append(daily_regime)
    if weekly_regime:
        regime_votes.append(weekly_regime)
    if monthly_regime:
        regime_votes.append(monthly_regime)

    regime_count = {}
    for r in regime_votes:
        name = r["regime"]
        regime_count[name] = regime_count.get(name, 0) + 1

    best_regime = max(regime_count, key=regime_count.get)
    confidence = regime_count[best_regime] / len(regime_votes)

    if confidence < 0.5 and len(regime_votes) > 1:
        best_regime = daily_regime["regime"]
        confidence = 0.6

    return {
        "regime": best_regime,
        "confidence": round(confidence, 2),
        "daily": daily_regime,
        "weekly": weekly_regime,
        "monthly": monthly_regime,
        "weights": REGIME_WEIGHTS.get(best_regime, REGIME_WEIGHTS["ranging"]),
    }


def _detect_daily_regime(df):
    lookback = min(REGIME_DETECTION_LOOKBACK, len(df))
    recent = df.tail(lookback).copy()

    returns = recent["close"].pct_change(fill_method=None).dropna()
    volatility = returns.std() * np.sqrt(252) if len(returns) > 5 else 0

    avg_volume = recent["volume"].tail(20).mean()
    volume_trend = _volume_trend(recent)

    price_range = (recent["high"].max() - recent["low"].min()) / recent["close"].iloc[-1] * 100

    ema_short = recent["close"].ewm(span=20).mean()
    ema_long = recent["close"].ewm(span=50).mean()
    trend_slope = (ema_short.iloc[-1] - ema_short.iloc[-5]) / ema_short.iloc[-5] * 100 if len(ema_short) > 5 else 0
    trend_strength = abs(trend_slope)

    if volatility > 0.40:
        regime = "volatile"
    elif trend_strength > 2.0 and trend_slope > 0:
        regime = "strong_uptrend"
    elif trend_strength > 2.0 and trend_slope < 0:
        regime = "strong_downtrend"
    elif trend_strength > 1.0 and trend_slope > 0:
        regime = "uptrend"
    elif trend_strength > 1.0 and trend_slope < 0:
        regime = "downtrend"
    elif price_range < 8 and volatility < 0.25:
        regime = "ranging"
    elif volume_trend == "declining" and volatility < 0.20:
        regime = "low_volume"
    else:
        regime = "ranging"

    return {
        "regime": regime,
        "volatility": round(volatility, 4),
        "trend_slope": round(trend_slope, 2),
        "trend_strength": round(trend_strength, 2),
        "price_range_pct": round(price_range, 2),
        "avg_volume": int(avg_volume) if pd.notna(avg_volume) else 0,
        "volume_trend": volume_trend,
    }


def _detect_weekly_regime(df):
    if df is None or len(df) < 12:
        return None

    recent = df.tail(26).copy()
    returns = recent["close"].pct_change(fill_method=None).dropna()
    volatility = returns.std() * np.sqrt(52) if len(returns) > 5 else 0

    ema_short = recent["close"].ewm(span=13).mean()
    ema_long = recent["close"].ewm(span=26).mean()
    trend_slope = (ema_short.iloc[-1] - ema_short.iloc[-3]) / ema_short.iloc[-3] * 100 if len(ema_short) > 3 else 0

    if volatility > 0.35:
        regime = "volatile"
    elif abs(trend_slope) > 3.0 and trend_slope > 0:
        regime = "uptrend"
    elif abs(trend_slope) > 3.0 and trend_slope < 0:
        regime = "downtrend"
    else:
        regime = "ranging"

    return {
        "regime": regime,
        "volatility": round(volatility, 4),
        "trend_slope": round(trend_slope, 2),
    }


def _detect_monthly_regime(df):
    if df is None or len(df) < 12:
        return None

    recent = df.tail(24).copy()
    returns = recent["close"].pct_change(fill_method=None).dropna()
    volatility = returns.std() * np.sqrt(12) if len(returns) > 5 else 0

    ema_6m = recent["close"].ewm(span=6).mean()
    ema_12m = recent["close"].ewm(span=12).mean()
    golden_cross = bool(ema_6m.iloc[-1] > ema_12m.iloc[-1]) if len(ema_6m) > 12 else None

    if volatility > 0.25:
        regime = "volatile"
    elif golden_cross and volatility < 0.20:
        regime = "uptrend"
    elif golden_cross is not None and not golden_cross and volatility < 0.20:
        regime = "downtrend"
    else:
        regime = "ranging"

    return {
        "regime": regime,
        "volatility": round(volatility, 4),
        "golden_cross": golden_cross,
    }


def _volume_trend(df):
    if df is None or len(df) < 10:
        return "unknown"
    recent_5 = df["volume"].tail(5).mean()
    prev_5 = df["volume"].tail(10).head(5).mean()
    if prev_5 == 0:
        return "stable"
    ratio = (recent_5 - prev_5) / prev_5
    if ratio > 0.2:
        return "increasing"
    elif ratio < -0.2:
        return "declining"
    return "stable"


def get_regime_adjusted_weights(regime_result):
    regime = regime_result["regime"]
    return REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS["ranging"])


def get_regime_label(regime):
    labels = {
        "strong_uptrend": "Strong Uptrend",
        "uptrend": "Uptrend",
        "strong_downtrend": "Strong Downtrend",
        "downtrend": "Downtrend",
        "ranging": "Ranging / Sideways",
        "volatile": "Volatile",
        "low_volume": "Low Volume",
        "unknown": "Unknown",
    }
    return labels.get(regime, regime)


def get_regime_color(regime):
    colors = {
        "strong_uptrend": "#00C853",
        "uptrend": "#66BB6A",
        "strong_downtrend": "#FF1744",
        "downtrend": "#EF5350",
        "ranging": "#FFA726",
        "volatile": "#AB47BC",
        "low_volume": "#78909C",
        "unknown": "#546E7A",
    }
    return colors.get(regime, "#546E7A")
