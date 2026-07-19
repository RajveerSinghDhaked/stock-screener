import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output" / "reports"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

USE_POSTGRESQL = os.getenv("USE_POSTGRESQL", "false").lower() == "true"

if USE_POSTGRESQL:
    DB_URL = os.getenv("DATABASE_URL", "")
else:
    _db_path = os.getenv("DATABASE_URL", "")
    if _db_path.startswith("sqlite:///"):
        DB_URL = _db_path
    elif _db_path and not _db_path.startswith("sqlite"):
        DB_URL = f"sqlite:///{_db_path}"
    else:
        _tmp_db = Path(tempfile.gettempdir()) / "stock_screener.db"
        try:
            _test = _tmp_db.parent / ".streamlit_write_test"
            _test.write_text("ok")
            _test.unlink()
            DB_URL = f"sqlite:///{_tmp_db}"
        except OSError:
            DB_URL = f"sqlite:///{DATA_DIR / 'stock_screener.db'}"

NSE_RATE_LIMIT = 3
BSE_RATE_LIMIT = 8

MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
MARKET_TIMEZONE_OFFSET = 5.5

STOCK_UNIVERSE = "NIFTY200"

EMA_SHORT = 20
EMA_MID = 50
EMA_LONG = 200
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2.0
ATR_PERIOD = 14
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0
ADX_PERIOD = 14
STOCH_RSI_K = 14
STOCH_RSI_D = 3
STOCH_RSI_SMOOTH = 14
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN = 26
ICHIMOKU_SENKOU = 52
SAR_AF = 0.02
SAR_MAX = 0.2

WEEKLY_EMA_FAST = 10
WEEKLY_EMA_SLOW = 40
MONTHLY_EMA = 10

MIN_SIGNALS_REQUIRED = 2
MIN_VOLUME = 100000
MIN_PRICE = 50.0
ATR_SL_MULTIPLIER = 1.5
MIN_RISK_REWARD = 2.0

SCAN_REFRESH_INTERVAL = 300
AUTO_SCAN_MINUTES = 15
CACHE_DAILY_MAX_AGE_HOURS = 24
CACHE_WEEKLY_MAX_AGE_HOURS = 72
CACHE_MONTHLY_MAX_AGE_HOURS = 168
CACHE_QUOTE_MAX_AGE_MINUTES = 5

ADX_TRENDING_THRESHOLD = 25
ADX_RANGING_THRESHOLD = 20
ATR_VOLATILE_MULTIPLIER = 1.3
LOW_VOLUME_THRESHOLD = 0.7

SCORING_REGIMES = {
    "trending": {
        "signal_count": 0.20,
        "adx_strength": 0.25,
        "volume": 0.15,
        "ema_alignment": 0.25,
        "risk_reward": 0.10,
        "ichimoku": 0.05,
    },
    "ranging": {
        "signal_count": 0.15,
        "adx_strength": 0.05,
        "volume": 0.15,
        "ema_alignment": 0.10,
        "risk_reward": 0.15,
        "ichimoku": 0.10,
        "bb_position": 0.15,
        "rsi_position": 0.15,
    },
    "volatile": {
        "signal_count": 0.15,
        "adx_strength": 0.10,
        "volume": 0.10,
        "ema_alignment": 0.10,
        "risk_reward": 0.25,
        "atr_score": 0.15,
        "stop_distance": 0.15,
    },
    "low_volume": {
        "signal_count": 0.20,
        "adx_strength": 0.15,
        "volume": 0.05,
        "ema_alignment": 0.20,
        "risk_reward": 0.20,
        "ichimoku": 0.10,
        "caution_penalty": 0.10,
    },
}

TREND_WEIGHTS = {"trend": 1.5, "ema_bullish": 1.5, "ema_bearish": 1.5, "golden_cross": 1.8, "death_cross": 1.8}
RSI_WEIGHTS = {"rsi_oversold": 1.0, "rsi_overbought": 1.0, "stoch_rsi_recovery": 1.2}
VOLUME_WEIGHTS = {"volume_surge": 1.5, "volume_decline": 0.8}
MOMENTUM_WEIGHTS = {"macd_bullish": 1.2, "macd_bearish": 1.2}
PATTERN_WEIGHTS = {"sar_flip": 1.0, "bb_squeeze": 1.3}
SUPERTREND_WEIGHTS = {"supertrend_buy": 1.4, "supertrend_sell": 1.4}
VOLATILITY_WEIGHTS = {"bb_squeeze_breakout": 1.3, "high_volatility": 0.8}
FIBONACCI_WEIGHTS = {"fib_bounce": 1.1}
ICHIMOKU_WEIGHTS = {"ichimoku_break": 1.3, "ichimoku_cloud_support": 1.0}

RISK_REWARD_RATIO = 3.0
MIN_RISK_REWARD_RATIO = 1.5
POSITION_SIZE_PCT = 0.05
MAX_POSITIONS = 10
MIN_SCORE_THRESHOLD = 40

REGIME_DETECTION_LOOKBACK = 60
REGIME_WEIGHTS = {
    "trending": {"trend": 2.0, "momentum": 1.5, "volume": 1.2, "volatility": 0.8, "pattern": 1.0, "supertrend": 1.5, "rsi": 1.0, "ichimoku": 1.2, "fibonacci": 1.0},
    "strong_uptrend": {"trend": 2.5, "momentum": 1.5, "volume": 1.3, "volatility": 0.7, "pattern": 1.0, "supertrend": 1.5, "rsi": 1.0, "ichimoku": 1.2, "fibonacci": 1.0},
    "uptrend": {"trend": 1.8, "momentum": 1.3, "volume": 1.2, "volatility": 0.9, "pattern": 1.0, "supertrend": 1.3, "rsi": 1.0, "ichimoku": 1.1, "fibonacci": 1.0},
    "ranging": {"trend": 0.8, "momentum": 1.0, "volume": 1.5, "volatility": 1.2, "pattern": 1.5, "supertrend": 0.8, "rsi": 1.5, "ichimoku": 0.8, "fibonacci": 1.3},
    "downtrend": {"trend": 1.5, "momentum": 1.2, "volume": 1.0, "volatility": 1.3, "pattern": 1.2, "supertrend": 1.3, "rsi": 1.0, "ichimoku": 1.0, "fibonacci": 1.0},
    "strong_downtrend": {"trend": 2.0, "momentum": 1.0, "volume": 0.8, "volatility": 1.5, "pattern": 1.5, "supertrend": 1.5, "rsi": 0.8, "ichimoku": 0.8, "fibonacci": 0.8},
    "volatile": {"trend": 0.7, "momentum": 0.8, "volume": 1.0, "volatility": 2.0, "pattern": 1.5, "supertrend": 0.8, "rsi": 1.5, "ichimoku": 0.7, "fibonacci": 1.2},
    "low_volume": {"trend": 1.0, "momentum": 1.0, "volume": 0.5, "volatility": 1.5, "pattern": 1.2, "supertrend": 0.8, "rsi": 1.3, "ichimoku": 0.8, "fibonacci": 1.0},
}

PATTERN_MEMORY_SEEDS = [
    {
        "pattern_name": "EMA Bullish Alignment + Volume Surge",
        "description": "Price above EMA20 > EMA50 > EMA200 with volume 1.5x+ average. Classic strong uptrend continuation.",
        "market_context": "Market trending up (Nifty above 200 DMA), sector rotation positive",
        "outcome": "15-25% rally in 2-3 months in 80% of cases",
        "return_pct": 18.0,
        "success_rate": 80.0,
        "timeframe_days": 60,
        "examples_count": 45,
    },
    {
        "pattern_name": "RSI Oversold Recovery at Support",
        "description": "RSI drops below 35 then recovers above 40 while price is near a major support (200 EMA or previous swing low).",
        "market_context": "Market in mild correction or consolidation phase",
        "outcome": "10-20% bounce in 1-2 months, high probability reversal",
        "return_pct": 14.0,
        "success_rate": 75.0,
        "timeframe_days": 40,
        "examples_count": 38,
    },
    {
        "pattern_name": "MACD Bullish Crossover + ADX Rising",
        "description": "MACD crosses above signal line while ADX is rising above 20. New trend forming with momentum.",
        "market_context": "Market transitioning from range to trend",
        "outcome": "12-18% move over 1-2 months, strongest when ADX > 25",
        "return_pct": 15.0,
        "success_rate": 72.0,
        "timeframe_days": 45,
        "examples_count": 52,
    },
    {
        "pattern_name": "Bollinger Band Squeeze Breakout",
        "description": "BB bandwidth narrows to minimum then price breaks above upper band with volume confirmation.",
        "market_context": "Low volatility period followed by expansion",
        "outcome": "10-20% breakout move in 2-4 weeks",
        "return_pct": 13.0,
        "success_rate": 68.0,
        "timeframe_days": 25,
        "examples_count": 30,
    },
    {
        "pattern_name": "Ichimoku Cloud Break with Volume",
        "description": "Price breaks above Ichimoku cloud (Senkou A/B) with volume surge. Strong bullish confirmation.",
        "market_context": "Uptrend strengthening, cloud acting as support",
        "outcome": "15-25% rally, cloud becomes support for pullbacks",
        "return_pct": 17.0,
        "success_rate": 77.0,
        "timeframe_days": 55,
        "examples_count": 28,
    },
    {
        "pattern_name": "Supertrend Buy + EMA Alignment",
        "description": "Supertrend flips bullish while EMA 20 > 50 > 200. Double trend confirmation.",
        "market_context": "Strong trending market, momentum building",
        "outcome": "12-20% continuation move, very reliable in trending markets",
        "return_pct": 16.0,
        "success_rate": 78.0,
        "timeframe_days": 50,
        "examples_count": 42,
    },
    {
        "pattern_name": "Death Cross Warning",
        "description": "EMA 50 crosses below EMA 200. Major bearish signal, historically precedes significant declines.",
        "market_context": "Market weakening, breadth deteriorating",
        "outcome": "10-30% decline over 2-6 months, exit longs immediately",
        "return_pct": -18.0,
        "success_rate": 70.0,
        "timeframe_days": 90,
        "examples_count": 25,
    },
    {
        "pattern_name": "Fibonacci 61.8% Bounce",
        "description": "Price pulls back to 61.8% Fibonacci retracement level and shows reversal candle with volume.",
        "market_context": "Healthy pullback in uptrend, Fibonacci support holding",
        "outcome": "Resume original trend, 15-25% from fib level",
        "return_pct": 16.0,
        "success_rate": 65.0,
        "timeframe_days": 35,
        "examples_count": 33,
    },
    {
        "pattern_name": "High Volume Reversal at Bottom",
        "description": "Stock makes new low but volume spikes 3x+ average with bullish candle. Capitulation selling exhaustion.",
        "market_context": "Panic selling, fear sentiment extreme",
        "outcome": "Sharp V-recovery, 20-40% in 1-3 months",
        "return_pct": 28.0,
        "success_rate": 62.0,
        "timeframe_days": 60,
        "examples_count": 20,
    },
    {
        "pattern_name": "Sector Rotation Signal",
        "description": "Sector showing relative strength while market is flat. Leadership changing hands.",
        "market_context": "Market in rotation phase, smart money shifting sectors",
        "outcome": "Sector outperforms by 10-15% over next quarter",
        "return_pct": 12.0,
        "success_rate": 70.0,
        "timeframe_days": 90,
        "examples_count": 35,
    },
]
