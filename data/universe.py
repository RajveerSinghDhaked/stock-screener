import os
import pandas as pd
from config import DATA_DIR

CSV_PATH = os.path.join(DATA_DIR, "Nifty_200_stock_list.csv")


def _load_csv():
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()
    return pd.read_csv(CSV_PATH)


def get_nifty_200_symbols():
    df = _load_csv()
    if df.empty or "Symbol" not in df.columns:
        return []
    return df["Symbol"].dropna().unique().tolist()


def get_stock_details_from_csv():
    df = _load_csv()
    if df.empty:
        return []
    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            "symbol": row.get("Symbol", ""),
            "name": row.get("Company Name", ""),
            "industry": row.get("Industry", ""),
            "series": row.get("Series", ""),
        })
    return stocks


def get_industries():
    df = _load_csv()
    if df.empty or "Industry" not in df.columns:
        return []
    return sorted(df["Industry"].dropna().unique().tolist())


def get_stocks_by_industry(industry):
    df = _load_csv()
    if df.empty:
        return []
    filtered = df[df["Industry"] == industry]
    return filtered["Symbol"].dropna().tolist()
