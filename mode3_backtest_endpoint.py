"""
Mode3 Backtest Endpoint v4.0 — Add AMT Position Modifier params.
"""
import os
import json as jsonlib
from dataclasses import asdict
from fastapi import APIRouter, Query, Body
from typing import Optional
import sqlite3
import numpy as np
from datetime import datetime

from mode3 import Mode3Config, Switcher, compute_ema_series, compute_va_at_bar

router = APIRouter(prefix="/mode3", tags=["mode3"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _ensure_experiments_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mode3_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            version TEXT, symbol TEXT, timeframe TEXT, days INTEGER,
            cap_pct REAL, tp_pct REAL, va_window INTEGER,
            entry_usd REAL, leverage REAL, fee_pct REAL, slippage_pct REAL,
            total_trades INTEGER, wins INTEGER, losses INTEGER, wr_pct REAL,
            pnl_usd REAL, pnl_pct REAL,
            sw_count INTEGER, sw_wr REAL, sw_pnl REAL,
            bull_count INTEGER, bull_wr REAL, bull_pnl REAL,
            bear_count INTEGER, bear_wr REAL, bear_pnl REAL,
            blocked_count INTEGER, final_state TEXT, config_json TEXT, notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def _log_experiment(config, result, symbol, timeframe, days):
    try:
        _ensure_experiments_table()
        s = result['summary']
        pt = result.get('per_tool', {})
        sw = pt.get('SIDEWAYS', {}); bl = pt.get('BULL', {}); br = pt.get('BEAR', {})
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO mode3_experiments (
                timestamp, version, symbol, timeframe, days,
                cap_pct, tp_pct, va_window, entry_usd, leverage, fee_pct, slippage_pct,
                total_trades, wins, losses, wr_pct, pnl_usd, pnl_pct,
                sw_count, sw_wr, sw_pnl, bull_count, bull_wr, bull_pnl, bear_count, bear_wr, bear_pnl,
                blocked_count, final_state, config_json
            ) VALUES (?,?,?,?,?, ?,?,?,?,?,?,?, ?,?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?)
        """, (
            int(datetime.utcnow().timestamp()), '4.0', symbol, timeframe, days,
            config.sideways_ema_distance_cap, config.tp_pct, config.va_window,
            config.entry_usd, config.leverage, config.fee_pct_roundtrip, config.slippage_pct,
            s['total_trades'], s['wins'], s['losses'], s['win_rate_pct'],
            s['total_pnl_usd'], s['total_pnl_pct'],
            sw.get('count', 0), sw.get('wr_pct', 0), sw.get('pnl_usd', 0),
            bl.get('count', 0), bl.get('wr_pct', 0), bl.get('pnl_usd', 0),
            br.get('count', 0), br.get('wr_pct', 0), br.get('pnl_usd', 0),
            s.get('sideways_blocked_count', 0), result.get('final_state', ''),
            jsonlib.dumps(asdict(config)),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Failed to log: {e}")


def load_candles_from_db(symbol, timeframe, start_ts, end_ts):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT open_time, open, high, low, close, volume FROM klines
        WHERE symbol = ? AND timeframe = ? AND open_time >= ? AND open_time < ?
        ORDER BY open_time ASC
    """, (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall()
    conn.close()
    return rows


def compute_mtf_bull_entry(rows_1h, rows_15m):
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
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
            if j is None: continue
            if (lows_15m[j] <= ema_15m[j] and closes_15m[j] > ema_15m[j]
                    and closes_15m[j] > opens_15m[j]):
                fc = float(closes_15m[j]); fl = float(lows_15m[j]); break
        entry_closes.append(fc); entry_lows.append(fl)
    return entry_closes, entry_lows


def compute_mtf_bear_entry(rows_1h, rows_15m):
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
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
            if j is None: continue
            if (highs_15m[j] >= ema_15m[j] and closes_15m[j] < ema_15m[j]
                    and closes_15m[j] < opens_15m[j]):
                fc = float(closes_15m[j]); fh = float(highs_15m[j]); break
        entry_closes.append(fc); entry_highs.append(fh)
    return entry_closes, entry_highs


def compute_mtf_sideways_entry(rows_1h, rows_15m, vahs, vals):
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
            short_c.append(None); short_h.append(None); long_c.append(None); long_l.append(None); continue
        for k in range(4):
            j = ts_to_idx.get(t_1h + k * ONE_15M_MS)
            if j is None: continue
            if sc is None and highs_15m[j] >= vah and closes_15m[j] <= vah:
                sc = float(closes_15m[j]); sh = float(highs_15m[j])
            if lc is None and lows_15m[j] <= val and closes_15m[j] >= val:
                lc = float(closes_15m[j]); ll = float(lows_15m[j])
            if sc is not None and lc is not None: break
        short_c.append(sc); short_h.append(sh); long_c.append(lc); long_l.append(ll)
    return short_c, short_h, long_c, long_l


def compute_htf_4h_context(rows_1h, rows_4h, va_window=50, trap_lookback=3):
    n = len(rows_1h)
    if not rows_4h:
        return {'vah':[None]*n,'val':[None]*n,'ema':[None]*n,'close':[None]*n,
                'trap_short':[False]*n,'trap_long':[False]*n}
    opens_4h = np.array([r[1] for r in rows_4h], dtype=float)
    highs_4h = np.array([r[2] for r in rows_4h], dtype=float)
    lows_4h = np.array([r[3] for r in rows_4h], dtype=float)
    closes_4h = np.array([r[4] for r in rows_4h], dtype=float)
    volumes_4h = np.array([r[5] for r in rows_4h], dtype=float)
    ts_4h = [r[0] for r in rows_4h]
    ONE_4H_MS = 4 * 60 * 60 * 1000
    ema_4h = compute_ema_series(closes_4h, 20)
    vahs_4h, vals_4h = [], []
    for i in range(len(rows_4h)):
        v, l_, _ = compute_va_at_bar(highs_4h, lows_4h, closes_4h, volumes_4h, i, va_window, 85.0, 15.0)
        vahs_4h.append(v); vals_4h.append(l_)
    reject_short_4h = [False]*len(rows_4h)
    reject_long_4h = [False]*len(rows_4h)
    for i in range(len(rows_4h)):
        v = vahs_4h[i]; l_ = vals_4h[i]
        if v is not None and highs_4h[i] >= v and closes_4h[i] < v and closes_4h[i] < opens_4h[i]:
            reject_short_4h[i] = True
        if l_ is not None and lows_4h[i] <= l_ and closes_4h[i] > l_ and closes_4h[i] > opens_4h[i]:
            reject_long_4h[i] = True
    vah_out, val_out, ema_out, close_out = [], [], [], []
    trap_short_out, trap_long_out = [], []
    idx_4h = 0
    for r in rows_1h:
        t_1h = r[0]
        while idx_4h + 1 < len(ts_4h) and ts_4h[idx_4h + 1] + ONE_4H_MS <= t_1h:
            idx_4h += 1
        if ts_4h[idx_4h] + ONE_4H_MS <= t_1h:
            vah_out.append(vahs_4h[idx_4h])
            val_out.append(vals_4h[idx_4h])
            ema_out.append(float(ema_4h[idx_4h]))
            close_out.append(float(closes_4h[idx_4h]))
            start = max(0, idx_4h - trap_lookback + 1)
            trap_short_out.append(any(reject_short_4h[start:idx_4h+1]))
            trap_long_out.append(any(reject_long_4h[start:idx_4h+1]))
        else:
            vah_out.append(None); val_out.append(None); ema_out.append(None); close_out.append(None)
            trap_short_out.append(False); trap_long_out.append(False)
    return {'vah':vah_out,'val':val_out,'ema':ema_out,'close':close_out,
            'trap_short':trap_short_out,'trap_long':trap_long_out}


def compute_htf_4h_slope(ema_4h_series, window_bars=20):
    slopes = [None] * len(ema_4h_series)
    for i in range(window_bars, len(ema_4h_series)):
        curr = ema_4h_series[i]
        prev = ema_4h_series[i - window_bars]
        if curr is not None and prev is not None and prev > 0:
            slopes[i] = (curr - prev) / prev * 100
    return slopes


def compute_htf_4h_downtrend(close_series, ema_series, slope_series, regime_bars=3, slope_max=-0.3):
    n = len(close_series)
    downtrend = [False] * n
    for i in range(regime_bars, n):
        all_below = True
        for k in range(regime_bars):
            c = close_series[i - k]; e = ema_series[i - k]
            if c is None or e is None or c >= e:
                all_below = False; break
        if not all_below: continue
        s = slope_series[i] if slope_series and i < len(slope_series) else None
        if s is None or s > slope_max: continue
        downtrend[i] = True
    return downtrend


def compute_htf_4h_uptrend(close_series, ema_series, slope_series, regime_bars=3, slope_min=0.3):
    n = len(close_series)
    uptrend = [False] * n
    for i in range(regime_bars, n):
        all_above = True
        for k in range(regime_bars):
            c = close_series[i - k]; e = ema_series[i - k]
            if c is None or e is None or c <= e:
                all_above = False; break
        if not all_above: continue
        s = slope_series[i] if slope_series and i < len(slope_series) else None
        if s is None or s < slope_min: continue
        uptrend[i] = True
    return uptrend


def compute_htf_4h_crs(rows_1h, rows_4h, lookback_bars=10, slope_series_1h=None, regime_gate=False, regime_max_slope=0.3):
    n = len(rows_1h)
    if not rows_4h or len(rows_4h) < lookback_bars + 1:
        return [False]*n, [None]*n
    opens_4h = np.array([r[1] for r in rows_4h], dtype=float)
    highs_4h = np.array([r[2] for r in rows_4h], dtype=float)
    lows_4h = np.array([r[3] for r in rows_4h], dtype=float)
    closes_4h = np.array([r[4] for r in rows_4h], dtype=float)
    ts_4h = [r[0] for r in rows_4h]
    ONE_4H_MS = 4 * 60 * 60 * 1000
    crs_4h = [False] * len(rows_4h)
    range_4h = [None] * len(rows_4h)
    for i in range(lookback_bars, len(rows_4h)):
        recent_high = float(np.max(highs_4h[i-lookback_bars:i]))
        recent_low = float(np.min(lows_4h[i-lookback_bars:i+1]))
        if (highs_4h[i] > recent_high 
                and closes_4h[i] < recent_high 
                and closes_4h[i] < opens_4h[i]):
            crs_4h[i] = True
            range_4h[i] = highs_4h[i] - recent_low
    crs_1h = [False] * n
    range_1h = [None] * n
    idx_4h = 0
    for i, r in enumerate(rows_1h):
        t_1h = r[0]
        while idx_4h + 1 < len(ts_4h) and ts_4h[idx_4h + 1] + ONE_4H_MS <= t_1h:
            idx_4h += 1
        if ts_4h[idx_4h] + ONE_4H_MS == t_1h and crs_4h[idx_4h]:
            if regime_gate and slope_series_1h and i < len(slope_series_1h):
                slope = slope_series_1h[i]
                if slope is not None and slope > regime_max_slope:
                    continue
            crs_1h[i] = True
            range_1h[i] = range_4h[idx_4h]
    return crs_1h, range_1h


def classify_balance_position(entry_price, vah, val, boundary_pct=0.005):
    if vah is None or val is None or entry_price is None:
        return 'UNKNOWN'
    if entry_price > vah:
        return 'ABOVE'
    if entry_price < val:
        return 'BELOW'
    dist_to_vah = (vah - entry_price) / vah
    dist_to_val = (entry_price - val) / val
    if dist_to_vah < boundary_pct:
        return 'NEAR_VAH'
    if dist_to_val < boundary_pct:
        return 'NEAR_VAL'
    return 'INSIDE'


@router.get("/backtest")
def backtest_mode3(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(30, ge=1, le=1500),
    end_days_ago: int = Query(0, ge=0, le=1500),
    va_window: int = Query(50, ge=20, le=200),
    tp_pct: float = Query(0.012, ge=0.001, le=0.05),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    fee_pct: float = Query(0.001),
    slippage_pct: float = Query(0.0005),
    sideways_ema_dist_cap: float = Query(0.003, ge=0.0, le=0.05),
    chop_max_crossings: int = Query(4, ge=0, le=20),
    bull_min_volume_ratio: float = Query(1.5, ge=0.0, le=5.0),
    bull_mtf_15m_entry: bool = Query(True),
    bull_use_rr_tp: bool = Query(False),
    bull_rr_ratio: float = Query(1.0, ge=0.5, le=5.0),
    bear_mtf_15m_entry: bool = Query(True),
    bear_min_sl_dist: float = Query(0.0, ge=0.0, le=0.01),
    bear_use_1h_sl_fallback: bool = Query(False),
    sideways_ema_invalidation: bool = Query(True),
    sideways_ema_invalidation_tolerance: float = Query(0.0015, ge=0.0, le=0.02),
    sideways_mtf_15m_entry: bool = Query(True),
    sideways_tp_pct: float = Query(0.003, ge=0.0, le=0.05),
    sideways_max_slope_pct: float = Query(0.018, ge=0.0, le=0.1),
    sm_fix_1_htf_confirm: bool = Query(False),
    sm_fix_2_bear_streak: bool = Query(True),
    sm_fix_2_streak_threshold: int = Query(2, ge=2, le=5),
    sm_fix_3_extreme_low: bool = Query(True),
    sm_fix_3_high_lookback: int = Query(100, ge=20, le=500),
    sm_fix_3_extreme_pct: float = Query(0.05, ge=0.05, le=0.5),
    sm_fix_4_bull_confirm: bool = Query(False),
    sm_fix_4_bear_confirm: bool = Query(False),
    bull_countertrend_enabled: bool = Query(True),
    bull_countertrend_use_position: bool = Query(True),
    bull_countertrend_max_close_pct: float = Query(0.0, ge=-10.0, le=10.0),
    bull_countertrend_slope_window: int = Query(20, ge=5, le=100),
    bull_countertrend_slope_threshold: float = Query(-0.5, ge=-10.0, le=0.0),
    bull_countertrend_tp_pct: float = Query(0.012, ge=0.005, le=0.10),
    bull_countertrend_size_mult: float = Query(2.0, ge=0.5, le=5.0),
    bear_trend_rider_enabled: bool = Query(True),
    bear_trend_rider_regime_bars: int = Query(3, ge=1, le=10),
    bear_trend_rider_regime_slope_max: float = Query(-0.3, ge=-10.0, le=0.0),
    bear_trend_rider_tp_pct: float = Query(0.030, ge=0.005, le=0.20),
    bear_trend_rider_trailing_activate_pct: float = Query(0.015, ge=0.001, le=0.10),
    bear_trend_rider_trailing_distance_pct: float = Query(0.008, ge=0.001, le=0.05),
    bear_trend_rider_disable_ct_bull: bool = Query(False),
    bull_trend_rider_enabled: bool = Query(False),
    bull_trend_rider_regime_bars: int = Query(3, ge=1, le=10),
    bull_trend_rider_regime_slope_min: float = Query(0.3, ge=0.0, le=10.0),
    bull_trend_rider_tp_pct: float = Query(0.030, ge=0.005, le=0.20),
    bull_trend_rider_trailing_activate_pct: float = Query(0.015, ge=0.001, le=0.10),
    bull_trend_rider_trailing_distance_pct: float = Query(0.008, ge=0.001, le=0.05),
    crs_enabled: bool = Query(False),
    crs_lookback_4h_bars: int = Query(10, ge=3, le=50),
    crs_active_hours: int = Query(8, ge=1, le=48),
    crs_size_mult: float = Query(1.0, ge=0.5, le=5.0),
    crs_use_projection_tp: bool = Query(False),
    crs_projection_divisor: float = Query(2.6, ge=1.0, le=10.0),
    crs_skip_bull_hours: int = Query(0, ge=0, le=72),
    crs_regime_gate: bool = Query(False),
    crs_regime_max_slope: float = Query(0.3, ge=-2.0, le=5.0),
    # v4.0 Fix #17 AMT
    amt_enabled: bool = Query(False),
    amt_boundary_pct: float = Query(0.005, ge=0.001, le=0.05),
    amt_skip_sw_above: bool = Query(True),
    amt_skip_bull_below: bool = Query(True),
    amt_bull_near_vah_mult: float = Query(2.0, ge=0.5, le=5.0),
    amt_bull_above_mult: float = Query(1.5, ge=0.5, le=5.0),
    trap_enabled: bool = Query(False),
    trap_lookback_4h: int = Query(3, ge=1, le=10),
    trap_zone_tolerance: float = Query(0.002, ge=0.0, le=0.02),
    trap_tp_pct: float = Query(0.012, ge=0.001, le=0.05),
    trap_use_1h_va_tp: bool = Query(False),
    trap_priority_over_state: bool = Query(True),
    include_htf: bool = Query(True),
    htf_slope_window: int = Query(20, ge=5, le=100),
    balance_boundary_pct: float = Query(0.005, ge=0.001, le=0.05),
    log_result: bool = Query(True),
):
    config = Mode3Config(
        va_window=va_window, tp_pct=tp_pct,
        entry_usd=entry_usd, leverage=leverage,
        fee_pct_roundtrip=fee_pct, slippage_pct=slippage_pct,
        sideways_ema_distance_cap=sideways_ema_dist_cap,
        chop_max_crossings=chop_max_crossings,
        bull_min_volume_ratio=bull_min_volume_ratio,
        bull_mtf_15m_entry=bull_mtf_15m_entry,
        bull_use_rr_tp=bull_use_rr_tp, bull_rr_ratio=bull_rr_ratio,
        bear_mtf_15m_entry=bear_mtf_15m_entry,
        bear_min_sl_dist=bear_min_sl_dist,
        bear_use_1h_sl_fallback=bear_use_1h_sl_fallback,
        sideways_ema_invalidation=sideways_ema_invalidation,
        sideways_ema_invalidation_tolerance=sideways_ema_invalidation_tolerance,
        sideways_mtf_15m_entry=sideways_mtf_15m_entry,
        sideways_tp_pct=sideways_tp_pct,
        sideways_max_slope_pct=sideways_max_slope_pct,
        sm_fix_1_htf_confirm=sm_fix_1_htf_confirm,
        sm_fix_2_bear_streak=sm_fix_2_bear_streak,
        sm_fix_2_streak_threshold=sm_fix_2_streak_threshold,
        sm_fix_3_extreme_low=sm_fix_3_extreme_low,
        sm_fix_3_high_lookback=sm_fix_3_high_lookback,
        sm_fix_3_extreme_pct=sm_fix_3_extreme_pct,
        sm_fix_4_bull_confirm=sm_fix_4_bull_confirm,
        sm_fix_4_bear_confirm=sm_fix_4_bear_confirm,
        bull_countertrend_enabled=bull_countertrend_enabled,
        bull_countertrend_use_position=bull_countertrend_use_position,
        bull_countertrend_max_close_pct=bull_countertrend_max_close_pct,
        bull_countertrend_slope_window=bull_countertrend_slope_window,
        bull_countertrend_slope_threshold=bull_countertrend_slope_threshold,
        bull_countertrend_tp_pct=bull_countertrend_tp_pct,
        bull_countertrend_size_mult=bull_countertrend_size_mult,
        bear_trend_rider_enabled=bear_trend_rider_enabled,
        bear_trend_rider_regime_bars=bear_trend_rider_regime_bars,
        bear_trend_rider_regime_slope_max=bear_trend_rider_regime_slope_max,
        bear_trend_rider_tp_pct=bear_trend_rider_tp_pct,
        bear_trend_rider_trailing_activate_pct=bear_trend_rider_trailing_activate_pct,
        bear_trend_rider_trailing_distance_pct=bear_trend_rider_trailing_distance_pct,
        bear_trend_rider_disable_ct_bull=bear_trend_rider_disable_ct_bull,
        bull_trend_rider_enabled=bull_trend_rider_enabled,
        bull_trend_rider_regime_bars=bull_trend_rider_regime_bars,
        bull_trend_rider_regime_slope_min=bull_trend_rider_regime_slope_min,
        bull_trend_rider_tp_pct=bull_trend_rider_tp_pct,
        bull_trend_rider_trailing_activate_pct=bull_trend_rider_trailing_activate_pct,
        bull_trend_rider_trailing_distance_pct=bull_trend_rider_trailing_distance_pct,
        crs_enabled=crs_enabled,
        crs_lookback_4h_bars=crs_lookback_4h_bars,
        crs_active_hours=crs_active_hours,
        crs_size_mult=crs_size_mult,
        crs_use_projection_tp=crs_use_projection_tp,
        crs_projection_divisor=crs_projection_divisor,
        crs_skip_bull_hours=crs_skip_bull_hours,
        crs_regime_gate=crs_regime_gate,
        crs_regime_max_slope=crs_regime_max_slope,
        amt_enabled=amt_enabled,
        amt_boundary_pct=amt_boundary_pct,
        amt_skip_sw_above=amt_skip_sw_above,
        amt_skip_bull_below=amt_skip_bull_below,
        amt_bull_near_vah_mult=amt_bull_near_vah_mult,
        amt_bull_above_mult=amt_bull_above_mult,
        trap_enabled=trap_enabled,
        trap_lookback_4h=trap_lookback_4h,
        trap_zone_tolerance=trap_zone_tolerance,
        trap_tp_pct=trap_tp_pct,
        trap_use_1h_va_tp=trap_use_1h_va_tp,
        trap_priority_over_state=trap_priority_over_state,
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

    vahs, vals = [], []
    for i in range(len(rows)):
        vah, val, poc = compute_va_at_bar(highs, lows, closes, volumes, i,
            config.va_window, config.va_percentile_high, config.va_percentile_low)
        vahs.append(vah); vals.append(val)

    switcher = Switcher(config)

    if bull_mtf_15m_entry or bear_mtf_15m_entry or sideways_mtf_15m_entry:
        rows_15m = load_candles_from_db(symbol, '15m', start_ts, end_ts)
        if rows_15m:
            if bull_mtf_15m_entry:
                ec, el = compute_mtf_bull_entry(rows, rows_15m)
                switcher.mtf_bull_entry_close = ec
                switcher.mtf_bull_entry_low = el
            if bear_mtf_15m_entry:
                ec, eh = compute_mtf_bear_entry(rows, rows_15m)
                switcher.mtf_bear_entry_close = ec
                switcher.mtf_bear_entry_high = eh
            if sideways_mtf_15m_entry:
                sc, sh, lc, ll = compute_mtf_sideways_entry(rows, rows_15m, vahs, vals)
                switcher.mtf_sideways_short_entry_close = sc
                switcher.mtf_sideways_short_entry_high = sh
                switcher.mtf_sideways_long_entry_close = lc
                switcher.mtf_sideways_long_entry_low = ll

    htf_ema_series = None; htf_slope_series = None; htf_close_series = None
    htf_vah_series = None; htf_val_series = None
    if trap_enabled or sm_fix_1_htf_confirm or include_htf or bull_countertrend_enabled or bear_trend_rider_enabled or bull_trend_rider_enabled or crs_enabled or amt_enabled:
        extended_start = start_ts - (config.va_window * 4 * 3600 * 1000)
        rows_4h = load_candles_from_db(symbol, '4h', extended_start, end_ts)
        htf = compute_htf_4h_context(rows, rows_4h, va_window=config.va_window,
                                       trap_lookback=config.trap_lookback_4h)
        switcher.htf_4h_vah = htf['vah']
        switcher.htf_4h_val = htf['val']
        switcher.htf_4h_ema20 = htf['ema']
        switcher.htf_4h_close = htf['close']
        switcher.htf_trap_short_recent = htf['trap_short']
        switcher.htf_trap_long_recent = htf['trap_long']
        htf_ema_series = htf['ema']; htf_close_series = htf['close']
        htf_vah_series = htf['vah']; htf_val_series = htf['val']
        countertrend_slope = compute_htf_4h_slope(htf['ema'], window_bars=bull_countertrend_slope_window)
        switcher.htf_4h_slope = countertrend_slope
        htf_slope_series = compute_htf_4h_slope(htf['ema'], window_bars=htf_slope_window)
        if bear_trend_rider_enabled:
            regime_slope = compute_htf_4h_slope(htf['ema'], window_bars=htf_slope_window)
            switcher.htf_4h_downtrend = compute_htf_4h_downtrend(
                htf['close'], htf['ema'], regime_slope,
                regime_bars=bear_trend_rider_regime_bars,
                slope_max=bear_trend_rider_regime_slope_max)
        if bull_trend_rider_enabled:
            regime_slope = compute_htf_4h_slope(htf['ema'], window_bars=htf_slope_window)
            switcher.htf_4h_uptrend = compute_htf_4h_uptrend(
                htf['close'], htf['ema'], regime_slope,
                regime_bars=bull_trend_rider_regime_bars,
                slope_min=bull_trend_rider_regime_slope_min)
        if crs_enabled:
            crs_flags, crs_ranges = compute_htf_4h_crs(
                rows, rows_4h, lookback_bars=crs_lookback_4h_bars,
                slope_series_1h=htf_slope_series,
                regime_gate=crs_regime_gate,
                regime_max_slope=crs_regime_max_slope)
            switcher.htf_4h_crs_confirmed = crs_flags
            switcher.htf_4h_crs_range = crs_ranges

    for i in range(len(rows)):
        vah, val = vahs[i], vals[i]
        switcher.process_candle(bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i], v=volumes[i],
            ema20=ema20[i], vah=vah, val=val, poc=None)

    trades = switcher.trades
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    total_pnl_usd = sum(t.pnl_usd for t in trades)
    total_pnl_pct = sum(t.pnl_pct for t in trades) * 100
    wr = 100.0 * len(wins) / n if n > 0 else 0

    tool_stats = {}
    for tool in ['SIDEWAYS', 'BULL', 'BEAR', 'TRAP']:
        tt = [t for t in trades if t.tool == tool]
        if tt:
            tw = [t for t in tt if t.pnl_usd > 0]
            tool_stats[tool] = {
                "count": len(tt),
                "wr_pct": round(100.0 * len(tw) / len(tt), 2),
                "pnl_usd": round(sum(t.pnl_usd for t in tt), 2),
                "pnl_pct": round(sum(t.pnl_pct for t in tt) * 100, 3),
            }

    crs_trades = [t for t in trades if getattr(t, 'is_crs', False)]
    crs_stats = None
    if crs_trades:
        crs_wins = [t for t in crs_trades if t.pnl_usd > 0]
        crs_stats = {
            "count": len(crs_trades),
            "wr_pct": round(100.0 * len(crs_wins) / len(crs_trades), 2),
            "pnl_usd": round(sum(t.pnl_usd for t in crs_trades), 2),
        }

    def get_htf_at_bar(bar):
        if htf_ema_series is None or bar >= len(htf_ema_series):
            return None, None, None, None, None
        ema_v = htf_ema_series[bar]
        slope_v = htf_slope_series[bar] if htf_slope_series else None
        close_v = htf_close_series[bar] if htf_close_series else None
        vah_v = htf_vah_series[bar] if htf_vah_series else None
        val_v = htf_val_series[bar] if htf_val_series else None
        return (round(ema_v, 2) if ema_v else None,
                round(slope_v, 3) if slope_v is not None else None,
                round(close_v, 2) if close_v else None,
                round(vah_v, 2) if vah_v else None,
                round(val_v, 2) if val_v else None)

    trade_list = []
    balance_stats = {'INSIDE':0, 'NEAR_VAH':0, 'NEAR_VAL':0, 'ABOVE':0, 'BELOW':0, 'UNKNOWN':0}
    for t in trades:
        htf_ema, htf_slope, htf_close, htf_vah, htf_val = get_htf_at_bar(t.entry_bar)
        pos = classify_balance_position(t.entry_price, htf_vah, htf_val, balance_boundary_pct)
        balance_stats[pos] = balance_stats.get(pos, 0) + 1
        trade_dict = {
            "tool": t.tool, "side": t.side,
            "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
            "entry_bar": t.entry_bar, "exit_bar": t.exit_bar, "exit_type": t.exit_type,
            "pnl_pct": round(t.pnl_pct * 100, 3), "pnl_usd": round(t.pnl_usd, 2),
            "sl_level": round(t.sl_level, 2), "tp_level": round(t.tp_level, 2),
            "sl_distance_pct": round(abs(t.entry_price - t.sl_level) / t.entry_price * 100, 3),
            "ema_at_entry": round(t.ema_at_entry, 2), "ema_at_exit": round(t.ema_at_exit, 2),
            "peak_high": round(t.peak_high, 2), "trough_low": round(t.trough_low, 2),
            "size_mult": t.size_mult,
            "is_trend_rider": t.is_trend_rider,
            "is_bull_trend_rider": t.is_bull_trend_rider,
            "is_crs": getattr(t, 'is_crs', False),
            "balance_position": pos,
        }
        if htf_ema is not None:
            trade_dict["htf_4h_ema"] = htf_ema
            trade_dict["htf_4h_close"] = htf_close
            trade_dict["htf_4h_slope_pct"] = htf_slope
            trade_dict["htf_4h_vah"] = htf_vah
            trade_dict["htf_4h_val"] = htf_val
        trade_list.append(trade_dict)

    result = {
        "symbol": symbol, "timeframe": timeframe, "days": days, "end_days_ago": end_days_ago,
        "candles_processed": len(rows),
        "period_start_utc": datetime.utcfromtimestamp(start_ts/1000).strftime('%Y-%m-%d'),
        "period_end_utc": datetime.utcfromtimestamp(end_ts/1000).strftime('%Y-%m-%d'),
        "config": asdict(config),
        "summary": {
            "total_trades": n,
            "win_rate_pct": round(wr, 2),
            "wins": len(wins), "losses": len(losses),
            "total_pnl_usd": round(total_pnl_usd, 2),
            "total_pnl_pct": round(total_pnl_pct, 3),
            "capital_start": config.capital_usd,
            "capital_end": round(config.capital_usd + total_pnl_usd, 2),
            "sideways_blocked_count": switcher._sideways_blocked_count,
            "sideways_blocked_slope": switcher._sideways_blocked_slope,
            "sideways_blocked_amt": switcher._sideways_blocked_amt,
            "chop_blocked_count": switcher._chop_blocked_count,
            "bull_blocked_volume": switcher._bull_blocked_volume,
            "bull_blocked_mtf": switcher._bull_blocked_mtf,
            "bull_blocked_crs": switcher._bull_blocked_crs,
            "bull_blocked_amt": switcher._bull_blocked_amt,
            "amt_bull_amplified": switcher._amt_bull_amplified,
            "bear_blocked_mtf": switcher._bear_blocked_mtf,
            "bear_blocked_min_sl": switcher._bear_blocked_min_sl,
            "sideways_blocked_mtf": switcher._sideways_blocked_mtf,
            "trap_short_count": switcher._trap_short_count,
            "trap_long_count": switcher._trap_long_count,
            "sm_fix2_count": switcher._sm_fix2_count,
            "sm_fix3_count": switcher._sm_fix3_count,
            "bull_countertrend_count": switcher._bull_countertrend_count,
            "bear_trend_rider_count": switcher._bear_trend_rider_count,
            "bear_trend_rider_trailing_hits": switcher._bear_trend_rider_trailing_hits,
            "bear_trend_rider_hard_exits": switcher._bear_trend_rider_hard_exits,
            "bull_trend_rider_count": switcher._bull_trend_rider_count,
            "crs_confirmed_count": switcher._crs_confirmed_count,
            "crs_trade_count": switcher._crs_trade_count,
            "balance_position_stats": balance_stats,
        },
        "per_tool": tool_stats,
        "crs_stats": crs_stats,
        "trades": trade_list,
        "final_state": switcher.state,
    }

    if log_result:
        _log_experiment(config, result, symbol, timeframe, days)

    return result


@router.get("/health")
def mode3_health():
    return {"status": "ok", "module": "mode3", "version": "4.0", "db_path": DB_PATH}
