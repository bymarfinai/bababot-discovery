"""
tick_discovery.py — Tick-by-Tick Discovery Engine
Phase 1: Event Extraction (walk 1m sub-candles, record level hits)
Phase 2: Statistical Analysis (aggregate patterns per pair × TF × hour)

BabaBot v17 — Clean slate, data-driven strategy discovery
"""

import os
import json
import sqlite3
import logging
import threading
import time
import requests
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
# SWEEP — Run extraction across multiple pairs × TFs
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
