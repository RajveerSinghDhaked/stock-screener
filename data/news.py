import re
from datetime import datetime


SENTIMENT_WORDS = {
    "positive": [
        "surge", "rally", "gains", "bullish", "upgrade", "buy", "outperform",
        "growth", "profit", "record high", "breakout", "beat", "strong",
        "positive", "recovery", "boom", "soar", "jump", "climb", "advance",
        "momentum", "uptrend", "premium", "dividend", "expansion",
    ],
    "negative": [
        "crash", "plunge", "fall", "bearish", "downgrade", "sell", "underperform",
        "loss", "decline", "weak", "recession", "debt", "crisis", "warning",
        "negative", "drop", "dip", "correction", "slump", "downturn", "miss",
        "bankruptcy", "default", "fraud", "investigation", "lawsuit",
    ],
    "neutral": [
        "stable", "flat", "unchanged", "steady", "mixed", "consolidation",
        "sideways", "wait", "hold", "monitor", "review", "analysis",
    ],
}


def analyze_news_sentiment(news_items):
    if not news_items:
        return {
            "sentiment_score": 0,
            "sentiment_label": "neutral",
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "headlines": [],
        }

    results = []
    for item in news_items:
        title = item.get("title", "")
        score = _score_text(title)
        results.append({
            "title": title,
            "publisher": item.get("publisher", ""),
            "score": score,
            "link": item.get("link", ""),
        })

    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    positive = sum(1 for s in scores if s > 0.1)
    negative = sum(1 for s in scores if s < -0.1)
    neutral = len(scores) - positive - negative

    if avg_score > 0.3:
        label = "strong_positive"
    elif avg_score > 0.1:
        label = "positive"
    elif avg_score < -0.3:
        label = "strong_negative"
    elif avg_score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return {
        "sentiment_score": round(avg_score, 3),
        "sentiment_label": label,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "total_articles": len(news_items),
        "headlines": sorted(results, key=lambda x: abs(x["score"]), reverse=True)[:5],
    }


def _score_text(text):
    import re
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    pos = sum(1 for w in SENTIMENT_WORDS["positive"] if w in words)
    neg = sum(1 for w in SENTIMENT_WORDS["negative"] if w in words)
    total = pos + neg
    if total == 0:
        return 0
    return (pos - neg) / total


def get_market_news():
    try:
        import yfinance as yf
        news = yf.Ticker("^NSEI").news
        if not news:
            return []
        return [
            {
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
            }
            for item in news[:10]
        ]
    except Exception:
        return []


def get_sector_news(sector=""):
    return get_market_news()


def sentiment_to_signal(sentiment):
    score = sentiment.get("sentiment_score", 0)
    label = sentiment.get("sentiment_label", "neutral")
    if score > 0.3:
        return {"type": "news_sentiment", "name": "News Sentiment", "action": "buy", "strength": 1.5, "description": f"Strong positive news sentiment ({score:.2f})"}
    elif score > 0.1:
        return {"type": "news_sentiment", "name": "News Sentiment", "action": "buy", "strength": 1.0, "description": f"Positive news sentiment ({score:.2f})"}
    elif score < -0.3:
        return {"type": "news_sentiment", "name": "News Sentiment", "action": "sell", "strength": 1.5, "description": f"Strong negative news sentiment ({score:.2f})"}
    elif score < -0.1:
        return {"type": "news_sentiment", "name": "News Sentiment", "action": "sell", "strength": 1.0, "description": f"Negative news sentiment ({score:.2f})"}
    return None


def format_sentiment_for_display(sentiment):
    label = sentiment.get("sentiment_label", "neutral")
    score = sentiment.get("sentiment_score", 0)
    icons = {
        "strong_positive": "🟢🟢",
        "positive": "🟢",
        "neutral": "⚪",
        "negative": "🔴",
        "strong_negative": "🔴🔴",
    }
    return f"{icons.get(label, '⚪')} {label.replace('_', ' ').title()} ({score:+.2f})"
