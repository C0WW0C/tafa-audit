#!/usr/bin/env python3
# ============================================================
# TAFA V10 — Elite Panel Control (Streamlit)
# ============================================================
# Améliorations :
# - Gestion d'état via session_state (flash, refresh)
# - Mise en cache efficace des bougies
# - Layout responsive et informations claires
# - Intégration avec runtime_config et status_bridge
# - Ordres manuels avec feedback immédiat
# - Rafraîchissement automatique configurable
# ============================================================

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Path setup
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.bot_process import is_running, start_bot, status_snapshot, stop_bot
from core.runtime_config import get_config, save_config

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="TAFA Elite Panel Control",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS PERSO
# ============================================================

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 1rem; max-width: 1400px; }
    div[data-testid="stMetricValue"] { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 1.15rem; }
    div[data-testid="stMetricDelta"] { font-family: ui-monospace, monospace; }
    .stButton>button { border-radius: 6px; font-weight: 600; }
    .tafa-banner {
        border: 1px solid #2a2e39; background: #131722; border-radius: 8px;
        padding: 10px 14px; margin-bottom: 10px; font-size: 0.92rem;
    }
    .tafa-ok { color: #26a69a; font-weight: 700; }
    .tafa-bad { color: #ef5350; font-weight: 700; }
    .tafa-hold { color: #90caf9; font-weight: 700; }
    .tafa-muted { color: #787b86; }
    .book-row { font-family: ui-monospace, monospace; font-size: 0.82rem; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE INIT
# ============================================================

if "flash" not in st.session_state:
    st.session_state.flash = None  # (type, message)
if "refresh_timer" not in st.session_state:
    st.session_state.refresh_timer = 0
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# ============================================================
# HELPERS
# ============================================================

def _fmt(n: Any, d: int = 2) -> str:
    """Format number with commas and decimal places."""
    try:
        if n is None or n == "":
            return "—"
        return f"{float(n):,.{d}f}"
    except Exception:
        return "—"

def _fmt_px(n: Any) -> str:
    """Format price (adapt decimals)."""
    try:
        if n is None:
            return "—"
        x = float(n)
        return _fmt(x, 1) if x >= 1000 else _fmt(x, 4)
    except Exception:
        return "—"

def _age_s(st_status: dict) -> Optional[float]:
    """Return age of status in seconds."""
    ts = st_status.get("updated_at")
    if isinstance(ts, (int, float)) and ts > 0:
        return max(0.0, time.time() - float(ts))
    return None

@st.cache_data(ttl=45, show_spinner=False)
def _load_candles(symbol: str, bar: str, limit: int = 220) -> Tuple[pd.DataFrame, str]:
    """Load OHLC candles (closed bars only) from candles_feed."""
    try:
        from core.candles_feed import candles_payload
        payload = candles_payload(symbol=symbol, bar=bar, limit=limit)
        rows = payload.get("candles") or []
        if not rows:
            return pd.DataFrame(), str(payload.get("source") or "none")
        df = pd.DataFrame(rows)
        df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df, str(payload.get("source") or "?")
    except Exception as exc:
        return pd.DataFrame(), f"error:{exc}"

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _candle_fig(df: pd.DataFrame, title: str, ma_fast: int = 12, ma_slow: int = 55) -> go.Figure:
    """Create OHLC chart with EMAs and volume."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.78, 0.22],
    )
    if df.empty:
        fig.update_layout(
            title=title + " — no data",
            height=500,
            template="plotly_dark",
            paper_bgcolor="#0b0e11",
            plot_bgcolor="#131722",
        )
        return fig

    fig.add_trace(
        go.Candlestick(
            x=df["dt"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            increasing_fillcolor="#26a69a",
            decreasing_fillcolor="#ef5350",
        ),
        row=1, col=1,
    )
    if len(df) >= ma_fast:
        fig.add_trace(
            go.Scatter(
                x=df["dt"],
                y=_ema(df["close"], ma_fast),
                name=f"EMA{ma_fast}",
                line=dict(color="#2962ff", width=1.2),
            ),
            row=1, col=1,
        )
    if len(df) >= ma_slow:
        fig.add_trace(
            go.Scatter(
                x=df["dt"],
                y=_ema(df["close"], ma_slow),
                name=f"EMA{ma_slow}",
                line=dict(color="#f0b90b", width=1.2),
            ),
            row=1, col=1,
        )

    colors = [
        "rgba(38,166,154,.4)" if c >= o else "rgba(239,83,80,.4)"
        for o, c in zip(df["open"], df["close"])
    ]
    fig.add_trace(
        go.Bar(x=df["dt"], y=df["volume"], name="Vol", marker_color=colors, showlegend=False),
        row=2, col=1,
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=520,
        template="plotly_dark",
        paper_bgcolor="#0b0e11",
        plot_bgcolor="#131722",
        margin=dict(l=8, r=8, t=36, b=8),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="rgba(42,46,57,.45)", showgrid=True)
    fig.update_yaxes(gridcolor="rgba(42,46,57,.45)", showgrid=True)
    return fig

def _extract_book(st_status: dict) -> dict:
    """Extract order book from status."""
    market = st_status.get("market", {})
    ws = st_status.get("ws", {})
    book = market.get("book", {})
    if not (book.get("bids") or book.get("asks")):
        wb = ws.get("book", {})
        if wb.get("bids") or wb.get("asks"):
            book = wb
    return book or {}

def _render_book(book: dict) -> None:
    """Render order book in a styled list."""
    asks = list(book.get("asks") or [])[:8]
    bids = list(book.get("bids") or [])[:8]

    def _lvl(row):
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            return float(row[0]), float(row[1])
        if isinstance(row, dict):
            return float(row.get("price") or row.get("px") or 0), float(row.get("size") or row.get("sz") or 0)
        return 0.0, 0.0

    ask_rows = [_lvl(r) for r in asks]
    bid_rows = [_lvl(r) for r in bids]
    best_ask = ask_rows[0][0] if ask_rows else None
    best_bid = bid_rows[0][0] if bid_rows else None
    spread = (best_ask - best_bid) if best_ask and best_bid else None

    st.caption(
        f"spread **{_fmt(spread, 2)}** · bid **{_fmt_px(best_bid)}** · ask **{_fmt_px(best_ask)}**"
        if spread is not None
        else "carnet indisponible (bot/WS)"
    )

    lines: List[str] = []
    for px, sz in reversed(ask_rows):
        lines.append(f"<div class='book-row' style='color:#ef5350'>{_fmt_px(px):>12}  {sz:>10.4f}</div>")
    mid = (best_ask + best_bid) / 2 if best_ask and best_bid else None
    lines.append(
        f"<div class='book-row' style='text-align:center;padding:6px 0;color:#d1d4dc;border-top:1px solid #2a2e39;border-bottom:1px solid #2a2e39'>"
        f"<b>{_fmt_px(mid)}</b></div>"
    )
    for px, sz in bid_rows:
        lines.append(f"<div class='book-row' style='color:#26a69a'>{_fmt_px(px):>12}  {sz:>10.4f}</div>")
    if len(lines) <= 1:
        st.info("Pas de niveaux books5 pour l’instant.")
    else:
        st.markdown("\n".join(lines), unsafe_allow_html=True)

def _position_from_paper(paper: dict) -> Tuple[str, Any, Any, Any]:
    """Extract position info from paper status."""
    side, entry, size, upnl = "FLAT", None, None, None
    if paper.get("qty") not in (None, 0, 0.0, "0"):
        try:
            q = float(paper["qty"])
            if q != 0:
                side = "LONG" if q > 0 else "SHORT"
                size = q
                entry = paper.get("entry_price") or paper.get("entry")
                upnl = paper.get("unrealized_pnl") or paper.get("upnl")
        except Exception:
            pass
    pos = paper.get("position") or paper.get("positions")
    if side == "FLAT" and isinstance(pos, dict) and (pos.get("side") or pos.get("qty")):
        side = str(pos.get("side") or "FLAT").upper()
        entry = pos.get("entry") or pos.get("avg_price")
        size = pos.get("qty") or pos.get("size")
        upnl = pos.get("unrealized_pnl") or pos.get("upnl")
    return side, entry, size, upnl

def _load_journal(limit: int = 50) -> pd.DataFrame:
    """Load journal entries from file or trades CSV."""
    journal = ROOT / "data" / "journal.jsonl"
    rows: List[dict] = []
    if journal.exists():
        try:
            for ln in journal.read_text(encoding="utf-8").strip().splitlines()[-limit:]:
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    pass
        except Exception:
            pass
    if rows:
        return pd.DataFrame(rows).iloc[::-1].reset_index(drop=True)
    trades_csv = ROOT / "data" / "datasets" / "tafa_trades.csv"
    if trades_csv.exists():
        try:
            return pd.read_csv(trades_csv).tail(limit).iloc[::-1]
        except Exception:
            pass
    return pd.DataFrame()

def _flash():
    """Display flash message from session_state."""
    msg = st.session_state.flash
    if not msg:
        return
    kind, text = msg
    if kind == "ok":
        st.success(text)
    elif kind == "warn":
        st.warning(text)
    else:
        st.error(text)
    st.session_state.flash = None  # clear

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## ◆ Elite Panel Control")
st.sidebar.caption("V10 · PAPER · closed-bars · bot_process")

# Get fresh status
st_status = status_snapshot()
running = bool(st_status.get("running"))
mode = str(st_status.get("mode") or "PAPER").upper()
age = _age_s(st_status)
cfg = get_config()

# Start / Stop
sc1, sc2 = st.sidebar.columns(2)
with sc1:
    if st.button("▶ Start", width="stretch", type="primary", disabled=running):
        res = start_bot()
        st.session_state.flash = ("ok" if res.get("ok") else "err", res.get("message", ""))
        time.sleep(0.35)
        st.rerun()
with sc2:
    if st.button("■ Stop", width="stretch", disabled=not is_running()):
        res = stop_bot()
        st.session_state.flash = ("ok", res.get("message", "Stop"))
        time.sleep(0.25)
        st.rerun()

# Status banner
alive_lbl = '<span class="tafa-ok">RUNNING</span>' if running else '<span class="tafa-bad">STOPPED</span>'
age_lbl = f"{age:.0f}s" if age is not None else "—"
stale = bool(running and age is not None and age > 45)
st.sidebar.markdown(
    f"""
<div class="tafa-banner">
  Bot {alive_lbl}<br/>
  Mode <b>{mode}</b> · PID <code>{st_status.get('pid') or '—'}</code><br/>
  Heartbeat <code>{age_lbl}</code>
  {" · <span class='tafa-bad'>STALE</span>" if stale else ""}<br/>
  <span class="tafa-muted">{st_status.get('script') or ''}</span>
</div>
""",
    unsafe_allow_html=True,
)

# Configuration form
st.sidebar.markdown("### Paramètres")
with st.sidebar.form("cfg_form"):
    capital = st.number_input(
        "Capital", min_value=10.0, max_value=10_000_000.0, value=float(cfg.get("capital", 1000.0))
    )
    risk_pct = st.number_input(
        "Risk % / trade",
        min_value=0.1,
        max_value=5.0,
        value=float(cfg.get("risk_per_trade_pct", cfg.get("risk_pct", 2.0))),
    )
    min_conf = st.number_input(
        "Min conf", min_value=0.0, max_value=1.0, value=float(cfg.get("min_conf", 0.40)), step=0.01
    )
    ma_fast = st.number_input("MA fast", min_value=3, max_value=100, value=int(cfg.get("ma_fast", 12)))
    ma_slow = st.number_input("MA slow", min_value=10, max_value=300, value=int(cfg.get("ma_slow", 55)))
    tsmom_lb = st.number_input(
        "TSMOM lookback", min_value=5, max_value=2000, value=int(cfg.get("tsmom_lookback", 120))
    )
    symbol = st.text_input(
        "Symbol", value=str(cfg.get("symbol") or st_status.get("symbol") or "BTC-USDC")
    )
    _tf_opts = ["5m", "15m", "1h", "4h", "1d"]
    _tf_default = str(cfg.get("timeframe") or "4h").lower()
    _tf_idx = _tf_opts.index(_tf_default) if _tf_default in _tf_opts else 3
    bar = st.selectbox("TF chart", _tf_opts, index=_tf_idx)

    submitted = st.form_submit_button("Appliquer config", width="stretch")
    if submitted:
        try:
            res = save_config({
                "capital": capital,
                "risk_per_trade_pct": risk_pct,
                "min_conf": min_conf,
                "ma_fast": int(ma_fast),
                "ma_slow": int(ma_slow),
                "tsmom_lookback": int(tsmom_lb),
                "symbol": symbol.strip(),
            })
            if res.get("ok"):
                st.session_state.flash = ("ok", "Config appliquée (capital si flat).")
            else:
                st.session_state.flash = ("warn", f"Rejected: {res.get('rejected')}")
        except Exception as exc:
            st.session_state.flash = ("err", f"Config: {exc}")
        st.rerun()

# Refresh controls
refresh_s = st.sidebar.slider("Auto-refresh (s)", 0, 30, 8, help="0 = manuel uniquement")
if st.sidebar.button("Rafraîchir maintenant", width="stretch"):
    # Invalidate cache
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Desk web · http://127.0.0.1:8765/desk")

# ============================================================
# MAIN
# ============================================================

_flash()

# Extract data from status
paper = st_status.get("paper", {})
ai = st_status.get("ai", {})
risk = st_status.get("risk", {})
perf = st_status.get("performance", {})
px = st_status.get("last_price") or paper.get("last_price") or paper.get("price")
eq = paper.get("equity") or paper.get("balance") or perf.get("equity")
cap = paper.get("initial_capital") or paper.get("capital") or cfg.get("capital")
pnl = paper.get("session_pnl") if paper.get("session_pnl") is not None else perf.get("session_pnl")
if pnl is None and eq is not None and cap:
    try:
        pnl = float(eq) - float(cap)
    except Exception:
        pnl = None
ret = paper.get("session_return_pct")
if ret is None and eq is not None and cap:
    try:
        ret = (float(eq) / float(cap) - 1.0) * 100.0
    except Exception:
        ret = None
sig = str(st_status.get("last_signal") or ai.get("signal") or "HOLD").upper()
dd = st_status.get("drawdown") if st_status.get("drawdown") is not None else risk.get("drawdown")

# Header
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("### TAFA Elite Panel Control")
with h2:
    sig_cls = "tafa-ok" if sig == "BUY" else ("tafa-bad" if sig == "SELL" else "tafa-hold")
    st.markdown(
        f"<div style='text-align:right;padding-top:8px'>Signal <span class='{sig_cls}'>{sig}</span></div>",
        unsafe_allow_html=True,
    )

# Metrics
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Prix", _fmt_px(px))
m2.metric("Equity", _fmt(eq, 2))
m3.metric(
    "Session PnL",
    _fmt(pnl, 2),
    delta=(f"{ret:+.2f}%" if isinstance(ret, (int, float)) else None),
)
m4.metric("Signal", sig)
m5.metric("Cycle", st_status.get("cycle", "—"))
dd_disp = None
try:
    if dd is not None:
        ddv = float(dd)
        dd_disp = f"{ddv * 100:.2f}%" if abs(ddv) <= 1 else f"{ddv:.2f}%"
except Exception:
    dd_disp = "—"
m6.metric("Drawdown", dd_disp or "—")

# Subheader with extra info
conf = ai.get("confidence")
try:
    conf_s = f"{float(conf) * 100:.1f}%" if conf is not None and float(conf) <= 1 else _fmt(conf, 2)
except Exception:
    conf_s = "—"
st.caption(
    f"`{st_status.get('symbol') or symbol}` · régime **{ai.get('regime') or st_status.get('regime') or '—'}** · "
    f"conf **{conf_s}** · state **{st_status.get('state')}** · "
    f"heartbeat **{age_lbl}**" + (" · ⚠️ STALE" if stale else "")
)

# Main panels: Chart + Book + Position
left, mid, right = st.columns([2.4, 0.95, 0.95])

with left:
    st.markdown("#### Bougies OHLC")
    df, src = _load_candles(str(symbol or "BTC-USDC"), bar, limit=220)
    last_c = None
    if not df.empty:
        last_c = float(df["close"].iloc[-1])
        chg = float(df["close"].iloc[-1] - df["open"].iloc[-1])
        st.caption(f"source `{src}` · {len(df)} barres · last `{_fmt_px(last_c)}` · barre `{chg:+.2f}`")
    else:
        st.caption(f"source `{src}` · aucune barre")
    st.plotly_chart(
        _candle_fig(df, f"{symbol} · {bar}", ma_fast=int(ma_fast), ma_slow=int(ma_slow)),
        width="stretch",
    )

with mid:
    st.markdown("#### Order book")
    _render_book(_extract_book(st_status))

with right:
    st.markdown("#### Position")
    side, entry, size, upnl = _position_from_paper(paper)
    side_cls = "tafa-ok" if side in ("LONG", "BUY") else ("tafa-bad" if side in ("SHORT", "SELL") else "tafa-muted")
    st.markdown(f"Side <span class='{side_cls}'>{side}</span>", unsafe_allow_html=True)
    st.write(f"Entry `{_fmt_px(entry)}`")
    st.write(f"Size `{_fmt(size, 6)}`")
    st.write(f"uPnL `{_fmt(upnl, 2)}`")
    st.write(f"Risk `{risk.get('state') or risk.get('status') or '—'}`")
    ws = st_status.get("ws", {})
    st.write(f"WS `{'on' if ws.get('connected') else ws.get('connected', '—')}`")
    st.markdown("---")
    st.markdown("#### Ticket paper")
    amt = st.number_input("USDC", min_value=5.0, max_value=250.0, value=25.0, step=5.0, key="ticket_amt")
    t1, t2 = st.columns(2)
    if t1.button("ACHETER", width="stretch", type="primary"):
        try:
            from core.manual_paper_orders import enqueue
            r = enqueue(str(symbol), "BUY", float(amt))
            st.session_state.flash = ("ok", f"BUY paper · id={str(r.get('id', ''))[:8]}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if t2.button("VENDRE", width="stretch"):
        try:
            from core.manual_paper_orders import enqueue
            r = enqueue(str(symbol), "SELL", float(amt))
            st.session_state.flash = ("ok", f"SELL paper · id={str(r.get('id', ''))[:8]}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    st.caption("Paper only · 5–250 USDC · pas d’ordre exchange")

# Blotter tabs
st.markdown("#### Blotter")
tab_t, tab_m, tab_s, tab_c = st.tabs(["Journal", "Manuels", "Status", "Config"])

with tab_t:
    jdf = _load_journal(50)
    if jdf.empty:
        st.info("Aucun événement journalisé.")
    else:
        st.dataframe(jdf, width="stretch", height=300)

with tab_m:
    pending = ROOT / "data" / "manual_paper_orders"
    files = sorted(pending.glob("*.json")) if pending.exists() else []
    if not files:
        st.caption("Aucune demande manuelle en file.")
    else:
        items = []
        for f in files[-20:]:
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass
        if items:
            st.dataframe(pd.DataFrame(items), width="stretch", height=240)
        else:
            st.caption("File vide / illisible.")

with tab_s:
    st.json(st_status)

with tab_c:
    st.json(get_config())

st.caption("Elite Panel Control · bot_process → run_v10 · status_bridge · OHLC closed-bars · PAPER only")

# ============================================================
# AUTO-REFRESH
# ============================================================

if refresh_s and refresh_s > 0:
    # Use a timer-based rerun
    now = time.time()
    if now - st.session_state.last_refresh >= refresh_s:
        st.session_state.last_refresh = now
        st.rerun()
    else:
        # Rerun after remaining time (simulate periodic refresh)
        time.sleep(0.5)  # small delay to avoid busy loop
        st.rerun()