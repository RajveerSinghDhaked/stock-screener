CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    name TEXT,
    exchange TEXT DEFAULT 'NSE',
    sector TEXT,
    market_cap_category TEXT,
    is_active INTEGER DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS weekly_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS monthly_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS intraday_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    UNIQUE(symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS live_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ltp REAL,
    open REAL,
    high REAL,
    low REAL,
    close_prev REAL,
    volume INTEGER,
    change_pct REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    pe_ratio REAL,
    roe REAL,
    debt_to_equity REAL,
    revenue_growth REAL,
    market_cap REAL,
    eps REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symbol TEXT NOT NULL,
    total_score REAL,
    regime TEXT,
    signals TEXT,
    indicator_values TEXT,
    recommendation TEXT,
    ai_analysis TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    target_price REAL,
    stop_loss REAL
);

CREATE TABLE IF NOT EXISTS cache_metadata (
    table_name TEXT PRIMARY KEY,
    last_refresh TIMESTAMP,
    record_count INTEGER
);

CREATE TABLE IF NOT EXISTS pattern_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_name TEXT NOT NULL,
    description TEXT,
    indicators_conditions TEXT,
    market_context TEXT,
    outcome TEXT,
    return_pct REAL,
    success_rate REAL,
    timeframe_days INTEGER,
    examples_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    recommendation TEXT,
    score REAL,
    entry_price REAL,
    target_price REAL,
    stop_loss REAL,
    actual_result TEXT,
    actual_return_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS earnings_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    earnings_date TEXT NOT NULL,
    estimated_eps REAL,
    actual_eps REAL,
    surprise_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON daily_candles(symbol, date);
CREATE INDEX IF NOT EXISTS idx_weekly_symbol_date ON weekly_candles(symbol, date);
CREATE INDEX IF NOT EXISTS idx_monthly_symbol_date ON monthly_candles(symbol, date);
CREATE INDEX IF NOT EXISTS idx_intraday_symbol_ts ON intraday_candles(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_scan_date ON scan_results(scan_date);
CREATE INDEX IF NOT EXISTS idx_live_symbol ON live_quotes(symbol);
CREATE INDEX IF NOT EXISTS idx_pattern_name ON pattern_memory(pattern_name);
CREATE INDEX IF NOT EXISTS idx_recommendation_symbol ON recommendation_history(symbol);
