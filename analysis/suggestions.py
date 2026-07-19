import json
from datetime import datetime
from data.cache import (
    get_all_patterns, find_matching_patterns, store_recommendation,
    get_recommendation_history,
)
from analysis.scorer import get_recommendation, get_score_label, get_score_color, get_position_size
from analysis.regime import get_regime_label, get_regime_color


def generate_veteran_analysis(symbol, score_result, regime_result, indicators, signals, weekly_ind=None, monthly_ind=None):
    total_score = score_result.get("total_score", 0)
    risk_reward = score_result.get("risk_reward", {})
    regime = regime_result.get("regime", "unknown")
    signal_count = score_result.get("signal_count", 0)
    factor_scores = score_result.get("factor_scores", {})

    regime_label = get_regime_label(regime)
    regime_confidence = regime_result.get("confidence", 0)
    recommendation = get_recommendation(score_result, risk_reward, regime=regime)

    narrative_parts = []

    market_assessment = _build_market_assessment(regime, regime_result, indicators)
    narrative_parts.append(market_assessment)

    technical_narrative = _build_technical_narrative(signals, indicators, factor_scores)
    narrative_parts.append(technical_narrative)

    multi_tf = _build_multi_tf_analysis(indicators, weekly_ind, monthly_ind)
    if multi_tf:
        narrative_parts.append(multi_tf)

    pattern_match = _build_pattern_analysis(indicators)
    if pattern_match:
        narrative_parts.append(pattern_match)

    risk_narrative = _build_risk_analysis(indicators, risk_reward, total_score, regime)
    narrative_parts.append(risk_narrative)

    action_narrative = _build_action_narrative(recommendation, risk_reward, indicators, regime)
    narrative_parts.append(action_narrative)

    full_narrative = " ".join(narrative_parts)

    store_recommendation(
        symbol, recommendation, total_score,
        risk_reward.get("entry_price", indicators.get("current_price", 0)),
        risk_reward.get("target", 0),
        risk_reward.get("stop_loss", 0),
    )

    return {
        "symbol": symbol,
        "narrative": full_narrative,
        "recommendation": recommendation,
        "recommendation_label": _get_rec_label(recommendation),
        "recommendation_color": _get_rec_color(recommendation),
        "regime": regime_label,
        "regime_color": get_regime_color(regime),
        "regime_confidence": regime_confidence,
        "total_score": total_score,
        "score_label": get_score_label(total_score),
        "score_color": get_score_color(total_score),
        "signal_count": signal_count,
        "risk_reward": risk_reward,
        "key_factors": _extract_key_factors(signals, factor_scores),
        "warnings": _extract_warnings(signals, indicators, regime),
        "position_size": get_position_size(total_score),
        "confidence_level": _compute_confidence(regime_confidence, signal_count, risk_reward.get("valid", False)),
    }


def _build_market_assessment(regime, regime_result, indicators):
    regime_label = get_regime_label(regime)
    conf = regime_result.get("confidence", 0) * 100

    daily = regime_result.get("daily", {})
    volatility = daily.get("volatility", 0) * 100
    trend_slope = daily.get("trend_slope", 0)
    volume_trend = daily.get("volume_trend", "stable")

    parts = []
    parts.append(f"The stock is currently in a {regime_label} regime (confidence: {conf:.0f}%).")

    if "uptrend" in regime:
        parts.append(f"Momentum is positive with a {trend_slope:.1f}% trend slope.")
    elif "downtrend" in regime:
        parts.append(f"Downward pressure persists with a {trend_slope:.1f}% trend slope.")
    elif "volatile" in regime:
        parts.append(f"High volatility detected ({volatility:.1f}% annualized).")
    elif "ranging" in regime:
        parts.append(f"Price is consolidating in a defined range.")

    if volume_trend == "increasing":
        parts.append("Volume is picking up, confirming the current direction.")
    elif volume_trend == "declining":
        parts.append("Volume is declining, which weakens the current move.")

    return " ".join(parts)


def _build_technical_narrative(signals, indicators, factor_scores):
    if not signals:
        return "No significant technical signals detected at current levels."

    bullish = [s for s in signals if s.get("action") == "buy"]
    bearish = [s for s in signals if s.get("action") == "sell"]
    neutral = [s for s in signals if s.get("action") not in ["buy", "sell"]]

    parts = []

    if bullish:
        names = [s.get("name", "") for s in bullish[:3]]
        parts.append(f"Bullish signals from {', '.join(names)}")

    if bearish:
        names = [s.get("name", "") for s in bearish[:3]]
        parts.append(f"bearish pressure from {', '.join(names)}")

    if neutral:
        parts.append(f"with {len(neutral)} neutral indicator(s) watching")

    if not parts:
        return f"Multiple technical indicators align ({len(signals)} signals detected)."

    return ". ".join(parts) + "."


def _build_multi_tf_analysis(daily_ind, weekly_ind, monthly_ind):
    if not weekly_ind and not monthly_ind:
        return ""

    parts = []
    if weekly_ind:
        w_ema = weekly_ind.get("ema20")
        w_price = weekly_ind.get("current_price")
        if w_ema and w_price:
            trend = "above" if w_price > w_ema else "below"
            parts.append(f"Weekly timeframe shows price {trend} the 20-week EMA")

    if monthly_ind:
        m_ema20 = monthly_ind.get("ema20")
        m_ema50 = monthly_ind.get("ema50")
        if m_ema20 and m_ema50:
            cross = "golden cross" if m_ema20 > m_ema50 else "death cross"
            parts.append(f"monthly chart shows a {cross}")

    if parts:
        return "Multi-timeframe analysis: " + "; ".join(parts) + "."
    return ""


def _build_pattern_analysis(indicators):
    if not indicators:
        return ""

    summary = _indicators_to_summary(indicators)
    patterns = find_matching_patterns(summary)

    if not patterns:
        return ""

    parts = ["Historical pattern memory identifies"]
    names = [p["pattern_name"] for p in patterns[:2]]
    parts.append(f"{', '.join(names)} as resembling current setup.")

    best = patterns[0]
    if best.get("success_rate"):
        parts.append(f"Historical success rate: {best['success_rate']:.0f}%.")

    return " ".join(parts)


def _build_risk_analysis(indicators, risk_reward, total_score, regime):
    parts = []

    if risk_reward.get("valid"):
        rr = risk_reward.get("ratio", 0)
        parts.append(f"Risk/reward ratio of {rr:.1f}:1 is favorable.")
    else:
        parts.append("Risk/reward ratio is not ideal at current levels.")

    atr = indicators.get("atr", 0)
    current_price = indicators.get("current_price", 1)
    if atr and current_price:
        atr_pct = (atr / current_price) * 100
        if atr_pct > 3:
            parts.append(f"High volatility warning: ATR at {atr_pct:.1f}% of price.")

    if regime in ["volatile", "strong_downtrend"]:
        parts.append("Consider smaller position size due to elevated risk.")

    if total_score >= 60 and risk_reward.get("valid"):
        parts.append("Technical setup supports controlled entry.")
    elif total_score >= 40:
        parts.append("Partial position with room to add on confirmation.")

    return " ".join(parts) if parts else ""


def _build_action_narrative(recommendation, risk_reward, indicators, regime):
    entry_price = risk_reward.get("entry_price", indicators.get("current_price", 0))
    target = risk_reward.get("target", 0)
    stop_loss = risk_reward.get("stop_loss", 0)

    parts = []
    if recommendation == "STRONG_BUY":
        parts.append("STRONG BUY: All major indicators align. Consider entering with a full position.")
    elif recommendation == "BUY":
        parts.append("BUY: Technical setup is favorable. Enter with a controlled position.")
    elif recommendation == "ACCUMULATE":
        parts.append("ACCUMULATE: Gradually build position on dips.")
    elif recommendation == "HOLD":
        parts.append("HOLD: Wait for clearer signals before adding.")
    elif recommendation == "WATCHLIST":
        parts.append("WATCHLIST: Set alerts for key levels. Not an immediate entry.")
    else:
        parts.append("AVOID: Current technicals do not support entry.")

    if target > 0 and stop_loss > 0:
        parts.append(f"Suggested target: Rs.{target:.0f}, Stop loss: Rs.{stop_loss:.0f}.")

    return " ".join(parts)


def _extract_key_factors(signals, factor_scores):
    sorted_factors = sorted(
        factor_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True,
    )
    return [
        {
            "name": name,
            "score": data["score"],
            "description": data.get("description", ""),
            "action": data.get("action", ""),
        }
        for name, data in sorted_factors[:5]
    ]


def _extract_warnings(signals, indicators, regime):
    warnings = []

    atr = indicators.get("atr", 0)
    current_price = indicators.get("current_price", 1)
    if atr and current_price and (atr / current_price) > 0.03:
        warnings.append("High volatility - consider tighter stop loss")

    if regime in ["volatile", "strong_downtrend"]:
        warnings.append(f"Elevated risk in {regime} market regime")

    rsi = indicators.get("rsi", 50)
    if rsi and rsi > 75:
        warnings.append("RSI in overbought territory - wait for pullback")
    elif rsi and rsi < 25:
        warnings.append("RSI in oversold territory - potential reversal zone")

    bb_upper = indicators.get("bb_upper", 0)
    bb_lower = indicators.get("bb_lower", 0)
    if bb_upper and bb_lower:
        bb_width = (bb_upper - bb_lower) / current_price if current_price else 0
        if bb_width < 0.05:
            warnings.append("Bollinger squeeze detected - expect volatility expansion")

    return warnings


def _compute_confidence(regime_conf, signal_count, rr_valid):
    score = 50
    score += regime_conf * 20
    score += min(signal_count * 5, 20)
    if rr_valid:
        score += 15
    return min(95, max(10, int(score)))


def _indicators_to_summary(indicators):
    return {
        "ema_bullish": indicators.get("ema20", 0) > indicators.get("ema50", 0),
        "rsi_oversold_recovery": 30 < indicators.get("rsi", 50) < 50,
        "macd_bullish": indicators.get("macd_hist", 0) > 0,
        "volume_surge": indicators.get("volume_ratio", 1) > 1.5,
        "bb_squeeze": indicators.get("bb_width", 1) < 0.05 if indicators.get("bb_width") else False,
        "ichimoku_break": indicators.get("price_above_cloud", False),
        "supertrend_buy": indicators.get("supertrend_signal", "") == "buy",
        "death_cross": indicators.get("ema50", 0) < indicators.get("ema200", 0),
    }


def _get_rec_label(rec):
    labels = {
        "STRONG_BUY": "STRONG BUY",
        "BUY": "BUY",
        "ACCUMULATE": "ACCUMULATE",
        "HOLD": "HOLD",
        "WATCHLIST": "WATCHLIST",
        "AVOID": "AVOID",
    }
    return labels.get(rec, rec)


def _get_rec_color(rec):
    colors = {
        "STRONG_BUY": "#00C853",
        "BUY": "#66BB6A",
        "ACCUMULATE": "#29B6F6",
        "HOLD": "#FFA726",
        "WATCHLIST": "#78909C",
        "AVOID": "#EF5350",
    }
    return colors.get(rec, "#546E7A")


def batch_analyze(stocks_data):
    results = []
    for symbol, data in stocks_data.items():
        try:
            result = generate_veteran_analysis(
                symbol,
                data["score"],
                data["regime"],
                data.get("indicators", {}),
                data.get("signals", []),
                data.get("weekly_indicators"),
                data.get("monthly_indicators"),
            )
            results.append(result)
        except Exception as e:
            print(f"Analysis failed for {symbol}: {e}")
    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results
