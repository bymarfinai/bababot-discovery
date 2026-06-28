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

        _sweep_status["running"] = False
        _sweep_status["finished_at"] = datetime.now().isoformat()
        _sweep_status["progress"] = "DONE"
        _log(f"🏁 Sweep complete! {_sweep_status['winners']} winners from {_sweep_status['completed_combos']} combos")

    _sweep_thread = threading.Thread(target=_run, daemon=True)
    _sweep_thread.start()

    return {"ok": True, "message": f"Sweep started: {total} combos", "total": total}


def stop_sweep_engine():
    _sweep_status["running"] = False
    return {"ok": True, "message": "Stop signal sent"}


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
        trades.append(trade_result)

        # Sequential constraint
        hold_candles = trade_result.get("hold_candles", 1)
        position_busy_until = i + 1 + hold_candles + 1

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
