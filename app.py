import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import subprocess
import sys
import os
from streamlit_autorefresh import st_autorefresh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MIN_SCORE_THRESHOLD
from data.universe import get_nifty_200_symbols
from db.connection import init_db as init_database
from data.fetcher import fetch_stock_news
from data.cache import (
    get_daily_candles, get_weekly_candles, get_monthly_candles,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    load_fresh_scan_results, get_stock_analysis,
    save_scan_status, get_scan_status,
    get_scan_progress, clear_scan_progress,
)
from analysis.backtest import backtest_strategy
from data.news import analyze_news_sentiment, format_sentiment_for_display

st.set_page_config(page_title="Stock AI Screener", page_icon="📈", layout="wide", initial_sidebar_state="expanded")
st_autorefresh(interval=6000, key="auto_refresh")
init_database()

ALL_SYMBOLS = get_nifty_200_symbols()

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    div[data-testid="stMetric"] {
        border-radius: 10px; padding: 12px 16px;
        border: 1px solid #ccc;
    }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    .signal-badge {
        display: inline-block; padding: 3px 10px; border-radius: 15px;
        font-size: 0.75rem; font-weight: 600; margin: 2px;
    }
    .buy-badge { background: #00C85325; color: #00802e; border: 1px solid #00C85350; }
    .sell-badge { background: #FF174425; color: #d1122e; border: 1px solid #FF174450; }
    .neutral-badge { background: #FFA72625; color: #cc6d00; border: 1px solid #FFA72650; }
    .rec-card {
        border-radius: 16px; padding: 24px; margin: 12px 0;
        border: 1px solid #ccc;
    }
    .narrative-box {
        border: 1px solid #ccc;
        border-radius: 12px; padding: 20px; margin: 8px 0;
        line-height: 1.8; font-size: 0.95rem;
    }
    .warn-box {
        background: #FF174418; border-left: 3px solid #FF1744;
        padding: 8px 14px; border-radius: 0 8px 8px 0; margin: 4px 0;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# WORKER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

WORKER_TIMEOUT_MINUTES = 35


def is_worker_alive():
    status = get_scan_status()
    if status != "running":
        return False
    progress = get_scan_progress()
    if not progress or "batch_time" not in progress:
        return False
    try:
        batch_time = datetime.fromisoformat(progress["batch_time"])
        elapsed = (datetime.now() - batch_time).total_seconds() / 60
        return elapsed < WORKER_TIMEOUT_MINUTES
    except Exception:
        return False


def spawn_worker():
    if is_worker_alive():
        return
    p = subprocess.Popen(
        [sys.executable, "scan_worker.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ═══════════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════════

def plot_candlestick(df, indicators=None):
    if df is None or df.empty:
        return None
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.6, 0.2, 0.2], subplot_titles=("Price", "Volume", "RSI"))
    fig.add_trace(go.Candlestick(x=df["date"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color="#00C853", decreasing_line_color="#FF1744"), row=1, col=1)
    if indicators:
        ema20_series = df["close"].ewm(span=20).mean()
        ema50_series = df["close"].ewm(span=50).mean()
        fig.add_trace(go.Scatter(x=df["date"], y=ema20_series, name="EMA20",
            line=dict(color="#FFA726", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=ema50_series, name="EMA50",
            line=dict(color="#29B6F6", width=1)), row=1, col=1)
        bb_mid = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        fig.add_trace(go.Scatter(x=df["date"], y=bb_upper, name="BB",
            line=dict(color="#78909C", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=bb_lower, name="",
            line=dict(color="#78909C", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(120,144,156,0.05)"), row=1, col=1)
    colors = ["#00C853" if c >= o else "#FF1744" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["date"], y=df["volume"], name="Vol",
        marker_color=colors, opacity=0.4), row=2, col=1)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    fig.add_trace(go.Scatter(x=df["date"], y=rsi, name="RSI",
        line=dict(color="#AB47BC", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 23, 68, 0.5)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(0, 200, 83, 0.5)", row=3, col=1)
    fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False,
        showlegend=False, margin=dict(l=40, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(gridcolor="#222", zeroline=False)
    fig.update_yaxes(gridcolor="#222", zeroline=False)
    return fig


def signal_badge(signal):
    action = signal.get("action", "")
    name = signal.get("name", "")
    cls = "buy-badge" if action == "buy" else "sell-badge" if action == "sell" else "neutral-badge"
    return f'<span class="signal-badge {cls}">{name}</span>'


def rec_box_html(analysis):
    label = analysis.get("recommendation_label", "HOLD")
    color = analysis.get("recommendation_color", "#FFA726")
    score = analysis.get("total_score", 0)
    regime = analysis.get("regime", "Unknown")
    regime_color = analysis.get("regime_color", "#546E7A")
    confidence = analysis.get("confidence_level", 50)
    rr = analysis.get("risk_reward", {})
    html = '<div class="rec-card">'
    html += '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">'
    html += f'<span style="font-size:1.8rem;font-weight:700;color:{color};">{label}</span>'
    html += f'<span style="background:{color}18;color:{color};padding:4px 14px;border-radius:20px;font-size:0.85rem;font-weight:600;">Score {score:.0f}/100</span>'
    html += f'<span style="background:{regime_color}18;color:{regime_color};padding:4px 14px;border-radius:20px;font-size:0.85rem;">{regime}</span>'
    html += f'<span style="font-size:0.8rem;">Confidence {confidence}%</span>'
    html += '</div>'
    if rr and rr.get("valid"):
        html += '<div style="display:flex;gap:24px;font-size:0.9rem;margin-top:8px;">'
        html += f'<span>Entry <b style="color:#29B6F6;">Rs.{rr.get("entry_price", 0):.0f}</b></span>'
        html += f'<span>Target <b style="color:#00C853;">Rs.{rr.get("target", 0):.0f}</b></span>'
        html += f'<span>Stop Loss <b style="color:#FF1744;">Rs.{rr.get("stop_loss", 0):.0f}</b></span>'
        html += f'<span>R:R <b style="color:#FFA726;">{rr.get("ratio", 0):.1f}:1</b></span>'
        html += '</div>'
    html += '</div>'
    return html


def navigate_to_stock(symbol):
    st.session_state.selected_stock = symbol
    st.session_state.sidebar_nav = "📊 Stock Detail"


def display_results(results, min_score):
    results = [r for r in results if r["score"]["total_score"] >= min_score]
    if results:
        st.markdown(f"### {len(results)} stocks found (score ≥ {min_score})")
        for idx, r in enumerate(results):
            analysis = r["analysis"]
            score = r["score"]
            symbol = r["symbol"]
            entry = score.get("entry", {})

            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
            with c1:
                regime_name = analysis.get('regime', '')
                warn = ' 🔴' if regime_name in ('strong_downtrend', 'downtrend') else ''
                st.markdown(f"**{symbol}**{warn}")
                st.caption(f"{regime_name} • {analysis.get('confidence_level', 0)}%")
            with c2:
                st.metric("Score", f"{score.get('total_score', 0):.0f}")
            with c3:
                st.metric("Signals", f"{score.get('signal_count', 0)}")
            with c4:
                st.metric("Entry", f"Rs.{entry.get('price', 0):.0f}")
            with c5:
                st.button("View →", key=f"v_{idx}_{symbol}",
                          on_click=navigate_to_stock, args=(symbol,))

            signals_html = "".join([signal_badge({"action": s.get("action", ""), "name": n})
                                    for n, s in score.get("factor_scores", {}).items()])
            st.markdown(signals_html, unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.warning("No stocks found above score threshold.")


def display_stock_detail(analysis_data, daily_df, symbol):
    indicators = analysis_data.get("indicators", {})
    signals_raw = analysis_data.get("signals", []) if "signals" in analysis_data else []
    factor_scores = analysis_data.get("factor_scores", {})
    entry = analysis_data.get("entry", {})
    risk_reward = analysis_data.get("risk_reward", {})
    regime_data = analysis_data.get("regime_data", {})

    score = {
        "total_score": analysis_data.get("total_score", 0),
        "signal_count": analysis_data.get("signal_count", 0),
        "entry": entry,
        "factor_scores": factor_scores,
    }
    regime = {"regime": analysis_data.get("regime", "unknown"), **regime_data}

    st.markdown(rec_box_html(analysis_data), unsafe_allow_html=True)

    regime_name = regime.get("regime", "unknown") if isinstance(regime, dict) else "unknown"
    if regime_name in ("strong_downtrend", "downtrend"):
        st.markdown(
            '<div style="background:#FF174415;border:1px solid #FF174440;border-radius:10px;'
            'padding:12px 18px;margin:8px 0;text-align:center;">'
            '<span style="color:#FF1744;font-weight:700;font-size:1rem;">'
            '⚠️ Strong Downtrend — Do Not Trade (Delivery)</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(f'<div class="narrative-box">{analysis_data.get("narrative", "")}</div>', unsafe_allow_html=True)
    if analysis_data.get("warnings"):
        for w in analysis_data["warnings"]:
            st.markdown(f'<div class="warn-box">⚠️ {w}</div>', unsafe_allow_html=True)
    st.markdown("---")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LTP", f"Rs.{indicators.get('current_price', 0):.2f}")
    c2.metric("RSI", f"{indicators.get('rsi', 0):.1f}")
    c3.metric("ATR", f"{indicators.get('atr', 0):.2f}")
    c4.metric("Vol Ratio", f"{indicators.get('volume_ratio', 1):.1f}x")
    c5.metric("ADX", f"{indicators.get('adx', 0):.0f}")

    tab_chart, tab_signals, tab_factors, tab_regime, tab_bt, tab_news = st.tabs([
        "📈 Chart", "🎯 Signals", "🧮 Score", "🔄 Regime", "🧪 Backtest", "📰 News"
    ])

    with tab_chart:
        fig = plot_candlestick(daily_df, indicators)
        if fig:
            st.plotly_chart(fig, width="stretch")
        st.markdown("**Key Indicators**")
        ic1, ic2, ic3, ic4 = st.columns(4)
        with ic1:
            st.markdown("**Trend**")
            st.write(f"EMA20: Rs.{indicators.get('ema20', 0):.2f}")
            st.write(f"EMA50: Rs.{indicators.get('ema50', 0):.2f}")
            st.write(f"EMA200: Rs.{indicators.get('ema200', 0):.2f}")
        with ic2:
            st.markdown("**Momentum**")
            st.write(f"MACD: {indicators.get('macd', 0):.2f}")
            st.write(f"StochRSI K: {indicators.get('stochrsi_k', 0):.1f}")
        with ic3:
            st.markdown("**Volatility**")
            st.write(f"BB Width: {indicators.get('bb_width', 0):.3f}")
            st.write(f"Supertrend: Rs.{indicators.get('supertrend', 0):.2f}")
        with ic4:
            st.markdown("**Volume**")
            st.write(f"Ratio: {indicators.get('volume_ratio', 1):.1f}x")
            st.write(f"OBV: {'↑' if indicators.get('obv_trend', 0) > 0 else '↓'}")

    with tab_signals:
        if signals_raw:
            for s in signals_raw:
                badge = signal_badge(s)
                st.markdown(f'{badge} {s.get("description", "")}', unsafe_allow_html=True)
                if s.get("level"):
                    st.caption(f"Level: Rs.{s['level']:.2f}")
        else:
            st.info("No active signals at current levels.")

    with tab_factors:
        if factor_scores:
            for name, data in sorted(factor_scores.items(), key=lambda x: x[1].get("score", 0), reverse=True):
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    st.write(f"**{name}**")
                    st.caption(data.get("description", ""))
                with c2:
                    ac = "#00C853" if data.get("action") == "buy" else "#FF1744" if data.get("action") == "sell" else "#FFA726"
                    st.markdown(f'<span style="color:{ac};font-weight:600;">{data.get("action", "").upper()}</span>', unsafe_allow_html=True)
                with c3:
                    st.write(f"**{data.get('score', 0):.1f}**")
        st.markdown("---")
        st.markdown("**Key Factors**")
        for f in analysis_data.get("key_factors", []):
            ac = "#00C853" if f.get("action") == "buy" else "#FF1744" if f.get("action") == "sell" else "#FFA726"
            st.markdown(f'**{f.get("name", "")}** — Score: {f.get("score", 0):.1f} — <span style="color:{ac}">{f.get("action", "").upper()}</span>', unsafe_allow_html=True)

    with tab_regime:
        daily_r = regime.get("daily", {})
        weekly_r = regime.get("weekly") or {}
        monthly_r = regime.get("monthly") or {}
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown("**Daily**")
            st.write(f"Regime: {daily_r.get('regime', 'N/A')}")
            st.write(f"Volatility: {daily_r.get('volatility', 0)*100:.1f}%")
            st.write(f"Trend: {daily_r.get('trend_slope', 0):.2f}%")
            st.write(f"Volume: {daily_r.get('volume_trend', 'N/A')}")
        with rc2:
            st.markdown("**Weekly**")
            st.write(f"Regime: {weekly_r.get('regime', 'N/A')}")
            st.write(f"Volatility: {weekly_r.get('volatility', 0)*100:.1f}%")
        with rc3:
            st.markdown("**Monthly**")
            st.write(f"Regime: {monthly_r.get('regime', 'N/A')}")
            if monthly_r.get("golden_cross") is not None:
                st.write(f"Golden Cross: {'Yes' if monthly_r['golden_cross'] else 'No'}")

    with tab_bt:
        tp = st.slider("Take Profit %", 1, 20, 8, key="tp")
        sl = st.slider("Stop Loss %", 1, 10, 4, key="sl")
        mh = st.slider("Max Hold Days", 5, 30, 20, key="mh")
        bt = backtest_strategy(daily_df, params={"take_profit_pct": tp/100, "stop_loss_pct": sl/100, "max_hold_days": mh}, regime=regime.get("regime"))
        if "error" in bt:
            st.error(bt["error"])
        else:
            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric("Trades", bt["total_trades"])
            bc2.metric("Win Rate", f"{bt['win_rate']:.0f}%")
            bc3.metric("Avg Return", f"{bt['avg_return']:.1f}%")
            bc4.metric("Sharpe", f"{bt['sharpe_ratio']:.2f}")
            if bt["trades"]:
                st.dataframe(pd.DataFrame(bt["trades"]), width="stretch")

    with tab_news:
        try:
            news = fetch_stock_news(symbol)
            if news:
                sentiment = analyze_news_sentiment(news)
                st.markdown(f"**Sentiment:** {format_sentiment_for_display(sentiment)}")
                for item in news[:5]:
                    st.write(f"• {item['title'][:100]}")
            else:
                st.info("No recent news.")
        except Exception:
            st.info("News unavailable.")

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════

if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = ALL_SYMBOLS[0] if ALL_SYMBOLS else ""

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "🔍 Scanner"


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 📊 Stock AI Screener")
    st.caption("Nifty 200 • Fully Automated")

    page = st.radio("Navigate", ["🔍 Scanner", "📊 Stock Detail"],
                     label_visibility="collapsed", key="sidebar_nav")

    st.markdown("---")
    min_score = st.slider("Min Score", 0, 100, MIN_SCORE_THRESHOLD, 5)

    st.markdown("---")
    status = get_scan_status()
    progress = get_scan_progress()
    if status == "running" and progress:
        st.caption(f"⏳ Scanning... {progress.get('current', 0)}/{progress.get('total', 199)}")
    elif status == "complete":
        st.caption("✅ Last scan complete")
    else:
        st.caption("🔄 Waiting for scan...")

    if st.button("🔄 Restart Worker", width="stretch", type="primary"):
        save_scan_status("idle")
        clear_scan_progress()
        spawn_worker()
        st.rerun()

    st.markdown("---")
    st.markdown("### ⭐ Watchlist")
    watchlist = get_watchlist()
    if watchlist:
        for w in watchlist:
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{w['symbol']}**")
            if c2.button("✕", key=f"rm_{w['symbol']}"):
                remove_from_watchlist(w['symbol'])
                st.rerun()
    else:
        st.caption("Empty")

    st.markdown("---")
    st.caption(f"Universe: {len(ALL_SYMBOLS)} stocks")


# ═══════════════════════════════════════════════════════════════
# SCANNER PAGE
# ═══════════════════════════════════════════════════════════════

if page == "🔍 Scanner":
    st.markdown("# 📈 Nifty 200 AI Screener")
    st.caption("Automated multi-timeframe analysis • Background worker • Updates every 15 min")

    tab_current, = st.tabs(["🔍 Current Scan"])

    with tab_current:
        status = get_scan_status()

        if status is None:
            spawn_worker()
            st.info("🚀 Starting first scan in background...")
            results = load_fresh_scan_results()
            if results:
                display_results(results, min_score)

        elif status == "idle":
            spawn_worker()
            st.info("🔄 Worker restarted...")
            results = load_fresh_scan_results()
            if results:
                st.caption("Showing cached results. Next scan running...")
                display_results(results, min_score)
            else:
                st.info("Waiting for scan to complete...")

        elif status == "running":
            if is_worker_alive():
                progress = get_scan_progress()
                if progress:
                    total = progress.get("total", 199)
                    current = progress.get("current", 0)
                    pct = current / total if total > 0 else 0
                    stock = progress.get("stock", "")
                    st.info(f"⏳ Scanning... {current}/{total} — {stock}")
                    st.progress(pct)
                results = load_fresh_scan_results()
                if results:
                    display_results(results, min_score)
            else:
                save_scan_status("idle")
                clear_scan_progress()
                spawn_worker()
                st.warning("⚠️ Worker crashed. Restarting...")

        elif status == "complete":
            results = load_fresh_scan_results()
            if results:
                display_results(results, min_score)
            else:
                st.warning("No stocks found. Try lowering Min Score.")


# ═══════════════════════════════════════════════════════════════
# STOCK DETAIL PAGE
# ═══════════════════════════════════════════════════════════════

elif page == "📊 Stock Detail":
    selected = st.session_state.get("selected_stock", ALL_SYMBOLS[0] if ALL_SYMBOLS else "")

    symbol = st.selectbox("Select Stock", ALL_SYMBOLS,
                          index=ALL_SYMBOLS.index(selected) if selected in ALL_SYMBOLS else 0,
                          key="stock_detail_select")

    if symbol:
        daily_df = get_daily_candles(symbol)
        analysis_data = get_stock_analysis(symbol)

        if analysis_data and daily_df is not None and len(daily_df) >= 30:
            display_stock_detail(analysis_data, daily_df, symbol)

            st.markdown("---")
            if st.button("⭐ Add to Watchlist"):
                add_to_watchlist(symbol)
                st.success(f"{symbol} added to watchlist!")
        elif daily_df is None or len(daily_df) < 30:
            st.warning(f"No candle data for {symbol}. Wait for scan to complete.")
        else:
            st.info(f"No analysis data for {symbol} yet. Wait for scan to complete.")
