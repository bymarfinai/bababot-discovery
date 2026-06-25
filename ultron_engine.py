"""
Ultron Phase 2 — Decision Engine
Observes live trading analytics, makes autonomous optimization decisions.
Jarvis (via MCP) can review, approve, override, and scold Ultron.

Deployed on Railway alongside baret_live.py.
"""

import os
import time
import threading
import requests as req
from datetime import datetime, timezone, timedelta
from collections import deque

WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")

# ══════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════

_ultron_log = deque(maxlen=200)
_ultron_state = {
    "enabled": True,
    "last_analysis": None,
    "analysis_count": 0,
    "active_decisions": [],    # currently applied decisions
    "skipped_pairs": {},       # symbol -> reason
    "skipped_hours": {},       # "symbol:hour" -> reason
    "buffer_adjustments": {},  # symbol -> delta
    "size_reductions": {},     # symbol -> factor (0.5 = half size)
}

# Cache config from D1 (refreshed every analysis)
_ultron_config_cache = {
    "enabled": True,
    "analyze_every_n_cycles": 4,
    "min_wr_threshold": 70,
    "min_trades_for_decision": 30,
    "bad_hour_wr_threshold": 60,
    "bad_hour_min_trades": 30,
    "max_slippage_pct": 0.05,
    "buffer_adjust_step": 0.1,
    "max_buffer_adjust": 0.2,
    "max_sltp_adjust": 0.2,
    "correlation_threshold": 50,
    "auto_apply_confidence": 70,
    "lookback_days": 7,
}


def _ulog(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] 🧠 {msg}"
    _ultron_log.append(entry)
    print(entry)


# ══════════════════════════════════════════════
# CONFIG — Fetch from D1
# ══════════════════════════════════════════════

def _refresh_config():
    """Pull latest Ultron config from D1 via Workers."""
    global _ultron_config_cache
    try:
        r = req.get(f"{WORKER_URL}/ultron/config", timeout=10)
        data = r.json()
        if data.get("ok") and data.get("config"):
            for k, v in data["config"].items():
                if k in _ultron_config_cache:
                    # Type-cast based on default type
                    default = _ultron_config_cache[k]
                    if isinstance(default, bool):
                        _ultron_config_cache[k] = str(v).lower() in ("true", "1", "yes")
                    elif isinstance(default, int):
                        _ultron_config_cache[k] = int(float(v))
                    elif isinstance(default, float):
                        _ultron_config_cache[k] = float(v)
                    else:
                        _ultron_config_cache[k] = v
            _ulog(f"Config refreshed: {len(data['config'])} keys")
    except Exception as e:
        _ulog(f"Config refresh failed: {e}")


# ══════════════════════════════════════════════
# FETCH ANALYTICS DATA
# ══════════════════════════════════════════════

def _fetch_analytics(period="7d"):
    """Pull analytics summary from Workers."""
    try:
        r = req.get(f"{WORKER_URL}/analytics/summary?period={period}", timeout=15)
        return r.json()
    except Exception as e:
        _ulog(f"Analytics fetch failed: {e}")
        return None


def _fetch_pair_profile(symbol):
    """Pull detailed pair profile from Workers."""
    try:
        r = req.get(f"{WORKER_URL}/analytics/pair-profile?symbol={symbol}", timeout=10)
        return r.json()
    except Exception as e:
        _ulog(f"Pair profile fetch failed for {symbol}: {e}")
        return None


def _fetch_correlation():
    """Pull correlation data from Workers."""
    try:
        r = req.get(f"{WORKER_URL}/analytics/correlation", timeout=10)
        return r.json()
    except Exception as e:
        _ulog(f"Correlation fetch failed: {e}")
        return None


def _fetch_active_decisions():
    """Pull currently active/pending decisions from D1."""
    try:
        r = req.get(f"{WORKER_URL}/ultron/decisions?status=applied,pending", timeout=10)
        data = r.json()
        return data.get("decisions", []) if data.get("ok") else []
    except:
        return []


# ══════════════════════════════════════════════
# SAVE DECISION TO D1
# ══════════════════════════════════════════════

def _save_decision(decision_type, symbol, old_value, new_value, reason,
                   confidence, data_points, hour=None, auto_apply=False):
    """Save an Ultron decision to D1 and optionally auto-apply."""
    status = "applied" if auto_apply and confidence >= _ultron_config_cache["auto_apply_confidence"] else "pending"
    applied_at = datetime.now(timezone.utc).isoformat() if status == "applied" else None

    try:
        r = req.post(f"{WORKER_URL}/ultron/log-decision", json={
            "decision_type": decision_type,
            "symbol": symbol,
            "hour": hour,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "reason": reason,
            "confidence": confidence,
            "data_points": data_points,
            "status": status,
            "applied_at": applied_at,
        }, timeout=10)
        result = r.json()
        _ulog(f"Decision saved: {decision_type} {symbol or 'GLOBAL'} → {new_value} (conf={confidence}, status={status})")
        return result
    except Exception as e:
        _ulog(f"Decision save failed: {e}")
        return None


# ══════════════════════════════════════════════
# ANALYZER — Core decision engine
# ══════════════════════════════════════════════

def ultron_analyze():
    """
    Main Ultron analysis loop. Pulls analytics, generates decisions.
    Called every N cycles from baret_live_loop.
    """
    cfg = _ultron_config_cache
    if not cfg["enabled"]:
        _ulog("Ultron disabled, skipping analysis")
        return

    _refresh_config()
    _ulog("═══ ULTRON ANALYSIS START ═══")

    # 1. Fetch analytics
    period = f"{cfg['lookback_days']}d"
    analytics = _fetch_analytics(period)
    if not analytics or not analytics.get("ok") or analytics.get("total", 0) == 0:
        _ulog("No analytics data available, skipping")
        return

    total_trades = analytics["total"]
    pairs = analytics.get("pairs", [])
    hours = analytics.get("hours", [])
    overall_wr = analytics.get("wr", 0)

    _ulog(f"Data: {total_trades} trades, {len(pairs)} pairs, overall WR={overall_wr}%")

    decisions_made = 0

    # ── 2. Per-pair WR analysis ──
    for pair in pairs:
        symbol = pair["symbol"]
        trades = pair["trades"]
        wr = pair["wr"]
        slippage = pair.get("avg_slippage", 0)

        # 2a. Auto-pause pair if WR too low
        if trades >= cfg["min_trades_for_decision"] and wr < cfg["min_wr_threshold"]:
            confidence = min(95, 50 + (cfg["min_wr_threshold"] - wr) * 3 + trades // 10)
            _save_decision(
                decision_type="pause_pair",
                symbol=symbol,
                old_value=f"WR={wr}%",
                new_value="PAUSED",
                reason=f"Rolling {cfg['lookback_days']}d WR={wr}% < threshold {cfg['min_wr_threshold']}% ({trades} trades)",
                confidence=confidence,
                data_points=trades,
                auto_apply=True,
            )
            _ultron_state["skipped_pairs"][symbol] = f"WR {wr}% < {cfg['min_wr_threshold']}%"
            decisions_made += 1

        # 2b. Adjust buffer if slippage is high
        if trades >= 10 and slippage > cfg["max_slippage_pct"]:
            adjust = min(cfg["buffer_adjust_step"], cfg["max_buffer_adjust"])
            confidence = min(85, 40 + int(slippage / cfg["max_slippage_pct"] * 20) + trades // 5)
            _save_decision(
                decision_type="adjust_buffer",
                symbol=symbol,
                old_value=f"slippage={slippage:.4f}%",
                new_value=f"+{adjust}%",
                reason=f"Avg slippage {slippage:.4f}% > threshold {cfg['max_slippage_pct']}% ({trades} trades). Suggest buffer +{adjust}%",
                confidence=confidence,
                data_points=trades,
                auto_apply=True,
            )
            _ultron_state["buffer_adjustments"][symbol] = adjust
            decisions_made += 1

    # ── 3. Per-hour WR analysis ──
    for h in hours:
        hour_val = h["hour"]
        h_trades = h["trades"]
        h_wr = h["wr"]

        if h_trades >= cfg["bad_hour_min_trades"] and h_wr < cfg["bad_hour_wr_threshold"]:
            confidence = min(90, 45 + (cfg["bad_hour_wr_threshold"] - h_wr) * 2 + h_trades // 10)
            _save_decision(
                decision_type="skip_hour",
                symbol=None,
                hour=hour_val,
                old_value=f"WR={h_wr}%",
                new_value="SKIP",
                reason=f"Hour {hour_val}:00 UTC WR={h_wr}% < {cfg['bad_hour_wr_threshold']}% ({h_trades} trades)",
                confidence=confidence,
                data_points=h_trades,
                auto_apply=True,
            )
            _ultron_state["skipped_hours"][f"*:{hour_val}"] = f"WR {h_wr}%"
            decisions_made += 1

    # ── 4. Correlation analysis ──
    corr = _fetch_correlation()
    if corr and corr.get("ok"):
        total_loss_events = corr.get("total_loss_events", 0)
        simultaneous = corr.get("simultaneous_losses", 0)
        if total_loss_events > 5 and simultaneous / max(total_loss_events, 1) * 100 > cfg["correlation_threshold"]:
            corr_pct = round(simultaneous / total_loss_events * 100, 1)
            confidence = min(80, 40 + int(corr_pct - cfg["correlation_threshold"]))
            _save_decision(
                decision_type="reduce_size",
                symbol=None,
                old_value=f"corr={corr_pct}%",
                new_value="0.5x size when 3+ pairs signal",
                reason=f"{corr_pct}% of losses are simultaneous across pairs ({simultaneous}/{total_loss_events}). Reduce position when 3+ pairs signal together.",
                confidence=confidence,
                data_points=total_loss_events,
                auto_apply=False,  # Jarvis must approve size reduction
            )
            decisions_made += 1

    # ── 5. Update state ──
    _ultron_state["last_analysis"] = datetime.now(timezone.utc).isoformat()
    _ultron_state["analysis_count"] += 1

    _ulog(f"═══ ULTRON ANALYSIS DONE — {decisions_made} decisions ═══")
    return decisions_made


# ══════════════════════════════════════════════
# DECISION CHECKER — Called before placing orders
# ══════════════════════════════════════════════

def should_skip_pair(symbol):
    """Check if Ultron has paused this pair. Returns (skip, reason)."""
    if symbol in _ultron_state["skipped_pairs"]:
        return True, _ultron_state["skipped_pairs"][symbol]
    return False, None


def should_skip_hour(symbol, hour):
    """Check if Ultron says skip this hour. Returns (skip, reason)."""
    # Check global hour skip
    key_global = f"*:{hour}"
    if key_global in _ultron_state["skipped_hours"]:
        return True, _ultron_state["skipped_hours"][key_global]
    # Check pair-specific hour skip
    key_pair = f"{symbol}:{hour}"
    if key_pair in _ultron_state["skipped_hours"]:
        return True, _ultron_state["skipped_hours"][key_pair]
    return False, None


def get_buffer_adjustment(symbol):
    """Get buffer adjustment for a pair. Returns delta (e.g., 0.1 means +0.1%)."""
    return _ultron_state["buffer_adjustments"].get(symbol, 0.0)


def get_size_factor(concurrent_count):
    """
    Get position size multiplier based on concurrent signals.
    Returns 1.0 (normal) or 0.5 (reduced).
    """
    if concurrent_count >= 3 and "reduce_size" in str(_ultron_state.get("active_decisions", [])):
        return 0.5
    return 1.0


# ══════════════════════════════════════════════
# RELOAD DECISIONS FROM D1 (on bot start)
# ══════════════════════════════════════════════

def reload_active_decisions():
    """Load applied decisions from D1 into local state. Called on bot start."""
    _ulog("Reloading active decisions from D1...")
    decisions = _fetch_active_decisions()

    # Reset state
    _ultron_state["skipped_pairs"] = {}
    _ultron_state["skipped_hours"] = {}
    _ultron_state["buffer_adjustments"] = {}
    _ultron_state["active_decisions"] = decisions

    for d in decisions:
        dtype = d.get("decision_type")
        symbol = d.get("symbol")
        status = d.get("status")

        if status not in ("applied", "pending"):
            continue

        if dtype == "pause_pair" and symbol:
            _ultron_state["skipped_pairs"][symbol] = d.get("reason", "paused by Ultron")

        elif dtype == "skip_hour":
            hour = d.get("hour")
            if hour is not None:
                key = f"{symbol or '*'}:{hour}"
                _ultron_state["skipped_hours"][key] = d.get("reason", "bad hour")

        elif dtype == "adjust_buffer" and symbol:
            try:
                delta = float(d.get("new_value", "0").replace("+", "").replace("%", ""))
                # Guardrail: max ±0.2%
                delta = max(-0.2, min(0.2, delta))
                _ultron_state["buffer_adjustments"][symbol] = delta
            except:
                pass

    _ulog(f"Loaded: {len(_ultron_state['skipped_pairs'])} paused pairs, "
           f"{len(_ultron_state['skipped_hours'])} skipped hours, "
           f"{len(_ultron_state['buffer_adjustments'])} buffer adjustments")


# ══════════════════════════════════════════════
# PUBLIC API — for app.py endpoints
# ══════════════════════════════════════════════

def ultron_status():
    """Return current Ultron state for /ultron/status endpoint."""
    return {
        "ok": True,
        "enabled": _ultron_config_cache["enabled"],
        "last_analysis": _ultron_state["last_analysis"],
        "analysis_count": _ultron_state["analysis_count"],
        "skipped_pairs": _ultron_state["skipped_pairs"],
        "skipped_hours": _ultron_state["skipped_hours"],
        "buffer_adjustments": _ultron_state["buffer_adjustments"],
        "config": _ultron_config_cache,
    }


def get_ultron_log(limit=100):
    """Return Ultron activity log."""
    return list(_ultron_log)[-limit:]


def manual_analyze():
    """Trigger analysis manually (from Jarvis or dashboard)."""
    _ulog("Manual analysis triggered by Jarvis")
    count = ultron_analyze()
    return {"ok": True, "decisions_made": count}


def clear_pair_skip(symbol):
    """Remove a pair from skip list (called after Jarvis override)."""
    _ultron_state["skipped_pairs"].pop(symbol, None)
    _ulog(f"Pair skip cleared: {symbol}")


def clear_hour_skip(hour):
    """Remove hour skip (called after Jarvis override)."""
    key = f"*:{hour}"
    _ultron_state["skipped_hours"].pop(key, None)
    _ulog(f"Hour skip cleared: {hour}")


def clear_buffer_adjustment(symbol):
    """Remove buffer adjustment (called after Jarvis override)."""
    _ultron_state["buffer_adjustments"].pop(symbol, None)
    _ulog(f"Buffer adjustment cleared: {symbol}")
