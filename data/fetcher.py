import time
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from config import (
    MIN_PRICE, MIN_VOLUME,
    CACHE_DAILY_MAX_AGE_HOURS, CACHE_WEEKLY_MAX_AGE_HOURS,
    CACHE_MONTHLY_MAX_AGE_HOURS,
)

FETCH_TIMEOUT = 15


class RateLimiter:
    def __init__(self, max_calls, period=1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def wait(self):
        now = time.time()
        self.calls = [t for t in self.calls if now - t < self.period]
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.calls.append(time.time())


rate_limiter = RateLimiter(max_calls=5, period=1.0)


def _yf_ticker(symbol):
    return yf.Ticker(f"{symbol}.NS")


def _run_with_timeout(func, *args, timeout=FETCH_TIMEOUT, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            return None
        except Exception:
            return None


def _normalize_df(df, date_col="date"):
    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    for col in ["date", "datetime"]:
        if col in df.columns:
            df[date_col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
            if col != date_col:
                df.drop(columns=[col], inplace=True)
            break
    return df


def fetch_stock_history(symbol, period="1y", interval="1d"):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        df = _run_with_timeout(ticker.history, period=period, interval=interval)
        if df is None or df.empty:
            return None
        df = _normalize_df(df, "date")
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def fetch_weekly_data(symbol, period="2y"):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        df = _run_with_timeout(ticker.history, period=period, interval="1wk")
        if df is None or df.empty:
            return None
        df = _normalize_df(df, "date")
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"Error fetching weekly {symbol}: {e}")
        return None


def fetch_monthly_data(symbol, period="5y"):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        df = _run_with_timeout(ticker.history, period=period, interval="1mo")
        if df is None or df.empty:
            return None
        df = _normalize_df(df, "date")
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"Error fetching monthly {symbol}: {e}")
        return None


def fetch_intraday_data(symbol, period="60d", interval="5m"):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        df = _run_with_timeout(ticker.history, period=period, interval=interval)
        if df is None or df.empty:
            return None
        df = _normalize_df(df, "timestamp")
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"Error fetching intraday {symbol}: {e}")
        return None


def fetch_live_quote(symbol):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        prev_close = getattr(info, "previous_close", price)
        if price is None:
            hist = ticker.history(period="1d")
            if hist.empty:
                return None
            price = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[0]
            volume = int(hist["Volume"].iloc[-1])
        else:
            volume = 0
        return {
            "symbol": symbol,
            "ltp": round(float(price), 2),
            "change_pct": round(((float(price) - float(prev_close)) / float(prev_close)) * 100, 2)
            if prev_close and float(prev_close) > 0 else 0,
            "volume": volume,
        }
    except Exception as e:
        print(f"Error fetching quote {symbol}: {e}")
        return None


def fetch_earnings_dates(symbol):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        cal = ticker.calendar
        if cal is None or cal.empty:
            return []
        dates = []
        for _, row in cal.iterrows():
            dates.append({
                "date": str(row.get("Earnings Date", ""))[:10],
                "estimated_eps": row.get("EPS Estimate"),
            })
        return dates
    except Exception:
        return []


def fetch_stock_news(symbol):
    try:
        rate_limiter.wait()
        ticker = _yf_ticker(symbol)
        news = ticker.news
        if not news:
            return []
        results = []
        for item in news[:5]:
            results.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
            })
        return results
    except Exception:
        return []


def fetch_multiple_stocks(symbols, period="1y", interval="1d"):
    results = {}
    total = len(symbols)
    for i, symbol in enumerate(symbols):
        print(f"  [{i+1}/{total}] Fetching {symbol}...")
        df = fetch_stock_history(symbol, period=period, interval=interval)
        if df is not None and not df.empty:
            results[symbol] = df
    return results


def filter_stocks(df, min_price=MIN_PRICE, min_volume=MIN_VOLUME):
    if df is None or df.empty:
        return False
    last_close = df["close"].iloc[-1]
    avg_volume = df["volume"].tail(20).mean()
    return last_close >= min_price and avg_volume >= min_volume
