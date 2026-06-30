"""
tick_discovery.py — Tick-by-Tick Discovery Engine
Phase 1: Event Extraction (walk 1m sub-candles, record level hits)
Phase 2: Statistical Analysis (aggregate patterns per pair × TF × hour)
Phase 3: Sweep Engine (auto-sweep buffer × TP × SL, find profitable combos)

BabaBot v17 — Clean slate, data-driven strategy discovery
"""

import os
import json
import sqlite3
import logging
import threading
import time
import requests
import math
from collections import defaultdict
from datetime import datetime, timezone

log = logging.getLogger("tick_discovery")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

DB_PATH = os.environ.get("DB_PATH", "market_data.db")
WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")

# ════════════════════════════════════════════════════════════
# PHASE 1 — EVENT EXTRACTION
# ════════════════════════════════════════════════════════════

def extract_tick_events(
    symbol: str,
    timeframe: str,
    window: int = 10,
    buffer_pct: float = 0.8,
    buffer2_pct: float = 1.0,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    days: int = 1825,
    sub_candle_tf: str = "1m",
    db_path: str = None,
    save_to_d1: bool = True,
    _preloaded_rows: list = None,
    _preloaded_sub_candles: dict = None,
) -> dict:
    """
    Phase 1: For each parent candle, walk 1m sub-candles and record
    when price crosses each of 10 key levels.
    
    Returns dict with events list and summary stats.
    """
    db_path = db_path or DB_PATH
    
    # Load data (reuse preloaded if available)
    if _preloaded_rows is not None:
        rows = _preloaded_rows
        sub_candle_lookup = _preloaded_sub_candles or {}
    else:
        rows, sub_candle_lookup = _load_data(db_path, symbol, timeframe, sub_candle_tf)
    
    if len(rows) < window + 10:
        return {"status": "insufficient_data", "rows": len(rows)}
    
    # Limit to last N days
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        rows = [r for r in rows if r[5] >= last_time - ms_limit]
    
    n = len(rows)
    if n < window + 10:
        return {"status": "insufficient_data", "candles": n}
    
    # Extract OHLC arrays
    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]
    
    # Calculate ratios
    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]
    
    # TF → milliseconds for sub-candle grouping
    tf_ms_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms_map.get(timeframe, 3600000)
    sub_ms = tf_ms_map.get(sub_candle_tf, 60000)
    
    events_list = []
    
    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        
        # ── Calculate predicted range ──
        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        
        pred_high  = highs[i] * avg_h
        pred_low   = lows[i] * avg_l
        pred_close = closes[i] * avg_c
        
        # ── Calculate all 10 levels ──
        entry_long   = pred_low * (1 - buffer_pct / 100)
        entry_short  = pred_high * (1 + buffer_pct / 100)
        tp_long      = entry_long * (1 + tp_pct / 100)
        tp_short     = entry_short * (1 - tp_pct / 100)
        sl_long      = entry_long * (1 - sl_pct / 100)
        sl_short     = entry_short * (1 + sl_pct / 100)
        entry_long_L2  = entry_long * (1 - buffer2_pct / 100)
        entry_short_L2 = entry_short * (1 + buffer2_pct / 100)
        
        # ── Next candle = the candle we analyze ──
        next_idx = i + 1
        candle_time = times[next_idx]
        
        # Get sub-candles for this parent candle
        parent_ts = (candle_time // parent_ms) * parent_ms
        sub_candles = sub_candle_lookup.get(parent_ts, [])
        
        if not sub_candles:
            continue  # No 1m data for this candle, skip
        
        # ── Walk sub-candles: record when each level is hit ──
        levels = {
            "pred_high":     {"price": pred_high,     "dir": "above", "min": None},
            "pred_low":      {"price": pred_low,      "dir": "below", "min": None},
            "entry_long":    {"price": entry_long,    "dir": "below", "min": None},
            "entry_short":   {"price": entry_short,   "dir": "above", "min": None},
            "tp_long":       {"price": tp_long,       "dir": "above", "min": None},
            "tp_short":      {"price": tp_short,      "dir": "below", "min": None},
            "sl_long":       {"price": sl_long,       "dir": "below", "min": None},
            "sl_short":      {"price": sl_short,      "dir": "above", "min": None},
            "entry_long_L2": {"price": entry_long_L2, "dir": "below", "min": None},
            "entry_short_L2":{"price": entry_short_L2,"dir": "above", "min": None},
        }
        
        for sc_idx, sc in enumerate(sub_candles):
            sc_high = sc["h"]
            sc_low = sc["l"]
            minute = sc_idx  # minute index within parent candle
            
            for level_name, level_info in levels.items():
                if level_info["min"] is not None:
                    continue  # Already hit, skip
                
                hit = False
                if level_info["dir"] == "above" and sc_high >= level_info["price"]:
                    hit = True
                elif level_info["dir"] == "below" and sc_low <= level_info["price"]:
                    hit = True
                
                if hit:
                    level_info["min"] = minute
        
        # ── Build sequence string (chronological order) ──
        hit_events = []
        for level_name, level_info in levels.items():
            if level_info["min"] is not None:
                hit_events.append((level_info["min"], level_name))
        
        hit_events.sort(key=lambda x: x[0])
        sequence = "→".join(e[1] for e in hit_events) if hit_events else "NONE"
        
        # ── Determine first extreme ──
        min_pred_high = levels["pred_high"]["min"]
        min_pred_low  = levels["pred_low"]["min"]
        
        if min_pred_high is not None and min_pred_low is not None:
            if min_pred_high < min_pred_low:
                first_extreme = "HIGH"
                first_extreme_min = min_pred_high
            elif min_pred_low < min_pred_high:
                first_extreme = "LOW"
                first_extreme_min = min_pred_low
            else:
                first_extreme = "SAME"
                first_extreme_min = min_pred_high
        elif min_pred_high is not None:
            first_extreme = "HIGH"
            first_extreme_min = min_pred_high
        elif min_pred_low is not None:
            first_extreme = "LOW"
            first_extreme_min = min_pred_low
        else:
            first_extreme = "NONE"
            first_extreme_min = None
        
        # ── Context: previous candle ──
        prev_close = closes[i]
        prev_open = opens[i]
        prev_high = highs[i]
        prev_low = lows[i]
        prev_direction = "bullish" if prev_close > prev_open else ("bearish" if prev_close < prev_open else "doji")
        prev_range_pct = round((prev_high - prev_low) / prev_open * 100, 4) if prev_open > 0 else 0
        
        # ── Hour and day of week ──
        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        candle_hour_utc = dt.hour
        candle_dow = dt.weekday()  # 0=Mon, 6=Sun
        
        # ── Build event record ──
        event = {
            "symbol": symbol,
            "timeframe": timeframe,
            "candle_time": candle_time,
            "candle_hour_utc": candle_hour_utc,
            "candle_dow": candle_dow,
            "pred_high": round(pred_high, 6),
            "pred_low": round(pred_low, 6),
            "pred_close": round(pred_close, 6),
            "first_extreme": first_extreme,
            "first_extreme_min": first_extreme_min,
            "min_pred_high": levels["pred_high"]["min"],
            "min_pred_low": levels["pred_low"]["min"],
            "min_entry_long": levels["entry_long"]["min"],
            "min_entry_short": levels["entry_short"]["min"],
            "min_tp_long": levels["tp_long"]["min"],
            "min_tp_short": levels["tp_short"]["min"],
            "min_sl_long": levels["sl_long"]["min"],
            "min_sl_short": levels["sl_short"]["min"],
            "min_entry_long_L2": levels["entry_long_L2"]["min"],
            "min_entry_short_L2": levels["entry_short_L2"]["min"],
            "sequence": sequence,
            "prev_direction": prev_direction,
            "prev_range_pct": prev_range_pct,
            "window": window,
            "buffer_pct": buffer_pct,
            "buffer2_pct": buffer2_pct,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
        }
        events_list.append(event)
    
    # ── Save to D1 via Workers ──
    saved_count = 0
    if save_to_d1 and events_list:
        saved_count = _save_events_to_d1(events_list)
    
    # ── Summary ──
    total = len(events_list)
    high_first = sum(1 for e in events_list if e["first_extreme"] == "HIGH")
    low_first = sum(1 for e in events_list if e["first_extreme"] == "LOW")
    none_extreme = sum(1 for e in events_list if e["first_extreme"] == "NONE")
    
    return {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "config": {"window": window, "buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct},
        "total_candles": total,
        "high_first": high_first,
        "high_first_pct": round(high_first / total * 100, 1) if total > 0 else 0,
        "low_first": low_first,
        "low_first_pct": round(low_first / total * 100, 1) if total > 0 else 0,
        "none_extreme": none_extreme,
        "saved_to_d1": saved_count,
        "sub_candle_tf": sub_candle_tf,
    }


# ════════════════════════════════════════════════════════════
# PHASE 2 — STATISTICAL ANALYSIS
# ════════════════════════════════════════════════════════════

def analyze_tick_stats(
    symbol: str,
    timeframe: str,
    window: int = 10,
    buffer_pct: float = 0.8,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    group_by: str = "hour_utc",
    db_path: str = None,
    days: int = 1825,
    sub_candle_tf: str = "1m",
    _preloaded_rows: list = None,
    _preloaded_sub_candles: dict = None,
) -> dict:
    """
    Phase 2: Run event extraction (or use cached), then aggregate
    statistics per group (hour_utc, day_of_week, prev_direction).
    
    Returns pattern distributions, level hit rates, conditional probabilities.
    """
    # Extract events first
    result = extract_tick_events(
        symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        days=days, sub_candle_tf=sub_candle_tf, db_path=db_path,
        save_to_d1=False,  # Don't double-save
        _preloaded_rows=_preloaded_rows,
        _preloaded_sub_candles=_preloaded_sub_candles,
    )
    
    if result.get("status") != "ok":
        return result
    
    # Re-extract events (extract_tick_events doesn't return full list for memory)
    # We need the full events — re-run with save_to_d1=False
    events = _extract_events_raw(
        symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        days=days, sub_candle_tf=sub_candle_tf, db_path=db_path,
        _preloaded_rows=_preloaded_rows,
        _preloaded_sub_candles=_preloaded_sub_candles,
    )
    
    if not events:
        return {"status": "no_events", "symbol": symbol, "timeframe": timeframe}
    
    # ── Group events ──
    groups = defaultdict(list)
    for e in events:
        if group_by == "hour_utc":
            key = e["candle_hour_utc"]
        elif group_by == "day_of_week":
            key = e["candle_dow"]
        elif group_by == "prev_direction":
            key = e["prev_direction"]
        else:
            key = "all"
        groups[key].append(e)
    
    # ── Compute stats per group ──
    stats = {}
    for key, group_events in sorted(groups.items()):
        stats[str(key)] = _compute_group_stats(group_events)
    
    # ── Overall stats ──
    overall = _compute_group_stats(events)
    
    return {
        "status": "ok",
        "symbol": symbol,
        "timeframe": timeframe,
        "config": {"window": window, "buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct},
        "group_by": group_by,
        "total_candles": len(events),
        "overall": overall,
        "groups": stats,
    }


def _compute_group_stats(events: list) -> dict:
    """Compute statistics for a group of events."""
    total = len(events)
    if total == 0:
        return {"total": 0}
    
    # ── First extreme distribution ──
    high_first = sum(1 for e in events if e["first_extreme"] == "HIGH")
    low_first = sum(1 for e in events if e["first_extreme"] == "LOW")
    none_extreme = sum(1 for e in events if e["first_extreme"] == "NONE")
    same_extreme = sum(1 for e in events if e["first_extreme"] == "SAME")
    
    # ── Level hit rates ──
    level_names = [
        "pred_high", "pred_low", "entry_long", "entry_short",
        "tp_long", "tp_short", "sl_long", "sl_short",
        "entry_long_L2", "entry_short_L2"
    ]
    hit_rates = {}
    avg_minutes = {}
    for ln in level_names:
        key = f"min_{ln}"
        hits = [e for e in events if e.get(key) is not None]
        hit_rates[f"{ln}_hit_pct"] = round(len(hits) / total * 100, 1)
        if hits:
            avg_minutes[f"{ln}_avg_min"] = round(sum(e[key] for e in hits) / len(hits), 1)
    
    # ── Conditional probabilities ──
    conditional = {}
    
    # If HIGH first → what happens?
    high_first_events = [e for e in events if e["first_extreme"] == "HIGH"]
    if high_first_events:
        hf_total = len(high_first_events)
        conditional["if_high_first"] = {
            "tp_short_hit_pct": round(sum(1 for e in high_first_events if e.get("min_tp_short") is not None) / hf_total * 100, 1),
            "sl_short_hit_pct": round(sum(1 for e in high_first_events if e.get("min_sl_short") is not None) / hf_total * 100, 1),
            "entry_long_hit_pct": round(sum(1 for e in high_first_events if e.get("min_entry_long") is not None) / hf_total * 100, 1),
            "entry_short_hit_pct": round(sum(1 for e in high_first_events if e.get("min_entry_short") is not None) / hf_total * 100, 1),
        }
    
    # If LOW first → what happens?
    low_first_events = [e for e in events if e["first_extreme"] == "LOW"]
    if low_first_events:
        lf_total = len(low_first_events)
        conditional["if_low_first"] = {
            "tp_long_hit_pct": round(sum(1 for e in low_first_events if e.get("min_tp_long") is not None) / lf_total * 100, 1),
            "sl_long_hit_pct": round(sum(1 for e in low_first_events if e.get("min_sl_long") is not None) / lf_total * 100, 1),
            "entry_long_hit_pct": round(sum(1 for e in low_first_events if e.get("min_entry_long") is not None) / lf_total * 100, 1),
            "entry_short_hit_pct": round(sum(1 for e in low_first_events if e.get("min_entry_short") is not None) / lf_total * 100, 1),
        }
    
    # If entry_long hit → TP or SL? (sequence order matters)
    entry_long_events = [e for e in events if e.get("min_entry_long") is not None]
    if entry_long_events:
        el_total = len(entry_long_events)
        tp_after_entry = sum(1 for e in entry_long_events 
                           if e.get("min_tp_long") is not None 
                           and e["min_tp_long"] > e["min_entry_long"])
        sl_after_entry = sum(1 for e in entry_long_events 
                           if e.get("min_sl_long") is not None 
                           and e["min_sl_long"] > e["min_entry_long"])
        conditional["if_entry_long_hit"] = {
            "tp_after_entry_pct": round(tp_after_entry / el_total * 100, 1),
            "sl_after_entry_pct": round(sl_after_entry / el_total * 100, 1),
            "neither_pct": round((el_total - tp_after_entry - sl_after_entry) / el_total * 100, 1),
        }
    
    # If entry_short hit → TP or SL?
    entry_short_events = [e for e in events if e.get("min_entry_short") is not None]
    if entry_short_events:
        es_total = len(entry_short_events)
        tp_after_entry = sum(1 for e in entry_short_events 
                           if e.get("min_tp_short") is not None 
                           and e["min_tp_short"] > e["min_entry_short"])
        sl_after_entry = sum(1 for e in entry_short_events 
                           if e.get("min_sl_short") is not None 
                           and e["min_sl_short"] > e["min_entry_short"])
        conditional["if_entry_short_hit"] = {
            "tp_after_entry_pct": round(tp_after_entry / es_total * 100, 1),
            "sl_after_entry_pct": round(sl_after_entry / es_total * 100, 1),
            "neither_pct": round((es_total - tp_after_entry - sl_after_entry) / es_total * 100, 1),
        }
    
    # ── Top sequences ──
    seq_counts = defaultdict(int)
    for e in events:
        seq_counts[e["sequence"]] += 1
    top_sequences = sorted(seq_counts.items(), key=lambda x: -x[1])[:10]
    
    # ── DCA analysis: L2 hit rate and timing ──
    l1_hits = [e for e in events if e.get("min_entry_long") is not None]
    l2_hits = [e for e in l1_hits if e.get("min_entry_long_L2") is not None]
    dca_stats = {}
    if l1_hits:
        dca_stats["l2_hit_rate_pct"] = round(len(l2_hits) / len(l1_hits) * 100, 1)
        if l2_hits:
            gaps = [e["min_entry_long_L2"] - e["min_entry_long"] for e in l2_hits]
            dca_stats["avg_l1_l2_gap_min"] = round(sum(gaps) / len(gaps), 1)
            dca_stats["fast_l2_pct"] = round(sum(1 for g in gaps if g <= 5) / len(gaps) * 100, 1)
    
    # ── Close filter analysis ──
    close_filter = {}
    if events:
        # Close position = (pred_close - pred_low) / (pred_high - pred_low)
        close_positions = []
        for e in events:
            rng = e["pred_high"] - e["pred_low"]
            if rng > 0:
                cp = (e["pred_close"] - e["pred_low"]) / rng
                close_positions.append(cp)
        if close_positions:
            close_filter["avg_close_position"] = round(sum(close_positions) / len(close_positions), 3)
            close_filter["close_below_30_pct"] = round(sum(1 for cp in close_positions if cp < 0.3) / len(close_positions) * 100, 1)
            close_filter["close_above_70_pct"] = round(sum(1 for cp in close_positions if cp > 0.7) / len(close_positions) * 100, 1)
    
    # ── Best direction suggestion ──
    high_first_pct = round(high_first / total * 100, 1)
    low_first_pct = round(low_first / total * 100, 1)
    edge = abs(high_first_pct - low_first_pct)
    
    if edge < 5:
        best_direction = "SKIP"
    elif high_first_pct > low_first_pct:
        best_direction = "SHORT"
    else:
        best_direction = "LONG"
    
    return {
        "total": total,
        "high_first_pct": high_first_pct,
        "low_first_pct": low_first_pct,
        "none_pct": round(none_extreme / total * 100, 1),
        "same_pct": round(same_extreme / total * 100, 1),
        "edge_pct": edge,
        "best_direction": best_direction,
        "hit_rates": hit_rates,
        "avg_minutes": avg_minutes,
        "conditional": conditional,
        "top_sequences": [{"seq": s, "count": c, "pct": round(c / total * 100, 1)} for s, c in top_sequences],
        "dca": dca_stats,
        "close_filter": close_filter,
    }


# ════════════════════════════════════════════════════════════
# DISCOVERY SWEEP — Run extraction across multiple pairs × TFs
# ════════════════════════════════════════════════════════════

_discovery_status = {
    "running": False,
    "progress": "",
    "current_pair": "",
    "current_tf": "",
    "completed": 0,
    "total": 0,
    "results": [],
    "started_at": None,
    "finished_at": None,
}
_discovery_thread = None
_discovery_log = []

def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _discovery_log.append(entry)
    if len(_discovery_log) > 500:
        _discovery_log.pop(0)
    log.info(msg)

PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT",
    "BNBUSDT", "1000PEPEUSDT", "SUIUSDT", "ARBUSDT", "NEARUSDT",
]
TIMEFRAMES = ["15m", "1h", "4h"]


def start_tick_discovery(
    pairs: list = None,
    timeframes: list = None,
    window: int = 10,
    buffer_pct: float = 0.8,
    buffer2_pct: float = 1.0,
    tp_pct: float = 1.0,
    sl_pct: float = 0.5,
    days: int = 1825,
):
    """Start tick discovery sweep in background thread."""
    global _discovery_thread
    
    if _discovery_status["running"]:
        return {"ok": False, "error": "Discovery already running"}
    
    pairs = pairs or PAIRS
    timeframes = timeframes or TIMEFRAMES
    
    def _run():
        _discovery_status["running"] = True
        _discovery_status["started_at"] = datetime.now().isoformat()
        _discovery_status["results"] = []
        _discovery_status["completed"] = 0
        _discovery_status["total"] = len(pairs) * len(timeframes)
        
        _log(f"🔬 Tick Discovery started: {len(pairs)} pairs × {len(timeframes)} TFs = {_discovery_status['total']} combos")
        
        for pair in pairs:
            # Preload data once per pair (all TFs share 1m data)
            _log(f"📦 Preloading {pair}...")
            _discovery_status["current_pair"] = pair
            
            for tf in timeframes:
                _discovery_status["current_tf"] = tf
                _discovery_status["progress"] = f"{pair} {tf}"
                
                try:
                    _log(f"  🔬 Extracting {pair} {tf}...")
                    
                    # Load data
                    rows, sub_lookup = _load_data(DB_PATH, pair, tf, "1m")
                    
                    if len(rows) < window + 10:
                        _log(f"  ⚠️ {pair} {tf}: insufficient data ({len(rows)} rows)")
                        _discovery_status["completed"] += 1
                        continue
                    
                    # Extract events
                    result = extract_tick_events(
                        symbol=pair, timeframe=tf, window=window,
                        buffer_pct=buffer_pct, buffer2_pct=buffer2_pct,
                        tp_pct=tp_pct, sl_pct=sl_pct, days=days,
                        save_to_d1=True,
                        _preloaded_rows=rows, _preloaded_sub_candles=sub_lookup,
                    )
                    
                    # Run stats analysis
                    stats = analyze_tick_stats(
                        symbol=pair, timeframe=tf, window=window,
                        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
                        days=days, group_by="hour_utc",
                        _preloaded_rows=rows, _preloaded_sub_candles=sub_lookup,
                    )
                    
                    total_candles = result.get("total_candles", 0)
                    high_pct = result.get("high_first_pct", 0)
                    low_pct = result.get("low_first_pct", 0)
                    saved = result.get("saved_to_d1", 0)
                    
                    _log(f"  ✅ {pair} {tf}: {total_candles} candles, HIGH_FIRST {high_pct}%, LOW_FIRST {low_pct}%, saved {saved}")
                    
                    # Save stats summary
                    _save_stats_to_d1(pair, tf, stats)
                    
                    _discovery_status["results"].append({
                        "symbol": pair,
                        "timeframe": tf,
                        "total_candles": total_candles,
                        "high_first_pct": high_pct,
                        "low_first_pct": low_pct,
                        "saved_to_d1": saved,
                    })
                    
                except Exception as ex:
                    _log(f"  ❌ {pair} {tf}: {str(ex)}")
                
                _discovery_status["completed"] += 1
        
        _discovery_status["running"] = False
        _discovery_status["finished_at"] = datetime.now().isoformat()
        _discovery_status["progress"] = "DONE"
        _log(f"🏁 Tick Discovery complete! {_discovery_status['completed']}/{_discovery_status['total']} processed")
    
    _discovery_thread = threading.Thread(target=_run, daemon=True)
    _discovery_thread.start()
    
    return {"ok": True, "message": f"Discovery started: {len(pairs)} pairs × {len(timeframes)} TFs"}


def stop_tick_discovery():
    """Stop tick discovery (sets flag, thread will exit after current pair)."""
    _discovery_status["running"] = False
    return {"ok": True, "message": "Stop signal sent"}


def get_discovery_status():
    """Get current discovery status."""
    return dict(_discovery_status)


def get_discovery_log(limit: int = 200):
    """Get discovery log."""
    return _discovery_log[-limit:]


# ════════════════════════════════════════════════════════════
# PHASE 3 — SWEEP ENGINE
# Auto-sweep buffer × TP × SL, backtest with 1m resolution,
# find profitable combos, save winners to D1 tick_strategies
# ════════════════════════════════════════════════════════════

# Sweep grids
DERET_GRID = {
    "buffer": [0.5, 0.8, 1.0, 1.5, 2.0],
    "tp":     [1.0, 1.5, 2.0, 2.5, 3.0],
    "sl":     [0.5, 1.0, 1.5, 2.0],
}
OPEN_GRID = {
    "tp": [0.3, 0.5, 0.7, 1.0, 1.5],
    "sl": [0.3, 0.5, 0.7, 1.0, 1.5],
}

# Quality thresholds
MIN_TRADES = 30
MIN_WR = 55.0
MIN_PPD = 0.50
# Stability gate
MIN_WEEKLY_WR = 40.0
MAX_WORST_STREAK = 6
MIN_CONSISTENCY = 60.0
MIN_WALK_FORWARD = 0.85

# Trade settings
POSITION_USD = 100
LEVERAGE = 50
FEE_PCT = 0.07  # 0.02% maker + 0.05% taker = 0.07% roundtrip
MAX_HOLD = 4    # max candles to hold before force close

_sweep_status = {
    "running": False,
    "paused": False,
    "progress": "",
    "current_pair": "",
    "current_tf": "",
    "current_mode": "",
    "completed_combos": 0,
    "total_combos": 0,
    "winners": 0,
    "results_summary": [],
    "started_at": None,
    "finished_at": None,
}
_sweep_thread = None


def start_sweep_engine(
    pairs: list = None,
    timeframes: list = None,
    window: int = 10,
    days: int = 1825,
    modes: str = "both",  # "deret", "open", "both"
    position_usd: float = 100,
    leverage: int = 50,
):
    """Start sweep engine in background thread."""
    global _sweep_thread

    if _sweep_status["running"]:
        return {"ok": False, "error": "Sweep already running"}
    if _discovery_status.get("running"):
        return {"ok": False, "error": "Discovery running, wait for it to finish"}

    pairs = pairs or PAIRS
    timeframes = timeframes or TIMEFRAMES
    do_deret = modes in ("deret", "both")
    do_open = modes in ("open", "both")

    deret_combos = len(DERET_GRID["buffer"]) * len(DERET_GRID["tp"]) * len(DERET_GRID["sl"])
    open_combos = len(OPEN_GRID["tp"]) * len(OPEN_GRID["sl"])
    combos_per_pair_tf = (deret_combos if do_deret else 0) + (open_combos if do_open else 0)
    total = len(pairs) * len(timeframes) * combos_per_pair_tf

    def _run():
        _sweep_status["running"] = True
        _sweep_status["started_at"] = datetime.now().isoformat()
        _sweep_status["finished_at"] = None
        _sweep_status["completed_combos"] = 0
        _sweep_status["total_combos"] = total
        _sweep_status["winners"] = 0
        _sweep_status["results_summary"] = []

        _log(f"🚀 Sweep Engine started: {len(pairs)} pairs × {len(timeframes)} TFs × {combos_per_pair_tf} combos = {total} total")

        for pair in pairs:
            if not _sweep_status["running"]:
                break
            _sweep_status["current_pair"] = pair

            for tf in timeframes:
                if not _sweep_status["running"]:
                    break
                # Pause check: wait until resumed
                while _sweep_status.get("paused") and _sweep_status["running"]:
                    import time as _time
                    _time.sleep(5)
                if not _sweep_status["running"]:
                    break
                _sweep_status["current_tf"] = tf
                _log(f"📦 Loading {pair} {tf}...")

                rows, sub_lookup = _load_data(DB_PATH, pair, tf, "1m")
                if len(rows) < window + 50:
                    _log(f"  ⚠️ {pair} {tf}: insufficient data ({len(rows)} rows), skipping")
                    _sweep_status["completed_combos"] += combos_per_pair_tf
                    continue

                # Limit by days
                if days and days > 0:
                    ms_limit = days * 86400 * 1000
                    last_time = rows[-1][5]
                    rows = [r for r in rows if r[5] >= last_time - ms_limit]

                # ── Sweep A: Deret Entry ──
                if do_deret:
                    _sweep_status["current_mode"] = "deret"
                    for buf in DERET_GRID["buffer"]:
                        for tp in DERET_GRID["tp"]:
                            for sl in DERET_GRID["sl"]:
                                if not _sweep_status["running"]:
                                    break
                                _sweep_status["progress"] = f"{pair} {tf} deret buf={buf} tp={tp} sl={sl}"

                                try:
                                    result = _backtest_deret_1m(
                                        rows, sub_lookup, pair, tf,
                                        window=window, buffer_pct=buf, tp_pct=tp, sl_pct=sl,
                                        position_usd=position_usd, leverage=leverage,
                                    )
                                    _process_sweep_result(result, pair, tf, "deret", window, buf, tp, sl)
                                except Exception as ex:
                                    _log(f"  ❌ deret {pair} {tf} buf={buf} tp={tp} sl={sl}: {str(ex)[:100]}")

                                _sweep_status["completed_combos"] += 1

                # ── Sweep B: Open Entry ──
                if do_open:
                    _sweep_status["current_mode"] = "open"
                    for tp in OPEN_GRID["tp"]:
                        for sl in OPEN_GRID["sl"]:
                            if not _sweep_status["running"]:
                                break
                            _sweep_status["progress"] = f"{pair} {tf} open tp={tp} sl={sl}"

                            try:
                                result = _backtest_open_1m(
                                    rows, sub_lookup, pair, tf,
                                    window=window, tp_pct=tp, sl_pct=sl,
                                    position_usd=position_usd, leverage=leverage,
                                )
                                _process_sweep_result(result, pair, tf, "open", window, 0, tp, sl)
                            except Exception as ex:
                                _log(f"  ❌ open {pair} {tf} tp={tp} sl={sl}: {str(ex)[:100]}")

                            _sweep_status["completed_combos"] += 1

                _log(f"  ✅ {pair} {tf} done — winners so far: {_sweep_status['winners']}")

                # ── Secondary Sweep: DCA + Close Filter on winners ──
                base_winners = [r for r in _sweep_status["results_summary"]
                               if r["symbol"] == pair and r["timeframe"] == tf and r["mode"] == "deret"]
                if base_winners and _sweep_status["running"]:
                    _log(f"  🔬 Secondary sweep: testing DCA + close filter on {len(base_winners)} winners...")
                    for bw in base_winners:
                        if not _sweep_status["running"]:
                            break
                        buf = bw["buffer_pct"]
                        tp = bw["tp_pct"]
                        sl = bw["sl_pct"]

                        # Test +DCA (buffer2 variants)
                        for b2 in [0.5, 1.0, 1.5]:
                            if not _sweep_status["running"]:
                                break
                            _sweep_status["progress"] = f"{pair} {tf} DCA buf2={b2} (base buf={buf})"
                            try:
                                result = _backtest_deret_1m(
                                    rows, sub_lookup, pair, tf,
                                    window=window, buffer_pct=buf, tp_pct=tp, sl_pct=sl,
                                    position_usd=position_usd, leverage=leverage,
                                    buffer2_pct=b2,
                                )
                                if result and result.get("win_rate", 0) > bw["win_rate"]:
                                    result["mode"] = "deret_dca"
                                    _process_sweep_result(result, pair, tf, "deret_dca", window, buf, tp, sl)
                                    _log(f"    📈 DCA buf2={b2} improved: WR {bw['win_rate']}→{result['win_rate']}%")
                            except Exception as ex:
                                _log(f"    ❌ DCA buf2={b2}: {str(ex)[:80]}")

                        # Test +close filter (threshold variants)
                        for cf in [0.1, 0.2, 0.3, 0.4]:
                            if not _sweep_status["running"]:
                                break
                            _sweep_status["progress"] = f"{pair} {tf} filter={cf} (base buf={buf})"
                            try:
                                result = _backtest_deret_1m(
                                    rows, sub_lookup, pair, tf,
                                    window=window, buffer_pct=buf, tp_pct=tp, sl_pct=sl,
                                    position_usd=position_usd, leverage=leverage,
                                    close_filter_pct=cf,
                                )
                                if result and result.get("win_rate", 0) > bw["win_rate"]:
                                    result["mode"] = "deret_filter"
                                    _process_sweep_result(result, pair, tf, "deret_filter", window, buf, tp, sl)
                                    _log(f"    📈 Filter={cf} improved: WR {bw['win_rate']}→{result['win_rate']}%")
                            except Exception as ex:
                                _log(f"    ❌ Filter={cf}: {str(ex)[:80]}")

                    _log(f"  ✅ Secondary sweep done — total winners: {_sweep_status['winners']}")

                # ── Clustering: auto-run after sweep per pair×tf ──
                if _sweep_status["running"]:
                    _log(f"  📊 Running clustering {pair} {tf}...")
                    try:
                        cl_result = cluster_levels(
                            rows, sub_lookup, pair, tf,
                            window=window, days=days, save_to_d1=True,
                        )
                        if cl_result.get("status") == "ok":
                            top = (cl_result.get("suggestions") or [None])[0]
                            if top:
                                _log(f"  📊 Top: {top['entry_name']} {top['entry_side']} "
                                     f"TP={top['tp']}% SL={top['sl']}% WR={top['est_wr']}% "
                                     f"consistency={top['consistency']}%")
                            else:
                                _log(f"  📊 Clustering done — no combos above threshold")
                    except Exception as ex:
                        _log(f"  ❌ Clustering error: {str(ex)[:100]}")

                # ── Combo Sweep: test ALL entry×TP×SL×DCA×hold combos ──
                if _sweep_status["running"]:
                    _log(f"  🔬 Running combo sweep {pair} {tf}...")
                    try:
                        combo_result = combo_sweep(
                            rows, sub_lookup, pair, tf,
                            window=window, days=days, save_to_d1=True,
                        )
                        if combo_result.get("status") == "ok":
                            n_profitable = combo_result.get("profitable_combos", 0)
                            top = combo_result.get("top_50", [None])[0] if combo_result.get("top_50") else None
                            if top:
                                _log(f"  🔬 Combo done — {n_profitable} profitable. Best: {top['entry']} {top['side']} "
                                     f"TP={top['tp_name']} SL={top['sl_pct']}% WR={top['wr']}% EV={top['ev_per_trade']}% "
                                     f"${top['avg_daily_capped']}/day")
                            else:
                                _log(f"  🔬 Combo done — {n_profitable} profitable combos")
                    except Exception as ex:
                        _log(f"  ❌ Combo sweep error: {str(ex)[:100]}")

        _sweep_status["running"] = False
        _sweep_status["finished_at"] = datetime.now().isoformat()
        _sweep_status["progress"] = "DONE"
        _log(f"🏁 Sweep complete! {_sweep_status['winners']} winners from {_sweep_status['completed_combos']} combos")

    _sweep_thread = threading.Thread(target=_run, daemon=True)
    _sweep_thread.start()

    return {"ok": True, "message": f"Sweep started: {total} combos", "total": total}


def stop_sweep_engine():
    _sweep_status["running"] = False
    _sweep_status["paused"] = False
    return {"ok": True, "message": "Stop signal sent"}


def pause_sweep_engine():
    if _sweep_status["running"]:
        _sweep_status["paused"] = True
        _log("⏸ Sweep PAUSED")
        return {"ok": True, "message": "Sweep paused"}
    return {"ok": False, "message": "Sweep not running"}


def resume_sweep_engine():
    _sweep_status["paused"] = False
    _log("▶ Sweep RESUMED")
    return {"ok": True, "message": "Sweep resumed"}


def get_sweep_status():
    return dict(_sweep_status)


# ────────────────────────────────────────
# DERET ENTRY BACKTEST (1m resolution)
# ────────────────────────────────────────

def _backtest_deret_1m(
    rows, sub_lookup, symbol, timeframe,
    window=10, buffer_pct=0.8, tp_pct=1.0, sl_pct=0.5,
    position_usd=100, leverage=50,
    buffer2_pct=0,          # DCA L2: 0 = disabled
    close_filter_pct=0,     # Close filter: 0 = disabled
    return_trades=False,     # Return raw trades list for profiling
):
    """
    Full backtest for Deret Entry mode using 1m sub-candle resolution.
    DIRECTION-AWARE: first pass computes first_extreme per hour,
    second pass only trades in dominant direction. Skip hours with <5% edge.
    Sequential constraint: 1 position at a time, max_hold=4 candles.
    Optional DCA (buffer2_pct > 0): L2 deeper entry, avg entry price.
    Optional close filter (close_filter_pct > 0): skip if pred_close too near entry.
    """
    n = len(rows)
    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    tf_ms_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms_map.get(timeframe, 3600000)

    notional = position_usd * leverage
    fee_per_trade = notional * FEE_PCT / 100

    # ══ FIRST PASS: compute first_extreme per hour to determine direction ══
    hour_stats = defaultdict(lambda: {"high": 0, "low": 0, "total": 0})
    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        candle_time = times[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_lookup.get(parent_ts, [])
        if not subs:
            continue

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l

        min_ph, min_pl = None, None
        for sc_idx, sc in enumerate(subs):
            if min_ph is None and sc["h"] >= pred_high:
                min_ph = sc_idx
            if min_pl is None and sc["l"] <= pred_low:
                min_pl = sc_idx
            if min_ph is not None and min_pl is not None:
                break

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        h = dt.hour
        hour_stats[h]["total"] += 1
        if min_ph is not None and min_pl is not None:
            if min_ph < min_pl:
                hour_stats[h]["high"] += 1
            else:
                hour_stats[h]["low"] += 1
        elif min_ph is not None:
            hour_stats[h]["high"] += 1
        elif min_pl is not None:
            hour_stats[h]["low"] += 1

    # Direction per hour: need ≥5% edge, ≥20 samples
    hour_direction = {}
    for h, s in hour_stats.items():
        if s["total"] < 20:
            hour_direction[h] = "SKIP"
            continue
        high_pct = s["high"] / s["total"] * 100
        low_pct = s["low"] / s["total"] * 100
        edge = abs(high_pct - low_pct)
        if edge < 5:
            hour_direction[h] = "SKIP"
        elif high_pct > low_pct:
            hour_direction[h] = "SHORT"  # high first → price goes up first → SHORT at top
        else:
            hour_direction[h] = "LONG"   # low first → price goes down first → LONG at bottom

    # ══ SECOND PASS: backtest with direction filter ══
    trades = []
    position_busy_until = 0

    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        if i + 1 < position_busy_until:
            continue

        candle_time = times[i + 1]
        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        hour_utc = dt.hour

        # ── DIRECTION FILTER: skip hours without edge ──
        direction = hour_direction.get(hour_utc, "SKIP")
        if direction == "SKIP":
            continue

        # Predicted range
        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window

        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l

        # ── Close filter: skip trade if pred_close too near entry zone ──
        if close_filter_pct > 0:
            avg_c = sum(close_ratios[i-window:i]) / window
            pred_close = closes[i] * avg_c
            pred_range = pred_high - pred_low
            if pred_range > 0:
                close_position = (pred_close - pred_low) / pred_range
                if direction == "LONG" and close_position < close_filter_pct:
                    continue  # pred_close too near pred_low = bearish, skip LONG
                if direction == "SHORT" and (1 - close_position) < close_filter_pct:
                    continue  # pred_close too near pred_high = bullish, skip SHORT

        entry_long  = pred_low * (1 - buffer_pct / 100)
        entry_short = pred_high * (1 + buffer_pct / 100)

        # DCA L2 levels
        entry_long_L2 = entry_long * (1 - buffer2_pct / 100) if buffer2_pct > 0 else None
        entry_short_L2 = entry_short * (1 + buffer2_pct / 100) if buffer2_pct > 0 else None

        tp_long     = entry_long * (1 + tp_pct / 100)
        tp_short    = entry_short * (1 - tp_pct / 100)
        sl_long     = entry_long * (1 - sl_pct / 100)
        sl_short    = entry_short * (1 + sl_pct / 100)

        # Walk across max_hold candles using 1m resolution
        trade_result = None
        for k in range(MAX_HOLD):
            ci = i + 1 + k
            if ci >= n:
                break

            parent_ts = (times[ci] // parent_ms) * parent_ms
            subs = sub_lookup.get(parent_ts, [])
            if not subs:
                continue

            for sc_idx, sc in enumerate(subs):
                if trade_result is not None:
                    break

                # ── Only try the direction that has edge ──
                if direction == "LONG" and sc["l"] <= entry_long:
                    actual_entry = entry_long
                    actual_fee = fee_per_trade
                    actual_tp = tp_long
                    actual_sl = sl_long
                    start_idx = sc_idx

                    # DCA: check if L2 also fills in remaining subs of this candle
                    if entry_long_L2 is not None:
                        for dca_idx in range(sc_idx + 1, len(subs)):
                            if subs[dca_idx]["l"] <= entry_long_L2:
                                actual_entry = (entry_long + entry_long_L2) / 2
                                actual_fee = fee_per_trade * 2  # double position
                                actual_tp = actual_entry * (1 + tp_pct / 100)
                                actual_sl = actual_entry * (1 - sl_pct / 100)
                                start_idx = dca_idx
                                break

                    trade_result = _walk_after_entry(
                        subs, start_idx,
                        sub_lookup, times, parent_ms, ci, n,
                        side="LONG", entry=actual_entry,
                        tp_price=actual_tp, sl_price=actual_sl,
                        max_hold=MAX_HOLD, hold_start=k,
                    )
                    if trade_result:
                        trade_result["side"] = "LONG"
                        trade_result["hour_utc"] = hour_utc
                        trade_result["candle_time"] = candle_time
                        trade_result["dca"] = actual_fee > fee_per_trade
                        trade_result["_fee"] = actual_fee
                        trade_result["_entry"] = actual_entry
                        trade_result["entry_fill_minute"] = sc_idx
                    break

                if direction == "SHORT" and sc["h"] >= entry_short:
                    actual_entry = entry_short
                    actual_fee = fee_per_trade
                    actual_tp = tp_short
                    actual_sl = sl_short
                    start_idx = sc_idx

                    # DCA: check if L2 also fills
                    if entry_short_L2 is not None:
                        for dca_idx in range(sc_idx + 1, len(subs)):
                            if subs[dca_idx]["h"] >= entry_short_L2:
                                actual_entry = (entry_short + entry_short_L2) / 2
                                actual_fee = fee_per_trade * 2
                                actual_tp = actual_entry * (1 - tp_pct / 100)
                                actual_sl = actual_entry * (1 + sl_pct / 100)
                                start_idx = dca_idx
                                break

                    trade_result = _walk_after_entry(
                        subs, start_idx,
                        sub_lookup, times, parent_ms, ci, n,
                        side="SHORT", entry=actual_entry,
                        tp_price=actual_tp, sl_price=actual_sl,
                        max_hold=MAX_HOLD, hold_start=k,
                    )
                    if trade_result:
                        trade_result["side"] = "SHORT"
                        trade_result["hour_utc"] = hour_utc
                        trade_result["candle_time"] = candle_time
                        trade_result["dca"] = actual_fee > fee_per_trade
                        trade_result["_fee"] = actual_fee
                        trade_result["_entry"] = actual_entry
                        trade_result["entry_fill_minute"] = sc_idx
                    break

            if trade_result:
                break

        if trade_result is None:
            continue

        # Calculate PnL (use actual entry/fee from DCA if applicable)
        actual_entry = trade_result.get("_entry", entry_long if trade_result["side"] == "LONG" else entry_short)
        actual_fee = trade_result.get("_fee", fee_per_trade)

        if trade_result["side"] == "LONG":
            pnl_pct = (trade_result["exit_price"] - actual_entry) / actual_entry * 100
        else:
            pnl_pct = (actual_entry - trade_result["exit_price"]) / actual_entry * 100

        pnl_dollar = notional * pnl_pct / 100 - actual_fee
        trade_result["pnl_pct"] = round(pnl_pct, 4)
        trade_result["pnl_dollar"] = round(pnl_dollar, 2)
        trade_result["win"] = pnl_dollar > 0

        # ── Trade context for profiling ──
        prev_direction = "bullish" if closes[i] > opens[i] else ("bearish" if closes[i] < opens[i] else "doji")
        prev_range_pct = round((highs[i] - lows[i]) / opens[i] * 100, 4) if opens[i] > 0 else 0
        pred_range_pct = round((pred_high - pred_low) / closes[i] * 100, 4) if closes[i] > 0 else 0
        trade_result["prev_direction"] = prev_direction
        trade_result["prev_range_pct"] = prev_range_pct
        trade_result["pred_range_pct"] = pred_range_pct
        trade_result["day_of_week"] = dt.weekday()

        trades.append(trade_result)

        # Sequential constraint
        hold_candles = trade_result.get("hold_candles", 1)
        position_busy_until = i + 1 + hold_candles + 1

    if return_trades:
        return trades

    result = _compile_backtest_result(trades, symbol, timeframe, "deret", window, buffer_pct, tp_pct, sl_pct)
    result["hour_direction"] = {str(h): d for h, d in hour_direction.items()}
    return result


def _walk_after_entry(
    current_subs, entry_sc_idx,
    sub_lookup, times, parent_ms, current_ci, n,
    side, entry, tp_price, sl_price,
    max_hold, hold_start,
):
    """After entry fills, walk remaining 1m candles to find TP or SL.
    Returns exit info including exit_minute (minutes after entry)."""
    minutes_after_entry = 0

    # Walk remaining subs in current candle
    for sc in current_subs[entry_sc_idx + 1:]:
        minutes_after_entry += 1
        if side == "LONG":
            if sc["h"] >= tp_price:
                return {"exit_price": tp_price, "exit_reason": "TP", "hold_candles": hold_start + 1, "exit_minute": minutes_after_entry}
            if sc["l"] <= sl_price:
                return {"exit_price": sl_price, "exit_reason": "SL", "hold_candles": hold_start + 1, "exit_minute": minutes_after_entry}
        else:  # SHORT
            if sc["l"] <= tp_price:
                return {"exit_price": tp_price, "exit_reason": "TP", "hold_candles": hold_start + 1, "exit_minute": minutes_after_entry}
            if sc["h"] >= sl_price:
                return {"exit_price": sl_price, "exit_reason": "SL", "hold_candles": hold_start + 1, "exit_minute": minutes_after_entry}

    # Walk subsequent candles
    for k in range(hold_start + 1, max_hold):
        ci = current_ci - hold_start + k
        if ci >= n:
            break
        parent_ts = (times[ci] // parent_ms) * parent_ms
        subs = sub_lookup.get(parent_ts, [])
        for sc in subs:
            minutes_after_entry += 1
            if side == "LONG":
                if sc["h"] >= tp_price:
                    return {"exit_price": tp_price, "exit_reason": "TP", "hold_candles": k + 1, "exit_minute": minutes_after_entry}
                if sc["l"] <= sl_price:
                    return {"exit_price": sl_price, "exit_reason": "SL", "hold_candles": k + 1, "exit_minute": minutes_after_entry}
            else:
                if sc["l"] <= tp_price:
                    return {"exit_price": tp_price, "exit_reason": "TP", "hold_candles": k + 1, "exit_minute": minutes_after_entry}
                if sc["h"] >= sl_price:
                    return {"exit_price": sl_price, "exit_reason": "SL", "hold_candles": k + 1, "exit_minute": minutes_after_entry}

    # Force close at last candle close
    last_ci = min(current_ci - hold_start + max_hold - 1, n - 1)
    return {"exit_price": entry, "exit_reason": "CLOSE", "hold_candles": max_hold, "exit_minute": minutes_after_entry}


# ────────────────────────────────────────
# OPEN ENTRY BACKTEST (1m resolution)
# ────────────────────────────────────────

def _backtest_open_1m(
    rows, sub_lookup, symbol, timeframe,
    window=10, tp_pct=0.5, sl_pct=0.5,
    position_usd=100, leverage=50,
):
    """
    Backtest Open Entry mode: entry at candle open, direction from first_extreme stats.
    Walk 1m to determine TP or SL hit order.
    """
    n = len(rows)
    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    tf_ms_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms_map.get(timeframe, 3600000)

    notional = position_usd * leverage
    fee_per_trade = notional * FEE_PCT / 100

    # First pass: compute first_extreme per hour to determine direction
    hour_stats = defaultdict(lambda: {"high": 0, "low": 0, "total": 0})
    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        candle_time = times[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_lookup.get(parent_ts, [])
        if not subs:
            continue

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l

        min_ph, min_pl = None, None
        for sc_idx, sc in enumerate(subs):
            if min_ph is None and sc["h"] >= pred_high:
                min_ph = sc_idx
            if min_pl is None and sc["l"] <= pred_low:
                min_pl = sc_idx
            if min_ph is not None and min_pl is not None:
                break

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        h = dt.hour
        hour_stats[h]["total"] += 1
        if min_ph is not None and min_pl is not None:
            if min_ph < min_pl:
                hour_stats[h]["high"] += 1
            else:
                hour_stats[h]["low"] += 1
        elif min_ph is not None:
            hour_stats[h]["high"] += 1
        elif min_pl is not None:
            hour_stats[h]["low"] += 1

    # Determine direction per hour (need ≥5% edge)
    hour_direction = {}
    for h, s in hour_stats.items():
        if s["total"] < 20:
            hour_direction[h] = "SKIP"
            continue
        high_pct = s["high"] / s["total"] * 100
        low_pct = s["low"] / s["total"] * 100
        edge = abs(high_pct - low_pct)
        if edge < 5:
            hour_direction[h] = "SKIP"
        elif high_pct > low_pct:
            hour_direction[h] = "SHORT"  # high first = short opportunity
        else:
            hour_direction[h] = "LONG"   # low first = long opportunity

    # Second pass: backtest with direction
    trades = []
    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        candle_time = times[i + 1]
        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        hour_utc = dt.hour

        direction = hour_direction.get(hour_utc, "SKIP")
        if direction == "SKIP":
            continue

        candle_open = opens[i + 1]
        parent_ts = (candle_time // parent_ms) * parent_ms
        subs = sub_lookup.get(parent_ts, [])
        if not subs:
            continue

        if direction == "LONG":
            tp_price = candle_open * (1 + tp_pct / 100)
            sl_price = candle_open * (1 - sl_pct / 100)
        else:  # SHORT
            tp_price = candle_open * (1 - tp_pct / 100)
            sl_price = candle_open * (1 + sl_pct / 100)

        # Walk 1m — which hits first?
        exit_price = None
        exit_reason = None
        for sc in subs:
            if direction == "LONG":
                if sc["h"] >= tp_price:
                    exit_price = tp_price; exit_reason = "TP"; break
                if sc["l"] <= sl_price:
                    exit_price = sl_price; exit_reason = "SL"; break
            else:
                if sc["l"] <= tp_price:
                    exit_price = tp_price; exit_reason = "TP"; break
                if sc["h"] >= sl_price:
                    exit_price = sl_price; exit_reason = "SL"; break

        if exit_reason is None:
            exit_price = closes[i + 1]
            exit_reason = "CLOSE"

        if direction == "LONG":
            pnl_pct = (exit_price - candle_open) / candle_open * 100
        else:
            pnl_pct = (candle_open - exit_price) / candle_open * 100

        pnl_dollar = notional * pnl_pct / 100 - fee_per_trade

        trades.append({
            "side": direction,
            "hour_utc": hour_utc,
            "candle_time": candle_time,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl_pct": round(pnl_pct, 4),
            "pnl_dollar": round(pnl_dollar, 2),
            "win": pnl_dollar > 0,
            "hold_candles": 1,
        })

    return _compile_backtest_result(trades, symbol, timeframe, "open", window, 0, tp_pct, sl_pct)


# ────────────────────────────────────────
# BACKTEST RESULT COMPILATION + STABILITY
# ────────────────────────────────────────

def _compile_backtest_result(trades, symbol, timeframe, mode, window, buffer_pct, tp_pct, sl_pct):
    """Compile trades into result dict with stability metrics."""
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "symbol": symbol, "timeframe": timeframe, "mode": mode,
            "window": window, "buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct,
            "total_trades": 0, "win_rate": 0, "profit_per_day": 0,
            "pass_quality": False,
        }

    wins = sum(1 for t in trades if t["win"])
    wr = wins / total_trades * 100
    total_pnl = sum(t["pnl_dollar"] for t in trades)

    # Period in days
    if len(trades) >= 2:
        first_ts = trades[0]["candle_time"]
        last_ts = trades[-1]["candle_time"]
        period_days = max((last_ts - first_ts) / 86400000, 1)
    else:
        period_days = 1
    ppd = total_pnl / period_days

    # Max drawdown
    equity = 0
    peak = 0
    max_dd = 0
    for t in trades:
        equity += t["pnl_dollar"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    avg_pnl = total_pnl / total_trades

    # ── Stability metrics ──
    # Weekly WR
    week_buckets = defaultdict(lambda: {"w": 0, "l": 0})
    for t in trades:
        week_key = int(t["candle_time"] // (7 * 86400000))
        if t["win"]:
            week_buckets[week_key]["w"] += 1
        else:
            week_buckets[week_key]["l"] += 1

    weekly_wrs = []
    for wk in week_buckets.values():
        tot = wk["w"] + wk["l"]
        if tot >= 2:  # need at least 2 trades per week to count
            weekly_wrs.append(wk["w"] / tot * 100)

    min_weekly_wr = min(weekly_wrs) if weekly_wrs else 0
    consistency_pct = (sum(1 for w in weekly_wrs if w >= 50) / len(weekly_wrs) * 100) if weekly_wrs else 0

    # Worst loss streak
    worst_streak = 0
    current_streak = 0
    for t in trades:
        if not t["win"]:
            current_streak += 1
            worst_streak = max(worst_streak, current_streak)
        else:
            current_streak = 0

    # Walk-forward: train on first 80%, test on last 20%
    split = int(total_trades * 0.8)
    if split > 10 and total_trades - split > 5:
        train_wins = sum(1 for t in trades[:split] if t["win"])
        test_wins = sum(1 for t in trades[split:] if t["win"])
        train_wr = train_wins / split * 100
        test_wr = test_wins / (total_trades - split) * 100
        wf_ratio = test_wr / train_wr if train_wr > 0 else 0
    else:
        train_wr = wr
        test_wr = wr
        wf_ratio = 1.0

    # Per-hour breakdown with timing and direction
    hour_detail = defaultdict(lambda: {"wins": 0, "total": 0, "pnl": 0, "tp_minutes": [], "sl_minutes": [], "sides": []})
    for t in trades:
        h = t["hour_utc"]
        hour_detail[h]["total"] += 1
        hour_detail[h]["pnl"] += t["pnl_dollar"]
        hour_detail[h]["sides"].append(t["side"])
        if t["win"]:
            hour_detail[h]["wins"] += 1
        if t.get("exit_minute") is not None:
            if t.get("exit_reason") == "TP":
                hour_detail[h]["tp_minutes"].append(t["exit_minute"])
            elif t.get("exit_reason") == "SL":
                hour_detail[h]["sl_minutes"].append(t["exit_minute"])

    per_hour = {}
    for h, s in sorted(hour_detail.items()):
        # Determine direction for this hour (most common side)
        if s["sides"]:
            long_count = sum(1 for x in s["sides"] if x == "LONG")
            short_count = sum(1 for x in s["sides"] if x == "SHORT")
            direction = "LONG" if long_count >= short_count else "SHORT"
        else:
            direction = "?"

        tp_mins = sorted(s["tp_minutes"])
        sl_mins = sorted(s["sl_minutes"])

        entry = {
            "trades": s["total"],
            "wr": round(s["wins"] / s["total"] * 100, 1) if s["total"] > 0 else 0,
            "pnl": round(s["pnl"], 2),
            "direction": direction,
        }
        if tp_mins:
            entry["avg_tp_min"] = round(sum(tp_mins) / len(tp_mins), 1)
            entry["median_tp_min"] = tp_mins[len(tp_mins) // 2]
        if sl_mins:
            entry["avg_sl_min"] = round(sum(sl_mins) / len(sl_mins), 1)
            entry["median_sl_min"] = sl_mins[len(sl_mins) // 2]

        per_hour[str(h)] = entry

    # Overall timing
    all_tp_mins = [t["exit_minute"] for t in trades if t.get("exit_reason") == "TP" and t.get("exit_minute") is not None]
    all_sl_mins = [t["exit_minute"] for t in trades if t.get("exit_reason") == "SL" and t.get("exit_minute") is not None]
    timing = {}
    if all_tp_mins:
        stp = sorted(all_tp_mins)
        timing["avg_tp_min"] = round(sum(stp) / len(stp), 1)
        timing["median_tp_min"] = stp[len(stp) // 2]
    if all_sl_mins:
        ssl = sorted(all_sl_mins)
        timing["avg_sl_min"] = round(sum(ssl) / len(ssl), 1)
        timing["median_sl_min"] = ssl[len(ssl) // 2]

    # Quality gate
    pass_quality = (
        total_trades >= MIN_TRADES
        and wr >= MIN_WR
        and ppd >= MIN_PPD
    )

    # Stability gate + failing_metrics diagnosis
    failing_metrics = []
    if min_weekly_wr < MIN_WEEKLY_WR:
        failing_metrics.append("min_weekly_wr")
    if worst_streak > MAX_WORST_STREAK:
        failing_metrics.append("worst_streak")
    if consistency_pct < MIN_CONSISTENCY:
        failing_metrics.append("consistency_pct")
    if wf_ratio < MIN_WALK_FORWARD:
        failing_metrics.append("walk_forward_ratio")

    pass_stability = len(failing_metrics) == 0

    stability_detail = {
        "min_weekly_wr": round(min_weekly_wr, 1),
        "min_weekly_wr_threshold": MIN_WEEKLY_WR,
        "worst_streak": worst_streak,
        "worst_streak_threshold": MAX_WORST_STREAK,
        "consistency_pct": round(consistency_pct, 1),
        "consistency_threshold": MIN_CONSISTENCY,
        "walk_forward_ratio": round(wf_ratio, 2),
        "walk_forward_threshold": MIN_WALK_FORWARD,
        "failing_metrics": failing_metrics,
        "weeks_counted": len(weekly_wrs),
        "p5_weekly_wr": round(sorted(weekly_wrs)[max(0, int(len(weekly_wrs) * 0.05))], 1) if weekly_wrs else 0,
    }

    # Confidence score (4 factors, no ATR)
    confidence = 0
    # 1. Pattern dominance proxy: WR distance from 50% (35%)
    confidence += min((wr - 50) / 25 * 35, 35) if wr > 50 else 0
    # 2. Backtest WR (25%)
    confidence += min(wr / 80 * 25, 25)
    # 3. Walk-forward (25%)
    confidence += min(wf_ratio / 1.0 * 25, 25) if wf_ratio > 0 else 0
    # 4. Recent consistency (15%)
    confidence += min(consistency_pct / 80 * 15, 15)
    confidence = round(min(confidence, 100), 1)

    return {
        "symbol": symbol, "timeframe": timeframe, "mode": mode,
        "window": window, "buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct,
        "total_trades": total_trades, "wins": wins,
        "win_rate": round(wr, 1),
        "total_pnl": round(total_pnl, 2),
        "profit_per_day": round(ppd, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_pnl_per_trade": round(avg_pnl, 2),
        "min_weekly_wr": round(min_weekly_wr, 1),
        "worst_streak": worst_streak,
        "consistency_pct": round(consistency_pct, 1),
        "train_wr": round(train_wr, 1),
        "test_wr": round(test_wr, 1),
        "walk_forward_ratio": round(wf_ratio, 2),
        "confidence_score": confidence,
        "pass_quality": pass_quality,
        "pass_stability": pass_stability,
        "stability_detail": stability_detail,
        "timing": timing,
        "per_hour": per_hour,
    }


def _process_sweep_result(result, symbol, timeframe, mode, window, buffer_pct, tp_pct, sl_pct):
    """Check if result passes gates, save to D1 if winner."""
    if not result or result["total_trades"] == 0:
        return

    wr = result["win_rate"]
    ppd = result["profit_per_day"]
    passes = result.get("pass_quality", False)

    if passes:
        _log(f"  🏆 WINNER: {mode} {symbol} {timeframe} buf={buffer_pct} tp={tp_pct} sl={sl_pct} → WR={wr}% PPD=${ppd} conf={result['confidence_score']}")
        _sweep_status["winners"] += 1

        summary_entry = {
            "symbol": symbol, "timeframe": timeframe, "mode": mode,
            "buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct,
            "win_rate": wr, "ppd": ppd, "trades": result["total_trades"],
            "confidence": result["confidence_score"],
            "pass_stability": result.get("pass_stability", False),
            "stability_detail": result.get("stability_detail", {}),
            "timing": result.get("timing", {}),
            "per_hour": result.get("per_hour", {}),
            "max_drawdown": result.get("max_drawdown", 0),
            "train_wr": result.get("train_wr", 0),
            "test_wr": result.get("test_wr", 0),
        }
        _sweep_status["results_summary"].append(summary_entry)

        # Save to D1
        _save_strategy_to_d1(result)


def _save_strategy_to_d1(result):
    """Save winning strategy to D1 tick_strategies table."""
    try:
        # Determine dominant direction from per_hour data
        per_hour = result.get("per_hour", {})
        hour_direction = result.get("hour_direction", {})
        
        # Find best hours and their directions
        best_hours = []
        for h, stats in per_hour.items():
            if stats.get("trades", 0) >= 5 and stats.get("wr", 0) >= 55:
                best_hours.append(h)
        
        direction = "BOTH"
        if hour_direction:
            dirs = [d for d in hour_direction.values() if d != "SKIP"]
            if dirs:
                long_count = sum(1 for d in dirs if d == "LONG")
                short_count = sum(1 for d in dirs if d == "SHORT")
                if long_count > short_count * 2:
                    direction = "LONG"
                elif short_count > long_count * 2:
                    direction = "SHORT"

        payload = {
            "symbol": result["symbol"],
            "timeframe": result["timeframe"],
            "mode": result["mode"],
            "direction": direction,
            "entry_level": "pred_low" if result["mode"] == "deret" else "open",
            "exit_tp_level": "tp_long",
            "exit_sl_level": "sl_long",
            "window": result["window"],
            "buffer_pct": result["buffer_pct"],
            "tp_pct": result["tp_pct"],
            "sl_pct": result["sl_pct"],
            "win_rate": result["win_rate"],
            "total_trades": result["total_trades"],
            "profit_per_day": result["profit_per_day"],
            "max_drawdown": result["max_drawdown"],
            "avg_pnl_per_trade": result["avg_pnl_per_trade"],
            "min_weekly_wr": result["min_weekly_wr"],
            "worst_streak": result["worst_streak"],
            "consistency_pct": result["consistency_pct"],
            "train_wr": result["train_wr"],
            "test_wr": result["test_wr"],
            "walk_forward_ratio": result["walk_forward_ratio"],
            "confidence_score": result["confidence_score"],
            "status": "candidate",
            "per_hour": json.dumps(result.get("per_hour", {})),
            "hour_direction": json.dumps(result.get("hour_direction", {})),
        }
        resp = requests.post(
            f"{WORKER_URL}/tick/save-strategy",
            json=payload,
            timeout=15,
        )
        if not resp.ok:
            _log(f"  ⚠️ D1 save strategy failed: {resp.status_code}")
    except Exception as ex:
        _log(f"  ⚠️ D1 save strategy error: {str(ex)[:100]}")


# ════════════════════════════════════════════════════════════
# TRADE PROFILING — Win vs Loss analysis
# ════════════════════════════════════════════════════════════

def profile_winning_combo(
    symbol, timeframe, window=10,
    buffer_pct=2.0, tp_pct=1.0, sl_pct=2.0,
    buffer2_pct=1.5, close_filter_pct=0,
    days=1825, position_usd=100, leverage=50,
):
    """
    Run a specific combo backtest, then profile winning vs losing trades.
    Returns detailed analysis of what differentiates wins from losses.
    """
    rows, sub_lookup = _load_data(DB_PATH, symbol, timeframe, "1m")
    if len(rows) < window + 50:
        return {"error": "insufficient data"}

    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        rows = [r for r in rows if r[5] >= last_time - ms_limit]

    trades = _backtest_deret_1m(
        rows, sub_lookup, symbol, timeframe,
        window=window, buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct,
        position_usd=position_usd, leverage=leverage,
        buffer2_pct=buffer2_pct, close_filter_pct=close_filter_pct,
        return_trades=True,
    )

    if not trades:
        return {"error": "no trades"}

    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]
    total = len(trades)

    def _dist(trade_list, key):
        vals = [t[key] for t in trade_list if t.get(key) is not None]
        if not vals:
            return {}
        s = sorted(vals)
        n = len(s)
        return {
            "count": n,
            "avg": round(sum(s) / n, 2),
            "median": s[n // 2],
            "p25": s[int(n * 0.25)],
            "p75": s[int(n * 0.75)],
            "min": s[0],
            "max": s[-1],
        }

    def _cat_dist(trade_list, key):
        counts = defaultdict(int)
        for t in trade_list:
            v = t.get(key, "unknown")
            counts[str(v)] += 1
        total_c = sum(counts.values())
        return {k: {"count": v, "pct": round(v / total_c * 100, 1)} for k, v in sorted(counts.items())} if total_c > 0 else {}

    # ── Per-factor profiling ──
    profile = {
        "symbol": symbol, "timeframe": timeframe,
        "config": {"buffer_pct": buffer_pct, "tp_pct": tp_pct, "sl_pct": sl_pct,
                   "buffer2_pct": buffer2_pct, "close_filter_pct": close_filter_pct},
        "total_trades": total,
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1),

        "by_hour_utc": {},
        "by_prev_direction": {},
        "by_day_of_week": {},
        "by_entry_fill_speed": {},
        "by_pred_range": {},
        "by_prev_range": {},
        "by_exit_reason": {},
    }

    # Hour UTC breakdown
    for h in sorted(set(t["hour_utc"] for t in trades)):
        h_trades = [t for t in trades if t["hour_utc"] == h]
        h_wins = [t for t in h_trades if t["win"]]
        h_losses = [t for t in h_trades if not t["win"]]
        profile["by_hour_utc"][str(h)] = {
            "trades": len(h_trades),
            "wins": len(h_wins), "losses": len(h_losses),
            "wr": round(len(h_wins) / len(h_trades) * 100, 1),
            "pnl": round(sum(t["pnl_dollar"] for t in h_trades), 2),
            "win_entry_fill": _dist(h_wins, "entry_fill_minute"),
            "loss_entry_fill": _dist(h_losses, "entry_fill_minute"),
            "win_exit_min": _dist(h_wins, "exit_minute"),
            "loss_exit_min": _dist(h_losses, "exit_minute"),
        }

    # Previous candle direction
    for pd in ["bullish", "bearish", "doji"]:
        pd_trades = [t for t in trades if t.get("prev_direction") == pd]
        if pd_trades:
            pd_wins = [t for t in pd_trades if t["win"]]
            profile["by_prev_direction"][pd] = {
                "trades": len(pd_trades),
                "wr": round(len(pd_wins) / len(pd_trades) * 100, 1),
                "pnl": round(sum(t["pnl_dollar"] for t in pd_trades), 2),
            }

    # Day of week
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d in range(7):
        d_trades = [t for t in trades if t.get("day_of_week") == d]
        if d_trades:
            d_wins = [t for t in d_trades if t["win"]]
            profile["by_day_of_week"][dow_names[d]] = {
                "trades": len(d_trades),
                "wr": round(len(d_wins) / len(d_trades) * 100, 1),
                "pnl": round(sum(t["pnl_dollar"] for t in d_trades), 2),
            }

    # Entry fill speed: fast (<15min) vs medium (15-60) vs slow (60+)
    for label, lo, hi in [("fast_0_15", 0, 15), ("medium_15_60", 15, 60), ("slow_60_plus", 60, 9999)]:
        f_trades = [t for t in trades if lo <= (t.get("entry_fill_minute") or 0) < hi]
        if f_trades:
            f_wins = [t for t in f_trades if t["win"]]
            profile["by_entry_fill_speed"][label] = {
                "trades": len(f_trades),
                "wr": round(len(f_wins) / len(f_trades) * 100, 1),
                "pnl": round(sum(t["pnl_dollar"] for t in f_trades), 2),
            }

    # Predicted range (narrow vs normal vs wide)
    pred_ranges = [t.get("pred_range_pct", 0) for t in trades if t.get("pred_range_pct")]
    if pred_ranges:
        p33 = sorted(pred_ranges)[len(pred_ranges) // 3]
        p66 = sorted(pred_ranges)[2 * len(pred_ranges) // 3]
        for label, lo, hi in [("narrow", 0, p33), ("normal", p33, p66), ("wide", p66, 999)]:
            r_trades = [t for t in trades if lo <= (t.get("pred_range_pct") or 0) < hi]
            if r_trades:
                r_wins = [t for t in r_trades if t["win"]]
                profile["by_pred_range"][label] = {
                    "trades": len(r_trades),
                    "wr": round(len(r_wins) / len(r_trades) * 100, 1),
                    "pnl": round(sum(t["pnl_dollar"] for t in r_trades), 2),
                    "range_pct": f"{lo:.2f}-{hi:.2f}",
                }

    # Previous candle range (low vol vs high vol)
    prev_ranges = [t.get("prev_range_pct", 0) for t in trades if t.get("prev_range_pct")]
    if prev_ranges:
        p33 = sorted(prev_ranges)[len(prev_ranges) // 3]
        p66 = sorted(prev_ranges)[2 * len(prev_ranges) // 3]
        for label, lo, hi in [("low_vol", 0, p33), ("mid_vol", p33, p66), ("high_vol", p66, 999)]:
            r_trades = [t for t in trades if lo <= (t.get("prev_range_pct") or 0) < hi]
            if r_trades:
                r_wins = [t for t in r_trades if t["win"]]
                profile["by_prev_range"][label] = {
                    "trades": len(r_trades),
                    "wr": round(len(r_wins) / len(r_trades) * 100, 1),
                    "pnl": round(sum(t["pnl_dollar"] for t in r_trades), 2),
                    "range_pct": f"{lo:.2f}-{hi:.2f}",
                }

    # Exit reason
    for reason in ["TP", "SL", "CLOSE"]:
        r_trades = [t for t in trades if t.get("exit_reason") == reason]
        if r_trades:
            r_wins = [t for t in r_trades if t["win"]]
            profile["by_exit_reason"][reason] = {
                "trades": len(r_trades),
                "wr": round(len(r_wins) / len(r_trades) * 100, 1),
                "pnl": round(sum(t["pnl_dollar"] for t in r_trades), 2),
            }

    # ── Overall comparison: wins vs losses ──
    profile["win_profile"] = {
        "entry_fill_minute": _dist(wins, "entry_fill_minute"),
        "exit_minute": _dist(wins, "exit_minute"),
        "prev_range_pct": _dist(wins, "prev_range_pct"),
        "pred_range_pct": _dist(wins, "pred_range_pct"),
        "prev_direction": _cat_dist(wins, "prev_direction"),
    }
    profile["loss_profile"] = {
        "entry_fill_minute": _dist(losses, "entry_fill_minute"),
        "exit_minute": _dist(losses, "exit_minute"),
        "prev_range_pct": _dist(losses, "prev_range_pct"),
        "pred_range_pct": _dist(losses, "pred_range_pct"),
        "prev_direction": _cat_dist(losses, "prev_direction"),
    }

    # ── Suggested filters ──
    suggestions = []
    # Check if any hour is significantly worse
    for h, data in profile["by_hour_utc"].items():
        if data["wr"] < profile["win_rate"] - 5 and data["trades"] > 50:
            saved_losses = data["losses"]
            lost_wins = data["wins"]
            suggestions.append({
                "filter": f"skip_hour_{h}",
                "description": f"Skip hour {h} UTC (WR {data['wr']}% vs overall {profile['win_rate']}%)",
                "trades_removed": data["trades"],
                "losses_removed": saved_losses,
                "wins_removed": lost_wins,
                "estimated_new_wr": round((len(wins) - lost_wins) / (total - data["trades"]) * 100, 1) if total > data["trades"] else 0,
            })

    # Check prev_direction
    for pd, data in profile["by_prev_direction"].items():
        if data["wr"] < profile["win_rate"] - 3 and data["trades"] > 100:
            pd_trades = [t for t in trades if t.get("prev_direction") == pd]
            pd_losses = sum(1 for t in pd_trades if not t["win"])
            pd_wins = sum(1 for t in pd_trades if t["win"])
            suggestions.append({
                "filter": f"skip_prev_{pd}",
                "description": f"Skip after {pd} candle (WR {data['wr']}%)",
                "trades_removed": data["trades"],
                "losses_removed": pd_losses,
                "wins_removed": pd_wins,
                "estimated_new_wr": round((len(wins) - pd_wins) / (total - data["trades"]) * 100, 1) if total > data["trades"] else 0,
            })

    # Check entry fill speed
    for speed, data in profile["by_entry_fill_speed"].items():
        if data["wr"] < profile["win_rate"] - 3 and data["trades"] > 50:
            s_trades = [t for t in trades if speed == "fast_0_15" and (t.get("entry_fill_minute") or 0) < 15
                        or speed == "medium_15_60" and 15 <= (t.get("entry_fill_minute") or 0) < 60
                        or speed == "slow_60_plus" and (t.get("entry_fill_minute") or 0) >= 60]
            s_losses = sum(1 for t in s_trades if not t["win"])
            s_wins = sum(1 for t in s_trades if t["win"])
            if s_trades:
                suggestions.append({
                    "filter": f"skip_{speed}",
                    "description": f"Skip {speed} entry fills (WR {data['wr']}%)",
                    "trades_removed": len(s_trades),
                    "losses_removed": s_losses,
                    "wins_removed": s_wins,
                    "estimated_new_wr": round((len(wins) - s_wins) / (total - len(s_trades)) * 100, 1) if total > len(s_trades) else 0,
                })

    # Check day of week
    for dow, data in profile["by_day_of_week"].items():
        if data["wr"] < profile["win_rate"] - 5 and data["trades"] > 50:
            d_idx = dow_names.index(dow)
            d_trades = [t for t in trades if t.get("day_of_week") == d_idx]
            d_losses = sum(1 for t in d_trades if not t["win"])
            d_wins = sum(1 for t in d_trades if t["win"])
            suggestions.append({
                "filter": f"skip_{dow}",
                "description": f"Skip {dow} (WR {data['wr']}%)",
                "trades_removed": data["trades"],
                "losses_removed": d_losses,
                "wins_removed": d_wins,
                "estimated_new_wr": round((len(wins) - d_wins) / (total - data["trades"]) * 100, 1) if total > data["trades"] else 0,
            })

    # Sort suggestions by net impact (losses removed - wins removed)
    suggestions.sort(key=lambda x: x["losses_removed"] - x["wins_removed"], reverse=True)
    profile["suggestions"] = suggestions

    return profile


"""
cluster_levels() — Level Clustering Engine v2
Insert into tick_discovery.py BEFORE _load_data() (line ~1907)
"""

# ════════════════════════════════════════════════════════════
# CLUSTERING — Level Order & Timing Analysis (1m resolution)
# ════════════════════════════════════════════════════════════

_CL_TP_LEVELS = [0.5, 0.7, 1.0, 1.5, 2.0]
_CL_SL_LEVELS = [0.5, 0.7, 1.0, 1.5, 2.0]
_CL_BUFFERS = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
_CL_MAX_HOLD = {"15m": 8, "1h": 4, "4h": 2}  # doubled from 4/2/1
_CL_TIMING_BUCKETS = {
    "15m": [(0, 5, "under_5m"), (5, 15, "5m_15m"), (15, 30, "15m_30m"), (30, 60, "30m_60m"), (60, 120, "60m_120m")],
    "1h":  [(0, 15, "under_15m"), (15, 60, "15m_60m"), (60, 120, "60m_120m"), (120, 240, "120m_240m")],
    "4h":  [(0, 30, "under_30m"), (30, 120, "30m_120m"), (120, 240, "120m_240m"), (240, 480, "240m_480m")],
}

_CL_LEVEL_NAMES = (
    [f"TP_{tp}" for tp in _CL_TP_LEVELS]
    + [f"SL_{sl}" for sl in _CL_SL_LEVELS]
    + ["pred_high", "pred_low", "pred_close", "candle_end"]
)


def _cl_entry_configs():
    """Build 18 entry point configurations."""
    cfgs = []
    # LONG (9)
    cfgs.append({"name": "open_long", "side": "LONG", "desc": "Open → LONG", "open": True, "buf": 0})
    cfgs.append({"name": "pred_low", "side": "LONG", "desc": "Predicted low → LONG", "open": False, "buf": 0})
    for b in _CL_BUFFERS:
        cfgs.append({"name": f"pred_low_buf_{b}", "side": "LONG",
                      "desc": f"pred_low - {b}% → LONG", "open": False, "buf": b})
    # SHORT (9)
    cfgs.append({"name": "open_short", "side": "SHORT", "desc": "Open → SHORT", "open": True, "buf": 0})
    cfgs.append({"name": "pred_high", "side": "SHORT", "desc": "Predicted high → SHORT", "open": False, "buf": 0})
    for b in _CL_BUFFERS:
        cfgs.append({"name": f"pred_high_buf_{b}", "side": "SHORT",
                      "desc": f"pred_high + {b}% → SHORT", "open": False, "buf": b})
    return cfgs


def cluster_levels(
    rows, sub_lookup, symbol, timeframe,
    window=10, days=1825, save_to_d1=True,
):
    """
    Level Clustering with 1m resolution.
    Tests 18 entry points × 14 levels. Records hit rates, timing distributions,
    order distributions, hit_before_sl rates, stability, and auto-suggestions.
    """
    n = len(rows)
    if n < window + 20:
        return {"status": "insufficient_data", "candles": n}

    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    tf_ms = {"1m": 60000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)
    max_hold = _CL_MAX_HOLD.get(timeframe, 1)
    buckets = _CL_TIMING_BUCKETS.get(timeframe, _CL_TIMING_BUCKETS["4h"])
    max_walk_min = buckets[-1][1]

    entry_cfgs = _cl_entry_configs()

    # ── Accumulators per entry config ──
    acc = {}
    for cfg in entry_cfgs:
        acc[cfg["name"]] = {
            "cfg": cfg, "checked": 0, "triggered": 0,
            "level_hits": {ln: [] for ln in _CL_LEVEL_NAMES},   # list of minutes
            "level_orders": {ln: [] for ln in _CL_LEVEL_NAMES}, # list of order values
            "raw": [],  # [(candle_time, {level: min_or_None})] for stability
        }

    # ── Limit by days ──
    start_idx = window
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        for ri in range(len(rows)):
            if rows[ri][5] >= last_time - ms_limit:
                start_idx = max(window, ri)
                break

    total_candles = 0

    # ═══════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════
    for i in range(start_idx, len(close_ratios)):
        if i + 1 >= n:
            break

        # Deret Statistik predicted range
        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l
        pred_close = closes[i] * avg_c

        next_idx = i + 1
        candle_time = times[next_idx]
        candle_open = opens[next_idx]

        # ── Context for per-hour + per-direction analysis ──
        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        hour_utc = dt.hour
        prev_dir = "bullish" if closes[i] > opens[i] else ("bearish" if closes[i] < opens[i] else "doji")
        prev_range = round((highs[i] - lows[i]) / opens[i] * 100, 4) if opens[i] > 0 else 0

        # ── Flatten 1m subs across max_hold candles ──
        first_parent_ts = (candle_time // parent_ms) * parent_ms
        first_subs = sub_lookup.get(first_parent_ts, [])
        if not first_subs:
            continue

        all_subs = list(first_subs)
        for k in range(1, max_hold):
            ci = next_idx + k
            if ci >= n:
                break
            pts = (times[ci] // parent_ms) * parent_ms
            s = sub_lookup.get(pts, [])
            all_subs.extend(s)

        total_candles += 1

        # ── Test each entry config ──
        for cfg in entry_cfgs:
            ename = cfg["name"]
            ea = acc[ename]
            ea["checked"] += 1
            side = cfg["side"]

            # Compute entry price
            if cfg["open"]:
                entry_price = candle_open
            elif side == "LONG":
                entry_price = pred_low * (1 - cfg["buf"] / 100) if cfg["buf"] > 0 else pred_low
            else:
                entry_price = pred_high * (1 + cfg["buf"] / 100) if cfg["buf"] > 0 else pred_high

            # Find trigger minute (only in first candle's subs)
            if cfg["open"]:
                trigger_idx = -1  # open = immediate, walk from 0
                walk_start = 0
            else:
                trigger_idx = -1
                for sc_i, sc in enumerate(first_subs):
                    if side == "LONG" and sc["l"] <= entry_price:
                        trigger_idx = sc_i
                        break
                    if side == "SHORT" and sc["h"] >= entry_price:
                        trigger_idx = sc_i
                        break
                if trigger_idx < 0:
                    continue  # not triggered
                walk_start = trigger_idx + 1  # start checking from NEXT 1m candle

            ea["triggered"] += 1

            # Build level target prices
            targets = {}
            for tp in _CL_TP_LEVELS:
                if side == "LONG":
                    targets[f"TP_{tp}"] = (entry_price * (1 + tp / 100), "above")
                else:
                    targets[f"TP_{tp}"] = (entry_price * (1 - tp / 100), "below")
            for sl in _CL_SL_LEVELS:
                if side == "LONG":
                    targets[f"SL_{sl}"] = (entry_price * (1 - sl / 100), "below")
                else:
                    targets[f"SL_{sl}"] = (entry_price * (1 + sl / 100), "above")
            targets["pred_high"] = (pred_high, "above")
            targets["pred_low"] = (pred_low, "below")
            targets["pred_close"] = (pred_close, "either")

            # Walk 1m subs from walk_start
            level_min = {ln: None for ln in _CL_LEVEL_NAMES}
            remaining = set(targets.keys())
            for sc_i in range(walk_start, len(all_subs)):
                minute = sc_i - walk_start
                if minute >= max_walk_min:
                    break
                if not remaining:
                    break
                sc = all_subs[sc_i]
                for ln in list(remaining):
                    price, direction = targets[ln]
                    hit = False
                    if direction == "above" and sc["h"] >= price:
                        hit = True
                    elif direction == "below" and sc["l"] <= price:
                        hit = True
                    elif direction == "either" and sc["l"] <= price <= sc["h"]:
                        hit = True
                    if hit:
                        level_min[ln] = minute
                        remaining.discard(ln)

            level_min["candle_end"] = min(len(all_subs) - walk_start, max_walk_min)

            # Compute order among hit levels
            hit_sorted = sorted(
                [(ln, m) for ln, m in level_min.items() if m is not None and ln != "candle_end"],
                key=lambda x: x[1]
            )
            order_map = {ln: rank for rank, (ln, _) in enumerate(hit_sorted, 1)}

            # Accumulate (include hour + context + prices for distance calc)
            ea["raw"].append((candle_time, level_min, hour_utc, prev_dir, prev_range, entry_price, pred_high, pred_low, pred_close))
            for ln in _CL_LEVEL_NAMES:
                m = level_min.get(ln)
                if m is not None and ln != "candle_end":
                    ea["level_hits"][ln].append(m)
                    ea["level_orders"][ln].append(order_map.get(ln, 99))

    _log(f"  📊 Clustering {symbol} {timeframe}: {total_candles} candles × {len(entry_cfgs)} entries")

    # ═══════════════════════════════════════════
    # AGGREGATE
    # ═══════════════════════════════════════════
    output_entries = []
    for cfg in entry_cfgs:
        ea = acc[cfg["name"]]
        trig = ea["triggered"]
        if trig == 0:
            continue

        entry_trig_pct = round(trig / ea["checked"] * 100, 1) if ea["checked"] > 0 else 0
        levels_out = []

        for ln in _CL_LEVEL_NAMES:
            hits = ea["level_hits"][ln]
            orders = ea["level_orders"][ln]
            hit_pct = round(len(hits) / trig * 100, 1) if ln != "candle_end" else 100.0

            lvl = {"level_name": ln, "side": cfg["side"], "hit_pct": hit_pct}

            # Timing distribution
            if hits:
                td = {}
                for lo, hi, bname in buckets:
                    c = sum(1 for m in hits if lo <= m < hi)
                    td[bname] = round(c / len(hits) * 100, 1)
                lvl["timing_distribution"] = td

            # Order distribution
            if orders:
                od = {}
                tot = len(orders)
                for o in [1, 2, 3, 4]:
                    od[str(o)] = round(sum(1 for v in orders if v == o) / tot * 100, 1)
                od["5+"] = round(sum(1 for v in orders if v >= 5) / tot * 100, 1)
                lvl["order_distribution"] = od

                # Cluster = most frequent order
                from collections import Counter
                oc = Counter(min(v, 5) for v in orders)
                mc = oc.most_common(1)[0]
                lvl["cluster_order"] = mc[0]
                lvl["cluster_pct"] = round(mc[1] / tot * 100, 1)

            # hit_before_sl (only for TP levels)
            if ln.startswith("TP_"):
                hbs = {}
                for sl_val in _CL_SL_LEVELS:
                    sl_n = f"SL_{sl_val}"
                    tp_before = 0
                    total_relevant = 0
                    for _, lm, *_ctx in ea["raw"]:
                        tp_m = lm.get(ln)
                        sl_m = lm.get(sl_n)
                        if tp_m is not None or sl_m is not None:
                            total_relevant += 1
                            if tp_m is not None and (sl_m is None or tp_m < sl_m):
                                tp_before += 1
                    hbs[f"before_SL_{sl_val}"] = round(tp_before / total_relevant * 100, 1) if total_relevant > 0 else 0
                lvl["hit_before_sl"] = hbs

            levels_out.append(lvl)

        # Best combo (with dynamic targets + dual hold)
        combo_result = _cl_best_combo(ea["raw"], trig, side=cfg["side"], max_walk_min=max_walk_min)
        if combo_result:
            best, top10 = combo_result
        else:
            best, top10 = None, []
        # Stability
        stab = _cl_stability(ea["raw"], best["tp_name"], best["sl_name"]) if best else {}

        # Per-hour breakdown
        per_hour = _cl_per_hour(ea["raw"], best) if best else {}

        ep_out = {
            "entry_name": cfg["name"],
            "entry_description": cfg["desc"],
            "entry_side": cfg["side"],
            "entry_triggered_pct": entry_trig_pct,
            "total_entries": trig,
            "levels": levels_out,
        }
        if best:
            ep_out["best_combo"] = {
                "tp": best["tp_val"], "sl": best["sl_val"],
                "tp_name": best["tp_name"], "tp_type": best.get("tp_type", "fixed"),
                "hold": best.get("hold", "short"), "hold_minutes": best.get("hold_minutes", 0),
                "est_wr": best["wr"], "trades": trig,
                "expired_pct": best.get("expired_pct", 0),
                "recovery_pct": best.get("recovery_pct", 0),
                "dist_info": best.get("dist_info", {}),
            }
        if top10:
            ep_out["top10_combos"] = [{
                "tp": c["tp_val"], "sl": c["sl_val"],
                "tp_name": c["tp_name"], "tp_type": c.get("tp_type", "fixed"),
                "hold": c.get("hold", "short"), "hold_min": c.get("hold_minutes", 0),
                "wr": c["wr"], "expired_pct": c.get("expired_pct", 0),
                "dist_info": c.get("dist_info", {}),
            } for c in top10]
        if stab:
            ep_out["stability"] = stab
        if per_hour:
            ep_out["per_hour"] = per_hour

        # Sequence narrator
        narrative = _cl_sequence_narrator(ea["raw"], best, side=cfg["side"])
        if narrative:
            ep_out["sequence"] = narrative
        output_entries.append(ep_out)

    # Auto-suggest
    suggestions = _cl_suggest(output_entries)

    result = {
        "status": "ok",
        "symbol": symbol, "timeframe": timeframe, "window": window,
        "total_candles": total_candles,
        "timing_buckets": {b[2]: f"{b[0]}-{b[1]}m" for b in buckets},
        "entry_points": output_entries,
        "suggestions": suggestions,
    }

    if save_to_d1:
        _save_clustering_to_d1(result)

    return result


def _cl_best_combo(raw, triggered, side="LONG", max_walk_min=240):
    """Find TP/SL combo with highest WR — includes dynamic targets + dual hold + actual distances."""
    results = []
    half_hold = max_walk_min // 2

    # ── Fixed TP targets ──
    tp_targets = [(f"TP_{v}", v, "fixed") for v in _CL_TP_LEVELS]

    # ── Dynamic TP targets ──
    if side == "LONG":
        tp_targets.append(("pred_high", 0, "dynamic"))
        tp_targets.append(("pred_close", 0, "dynamic"))
    else:
        tp_targets.append(("pred_low", 0, "dynamic"))
        tp_targets.append(("pred_close", 0, "dynamic"))

    for tp_n, tp_v, tp_type in tp_targets:
        for sl_v in _CL_SL_LEVELS:
            sl_n = f"SL_{sl_v}"

            for hold_label, hold_limit in [("short", half_hold), ("long", max_walk_min)]:
                wins = 0
                losses = 0
                expired = 0
                expired_toward_tp = 0
                distances = []  # actual TP distance per trade

                for entry in raw:
                    lm = entry[1]
                    tp_m = lm.get(tp_n)
                    sl_m = lm.get(sl_n)

                    # Compute actual distance for dynamic targets
                    if tp_type == "dynamic" and len(entry) >= 9:
                        ep = entry[5]  # entry_price
                        ph, pl, pc = entry[6], entry[7], entry[8]
                        if side == "LONG":
                            if tp_n == "pred_high":
                                dist = abs(ph - ep) / ep * 100 if ep > 0 else 0
                            else:  # pred_close
                                dist = abs(pc - ep) / ep * 100 if ep > 0 else 0
                        else:
                            if tp_n == "pred_low":
                                dist = abs(ep - pl) / ep * 100 if ep > 0 else 0
                            else:  # pred_close
                                dist = abs(ep - pc) / ep * 100 if ep > 0 else 0
                        distances.append(round(dist, 3))

                    tp_in_range = tp_m is not None and tp_m <= hold_limit
                    sl_in_range = sl_m is not None and sl_m <= hold_limit

                    if tp_in_range and (not sl_in_range or tp_m < sl_m):
                        wins += 1
                    elif sl_in_range and (not tp_in_range or sl_m <= tp_m):
                        losses += 1
                    else:
                        expired += 1
                        if tp_m is not None:
                            expired_toward_tp += 1

                total = wins + losses + expired
                if total < 30:
                    continue

                wr = round(wins / total * 100, 1)
                expired_pct = round(expired / total * 100, 1)
                recovery_pct = round(expired_toward_tp / expired * 100, 1) if expired > 0 else 0

                # Distance stats for dynamic targets
                avg_dist = round(sum(distances) / len(distances), 3) if distances else tp_v
                dist_info = {}
                if distances:
                    sd = sorted(distances)
                    dist_info = {
                        "avg": avg_dist,
                        "median": round(sd[len(sd)//2], 3),
                        "p25": round(sd[int(len(sd)*0.25)], 3),
                        "p75": round(sd[int(len(sd)*0.75)], 3),
                        "min": round(sd[0], 3),
                        "max": round(sd[-1], 3),
                    }

                results.append({
                    "tp_val": avg_dist if tp_type == "dynamic" else tp_v,
                    "sl_val": sl_v,
                    "tp_name": tp_n, "sl_name": sl_n,
                    "tp_type": tp_type, "hold": hold_label,
                    "hold_minutes": hold_limit,
                    "wr": wr, "wins": wins, "losses": losses,
                    "expired": expired, "expired_pct": expired_pct,
                    "recovery_pct": recovery_pct,
                    "total": total,
                    "dist_info": dist_info,
                })

    if not results:
        return None

    # Best = highest WR
    results.sort(key=lambda x: (x["wr"], -x["expired_pct"]), reverse=True)
    return results[0], results[:10]  # best + top 10


def _cl_stability(raw, tp_name, sl_name):
    """Compute stability metrics for a TP/SL combo."""
    trades = []
    for ct, lm, *_ctx in raw:
        tp_m = lm.get(tp_name)
        sl_m = lm.get(sl_name)
        win = tp_m is not None and (sl_m is None or tp_m < sl_m)
        trades.append({"time": ct, "win": win})

    if len(trades) < 10:
        return {}

    total = len(trades)
    wins = sum(1 for t in trades if t["win"])
    wr = round(wins / total * 100, 1)

    # Weekly WR
    wk_buckets = defaultdict(lambda: {"w": 0, "l": 0})
    for t in trades:
        wk = int(t["time"] // (7 * 86400000))
        wk_buckets[wk]["w" if t["win"] else "l"] += 1

    weekly_wrs = []
    for wb in wk_buckets.values():
        tot = wb["w"] + wb["l"]
        if tot >= 2:
            weekly_wrs.append(wb["w"] / tot * 100)

    consistency = (sum(1 for w in weekly_wrs if w >= 50) / len(weekly_wrs) * 100) if weekly_wrs else 0
    p5_wr = round(sorted(weekly_wrs)[max(0, int(len(weekly_wrs) * 0.05))], 1) if weekly_wrs else 0

    # Worst streak
    worst = 0
    cur = 0
    for t in trades:
        if not t["win"]:
            cur += 1
            worst = max(worst, cur)
        else:
            cur = 0

    # Walk-forward
    sp = int(total * 0.8)
    if sp > 10 and total - sp > 5:
        train_w = sum(1 for t in trades[:sp] if t["win"])
        test_w = sum(1 for t in trades[sp:] if t["win"])
        train_wr = train_w / sp * 100
        test_wr = test_w / (total - sp) * 100
        wf = round(test_wr / train_wr, 2) if train_wr > 0 else 0
    else:
        train_wr, test_wr, wf = wr, wr, 1.0

    return {
        "win_rate": wr, "consistency_pct": round(consistency, 1),
        "p5_weekly_wr": p5_wr, "worst_streak": worst,
        "walk_forward_ratio": wf,
        "train_wr": round(train_wr, 1), "test_wr": round(test_wr, 1),
        "weeks_counted": len(weekly_wrs), "total_trades": total,
    }


def _cl_per_hour(raw, best_combo):
    """Per-hour breakdown: WR, trades, direction dominance, prev_direction stats."""
    if not raw or not best_combo:
        return {}

    tp_n = best_combo["tp_name"]
    sl_n = best_combo["sl_name"]

    hours = defaultdict(lambda: {
        "wins": 0, "total": 0,
        "prev_bullish": 0, "prev_bearish": 0,
        "prev_bull_wins": 0, "prev_bear_wins": 0,
        "high_vol_wins": 0, "high_vol_total": 0,
        "low_vol_wins": 0, "low_vol_total": 0,
    })

    # Compute vol thresholds (p33/p66 of prev_range)
    all_ranges = [r[4] for r in raw if len(r) > 4 and r[4] > 0]
    if all_ranges:
        sr = sorted(all_ranges)
        vol_lo = sr[len(sr) // 3]
        vol_hi = sr[2 * len(sr) // 3]
    else:
        vol_lo, vol_hi = 1.0, 3.0

    for entry in raw:
        ct, lm = entry[0], entry[1]
        h = entry[2] if len(entry) > 2 else 0
        pd = entry[3] if len(entry) > 3 else "doji"
        pr = entry[4] if len(entry) > 4 else 0

        tp_m = lm.get(tp_n)
        sl_m = lm.get(sl_n)
        win = tp_m is not None and (sl_m is None or tp_m < sl_m)

        hd = hours[h]
        hd["total"] += 1
        if win:
            hd["wins"] += 1

        # By prev direction
        if pd == "bullish":
            hd["prev_bullish"] += 1
            if win:
                hd["prev_bull_wins"] += 1
        elif pd == "bearish":
            hd["prev_bearish"] += 1
            if win:
                hd["prev_bear_wins"] += 1

        # By volatility
        if pr >= vol_hi:
            hd["high_vol_total"] += 1
            if win:
                hd["high_vol_wins"] += 1
        elif pr <= vol_lo:
            hd["low_vol_total"] += 1
            if win:
                hd["low_vol_wins"] += 1

    result = {}
    for h in sorted(hours.keys()):
        hd = hours[h]
        if hd["total"] < 5:
            continue
        entry = {
            "trades": hd["total"],
            "wr": round(hd["wins"] / hd["total"] * 100, 1),
        }
        if hd["prev_bullish"] >= 3:
            entry["wr_after_bullish"] = round(hd["prev_bull_wins"] / hd["prev_bullish"] * 100, 1)
        if hd["prev_bearish"] >= 3:
            entry["wr_after_bearish"] = round(hd["prev_bear_wins"] / hd["prev_bearish"] * 100, 1)
        if hd["high_vol_total"] >= 3:
            entry["wr_high_vol"] = round(hd["high_vol_wins"] / hd["high_vol_total"] * 100, 1)
        if hd["low_vol_total"] >= 3:
            entry["wr_low_vol"] = round(hd["low_vol_wins"] / hd["low_vol_total"] * 100, 1)

        # Flag exceptional hours
        if entry["wr"] >= 75:
            entry["flag"] = "★ HIGH EDGE"
        elif entry["wr"] <= 45:
            entry["flag"] = "❌ SKIP"

        result[str(h)] = entry

    return result


def _cl_sequence_narrator(raw, best_combo, side="LONG"):
    """
    Enhanced sequence narrator — answers:
    1. DCA scenarios (pred_high, pred_close as DCA points)
    2. Distance distribution per level (not just avg)
    3. Actual counts per level per order
    4. SL = TP mirror detection
    5. Conditional sequences (after X hits, what's next?)
    Plus conclusion + opportunity detection.
    """
    if not raw or not best_combo:
        return {}

    total_trades = len(raw)
    fee = 0.07

    # ═══ ORDER SEQUENCE: per order, what level hits ═══
    order_counts = defaultdict(lambda: defaultdict(int))
    for entry in raw:
        lm = entry[1]
        hit_sorted = sorted(
            [(ln, m) for ln, m in lm.items() if m is not None and ln != "candle_end"],
            key=lambda x: x[1]
        )
        for pos, (ln, _) in enumerate(hit_sorted, 1):
            order_key = str(pos) if pos <= 5 else "5+"
            order_counts[order_key][ln] += 1

    sequence = {}
    for order in ["1", "2", "3", "4", "5+"]:
        counts = order_counts.get(order, {})
        total_at_pos = sum(counts.values())
        if total_at_pos == 0:
            continue
        levels = {}
        for ln, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            pct = round(cnt / total_trades * 100, 1)
            if pct >= 1:
                levels[ln] = {"pct": pct, "count": cnt}
        sequence[order] = {"levels": levels, "trades_at_pos": total_at_pos}

    # ═══ DISTANCE DISTRIBUTION per dynamic level ═══
    distance_dist = {}
    for dyn_name in ["pred_high", "pred_low", "pred_close"]:
        distances = []
        for entry in raw:
            if len(entry) < 9:
                continue
            ep = entry[5]
            ph, pl, pc = entry[6], entry[7], entry[8]
            if ep <= 0:
                continue
            if dyn_name == "pred_high":
                d = abs(ph - ep) / ep * 100
            elif dyn_name == "pred_low":
                d = abs(ep - pl) / ep * 100
            else:
                d = abs(pc - ep) / ep * 100
            distances.append(round(d, 4))

        if not distances:
            continue

        sd = sorted(distances)
        n = len(sd)

        # Bucket distribution
        buckets = [
            (0, 0.1, "0-0.1%"),
            (0.1, 0.3, "0.1-0.3%"),
            (0.3, 0.5, "0.3-0.5%"),
            (0.5, 1.0, "0.5-1.0%"),
            (1.0, 2.0, "1.0-2.0%"),
            (2.0, 5.0, "2.0-5.0%"),
            (5.0, 100, "5.0%+"),
        ]
        dist_buckets = {}
        for lo, hi, label in buckets:
            cnt = sum(1 for d in distances if lo <= d < hi)
            if cnt > 0:
                dist_buckets[label] = {"count": cnt, "pct": round(cnt / n * 100, 1)}

        distance_dist[dyn_name] = {
            "avg": round(sum(distances) / n, 4),
            "median": round(sd[n // 2], 4),
            "p25": round(sd[int(n * 0.25)], 4),
            "p75": round(sd[int(n * 0.75)], 4),
            "min": round(sd[0], 4),
            "max": round(sd[-1], 4),
            "total_samples": n,
            "distribution": dist_buckets,
        }

    # ═══ PREDICTED RANGE distribution ═══
    ranges = []
    for entry in raw:
        if len(entry) < 9:
            continue
        ph, pl = entry[6], entry[7]
        if pl > 0:
            r = (ph - pl) / pl * 100
            ranges.append(round(r, 4))

    range_dist = {}
    if ranges:
        sr = sorted(ranges)
        nr = len(sr)
        range_buckets = {}
        for lo, hi, label in [(0, 0.5, "<0.5%"), (0.5, 1, "0.5-1%"), (1, 2, "1-2%"), (2, 5, "2-5%"), (5, 100, "5%+")]:
            cnt = sum(1 for r in ranges if lo <= r < hi)
            if cnt > 0:
                range_buckets[label] = {"count": cnt, "pct": round(cnt / nr * 100, 1)}
        range_dist = {
            "avg": round(sum(ranges) / nr, 4),
            "median": round(sr[nr // 2], 4),
            "distribution": range_buckets,
        }

    # ═══ DCA SCENARIOS ═══
    dca_scenarios = []

    # DCA at pred_high (for SHORT: DCA when price goes up more)
    # DCA at pred_low (for LONG: DCA when price goes down more)
    for dca_level, dca_side_match in [("pred_high", "SHORT"), ("pred_low", "LONG")]:
        if side != dca_side_match:
            # Also check: LONG entry, DCA at pred_high = price went up, bad for LONG
            # But could be useful if we flip to SHORT at pred_high
            pass

        dca_trigger_count = sum(1 for e in raw if e[1].get(dca_level) is not None)
        dca_trigger_pct = round(dca_trigger_count / total_trades * 100, 1)

        if dca_trigger_pct < 10:
            continue

        # Compute avg distance from entry to DCA level
        dca_distances = []
        for entry in raw:
            if len(entry) < 9 or entry[1].get(dca_level) is None:
                continue
            ep = entry[5]
            ph, pl = entry[6], entry[7]
            if ep <= 0:
                continue
            if dca_level == "pred_high":
                d = (ph - ep) / ep * 100
            else:
                d = (ep - pl) / ep * 100
            dca_distances.append(round(d, 4))

        avg_dca_dist = round(sum(dca_distances) / len(dca_distances), 4) if dca_distances else 0

        # After DCA triggers, what's the new avg entry and distance to TP?
        # For LONG with DCA at pred_low: new_entry = (entry + pred_low) / 2
        # Distance to pred_high from new_entry
        new_distances_to_target = []
        for entry in raw:
            if len(entry) < 9 or entry[1].get(dca_level) is None:
                continue
            ep = entry[5]
            ph, pl, pc = entry[6], entry[7], entry[8]
            if ep <= 0:
                continue
            if dca_level == "pred_low" and side == "LONG":
                new_entry = (ep + pl) / 2
                dist_to_ph = (ph - new_entry) / new_entry * 100
                dist_to_pc = (pc - new_entry) / new_entry * 100
                new_distances_to_target.append({"to_pred_high": round(dist_to_ph, 4), "to_pred_close": round(dist_to_pc, 4)})
            elif dca_level == "pred_high" and side == "SHORT":
                new_entry = (ep + ph) / 2
                dist_to_pl = (new_entry - pl) / new_entry * 100
                dist_to_pc = (new_entry - pc) / new_entry * 100
                new_distances_to_target.append({"to_pred_low": round(dist_to_pl, 4), "to_pred_close": round(dist_to_pc, 4)})

        avg_new_dists = {}
        if new_distances_to_target:
            for key in new_distances_to_target[0]:
                vals = [d[key] for d in new_distances_to_target if key in d]
                avg_new_dists[key] = round(sum(vals) / len(vals), 4) if vals else 0

        dca_scenarios.append({
            "dca_level": dca_level,
            "trigger_pct": dca_trigger_pct,
            "trigger_count": dca_trigger_count,
            "avg_distance_to_dca": avg_dca_dist,
            "after_dca_distances": avg_new_dists,
            "insight": f"DCA di {dca_level} ({dca_trigger_pct}% trigger, jarak {avg_dca_dist}% dari entry). "
                       f"Setelah DCA: {', '.join(f'{k}={v}%' for k,v in avg_new_dists.items())}",
        })

    # ═══ SL = TP MIRROR detection ═══
    mirrors = []
    for sl_pct in _CL_SL_LEVELS:
        sl_key = f"SL_{sl_pct}"
        # Count SL hits at order 1 (first thing that happens)
        sl_at_order1 = order_counts.get("1", {}).get(sl_key, 0)
        sl_at_order1_pct = round(sl_at_order1 / total_trades * 100, 1) if total_trades > 0 else 0

        if sl_at_order1_pct >= 1:
            flip_side = "SHORT" if side == "LONG" else "LONG"
            mirrors.append({
                "sl_level": sl_key,
                "sl_pct": sl_pct,
                "hits_at_order1": sl_at_order1,
                "hits_at_order1_pct": sl_at_order1_pct,
                "insight": f"SL {sl_pct}% kena {sl_at_order1}× di urutan 1 → flip {flip_side} TP {sl_pct}% = {sl_at_order1} potential wins",
            })

    # ═══ CONDITIONAL SEQUENCE: after X hits, what's next? ═══
    conditional = {}
    for first_level in ["pred_high", "pred_low", "pred_close"]:
        next_counts = defaultdict(int)
        total_first = 0
        for entry in raw:
            lm = entry[1]
            hit_sorted = sorted(
                [(ln, m) for ln, m in lm.items() if m is not None and ln != "candle_end"],
                key=lambda x: x[1]
            )
            if hit_sorted and hit_sorted[0][0] == first_level:
                total_first += 1
                if len(hit_sorted) > 1:
                    next_counts[hit_sorted[1][0]] += 1

        if total_first >= 50:
            next_levels = {}
            for ln, cnt in sorted(next_counts.items(), key=lambda x: -x[1])[:5]:
                next_levels[ln] = {"count": cnt, "pct": round(cnt / total_first * 100, 1)}
            conditional[first_level] = {
                "first_hit_count": total_first,
                "then_what": next_levels,
            }

    # ═══ CONCLUSION ═══
    tp_val = best_combo.get("tp_val", 0)
    sl_val = best_combo.get("sl_val", 0)
    wr = best_combo.get("wr", 0)
    ev = round((wr / 100 * (tp_val - fee)) - ((1 - wr / 100) * (sl_val + fee)), 4)

    conclusion = f"WR {wr}%, TP {tp_val}% vs SL {sl_val}%, EV = {ev}%/trade"
    if ev > 0:
        conclusion += f" ✅ PROFITABLE (${round(ev * total_trades, 1)} total dari {total_trades} trades)"
    else:
        conclusion += f" ❌ RUGI (kehilangan ${round(abs(ev) * total_trades, 1)} total)"

    # ═══ OPPORTUNITIES ═══
    opportunities = []

    for dyn in ["pred_high", "pred_low", "pred_close"]:
        hits = sum(1 for e in raw if e[1].get(dyn) is not None)
        hit_pct = round(hits / total_trades * 100, 1)
        if hit_pct >= 60:
            dist = distance_dist.get(dyn, {})
            avg_d = dist.get("avg", 0)
            opportunities.append({
                "target": dyn, "hit_pct": hit_pct, "avg_distance": avg_d,
                "insight": f"{dyn} kena {hit_pct}% trades (avg {avg_d}% dari entry) → {'worth jadi TP' if avg_d > 0.3 else 'terlalu dekat untuk TP'}",
            })

    for sl_check in _CL_SL_LEVELS:
        sl_key = f"SL_{sl_check}"
        sl_hits = sum(1 for e in raw if e[1].get(sl_key) is not None)
        sl_hit_pct = round(sl_hits / total_trades * 100, 1)
        if sl_hit_pct > 70:
            opportunities.append({
                "target": sl_key, "hit_pct": sl_hit_pct,
                "insight": f"SL {sl_check}% kena di {sl_hit_pct}% trades → terlalu ketat, perbesar SL atau flip direction",
            })

    if ev <= 0:
        opportunities.append({
            "target": "ratio",
            "insight": f"EV negatif ({ev}%). Coba naikkan TP atau kecilkan SL untuk ratio lebih baik",
        })

    # Check range
    if range_dist:
        avg_range = range_dist.get("avg", 0)
        if avg_range < 0.5:
            opportunities.append({
                "target": "range",
                "insight": f"Avg range cuma {avg_range}% → pair/TF ini range terlalu kecil. Coba TF lebih besar atau pair lebih volatile",
            })

    return {
        "sequence": sequence,
        "distance_distribution": distance_dist,
        "predicted_range": range_dist,
        "dca_scenarios": dca_scenarios,
        "sl_tp_mirrors": mirrors,
        "conditional_sequence": conditional,
        "conclusion": conclusion,
        "ev_per_trade": ev,
        "total_net": round(ev * total_trades, 1),
        "opportunities": opportunities,
    }


def _cl_suggest(entry_points):
    """Rank all entry+combo by stability-adjusted WR."""
    sugg = []
    for ep in entry_points:
        bc = ep.get("best_combo")
        st = ep.get("stability", {})
        if not bc or bc["est_wr"] < 50:
            continue

        wr = bc["est_wr"]
        con = st.get("consistency_pct", 0)
        wf = st.get("walk_forward_ratio", 0)
        ws = st.get("worst_streak", 99)

        score = wr * 0.40 + con * 0.30 + min(wf * 100, 100) * 0.20 + max(0, 100 - ws * 10) * 0.10

        # Insight
        nm = ep["entry_name"]
        tp_type = bc.get("tp_type", "fixed")
        tp_name = bc.get("tp_name", "")
        hold = bc.get("hold", "short")

        if tp_type == "dynamic":
            ins = f"→ {tp_name}"
        elif nm.startswith("open"):
            ins = "Baseline (open)"
        elif "buf_0.5" in nm:
            ins = "Sweet spot buffer"
        elif "buf_2.0" in nm:
            ins = "Deep entry"
        elif nm in ("pred_low", "pred_high"):
            ins = "Predicted extreme"
        else:
            ins = f"Buffer {nm.split('buf_')[-1]}%"

        if hold == "long":
            ins += " [hold panjang]"
        if bc.get("expired_pct", 0) > 30:
            ins += f" ({bc['expired_pct']}% expired)"
        if wr >= 65 and con >= 70:
            ins += " ★"
        elif wr < 55:
            ins += " ❌"

        sugg.append({
            "rank": 0, "entry_name": nm, "entry_side": ep["entry_side"],
            "tp": bc["tp"], "sl": bc["sl"],
            "tp_type": tp_type, "tp_target": tp_name if tp_type == "dynamic" else f"TP_{bc['tp']}%",
            "hold": hold, "hold_min": bc.get("hold_minutes", 0),
            "est_wr": wr, "expired_pct": bc.get("expired_pct", 0),
            "trades": ep["total_entries"], "consistency": round(con, 1),
            "wf_ratio": wf, "worst_streak": ws, "score": round(score, 1),
            "insight": ins,
        })

    sugg.sort(key=lambda x: x["score"], reverse=True)
    for i, s in enumerate(sugg):
        s["rank"] = i + 1
    return sugg[:10]


def _save_clustering_to_d1(result):
    """Save clustering results to D1 via Workers."""
    try:
        payload = {
            "symbol": result["symbol"],
            "timeframe": result["timeframe"],
            "window": result["window"],
            "total_candles": result["total_candles"],
            "timing_buckets": json.dumps(result["timing_buckets"]),
            "entry_points": [],
            "suggestions": result.get("suggestions", []),
        }
        for ep in result["entry_points"]:
            payload["entry_points"].append({
                "entry_name": ep["entry_name"],
                "entry_side": ep["entry_side"],
                "entry_triggered_pct": ep["entry_triggered_pct"],
                "total_entries": ep["total_entries"],
                "best_combo": ep.get("best_combo"),
                "stability": ep.get("stability"),
                "levels_json": json.dumps(ep["levels"]),
                "per_hour_json": json.dumps(ep.get("per_hour", {})),
                "sequence_json": json.dumps(ep.get("sequence", {})),
            })
        resp = requests.post(f"{WORKER_URL}/tick/save-clustering", json=payload, timeout=30)
        if resp.ok:
            _log(f"  💾 Clustering saved: {result['symbol']} {result['timeframe']}")
        else:
            _log(f"  ⚠️ Clustering save failed: {resp.status_code}")
    except Exception as ex:
        _log(f"  ⚠️ Clustering save error: {str(ex)[:100]}")

# ════════════════════════════════════════════════════════════

# COMBO SWEEP ENGINE
# ════════════════════════════════════════════════════════════

_COMBO_TP_FIXED = [0.5, 0.7, 1.0, 1.5, 2.0]
_COMBO_SL_FIXED = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
_COMBO_DCA = [0, 0.5, 1.0]  # 0 = no DCA
_COMBO_FEE = 0.07  # maker+taker

_combo_sweep_status = {
    "running": False, "paused": False,
    "progress": "", "completed": 0, "total": 0,
    "winners": 0, "started_at": None, "finished_at": None,
}


def combo_sweep(
    rows, sub_lookup, symbol, timeframe,
    window=10, days=1825, daily_cap=5.0, position_size=100,
    save_to_d1=True,
):
    """
    Test ALL entry×TP×SL×DCA×hold combos using pre-computed 1m level data.
    Rank by total_profit (EV × trades), not just WR.
    Include daily cap simulation.
    """
    n = len(rows)
    if n < window + 20:
        return {"status": "insufficient_data"}

    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    tf_ms = {"1m": 60000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)
    max_hold_map = {"15m": 8, "1h": 4, "4h": 2}
    max_hold = max_hold_map.get(timeframe, 2)
    half_hold_min = {"15m": 60, "1h": 120, "4h": 240}
    full_hold_min = {"15m": 120, "1h": 240, "4h": 480}

    entry_cfgs = _cl_entry_configs()  # reuse from clustering

    # ── Limit by days ──
    start_idx = window
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        for ri in range(len(rows)):
            if rows[ri][5] >= last_time - ms_limit:
                start_idx = max(window, ri)
                break

    _log(f"  🔬 Combo sweep {symbol} {timeframe}: pre-computing level hits...")

    # ═══════════════════════════════════════════
    # PHASE 1: Pre-compute ALL level hit minutes per candle per entry
    # ═══════════════════════════════════════════
    # Structure: trades[entry_name] = [(candle_time, entry_price, pred_h, pred_l, pred_c, {level: min}, hour_utc, date_str)]
    all_trades = {cfg["name"]: [] for cfg in entry_cfgs}

    for i in range(start_idx, len(close_ratios)):
        if i + 1 >= n:
            break

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l
        pred_close = closes[i] * avg_c

        next_idx = i + 1
        candle_time = times[next_idx]
        candle_open = opens[next_idx]

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        hour_utc = dt.hour
        date_str = dt.strftime("%Y-%m-%d")

        # Flatten 1m subs
        first_parent_ts = (candle_time // parent_ms) * parent_ms
        first_subs = sub_lookup.get(first_parent_ts, [])
        if not first_subs:
            continue

        all_subs = list(first_subs)
        for k in range(1, max_hold):
            ci = next_idx + k
            if ci >= n:
                break
            pts = (times[ci] // parent_ms) * parent_ms
            s = sub_lookup.get(pts, [])
            all_subs.extend(s)

        max_walk = full_hold_min.get(timeframe, 480)

        for cfg in entry_cfgs:
            side = cfg["side"]

            # Compute entry price
            if cfg["open"]:
                entry_price = candle_open
            elif side == "LONG":
                entry_price = pred_low * (1 - cfg["buf"] / 100) if cfg["buf"] > 0 else pred_low
            else:
                entry_price = pred_high * (1 + cfg["buf"] / 100) if cfg["buf"] > 0 else pred_high

            # Find trigger
            if cfg["open"]:
                walk_start = 0
            else:
                trigger_idx = -1
                for sc_i, sc in enumerate(first_subs):
                    if side == "LONG" and sc["l"] <= entry_price:
                        trigger_idx = sc_i
                        break
                    if side == "SHORT" and sc["h"] >= entry_price:
                        trigger_idx = sc_i
                        break
                if trigger_idx < 0:
                    continue
                walk_start = trigger_idx + 1

            # Walk and record ALL levels
            level_min = {}

            # Fixed TP/SL levels
            for tp in _COMBO_TP_FIXED:
                if side == "LONG":
                    level_min[f"TP_{tp}"] = None
                    tp_price = entry_price * (1 + tp / 100)
                else:
                    level_min[f"TP_{tp}"] = None
                    tp_price = entry_price * (1 - tp / 100)
                for sc_i in range(walk_start, min(len(all_subs), walk_start + max_walk)):
                    sc = all_subs[sc_i]
                    if side == "LONG" and sc["h"] >= tp_price:
                        level_min[f"TP_{tp}"] = sc_i - walk_start
                        break
                    if side == "SHORT" and sc["l"] <= tp_price:
                        level_min[f"TP_{tp}"] = sc_i - walk_start
                        break

            for sl in _COMBO_SL_FIXED:
                if side == "LONG":
                    sl_price = entry_price * (1 - sl / 100)
                else:
                    sl_price = entry_price * (1 + sl / 100)
                level_min[f"SL_{sl}"] = None
                for sc_i in range(walk_start, min(len(all_subs), walk_start + max_walk)):
                    sc = all_subs[sc_i]
                    if side == "LONG" and sc["l"] <= sl_price:
                        level_min[f"SL_{sl}"] = sc_i - walk_start
                        break
                    if side == "SHORT" and sc["h"] >= sl_price:
                        level_min[f"SL_{sl}"] = sc_i - walk_start
                        break

            # Dynamic targets
            for dyn_name, dyn_price, dyn_dir in [
                ("pred_high", pred_high, "above"),
                ("pred_low", pred_low, "below"),
                ("pred_close", pred_close, "either"),
            ]:
                level_min[dyn_name] = None
                for sc_i in range(walk_start, min(len(all_subs), walk_start + max_walk)):
                    sc = all_subs[sc_i]
                    hit = False
                    if dyn_dir == "above" and sc["h"] >= dyn_price:
                        hit = True
                    elif dyn_dir == "below" and sc["l"] <= dyn_price:
                        hit = True
                    elif dyn_dir == "either" and sc["l"] <= dyn_price <= sc["h"]:
                        hit = True
                    if hit:
                        level_min[dyn_name] = sc_i - walk_start
                        break

            # Dynamic TP distances (actual %)
            dyn_distances = {}
            if side == "LONG":
                dyn_distances["pred_high"] = round((pred_high - entry_price) / entry_price * 100, 4) if entry_price > 0 else 0
                dyn_distances["pred_close"] = round((pred_close - entry_price) / entry_price * 100, 4) if entry_price > 0 else 0
            else:
                dyn_distances["pred_low"] = round((entry_price - pred_low) / entry_price * 100, 4) if entry_price > 0 else 0
                dyn_distances["pred_close"] = round((entry_price - pred_close) / entry_price * 100, 4) if entry_price > 0 else 0

            # DCA entry levels
            for dca_pct in _COMBO_DCA:
                if dca_pct > 0:
                    if side == "LONG":
                        dca_price = entry_price * (1 - dca_pct / 100)
                    else:
                        dca_price = entry_price * (1 + dca_pct / 100)
                    dca_min = None
                    for sc_i in range(walk_start, min(len(all_subs), walk_start + max_walk)):
                        sc = all_subs[sc_i]
                        if side == "LONG" and sc["l"] <= dca_price:
                            dca_min = sc_i - walk_start
                            break
                        if side == "SHORT" and sc["h"] >= dca_price:
                            dca_min = sc_i - walk_start
                            break
                    level_min[f"DCA_{dca_pct}"] = dca_min

            all_trades[cfg["name"]].append((
                candle_time, entry_price, pred_high, pred_low, pred_close,
                level_min, hour_utc, date_str, dyn_distances,
            ))

    _log(f"  🔬 Phase 1 done. Pre-computed {sum(len(v) for v in all_trades.values())} trade records")

    # ═══════════════════════════════════════════
    # PHASE 2: Grid search all combos
    # ═══════════════════════════════════════════

    # Build TP configs: fixed + dynamic
    tp_configs = []
    for tp_pct in _COMBO_TP_FIXED:
        tp_configs.append({"name": f"TP_{tp_pct}", "type": "fixed", "pct": tp_pct})
    tp_configs.append({"name": "pred_high", "type": "dynamic", "pct": 0})
    tp_configs.append({"name": "pred_low", "type": "dynamic", "pct": 0})
    tp_configs.append({"name": "pred_close", "type": "dynamic", "pct": 0})

    sl_configs = [{"name": f"SL_{sl}", "pct": sl} for sl in _COMBO_SL_FIXED]
    hold_configs = [
        {"name": "short", "max_min": half_hold_min.get(timeframe, 120)},
        {"name": "long", "max_min": full_hold_min.get(timeframe, 480)},
    ]

    results = []
    total_combos = len(entry_cfgs) * len(tp_configs) * len(sl_configs) * len(_COMBO_DCA) * len(hold_configs)
    checked = 0

    _log(f"  🔬 Phase 2: testing {total_combos} combos...")

    for cfg in entry_cfgs:
        trades = all_trades[cfg["name"]]
        if len(trades) < 30:
            checked += len(tp_configs) * len(sl_configs) * len(_COMBO_DCA) * len(hold_configs)
            continue

        side = cfg["side"]

        # Filter valid dynamic TPs for this side
        valid_tp = []
        for tp_cfg in tp_configs:
            if tp_cfg["type"] == "dynamic":
                if side == "LONG" and tp_cfg["name"] in ("pred_high", "pred_close"):
                    valid_tp.append(tp_cfg)
                elif side == "SHORT" and tp_cfg["name"] in ("pred_low", "pred_close"):
                    valid_tp.append(tp_cfg)
            else:
                valid_tp.append(tp_cfg)

        for tp_cfg in valid_tp:
            tp_name = tp_cfg["name"]
            tp_type = tp_cfg["type"]

            for sl_cfg in sl_configs:
                sl_name = sl_cfg["name"]
                sl_pct = sl_cfg["pct"]

                for dca_pct in _COMBO_DCA:

                    for hold_cfg in hold_configs:
                        hold_max = hold_cfg["max_min"]
                        checked += 1

                        # ── Evaluate all trades ──
                        wins = 0
                        losses = 0
                        expired = 0
                        tp_distances = []
                        daily_pnl = defaultdict(float)
                        hour_stats = defaultdict(lambda: {"w": 0, "l": 0})

                        for trade in trades:
                            ct, ep, ph, pl, pc, lm, hour, date, dyn_dist = trade

                            tp_min = lm.get(tp_name)
                            sl_min = lm.get(sl_name)

                            # Apply hold limit
                            tp_in = tp_min is not None and tp_min <= hold_max
                            sl_in = sl_min is not None and sl_min <= hold_max

                            # DCA adjustment: if DCA triggered, recalculate TP min
                            # Simplified: DCA gives better avg entry, TP more likely
                            dca_triggered = False
                            if dca_pct > 0:
                                dca_min = lm.get(f"DCA_{dca_pct}")
                                if dca_min is not None and dca_min <= hold_max:
                                    dca_triggered = True
                                    # DCA triggered before TP → avg entry better
                                    # Check if TP hits AFTER DCA
                                    if tp_min is not None and tp_min > dca_min:
                                        tp_in = True  # more likely with better entry

                            # Determine outcome
                            if tp_in and (not sl_in or tp_min < sl_min):
                                win = True
                            elif sl_in and (not tp_in or sl_min <= tp_min):
                                win = False
                            else:
                                win = False  # expired = loss (fee)
                                expired += 1

                            # Compute profit
                            if tp_type == "fixed":
                                tp_dist = tp_cfg["pct"]
                            else:
                                tp_dist = dyn_dist.get(tp_name, 0)
                                if tp_dist <= 0:
                                    tp_dist = 0.1  # fallback

                            if win:
                                wins += 1
                                pnl_pct = tp_dist - _COMBO_FEE
                            else:
                                losses += 1
                                pnl_pct = -(sl_pct + _COMBO_FEE)

                            tp_distances.append(tp_dist)
                            pnl_dollar = pnl_pct / 100 * position_size
                            daily_pnl[date] += pnl_dollar
                            hour_stats[hour]["w" if win else "l"] += 1

                        total = wins + losses
                        if total < 30:
                            continue

                        wr = round(wins / total * 100, 1)
                        avg_tp_dist = round(sum(tp_distances) / len(tp_distances), 3) if tp_distances else 0

                        # EV
                        if tp_type == "fixed":
                            ev = round((wr / 100 * (tp_cfg["pct"] - _COMBO_FEE)) - ((1 - wr / 100) * (sl_pct + _COMBO_FEE)), 4)
                        else:
                            ev = round((wr / 100 * (avg_tp_dist - _COMBO_FEE)) - ((1 - wr / 100) * (sl_pct + _COMBO_FEE)), 4)

                        if ev <= 0:
                            continue  # skip EV negative

                        ratio = round((avg_tp_dist if tp_type == "dynamic" else tp_cfg["pct"]) / sl_pct, 2)
                        total_profit = round(ev * total * position_size / 100, 2)

                        # Daily cap simulation
                        cap_days = 0
                        cap_profit = 0
                        loss_days = 0
                        for date, pnl in daily_pnl.items():
                            capped = min(pnl, daily_cap)
                            cap_profit += capped
                            if pnl >= daily_cap:
                                cap_days += 1
                            if pnl < 0:
                                loss_days += 1

                        total_days = len(daily_pnl)
                        avg_daily = round(cap_profit / total_days, 2) if total_days > 0 else 0
                        hit_cap_pct = round(cap_days / total_days * 100, 1) if total_days > 0 else 0

                        # Consistency
                        week_buckets = defaultdict(lambda: {"w": 0, "l": 0})
                        for trade in trades:
                            wk = int(trade[0] // (7 * 86400000))
                            # simplified: use overall win/loss
                        # Use daily_pnl for weekly
                        weekly_profits = defaultdict(float)
                        for date, pnl in daily_pnl.items():
                            # week number
                            from datetime import datetime as dt2
                            d = dt2.strptime(date, "%Y-%m-%d")
                            wk = d.isocalendar()[1] + d.year * 100
                            weekly_profits[wk] += min(pnl, daily_cap)

                        profitable_weeks = sum(1 for v in weekly_profits.values() if v > 0)
                        consistency = round(profitable_weeks / len(weekly_profits) * 100, 1) if weekly_profits else 0

                        # Per-hour best
                        best_hours = []
                        for h, st in sorted(hour_stats.items()):
                            tot_h = st["w"] + st["l"]
                            if tot_h >= 5:
                                wr_h = round(st["w"] / tot_h * 100, 1)
                                if wr_h >= 60:
                                    best_hours.append({"hour": h, "wr": wr_h, "trades": tot_h})

                        results.append({
                            "entry": cfg["name"], "side": side,
                            "tp_name": tp_name, "tp_type": tp_type,
                            "tp_pct": tp_cfg["pct"] if tp_type == "fixed" else avg_tp_dist,
                            "sl_pct": sl_pct,
                            "dca": dca_pct,
                            "hold": hold_cfg["name"],
                            "wr": wr, "ev_per_trade": ev,
                            "ratio": ratio,
                            "trades": total, "expired": expired,
                            "total_profit": total_profit,
                            "avg_daily_capped": avg_daily,
                            "hit_cap_pct": hit_cap_pct,
                            "loss_days_pct": round(loss_days / total_days * 100, 1) if total_days > 0 else 0,
                            "consistency": consistency,
                            "best_hours": best_hours[:5],
                            "avg_tp_distance": avg_tp_dist if tp_type == "dynamic" else tp_cfg["pct"],
                        })

        if checked % 500 == 0:
            _log(f"  🔬 {checked}/{total_combos} combos checked, {len(results)} EV+ found")

    # ═══════════════════════════════════════════
    # PHASE 3: Rank and output
    # ═══════════════════════════════════════════
    results.sort(key=lambda x: x["total_profit"], reverse=True)

    _log(f"  🔬 Combo sweep done: {len(results)} profitable combos from {checked} tested")

    output = {
        "status": "ok",
        "symbol": symbol, "timeframe": timeframe,
        "total_combos_tested": checked,
        "profitable_combos": len(results),
        "top_50": results[:50],
        "top_by_ev": sorted(results, key=lambda x: x["ev_per_trade"], reverse=True)[:20],
        "top_by_wr": sorted(results, key=lambda x: x["wr"], reverse=True)[:20],
        "top_by_daily": sorted(results, key=lambda x: x["avg_daily_capped"], reverse=True)[:20],
        "top_by_consistency": sorted(results, key=lambda x: x["consistency"], reverse=True)[:20],
    }

    if save_to_d1:
        _save_combo_results(symbol, timeframe, results[:100])

    return output


def _save_combo_results(symbol, timeframe, results):
    """Save combo sweep results to D1."""
    try:
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "results": [{
                "entry": r["entry"], "side": r["side"],
                "tp_name": r["tp_name"], "tp_type": r["tp_type"],
                "tp_pct": r["tp_pct"], "sl_pct": r["sl_pct"],
                "dca": r["dca"], "hold": r["hold"],
                "wr": r["wr"], "ev": r["ev_per_trade"],
                "ratio": r["ratio"], "trades": r["trades"],
                "total_profit": r["total_profit"],
                "avg_daily": r["avg_daily_capped"],
                "consistency": r["consistency"],
            } for r in results],
        }
        resp = requests.post(f"{WORKER_URL}/tick/save-combo-results", json=payload, timeout=30)
        if resp.ok:
            _log(f"  💾 Combo results saved: {symbol} {timeframe} ({len(results)} strategies)")
    except Exception as ex:
        _log(f"  ⚠️ Combo save error: {str(ex)[:100]}")



# ════════════════════════════════════════════════════════════
# REGIME DETECTION — Using Deret Statistik Ratios (V19)
# ════════════════════════════════════════════════════════════

def _detect_regime(high_ratios, low_ratios, i, regime_window=3):
    """
    Detect market regime from Deret Statistik ratios.
    avg_ratio > 1.0 = price trending UP, < 1.0 = trending DOWN.
    Returns: (regime_str, strength_bps)
    """
    if i < regime_window:
        return "UNKNOWN", 0

    h_slice = high_ratios[i - regime_window:i]
    l_slice = low_ratios[i - regime_window:i]

    if not h_slice or not l_slice:
        return "UNKNOWN", 0

    avg_h = sum(h_slice) / len(h_slice)
    avg_l = sum(l_slice) / len(l_slice)

    h_bull = avg_h > 1.0
    l_bull = avg_l > 1.0

    h_strength = (avg_h - 1.0) * 10000
    l_strength = (avg_l - 1.0) * 10000
    avg_strength = (h_strength + l_strength) / 2

    if h_bull and l_bull:
        regime = "BULL"
    elif not h_bull and not l_bull:
        regime = "BEAR"
    else:
        regime = "SIDEWAYS"

    if regime != "SIDEWAYS" and abs(avg_strength) > 30:
        regime = f"STRONG_{regime}"

    return regime, round(avg_strength, 1)


def _get_adaptive_params(regime, strength, side):
    """
    Return adaptive overrides based on regime + trade side.
    Returns dict with entry/tp/sl overrides, or skip=True.

    STRONG_BULL + LONG  -> entry=open, TP=pred_high, SL=pred_close (ride trend)
    STRONG_BULL + SHORT -> SKIP
    BULL + LONG         -> TP=pred_close, SL=0.7%
    BULL + SHORT        -> SKIP
    SIDEWAYS            -> SL=0.5%, TP=0.5%
    BEAR + LONG         -> SKIP
    BEAR + SHORT        -> TP=pred_close, SL=0.7%
    STRONG_BEAR + SHORT -> entry=open, TP=pred_low, SL=pred_close
    STRONG_BEAR + LONG  -> SKIP
    """
    result = {
        "entry_override": None,
        "tp_override": None,
        "sl_override": None,
        "sl_use_pred_close": False,
        "skip": False,
        "regime": regime,
        "strength": strength,
    }

    if regime == "STRONG_BULL":
        if side == "LONG":
            result["entry_override"] = "open"
            result["tp_override"] = "pred_high"
            result["sl_use_pred_close"] = True
        else:
            result["skip"] = True

    elif regime == "BULL":
        if side == "LONG":
            result["tp_override"] = "pred_close"
            result["sl_override"] = 0.7
        else:
            result["skip"] = True

    elif regime == "STRONG_BEAR":
        if side == "SHORT":
            result["entry_override"] = "open"
            result["tp_override"] = "pred_low"
            result["sl_use_pred_close"] = True
        else:
            result["skip"] = True

    elif regime == "BEAR":
        if side == "SHORT":
            result["tp_override"] = "pred_close"
            result["sl_override"] = 0.7
        else:
            result["skip"] = True

    else:  # SIDEWAYS / UNKNOWN
        result["sl_override"] = 0.5
        result["tp_override"] = "0.5"

    return result


def custom_backtest(symbol, timeframe, config, window=10, days=1825):
    """
    Custom backtest — V19 with regime detection.

    New config keys:
      regime_mode:   null | "filter" | "adaptive"
      regime_window: 3 (default, lookback candles for regime)

    regime_mode=None    -> identical to V18 behavior (backward compatible)
    regime_mode="filter" -> skip counter-trend trades only
    regime_mode="adaptive" -> full adaptive entry/TP/SL per regime
    """
    _log(f"  🧪 Custom backtest: {symbol} {timeframe} — {config}")

    rows, sub_lookup = _load_data(DB_PATH, symbol, timeframe)
    if not rows or len(rows) < window + 20:
        return {"status": "error", "message": "Insufficient data"}

    n = len(rows)
    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]

    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]

    tf_ms = {"1m": 60000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)
    max_hold_map = {"15m": 120, "1h": 240, "4h": 480}
    max_walk = max_hold_map.get(timeframe, 480)

    # Parse config (original values — may be overridden per-candle by regime)
    entry_type_orig = str(config.get("entry", "open"))
    side_orig = config.get("entry_side", "LONG")
    tp_config_orig = str(config.get("tp", "0.5"))
    sl_pct_orig = float(config.get("sl", "0.3"))
    dca_pct = float(config.get("dca", 0)) if config.get("dca") else 0
    range_filter = float(config.get("range_filter", 0))
    daily_cap = float(config.get("daily_cap", 5.0))
    position_size = float(config.get("position_size", 500))
    fee = 0.07
    only_first = config.get("only_first", False)

    # [V19] Regime config
    regime_mode = config.get("regime_mode", None)
    regime_window = int(config.get("regime_window", 3))
    regime_stats = defaultdict(lambda: {"trades": 0, "wins": 0, "skipped": 0})

    # Determine if TP is fixed or dynamic (original — may change per candle)
    tp_is_dynamic_orig = tp_config_orig in ("pred_high", "pred_low", "pred_close")
    tp_pct_fixed_orig = 0 if tp_is_dynamic_orig else float(tp_config_orig)

    # Conditional entry flags (original)
    conditional_entry_orig = entry_type_orig in ("pred_high", "pred_low", "pred_close")

    # Parse buffer entries like "pred_low_buf_2.0"
    buf_entry_orig = False
    buf_pct_orig = 0
    entry_base_orig = ""
    if entry_type_orig.startswith("pred_low_buf_"):
        buf_entry_orig = True
        buf_pct_orig = float(entry_type_orig.split("_")[-1])
        entry_base_orig = "pred_low"
    elif entry_type_orig.startswith("pred_high_buf_"):
        buf_entry_orig = True
        buf_pct_orig = float(entry_type_orig.split("_")[-1])
        entry_base_orig = "pred_high"

    # Limit by days
    start_idx = window
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        for ri in range(len(rows)):
            if rows[ri][5] >= last_time - ms_limit:
                start_idx = max(window, ri)
                break

    # ═══ WALK CANDLES ═══
    trades = []
    skipped_range = 0

    for i in range(start_idx, len(close_ratios)):
        if i + 1 >= n:
            break

        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        pred_high = highs[i] * avg_h
        pred_low  = lows[i] * avg_l
        pred_close = closes[i] * avg_c

        next_idx = i + 1
        candle_time = times[next_idx]
        candle_open = opens[next_idx]

        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        hour_utc = dt.hour
        date_str = dt.strftime("%Y-%m-%d")

        # ═══ [V19] REGIME DETECTION — per-candle override ═══
        # Reset to original config each candle
        entry_type = entry_type_orig
        side = side_orig
        tp_config = tp_config_orig
        sl_pct = sl_pct_orig
        tp_is_dynamic = tp_is_dynamic_orig
        tp_pct_fixed = tp_pct_fixed_orig
        conditional_entry = conditional_entry_orig
        buf_entry = buf_entry_orig
        buf_pct = buf_pct_orig
        entry_base = entry_base_orig
        adaptive = None
        regime = "UNKNOWN"
        strength = 0

        if regime_mode in ("filter", "adaptive"):
            regime, strength = _detect_regime(high_ratios, low_ratios, i, regime_window)
            regime_stats[regime]["trades"] += 1

            if regime_mode == "adaptive":
                adaptive = _get_adaptive_params(regime, strength, side)

                if adaptive["skip"]:
                    regime_stats[regime]["skipped"] += 1
                    continue

                # Override entry type
                if adaptive["entry_override"]:
                    entry_type = adaptive["entry_override"]
                    conditional_entry = entry_type in ("pred_high", "pred_low", "pred_close")
                    buf_entry = False
                    buf_pct = 0
                    entry_base = ""

                # Override TP
                if adaptive["tp_override"]:
                    tp_config = adaptive["tp_override"]
                    tp_is_dynamic = tp_config in ("pred_high", "pred_low", "pred_close")
                    tp_pct_fixed = 0 if tp_is_dynamic else float(tp_config)

                # Override SL
                if adaptive["sl_override"]:
                    sl_pct = adaptive["sl_override"]

            elif regime_mode == "filter":
                # Simple: skip counter-trend only
                if regime in ("STRONG_BULL", "BULL") and side == "SHORT":
                    regime_stats[regime]["skipped"] += 1
                    continue
                if regime in ("STRONG_BEAR", "BEAR") and side == "LONG":
                    regime_stats[regime]["skipped"] += 1
                    continue

        # Range filter
        if range_filter > 0:
            pred_range = (pred_high - pred_low) / pred_low * 100 if pred_low > 0 else 0
            if pred_range < range_filter:
                skipped_range += 1
                continue

        # Flatten 1m subs (multiple candles for hold)
        max_hold_candles = {"15m": 8, "1h": 4, "4h": 2}.get(timeframe, 2)
        first_parent_ts = (candle_time // parent_ms) * parent_ms
        first_subs = sub_lookup.get(first_parent_ts, [])
        if not first_subs:
            continue

        all_subs = list(first_subs)
        for k in range(1, max_hold_candles):
            ci = next_idx + k
            if ci >= n:
                break
            pts = (times[ci] // parent_ms) * parent_ms
            s = sub_lookup.get(pts, [])
            all_subs.extend(s)

        # ═══ DETERMINE ENTRY PRICE AND TRIGGER ═══
        entry_price = None
        walk_start = 0

        if entry_type == "open":
            entry_price = candle_open
            walk_start = 0

        elif conditional_entry:
            level_prices = {"pred_high": pred_high, "pred_low": pred_low, "pred_close": pred_close}
            target_price = level_prices[entry_type]

            trigger_idx = -1
            for sc_i, sc in enumerate(first_subs):
                if entry_type == "pred_high" and sc["h"] >= target_price:
                    trigger_idx = sc_i
                    break
                elif entry_type == "pred_low" and sc["l"] <= target_price:
                    trigger_idx = sc_i
                    break
                elif entry_type == "pred_close":
                    if sc["l"] <= target_price <= sc["h"]:
                        trigger_idx = sc_i
                        break

            if trigger_idx < 0:
                continue  # level never hit in this candle

            if only_first:
                other_levels = {"pred_high": pred_high, "pred_low": pred_low, "pred_close": pred_close}
                del other_levels[entry_type]
                skip = False
                for ol_name, ol_price in other_levels.items():
                    for sc_j in range(trigger_idx):
                        sc_check = first_subs[sc_j]
                        if ol_name == "pred_high" and sc_check["h"] >= ol_price:
                            skip = True; break
                        elif ol_name == "pred_low" and sc_check["l"] <= ol_price:
                            skip = True; break
                        elif ol_name == "pred_close" and sc_check["l"] <= ol_price <= sc_check["h"]:
                            skip = True; break
                    if skip:
                        break
                if skip:
                    continue

            entry_price = target_price
            walk_start = trigger_idx + 1

        elif buf_entry:
            if entry_base == "pred_low":
                entry_price = pred_low * (1 - buf_pct / 100)
            else:
                entry_price = pred_high * (1 + buf_pct / 100)

            trigger_idx = -1
            for sc_i, sc in enumerate(first_subs):
                if side == "LONG" and sc["l"] <= entry_price:
                    trigger_idx = sc_i
                    break
                if side == "SHORT" and sc["h"] >= entry_price:
                    trigger_idx = sc_i
                    break
            if trigger_idx < 0:
                continue
            walk_start = trigger_idx + 1

        if entry_price is None or entry_price <= 0:
            continue

        # ═══ COMPUTE TP/SL PRICES ═══
        if tp_is_dynamic:
            tp_prices = {"pred_high": pred_high, "pred_low": pred_low, "pred_close": pred_close}
            tp_price = tp_prices[tp_config]
            tp_distance = abs(tp_price - entry_price) / entry_price * 100
        else:
            tp_distance = tp_pct_fixed
            if side == "LONG":
                tp_price = entry_price * (1 + tp_pct_fixed / 100)
            else:
                tp_price = entry_price * (1 - tp_pct_fixed / 100)

        if side == "LONG":
            sl_price = entry_price * (1 - sl_pct / 100)
        else:
            sl_price = entry_price * (1 + sl_pct / 100)

        # ═══ [V19] Override SL to pred_close for strong trend ═══
        if adaptive and adaptive.get("sl_use_pred_close"):
            if side == "LONG" and pred_close < entry_price:
                sl_price = pred_close * 0.999  # tiny buffer below
                sl_pct = abs(entry_price - sl_price) / entry_price * 100
            elif side == "SHORT" and pred_close > entry_price:
                sl_price = pred_close * 1.001  # tiny buffer above
                sl_pct = abs(sl_price - entry_price) / entry_price * 100

        # DCA price
        dca_price = None
        if dca_pct > 0:
            if side == "LONG":
                dca_price = entry_price * (1 - dca_pct / 100)
            else:
                dca_price = entry_price * (1 + dca_pct / 100)

        # ═══ WALK 1M SUBS — DETERMINE OUTCOME ═══
        result = None
        dca_triggered = False
        active_entry = entry_price

        for sc_i in range(walk_start, min(len(all_subs), walk_start + max_walk)):
            sc = all_subs[sc_i]
            minute = sc_i - walk_start

            # Check DCA trigger
            if dca_price and not dca_triggered:
                if side == "LONG" and sc["l"] <= dca_price:
                    dca_triggered = True
                    active_entry = (entry_price + dca_price) / 2
                    if not tp_is_dynamic:
                        tp_price = active_entry * (1 + tp_pct_fixed / 100) if side == "LONG" else active_entry * (1 - tp_pct_fixed / 100)
                elif side == "SHORT" and sc["h"] >= dca_price:
                    dca_triggered = True
                    active_entry = (entry_price + dca_price) / 2
                    if not tp_is_dynamic:
                        tp_price = active_entry * (1 - tp_pct_fixed / 100) if side == "SHORT" else active_entry * (1 + tp_pct_fixed / 100)

            # Check TP
            tp_hit = False
            if side == "LONG" and sc["h"] >= tp_price:
                tp_hit = True
            elif side == "SHORT" and sc["l"] <= tp_price:
                tp_hit = True

            # Check SL
            sl_hit = False
            if side == "LONG" and sc["l"] <= sl_price:
                sl_hit = True
            elif side == "SHORT" and sc["h"] >= sl_price:
                sl_hit = True

            if tp_hit and sl_hit:
                result = "win"  # same minute = assume TP first
                break
            elif tp_hit:
                result = "win"
                break
            elif sl_hit:
                result = "loss"
                break

        if result is None:
            result = "expired"

        # Compute PnL
        if result == "win":
            pnl_pct = tp_distance - fee
            if dca_triggered:
                pnl_pct = pnl_pct * 1.0  # simplified
        elif result == "loss":
            pnl_pct = -(sl_pct + fee)
            if dca_triggered:
                pnl_pct = pnl_pct * 2
        else:
            pnl_pct = -fee

        pnl_dollar = pnl_pct / 100 * position_size
        if dca_triggered and result == "win":
            pnl_dollar = pnl_dollar * 2

        trades.append({
            "date": date_str, "hour": hour_utc,
            "result": result, "pnl_pct": round(pnl_pct, 4),
            "pnl_dollar": round(pnl_dollar, 4),
            "tp_distance": round(tp_distance, 4),
            "dca_triggered": dca_triggered,
            "regime": regime,
            "strength": strength,
        })

        # [V19] Track regime wins
        if regime_mode and result == "win":
            regime_stats[regime]["wins"] += 1

    # ═══ AGGREGATE RESULTS ═══
    total = len(trades)
    if total == 0:
        return {"status": "ok", "message": "No trades triggered", "trades": 0, "skipped_range_filter": skipped_range}

    wins = sum(1 for t in trades if t["result"] == "win")
    losses = sum(1 for t in trades if t["result"] == "loss")
    expired = sum(1 for t in trades if t["result"] == "expired")
    wr = round(wins / total * 100, 1)

    # EV
    avg_win = sum(t["pnl_dollar"] for t in trades if t["result"] == "win") / wins if wins > 0 else 0
    avg_loss = sum(t["pnl_dollar"] for t in trades if t["result"] == "loss") / losses if losses > 0 else 0
    ev_dollar = round((wr / 100 * avg_win) + ((1 - wr / 100) * avg_loss), 4)
    total_pnl = round(sum(t["pnl_dollar"] for t in trades), 2)

    # Daily cap simulation
    daily_pnl = defaultdict(float)
    for t in trades:
        daily_pnl[t["date"]] += t["pnl_dollar"]

    total_days = len(daily_pnl)
    capped_profit = 0
    hit_cap_days = 0
    loss_days = 0
    max_drawdown = 0
    running_pnl = 0
    peak = 0

    for date in sorted(daily_pnl.keys()):
        day_pnl = daily_pnl[date]
        capped = min(day_pnl, daily_cap)
        capped_profit += capped
        if day_pnl >= daily_cap:
            hit_cap_days += 1
        if day_pnl < 0:
            loss_days += 1
        running_pnl += capped
        peak = max(peak, running_pnl)
        dd = peak - running_pnl
        max_drawdown = max(max_drawdown, dd)

    avg_daily = round(capped_profit / total_days, 2) if total_days > 0 else 0

    # Per-hour breakdown
    hour_stats_out = defaultdict(lambda: {"w": 0, "l": 0, "e": 0})
    for t in trades:
        if t["result"] == "win":
            hour_stats_out[t["hour"]]["w"] += 1
        elif t["result"] == "loss":
            hour_stats_out[t["hour"]]["l"] += 1
        else:
            hour_stats_out[t["hour"]]["e"] += 1

    best_hours = []
    worst_hours = []
    for h, st in sorted(hour_stats_out.items()):
        tot = st["w"] + st["l"] + st["e"]
        if tot >= 10:
            hr_wr = round(st["w"] / tot * 100, 1)
            entry = {"hour": h, "wr": hr_wr, "trades": tot}
            if hr_wr >= 60:
                best_hours.append(entry)
            elif hr_wr < 40:
                worst_hours.append(entry)

    # DCA stats
    dca_count = sum(1 for t in trades if t["dca_triggered"])
    dca_pct_actual = round(dca_count / total * 100, 1) if total > 0 else 0

    # TP distance distribution
    tp_dists = [t["tp_distance"] for t in trades]
    tp_dist_avg = round(sum(tp_dists) / len(tp_dists), 4) if tp_dists else 0

    # Weekly consistency
    weekly = defaultdict(float)
    for t in trades:
        d = datetime.strptime(t["date"], "%Y-%m-%d")
        wk = f"{d.year}-W{d.isocalendar()[1]}"
        weekly[wk] += t["pnl_dollar"]
    profitable_weeks = sum(1 for v in weekly.values() if v > 0)
    consistency = round(profitable_weeks / len(weekly) * 100, 1) if weekly else 0

    result = {
        "status": "ok",
        "symbol": symbol, "timeframe": timeframe,
        "config": config,
        "summary": {
            "trades": total, "wins": wins, "losses": losses, "expired": expired,
            "wr": wr,
            "ev_per_trade_dollar": ev_dollar,
            "ev_per_trade_pct": round(ev_dollar / position_size * 100, 4),
            "total_pnl": total_pnl,
            "total_pnl_capped": round(capped_profit, 2),
            "avg_daily_capped": avg_daily,
            "hit_cap_pct": round(hit_cap_days / total_days * 100, 1) if total_days > 0 else 0,
            "loss_days_pct": round(loss_days / total_days * 100, 1) if total_days > 0 else 0,
            "max_drawdown": round(max_drawdown, 2),
            "consistency": consistency,
            "avg_tp_distance": tp_dist_avg,
            "dca_trigger_pct": dca_pct_actual,
            "skipped_range_filter": skipped_range,
        },
        "best_hours": sorted(best_hours, key=lambda x: -x["wr"])[:5],
        "worst_hours": sorted(worst_hours, key=lambda x: x["wr"])[:3],
    }

    # ═══ [V19] Regime breakdown in output ═══
    if regime_mode:
        regime_breakdown = {}
        for rg, st in regime_stats.items():
            t = st["trades"]
            w = st["wins"]
            sk = st["skipped"]
            traded = t - sk
            regime_breakdown[rg] = {
                "candles": t,
                "skipped": sk,
                "traded": traded,
                "wins": w,
                "wr": round(w / traded * 100, 1) if traded > 0 else 0,
            }
        result["regime_mode"] = regime_mode
        result["regime_window"] = regime_window
        result["regime_breakdown"] = regime_breakdown

    _log(f"  🧪 Result: {total} trades, WR={wr}%, EV=${ev_dollar}/trade, ${avg_daily}/day capped"
         + (f" | regime={regime_mode}" if regime_mode else ""))
    return result


# INTERNAL HELPERS
# ════════════════════════════════════════════════════════════

def _load_data(db_path: str, symbol: str, timeframe: str, sub_candle_tf: str = "1m"):
    """Load parent klines + 1m sub-candle data from SQLite."""
    from collections import defaultdict
    
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    
    rows = conn.execute("""
        SELECT open, high, low, close, volume, open_time 
        FROM klines WHERE symbol = ? AND timeframe = ?
        ORDER BY open_time ASC
    """, (symbol, timeframe)).fetchall()
    
    sub_candle_lookup = {}
    if sub_candle_tf:
        sub_rows = conn.execute("""
            SELECT open, high, low, close, open_time 
            FROM klines WHERE symbol = ? AND timeframe = ?
            ORDER BY open_time ASC
        """, (symbol, sub_candle_tf)).fetchall()
        
        tf_ms_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000}
        parent_ms = tf_ms_map.get(timeframe, 3600000)
        
        sub_groups = defaultdict(list)
        for sr in sub_rows:
            parent_ts = (sr[4] // parent_ms) * parent_ms
            sub_groups[parent_ts].append({"o": sr[0], "h": sr[1], "l": sr[2], "c": sr[3], "ts": sr[4]})
        sub_candle_lookup = dict(sub_groups)
    
    conn.close()
    return rows, sub_candle_lookup


def _extract_events_raw(
    symbol, timeframe, window, buffer_pct, tp_pct, sl_pct,
    days, sub_candle_tf, db_path=None, buffer2_pct=1.0,
    _preloaded_rows=None, _preloaded_sub_candles=None,
) -> list:
    """Internal: extract events and return full list (for stats analysis)."""
    db_path = db_path or DB_PATH
    
    if _preloaded_rows is not None:
        rows = _preloaded_rows
        sub_candle_lookup = _preloaded_sub_candles or {}
    else:
        rows, sub_candle_lookup = _load_data(db_path, symbol, timeframe, sub_candle_tf)
    
    if len(rows) < window + 10:
        return []
    
    if days and days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows[-1][5]
        rows = [r for r in rows if r[5] >= last_time - ms_limit]
    
    n = len(rows)
    if n < window + 10:
        return []
    
    opens  = [r[0] for r in rows]
    highs  = [r[1] for r in rows]
    lows   = [r[2] for r in rows]
    closes = [r[3] for r in rows]
    times  = [r[5] for r in rows]
    
    close_ratios = [closes[i] / closes[i-1] if closes[i-1] != 0 else 1.0 for i in range(1, n)]
    high_ratios  = [highs[i] / highs[i-1] if highs[i-1] != 0 else 1.0 for i in range(1, n)]
    low_ratios   = [lows[i] / lows[i-1] if lows[i-1] != 0 else 1.0 for i in range(1, n)]
    
    tf_ms_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms_map.get(timeframe, 3600000)
    
    events_list = []
    
    for i in range(window, len(close_ratios)):
        if i + 1 >= n:
            break
        
        avg_h = sum(high_ratios[i-window:i]) / window
        avg_l = sum(low_ratios[i-window:i]) / window
        avg_c = sum(close_ratios[i-window:i]) / window
        
        pred_high  = highs[i] * avg_h
        pred_low   = lows[i] * avg_l
        pred_close = closes[i] * avg_c
        
        entry_long   = pred_low * (1 - buffer_pct / 100)
        entry_short  = pred_high * (1 + buffer_pct / 100)
        tp_long_price = entry_long * (1 + tp_pct / 100)
        tp_short_price = entry_short * (1 - tp_pct / 100)
        sl_long_price  = entry_long * (1 - sl_pct / 100)
        sl_short_price = entry_short * (1 + sl_pct / 100)
        entry_long_L2  = entry_long * (1 - buffer2_pct / 100)
        entry_short_L2 = entry_short * (1 + buffer2_pct / 100)
        
        next_idx = i + 1
        candle_time = times[next_idx]
        parent_ts = (candle_time // parent_ms) * parent_ms
        sub_candles = sub_candle_lookup.get(parent_ts, [])
        
        if not sub_candles:
            continue
        
        levels = {
            "pred_high":     {"price": pred_high,      "dir": "above", "min": None},
            "pred_low":      {"price": pred_low,       "dir": "below", "min": None},
            "entry_long":    {"price": entry_long,     "dir": "below", "min": None},
            "entry_short":   {"price": entry_short,    "dir": "above", "min": None},
            "tp_long":       {"price": tp_long_price,  "dir": "above", "min": None},
            "tp_short":      {"price": tp_short_price, "dir": "below", "min": None},
            "sl_long":       {"price": sl_long_price,  "dir": "below", "min": None},
            "sl_short":      {"price": sl_short_price, "dir": "above", "min": None},
            "entry_long_L2": {"price": entry_long_L2,  "dir": "below", "min": None},
            "entry_short_L2":{"price": entry_short_L2, "dir": "above", "min": None},
        }
        
        for sc_idx, sc in enumerate(sub_candles):
            for level_name, level_info in levels.items():
                if level_info["min"] is not None:
                    continue
                hit = False
                if level_info["dir"] == "above" and sc["h"] >= level_info["price"]:
                    hit = True
                elif level_info["dir"] == "below" and sc["l"] <= level_info["price"]:
                    hit = True
                if hit:
                    level_info["min"] = sc_idx
        
        hit_events = [(v["min"], k) for k, v in levels.items() if v["min"] is not None]
        hit_events.sort()
        sequence = "→".join(e[1] for e in hit_events) if hit_events else "NONE"
        
        min_ph = levels["pred_high"]["min"]
        min_pl = levels["pred_low"]["min"]
        if min_ph is not None and min_pl is not None:
            first_extreme = "HIGH" if min_ph < min_pl else ("LOW" if min_pl < min_ph else "SAME")
            first_extreme_min = min(min_ph, min_pl)
        elif min_ph is not None:
            first_extreme, first_extreme_min = "HIGH", min_ph
        elif min_pl is not None:
            first_extreme, first_extreme_min = "LOW", min_pl
        else:
            first_extreme, first_extreme_min = "NONE", None
        
        prev_direction = "bullish" if closes[i] > opens[i] else ("bearish" if closes[i] < opens[i] else "doji")
        prev_range_pct = round((highs[i] - lows[i]) / opens[i] * 100, 4) if opens[i] > 0 else 0
        
        dt = datetime.fromtimestamp(candle_time / 1000, tz=timezone.utc)
        
        events_list.append({
            "symbol": symbol, "timeframe": timeframe,
            "candle_time": candle_time,
            "candle_hour_utc": dt.hour, "candle_dow": dt.weekday(),
            "pred_high": round(pred_high, 6), "pred_low": round(pred_low, 6),
            "pred_close": round(pred_close, 6),
            "first_extreme": first_extreme, "first_extreme_min": first_extreme_min,
            "min_pred_high": levels["pred_high"]["min"],
            "min_pred_low": levels["pred_low"]["min"],
            "min_entry_long": levels["entry_long"]["min"],
            "min_entry_short": levels["entry_short"]["min"],
            "min_tp_long": levels["tp_long"]["min"],
            "min_tp_short": levels["tp_short"]["min"],
            "min_sl_long": levels["sl_long"]["min"],
            "min_sl_short": levels["sl_short"]["min"],
            "min_entry_long_L2": levels["entry_long_L2"]["min"],
            "min_entry_short_L2": levels["entry_short_L2"]["min"],
            "sequence": sequence,
            "prev_direction": prev_direction, "prev_range_pct": prev_range_pct,
            "window": window, "buffer_pct": buffer_pct,
            "buffer2_pct": buffer2_pct, "tp_pct": tp_pct, "sl_pct": sl_pct,
        })
    
    return events_list


def _save_events_to_d1(events: list, batch_size: int = 100) -> int:
    """Save tick events to D1 via Workers API in batches."""
    saved = 0
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        try:
            resp = requests.post(
                f"{WORKER_URL}/tick/save-events",
                json={"events": batch},
                timeout=30,
            )
            if resp.ok:
                data = resp.json()
                saved += data.get("saved", len(batch))
            else:
                _log(f"⚠️ D1 save batch failed: {resp.status_code}")
        except Exception as ex:
            _log(f"⚠️ D1 save error: {str(ex)}")
    return saved


def _save_stats_to_d1(symbol: str, timeframe: str, stats: dict):
    """Save stats summary to D1 (optional, for dashboard caching)."""
    try:
        requests.post(
            f"{WORKER_URL}/tick/save-stats",
            json={"symbol": symbol, "timeframe": timeframe, "stats": stats},
            timeout=15,
        )
    except Exception:
        pass  # Non-critical
