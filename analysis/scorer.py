import pandas as pd
import numpy as np
from config import (
    RISK_REWARD_RATIO, MIN_RISK_REWARD_RATIO, POSITION_SIZE_PCT,
    MAX_POSITIONS, MIN_SCORE_THRESHOLD, ATR_SL_MULTIPLIER,
)


DOWNTREND_PENALTY = 0.3


def compute_score(signals, indicators, regime_weights=None, regime=None):
    if not signals or len(signals) == 0:
        return {
            "total_score": 0,
            "factor_scores": {},
            "active_signals": [],
            "signal_count": 0,
            "regime_override": None,
        }

    is_downtrend = regime in ("strong_downtrend", "downtrend")

    factor_scores = {}
    for signal in signals:
        signal_type = signal.get("type", "")
        signal_name = signal.get("name", "")
        strength = signal.get("strength", 1.0)
        action = signal.get("action", "")
        weight = _get_signal_weight(signal_type, regime_weights)
        score = weight * strength

        if is_downtrend and action == "buy":
            score = round(score * DOWNTREND_PENALTY, 2)

        factor_scores[signal_name] = {
            "score": round(score, 2),
            "weight": weight,
            "strength": round(strength, 2),
            "description": signal.get("description", ""),
            "action": action,
            "level": signal.get("level"),
        }

    total = sum(f["score"] for f in factor_scores.values())
    max_possible = len(factor_scores) * 3.0
    normalized = (total / max_possible * 100) if max_possible > 0 else 0
    normalized = min(100, max(0, normalized))

    regime_override = None
    if is_downtrend and normalized < 50:
        regime_override = "AVOID"

    entry = _compute_entry_level(indicators)
    risk_reward = _compute_risk_reward(indicators, entry)

    return {
        "total_score": round(normalized, 1),
        "factor_scores": factor_scores,
        "active_signals": [s.get("name", "") for s in signals],
        "signal_count": len(signals),
        "entry": entry,
        "risk_reward": risk_reward,
        "max_possible": round(max_possible, 2),
        "raw_score": round(total, 2),
        "regime_override": regime_override,
    }


def _get_signal_weight(signal_type, regime_weights=None):
    if regime_weights:
        return regime_weights.get(signal_type, 1.0)
    return 1.0


def _compute_entry_level(indicators):
    if not indicators:
        return None

    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    supertrend = indicators.get("supertrend")
    bb_upper = indicators.get("bb_upper")
    bb_lower = indicators.get("bb_lower")
    current_price = indicators.get("current_price")

    if current_price is None:
        return None

    candidates = []
    if ema20:
        candidates.append(("EMA20", round(ema20, 2)))
    if ema50:
        candidates.append(("EMA50", round(ema50, 2)))
    if ema200:
        candidates.append(("EMA200", round(ema200, 2)))
    if supertrend:
        candidates.append(("Supertrend", round(supertrend, 2)))
    if bb_lower:
        candidates.append(("BB Lower", round(bb_lower, 2)))

    if not candidates:
        return {"price": round(current_price, 2), "method": "current_price"}

    support_levels = [c for c in candidates if c[1] < current_price]
    if support_levels:
        best = max(support_levels, key=lambda x: x[1])
        return {
            "price": best[1],
            "method": f"nearest support ({best[0]})",
            "all_supports": candidates,
        }

    return {
        "price": round(current_price * 0.98, 2),
        "method": "slight discount to current",
        "all_supports": candidates,
    }


def _compute_risk_reward(indicators, entry):
    if not indicators or not entry:
        return {"ratio": 0, "valid": False}

    entry_price = entry["price"]
    current_price = indicators.get("current_price", entry_price)
    atr = indicators.get("atr", 0)

    if entry_price <= 0:
        return {"ratio": 0, "valid": False}

    if atr and atr > 0:
        stop_loss = entry_price - (atr * ATR_SL_MULTIPLIER)
        target = entry_price + (atr * ATR_SL_MULTIPLIER * RISK_REWARD_RATIO)
    else:
        stop_loss = entry_price * 0.95
        target = entry_price * 1.15

    risk = entry_price - stop_loss
    reward = target - entry_price
    ratio = reward / risk if risk > 0 else 0

    return {
        "ratio": round(ratio, 2),
        "entry_price": round(entry_price, 2),
        "target": round(target, 2),
        "stop_loss": round(stop_loss, 2),
        "valid": ratio >= MIN_RISK_REWARD_RATIO,
    }


def get_recommendation(score, risk_reward, regime=None):
    total_score = score.get("total_score", 0)
    rr = risk_reward.get("ratio", 0)
    regime_override = score.get("regime_override")

    if regime_override:
        return regime_override

    is_downtrend = regime in ("strong_downtrend", "downtrend")

    if total_score >= MIN_SCORE_THRESHOLD:
        if is_downtrend:
            return "AVOID"
        if rr >= 3:
            return "STRONG_BUY"
        elif rr >= 2:
            return "BUY"
        else:
            return "ACCUMULATE"
    elif total_score >= 50:
        if is_downtrend:
            return "AVOID"
        if rr >= 3:
            return "BUY"
        else:
            return "HOLD"
    elif total_score >= 30:
        return "HOLD"
    elif total_score >= 15:
        return "WATCHLIST"
    else:
        return "AVOID"


def get_position_size(total_score, account_size=1000000):
    if total_score >= 80:
        return round(account_size * POSITION_SIZE_PCT * 1.5)
    elif total_score >= 60:
        return round(account_size * POSITION_SIZE_PCT)
    elif total_score >= 40:
        return round(account_size * POSITION_SIZE_PCT * 0.5)
    return 0


def get_score_label(score):
    if score >= 80:
        return "STRONG BUY"
    elif score >= 60:
        return "BUY"
    elif score >= 40:
        return "HOLD"
    elif score >= 20:
        return "WATCH"
    return "AVOID"


def get_score_color(score):
    if score >= 80:
        return "#00C853"
    elif score >= 60:
        return "#66BB6A"
    elif score >= 40:
        return "#FFA726"
    elif score >= 20:
        return "#FF7043"
    return "#EF5350"


def rank_stocks(results):
    ranked = []
    for r in results:
        score = r.get("total_score", 0)
        rr = r.get("risk_reward", {}).get("ratio", 0)
        regime_bonus = 5 if r.get("regime") in ["uptrend", "strong_uptrend"] else 0
        composite = score + rr * 5 + regime_bonus
        ranked.append({**r, "composite_score": round(composite, 1)})
    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    return ranked
