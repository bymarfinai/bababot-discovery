"""Mode3 BBC Backtest Endpoint — /mode3_bbc/backtest.
BULL/BEAR/SIDEWAYS all support MTF 15m precision.
"""
import os
from dataclasses import asdict
from fastapi import APIRouter, Query
import sqlite3
import numpy as np
from datetime import datetime

from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def load_candles_from_db(symbol, timeframe, start_ts, end_ts):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT open_time, open, high, low, close, volume FROM klines
        WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC""", (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall()
    conn.close()
    return rows


def compute_mtf_bull_entry(rows_1h, rows_15m):
    if not rows_15m:
        return [None] * len(rows_1h), [None] * len(rows_1h)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    lows_15m = np.array([r[3] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ema_15m = compute_ema_series(closes_15m, 20)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    entry_closes, entry_lows = [], []
    for r in rows_1h:
        t_1h = r[0]
        fc, fl = None, None
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None:
                continue
            if (lows_15m[j] <= ema_15m[j] and closes_15m[j] > ema_15m[j] and closes_15m[j] > opens_15m[j]):
                fc = float(closes_15m[j])
                fl = float(lows_15m[j])
                break
        entry_closes.append(fc)
        entry_lows.append(fl)
    return entry_closes, entry_lows


def compute_mtf_bear_entry(rows_1h, rows_15m):
    if not rows_15m:
        return [None] * len(rows_1h), [None] * len(rows_1h)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    highs_15m = np.array([r[2] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ema_15m = compute_ema_series(closes_15m, 20)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    entry_closes, entry_highs = [], []
    for r in rows_1h:
        t_1h = r[0]
        fc, fh = None, None
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None:
                continue
            if (highs_15m[j] >= ema_15m[j] and closes_15m[j] < ema_15m[j] and closes_15m[j] < opens_15m[j]):
                fc = float(closes_15m[j])
                fh = float(highs_15m[j])
                break
        entry_closes.append(fc)
        entry_highs.append(fh)
    return entry_closes, entry_highs


def compute_mtf_sideways_entry(rows_1h, rows_15m, vahs, vals):
    """SIDEWAYS MTF: scan 4 sub-15m for VAH/VAL touch pattern (uses 1h VAH/VAL levels)."""
    n = len(rows_1h)
    if not rows_15m:
        return [None]*n, [None]*n, [None]*n, [None]*n
    highs_15m = np.array([r[2] for r in rows_15m], dtype=float)
    lows_15m = np.array([r[3] for r in rows_15m], dtype=float)
    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    ts_to_idx = {r[0]: i for i, r in enumerate(rows_15m)}
    ONE_15M_MS = 15 * 60 * 1000
    short_c, short_h, long_c, long_l = [], [], [], []
    for i, r in enumerate(rows_1h):
        t_1h = r[0]
        vah = vahs[i]; val = vals[i]
        sc, sh, lc, ll = None, None, None, None
        if vah is None or val is None:
            short_c.append(None); short_h.append(None)
            long_c.append(None); long_l.append(None)
            continue
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None:
                continue
            # SHORT: 15m high >= vah AND 15m close <= vah
            if sc is None and highs_15m[j] >= vah and closes_15m[j] <= vah:
                sc = float(closes_15m[j])
                sh = float(highs_15m[j])
            # LONG: 15m low <= val AND 15m close >= val
            if lc is None and lows_15m[j] <= val and closes_15m[j] >= val:
                lc = float(closes_15m[j])
                ll = float(lows_15m[j])
            if sc is not None and lc is not None:
                break
        short_c.append(sc); short_h.append(sh)
        long_c.append(lc); long_l.append(ll)
    return short_c, short_h, long_c, long_l


@router.get("/backtest")
def backtest_mode3_bbc(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(30, ge=1, le=1500),
    end_days_ago: int = Query(0, ge=0, le=1500),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.012, ge=0.001, le=0.05),
    sideways_tp_pct: float = Query(0.003, ge=0.0, le=0.05),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    fee_pct: float = Query(0.001),
    slippage_pct: float = Query(0.0005),
    bull_poc_entry_enabled: bool = Query(False),
    bull_poc_max_distance_pct: float = Query(0.02, ge=0.001, le=0.10),
    bull_mtf_15m_enabled: bool = Query(False),
    bull_body_ratio_min: float = Query(0.0, ge=0.0, le=1.0),
    bull_wait_retest_enabled: bool = Query(False),
    bull_retest_swing_lookback: int = Query(20, ge=5, le=200),
    bull_retest_tolerance_pct: float = Query(0.003, ge=0.0, le=0.05),
    bull_retest_max_bars: int = Query(5, ge=1, le=20),
    bull_use_swing_break: bool = Query(False),
    bull_swing_lookback: int = Query(20, ge=5, le=200),
    bull_use_26_support: bool = Query(False),
    bull_26_lookback: int = Query(50, ge=10, le=200),
    bull_26_ratio: float = Query(2.6, ge=1.5, le=5.0),
    bull_26_tolerance_pct: float = Query(0.003, ge=0.0, le=0.05),
    bear_mtf_15m_enabled: bool = Query(False),
    bear_body_ratio_min: float = Query(0.0, ge=0.0, le=1.0),
    sideways_mtf_15m_enabled: bool = Query(False),
):
    config = Mode3BBCConfig(
        va_window=va_window, ema_period=ema_period,
        tp_pct=tp_pct, sideways_tp_pct=sideways_tp_pct,
        bear_tp_pct=bear_tp_pct,
        entry_usd=entry_usd, leverage=leverage,
        fee_pct_roundtrip=fee_pct, slippage_pct=slippage_pct,
        bull_poc_entry_enabled=bull_poc_entry_enabled,
        bull_poc_max_distance_pct=bull_poc_max_distance_pct,
        bull_mtf_15m_enabled=bull_mtf_15m_enabled,
        bull_body_ratio_min=bull_body_ratio_min,
        bull_wait_retest_enabled=bull_wait_retest_enabled,
        bull_retest_swing_lookback=bull_retest_swing_lookback,
        bull_retest_tolerance_pct=bull_retest_tolerance_pct,
        bull_retest_max_bars=bull_retest_max_bars,
        bull_use_swing_break=bull_use_swing_break,
        bull_swing_lookback=bull_swing_lookback,
        bull_use_26_support=bull_use_26_support,
        bull_26_lookback=bull_26_lookback,
        bull_26_ratio=bull_26_ratio,
        bull_26_tolerance_pct=bull_26_tolerance_pct,
        bear_mtf_15m_enabled=bear_mtf_15m_enabled,
        bear_body_ratio_min=bear_body_ratio_min,
        sideways_mtf_15m_enabled=sideways_mtf_15m_enabled,
    )

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ts = now_ms - (end_days_ago * 86400 * 1000)
    start_ts = end_ts - (days * 86400 * 1000)
    rows = load_candles_from_db(symbol, timeframe, start_ts, end_ts)

    if len(rows) < config.startup_warmup_candles:
        return {"error": f"Not enough candles: {len(rows)}", "trades": []}

    opens = np.array([r[1] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    closes = np.array([r[4] for r in rows], dtype=float)
    volumes = np.array([r[5] for r in rows], dtype=float)

    ema20 = compute_ema_series(closes, config.ema_period)

    vahs, vals, pocs = [], [], []
    for i in range(len(rows)):
        vah, val, poc = compute_va_at_bar(
            highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low,
        )
        vahs.append(vah); vals.append(val); pocs.append(poc)

    switcher = Switcher(config)

    if bull_mtf_15m_enabled or bear_mtf_15m_enabled or sideways_mtf_15m_enabled:
        rows_15m = load_candles_from_db(symbol, '15m', start_ts, end_ts)
        if rows_15m:
            if bull_mtf_15m_enabled:
                ec, el = compute_mtf_bull_entry(rows, rows_15m)
                switcher.mtf_bull_entry_close = ec
                switcher.mtf_bull_entry_low = el
            if bear_mtf_15m_enabled:
                ec, eh = compute_mtf_bear_entry(rows, rows_15m)
                switcher.mtf_bear_entry_close = ec
                switcher.mtf_bear_entry_high = eh
            if sideways_mtf_15m_enabled:
                sc, sh, lc, ll = compute_mtf_sideways_entry(rows, rows_15m, vahs, vals)
                switcher.mtf_sideways_short_entry_close = sc
                switcher.mtf_sideways_short_entry_high = sh
                switcher.mtf_sideways_long_entry_close = lc
                switcher.mtf_sideways_long_entry_low = ll

    for i in range(len(rows)):
        switcher.process_candle(
            bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i],
            ema20=ema20[i], vah=vahs[i], val=vals[i], poc=pocs[i],
        )

    trades = switcher.trades
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    total_pnl_usd = sum(t.pnl_usd for t in trades)
    total_pnl_pct = sum(t.pnl_pct for t in trades) * 100
    wr = 100.0 * len(wins) / n if n > 0 else 0

    tool_stats = {}
    for tool in ['SIDEWAYS', 'BULL', 'BEAR']:
        tt = [t for t in trades if t.tool == tool]
        if tt:
            tw = [t for t in tt if t.pnl_usd > 0]
            tool_stats[tool] = {
                "count": len(tt), "wr_pct": round(100.0 * len(tw) / len(tt), 2),
                "pnl_usd": round(sum(t.pnl_usd for t in tt), 2),
                "pnl_pct": round(sum(t.pnl_pct for t in tt) * 100, 3),
            }

    bull_trigger_stats = {}
    for trig in ['ema_reclaim', 'poc_bounce', 'swing_break', 'retest_entry', '26_bounce']:
        tt = [t for t in trades if t.tool == 'BULL' and t.entry_trigger == trig]
        if tt:
            tw = [t for t in tt if t.pnl_usd > 0]
            bull_trigger_stats[trig] = {
                "count": len(tt), "wr_pct": round(100.0 * len(tw) / len(tt), 2),
                "pnl_usd": round(sum(t.pnl_usd for t in tt), 2),
            }

    exit_type_breakdown = {}
    for t in trades:
        exit_type_breakdown[t.exit_type] = exit_type_breakdown.get(t.exit_type, 0) + 1

    trade_list = []
    for t in trades:
        trade_list.append({
            "tool": t.tool, "side": t.side,
            "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
            "entry_bar": t.entry_bar, "exit_bar": t.exit_bar, "exit_type": t.exit_type,
            "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2),
            "sl_level": round(t.sl_level, 2), "tp_level": round(t.tp_level, 2),
            "sl_distance_pct": round(abs(t.entry_price - t.sl_level) / t.entry_price * 100, 3),
            "ema_at_entry": round(t.ema_at_entry, 2), "ema_at_exit": round(t.ema_at_exit, 2),
            "peak_high": round(t.peak_high, 2), "trough_low": round(t.trough_low, 2),
            "entry_trigger": t.entry_trigger,
        })

    return {
        "symbol": symbol, "timeframe": timeframe, "days": days, "end_days_ago": end_days_ago,
        "candles_processed": len(rows),
        "period_start_utc": datetime.utcfromtimestamp(start_ts / 1000).strftime('%Y-%m-%d'),
        "period_end_utc": datetime.utcfromtimestamp(end_ts / 1000).strftime('%Y-%m-%d'),
        "config": asdict(config),
        "summary": {
            "total_trades": n, "win_rate_pct": round(wr, 2),
            "wins": len(wins), "losses": len(losses),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_pct": round(total_pnl_pct, 3),
            "capital_start": config.capital_usd,
            "capital_end": round(config.capital_usd + total_pnl_usd, 2),
            "sideways_entries": switcher._sideways_entries,
            "sideways_blocked_mtf": switcher._sideways_blocked_mtf,
            "bull_entries_attempted": switcher._bull_entries,
            "bull_ema_reclaim_entries": switcher._bull_ema_reclaim_entries,
            "bull_poc_bounce_entries": switcher._bull_poc_bounce_entries,
            "bull_swing_break_entries": switcher._bull_swing_break_entries,
            "bull_retest_entries": switcher._bull_retest_entries,
            "bull_26_bounce_entries": switcher._bull_26_bounce_entries,
            "bull_blocked_mtf": switcher._bull_blocked_mtf,
            "bull_blocked_body": switcher._bull_blocked_body,
            "bear_entries_attempted": switcher._bear_entries,
            "bear_blocked_mtf": switcher._bear_blocked_mtf,
            "bear_blocked_body": switcher._bear_blocked_body,
            "exit_type_breakdown": exit_type_breakdown,
        },
        "per_tool": tool_stats,
        "bull_trigger_stats": bull_trigger_stats,
        "trades": trade_list,
        "final_state": switcher.state,
    }


@router.get("/health")
def mode3_bbc_health():
    return {"status": "ok", "module": "mode3_bbc", "version": "0.9", "db_path": DB_PATH}
