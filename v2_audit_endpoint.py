"""V2 Audit — matched control base rate + alternative labels.

FIX: event fires ON the bar where phase transitions from PULLBACK→TREND.
Episode end is that same bar. Match must include ep["end"].

GET /continuation/v2/audit?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone

router_audit = APIRouter(prefix="/continuation/v2", tags=["continuation_audit"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(symbol, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (symbol, tf, start, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(c, p):
    e = np.zeros(len(c)); e[0] = c[0]; k = 2.0/(p+1)
    for i in range(1, len(c)): e[i] = c[i]*k + e[i-1]*(1-k)
    return e

def _atr(H, L, C, period=14):
    n = len(H); atr = np.zeros(n)
    for i in range(1, n):
        tr = max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        if i < period: atr[i] = (atr[i-1]*(i-1) + tr) / i if i > 0 else tr
        else: atr[i] = atr[i-1] + (tr - atr[i-1]) / period
    return atr

def _wilson_ci(successes, total, z=1.96):
    if total == 0: return 0, 0, 0
    p = successes / total
    den = 1 + z*z/total
    ctr = (p + z*z/(2*total)) / den
    spr = z * math.sqrt((p*(1-p) + z*z/(4*total)) / total) / den
    return round(100*p, 1), round(100*max(0, ctr-spr), 1), round(100*min(1, ctr+spr), 1)

from continuation_detector_endpoint import ContinuationDetectorV2

def _eval_labels(i, side, H, L, C, ef, es, atr_arr, prot, n):
    result = {}
    for hz in [2, 4, 8]:
        end = min(i + hz + 1, n)
        if i + 1 >= n:
            for k in ["ema_hold","hh_close","prot_intact","mfe_atr"]:
                result[f"{k}_h{hz}"] = None
            continue
        if side == "BULL":
            ema_hold = all(C[j] > es[j] for j in range(i+1, end))
            hh = any(H[j] > C[i] for j in range(i+1, end))
            intact = all(L[j] >= prot for j in range(i+1, end)) if prot else True
            mfe = 0; atr_at = atr_arr[i] if atr_arr[i] > 0 else 1
            for j in range(i+1, min(i+hz+1, n)):
                exc = (H[j] - C[i]) / atr_at
                if exc > mfe: mfe = exc
                if prot and L[j] < prot: break
        else:
            ema_hold = all(C[j] < es[j] for j in range(i+1, end))
            hh = any(L[j] < C[i] for j in range(i+1, end))
            intact = all(H[j] <= prot for j in range(i+1, end)) if prot else True
            mfe = 0; atr_at = atr_arr[i] if atr_arr[i] > 0 else 1
            for j in range(i+1, min(i+hz+1, n)):
                exc = (C[i] - L[j]) / atr_at
                if exc > mfe: mfe = exc
                if prot and H[j] > prot: break
        result[f"ema_hold_h{hz}"] = ema_hold
        result[f"hh_close_h{hz}"] = hh
        result[f"prot_intact_h{hz}"] = intact
        result[f"mfe_atr_h{hz}"] = round(mfe, 2)
    return result


@router_audit.get("/audit")
def v2_audit(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=30, le=1500),
    ema_fast: int = Query(7), ema_slow: int = Query(20),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5), slope_lb: int = Query(3),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < ema_slow*2+50: return {"error": f"Not enough: {len(rows)}"}
    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    T=[r[0] for r in rows]; n=len(rows)
    ef=_ema(C,ema_fast); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)

    det = ContinuationDetectorV2(ema_fast, ema_slow, swing_lb, swing_atr, slope_lb, min_pb_bars=1)

    # First pass: collect all events with their protected levels
    events_by_bar = {}
    # Also track per-bar state for episode construction
    bar_state = []  # (regime, phase) per bar

    for i in range(n):
        result = det.process(i, O, H, L, C, ef, es, atr_arr)
        bar_state.append((det.regime, det.phase))
        if result:
            for ev in result.get("events", []):
                if "CONTINUATION" in ev:
                    side = "BULL" if "BULL" in ev else "BEAR"
                    prot = det.swing.protected_low if side=="BULL" else det.swing.protected_high
                    events_by_bar[i] = {"side": side, "prot": prot,
                        "tgt": det.swing.last_swing_high if side=="BULL" else det.swing.last_swing_low}

    # Build episodes from bar_state
    episodes = []
    in_pb = False; pb_start = None; pb_side = None
    for i in range(n):
        regime, phase = bar_state[i]
        if regime in ("BULL","BEAR") and phase == "PULLBACK":
            if not in_pb:
                in_pb = True; pb_start = i
                pb_side = "BULL" if regime == "BULL" else "BEAR"
        else:
            if in_pb:
                # Episode ends. The reclaim bar (if any) is THIS bar (i) where phase just changed.
                # Include i in the search since event fires on the transition bar.
                episodes.append({"start": pb_start, "end": i, "side": pb_side, "duration": i - pb_start})
                in_pb = False
    if in_pb:
        episodes.append({"start": pb_start, "end": n-1, "side": pb_side, "duration": n-1 - pb_start})

    # Match episodes to events — include ep["end"] in search!
    for ep in episodes:
        ep["had_event"] = False; ep["event_bar"] = None
        # Search range: start to end INCLUSIVE (end is the transition bar where event fires)
        for bar in range(ep["start"], ep["end"] + 1):
            if bar in events_by_bar and events_by_bar[bar]["side"] == ep["side"]:
                ep["had_event"] = True; ep["event_bar"] = bar
                break

    label_names = ["ema_hold","hh_close","prot_intact","mfe_atr"]
    horizons = [2, 4, 8]
    results = {}

    for side in ["BULL","BEAR"]:
        side_eps = [ep for ep in episodes if ep["side"] == side]
        event_eps = [ep for ep in side_eps if ep["had_event"]]
        no_event_eps = [ep for ep in side_eps if not ep["had_event"]]

        # CONTROL: evaluate at pullback start
        ctrl_labels = {f"{ln}_h{hz}": [] for ln in label_names for hz in horizons}
        for ep in side_eps:
            bi = ep["start"]
            if bi + 9 >= n: continue
            if side == "BULL": prot = float(min(L[max(0,bi-20):bi+1]))
            else: prot = float(max(H[max(0,bi-20):bi+1]))
            labels = _eval_labels(bi, side, H, L, C, ef, es, atr_arr, prot, n)
            for k, v in labels.items():
                if v is not None and k in ctrl_labels: ctrl_labels[k].append(v)

        # EVENT: evaluate at reclaim bar
        evt_labels = {f"{ln}_h{hz}": [] for ln in label_names for hz in horizons}
        for ep in event_eps:
            bi = ep["event_bar"]
            if bi is None or bi + 9 >= n: continue
            ev_info = events_by_bar.get(bi, {})
            prot = ev_info.get("prot")
            if prot is None:
                if side == "BULL": prot = float(min(L[max(0,bi-20):bi+1]))
                else: prot = float(max(H[max(0,bi-20):bi+1]))
            labels = _eval_labels(bi, side, H, L, C, ef, es, atr_arr, prot, n)
            for k, v in labels.items():
                if v is not None and k in evt_labels: evt_labels[k].append(v)

        side_result = {
            "total_episodes": len(side_eps),
            "episodes_with_event": len(event_eps),
            "episodes_without_event": len(no_event_eps),
            "event_rate_pct": round(100*len(event_eps)/len(side_eps),1) if side_eps else 0,
        }

        comparison = {}
        for ln in label_names:
            for hz in horizons:
                key = f"{ln}_h{hz}"
                ctrl = ctrl_labels[key]; evt = evt_labels[key]
                if ln == "mfe_atr":
                    comparison[key] = {
                        "ctrl_n": len(ctrl), "ctrl_mean": round(np.mean(ctrl),2) if ctrl else 0, "ctrl_med": round(float(np.median(ctrl)),2) if ctrl else 0,
                        "evt_n": len(evt), "evt_mean": round(np.mean(evt),2) if evt else 0, "evt_med": round(float(np.median(evt)),2) if evt else 0,
                        "lift_mean": round((np.mean(evt) if evt else 0) - (np.mean(ctrl) if ctrl else 0), 2),
                    }
                else:
                    ct = sum(1 for v in ctrl if v); ca, clo, chi = _wilson_ci(ct, len(ctrl))
                    et = sum(1 for v in evt if v); ea, elo, ehi = _wilson_ci(et, len(evt))
                    lift = round(ea - ca, 1)
                    comparison[key] = {
                        "ctrl_n": len(ctrl), "ctrl_true": ct, "ctrl_acc": ca, "ctrl_ci": [clo, chi],
                        "evt_n": len(evt), "evt_true": et, "evt_acc": ea, "evt_ci": [elo, ehi],
                        "lift": lift, "significant": abs(lift) > 3 and (elo > chi or clo > ehi),
                    }
        side_result["comparison"] = comparison
        results[side] = side_result

    return {
        "symbol": symbol, "days": days, "candles": n,
        "total_episodes": len(episodes),
        "total_events_found": len(events_by_bar),
        "results": results,
    }
