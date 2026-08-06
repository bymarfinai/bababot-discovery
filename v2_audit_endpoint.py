"""V2 Audit — matched control base rate + alternative labels.

Control = first candle of each pullback episode (pullback_start_bar)
Event = reclaim candle (continuation event bar)
One control per pullback, one event per pullback.

Alternative labels (all BULL, BEAR symmetric):
A. Close stays above EMA_slow for next N candles
B. Higher-high vs event close within N candles  
C. Protected low intact for next N candles
D. MFE (max favorable excursion) in ATR units before invalidation

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

# Import detector (same file has it via router_v2)
from continuation_detector_endpoint import ContinuationDetectorV2

def _eval_labels(i, side, H, L, C, ef, es, atr_arr, prot, n):
    """Evaluate all alternative labels at bar i. Returns dict."""
    result = {}
    for hz in [2, 4, 8]:
        end = min(i + hz + 1, n)
        if i + 1 >= n:
            for k in ["ema_hold", "hh_close", "prot_intact", "mfe_atr"]:
                result[f"{k}_h{hz}"] = None
            continue

        if side == "BULL":
            # A: close stays above EMA_slow
            ema_hold = all(C[j] > es[j] for j in range(i+1, end))
            # B: higher high vs event close
            hh = any(H[j] > C[i] for j in range(i+1, end))
            # C: protected low intact
            intact = all(L[j] >= prot for j in range(i+1, end)) if prot else True
            # D: MFE in ATR before invalidation
            mfe = 0
            atr_at_i = atr_arr[i] if atr_arr[i] > 0 else 1
            for j in range(i+1, min(i+hz+1, n)):
                excursion = (H[j] - C[i]) / atr_at_i
                if excursion > mfe: mfe = excursion
                if prot and L[j] < prot: break
        else:
            ema_hold = all(C[j] < es[j] for j in range(i+1, end))
            hh = any(L[j] < C[i] for j in range(i+1, end))
            intact = all(H[j] <= prot for j in range(i+1, end)) if prot else True
            mfe = 0
            atr_at_i = atr_arr[i] if atr_arr[i] > 0 else 1
            for j in range(i+1, min(i+hz+1, n)):
                excursion = (C[i] - L[j]) / atr_at_i
                if excursion > mfe: mfe = excursion
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

    # Track pullback episodes
    # Each episode: (start_bar, end_bar, side, had_event, event_bar)
    episodes = []
    current_pb_start = None; current_pb_side = None
    events_by_bar = {}

    for i in range(n):
        old_phase = det.phase; old_regime = det.regime
        result = det.process(i, O, H, L, C, ef, es, atr_arr)

        # Track pullback start/end
        if det.regime in ("BULL","BEAR") and det.phase == "PULLBACK":
            if current_pb_start is None:
                current_pb_start = i
                current_pb_side = "BULL" if det.regime == "BULL" else "BEAR"
        else:
            if current_pb_start is not None:
                episodes.append({
                    "start": current_pb_start, "end": i,
                    "side": current_pb_side, "duration": i - current_pb_start,
                })
                current_pb_start = None; current_pb_side = None

        if result:
            for ev in result.get("events", []):
                if "CONTINUATION" in ev:
                    side = "BULL" if "BULL" in ev else "BEAR"
                    prot = det.swing.protected_low if side=="BULL" else det.swing.protected_high
                    events_by_bar[i] = {"side": side, "prot": prot,
                        "tgt": det.swing.last_swing_high if side=="BULL" else det.swing.last_swing_low}

    # Close final episode
    if current_pb_start is not None:
        episodes.append({"start": current_pb_start, "end": n, "side": current_pb_side, "duration": n - current_pb_start})

    # Match episodes to events
    for ep in episodes:
        ep["had_event"] = False; ep["event_bar"] = None
        for bar in range(ep["start"], ep["end"]):
            if bar in events_by_bar and events_by_bar[bar]["side"] == ep["side"]:
                ep["had_event"] = True; ep["event_bar"] = bar
                break  # first event per episode only

    # Compute labels for CONTROL (pullback start) and EVENT (reclaim bar)
    label_names = ["ema_hold", "hh_close", "prot_intact", "mfe_atr"]
    horizons = [2, 4, 8]

    results = {}
    for side in ["BULL", "BEAR"]:
        side_eps = [ep for ep in episodes if ep["side"] == side]
        event_eps = [ep for ep in side_eps if ep["had_event"]]
        no_event_eps = [ep for ep in side_eps if not ep["had_event"]]

        # CONTROL: evaluate at pullback start bar for ALL episodes
        ctrl_labels = {f"{ln}_h{hz}": [] for ln in label_names for hz in horizons}
        for ep in side_eps:
            bi = ep["start"]
            if bi + 9 >= n: continue
            # Use current protected level at episode start
            # Re-run detector to get exact prot at that bar... approximate with nearest event's prot
            # For simplicity, use the swing tracker's state. Since we can't easily get historical prot,
            # use the protected level from the nearest event or recompute
            # APPROXIMATE: use a rolling 20-bar swing as proxy
            if side == "BULL":
                prot = float(min(L[max(0,bi-20):bi+1]))
            else:
                prot = float(max(H[max(0,bi-20):bi+1]))
            labels = _eval_labels(bi, side, H, L, C, ef, es, atr_arr, prot, n)
            for k, v in labels.items():
                if v is not None and k in ctrl_labels:
                    ctrl_labels[k].append(v)

        # EVENT: evaluate at event bar for episodes that had events
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
                if v is not None and k in evt_labels:
                    evt_labels[k].append(v)

        # Compute accuracy for each label
        side_result = {
            "total_episodes": len(side_eps),
            "episodes_with_event": len(event_eps),
            "episodes_without_event": len(no_event_eps),
        }

        comparison = {}
        for ln in label_names:
            for hz in horizons:
                key = f"{ln}_h{hz}"
                # Control
                ctrl = ctrl_labels[key]
                if ln == "mfe_atr":
                    ctrl_mean = round(np.mean(ctrl), 2) if ctrl else 0
                    ctrl_med = round(float(np.median(ctrl)), 2) if ctrl else 0
                    evt = evt_labels[key]
                    evt_mean = round(np.mean(evt), 2) if evt else 0
                    evt_med = round(float(np.median(evt)), 2) if evt else 0
                    comparison[key] = {
                        "ctrl_n": len(ctrl), "ctrl_mean_atr": ctrl_mean, "ctrl_median_atr": ctrl_med,
                        "evt_n": len(evt), "evt_mean_atr": evt_mean, "evt_median_atr": evt_med,
                        "lift_mean": round(evt_mean - ctrl_mean, 2),
                    }
                else:
                    ctrl_true = sum(1 for v in ctrl if v)
                    ctrl_acc, ctrl_lo, ctrl_hi = _wilson_ci(ctrl_true, len(ctrl))
                    evt = evt_labels[key]
                    evt_true = sum(1 for v in evt if v)
                    evt_acc, evt_lo, evt_hi = _wilson_ci(evt_true, len(evt))
                    lift = round(evt_acc - ctrl_acc, 1)
                    comparison[key] = {
                        "ctrl_n": len(ctrl), "ctrl_true": ctrl_true, "ctrl_acc": ctrl_acc, "ctrl_ci": [ctrl_lo, ctrl_hi],
                        "evt_n": len(evt), "evt_true": evt_true, "evt_acc": evt_acc, "evt_ci": [evt_lo, evt_hi],
                        "lift": lift, "significant": abs(lift) > 3 and (evt_lo > ctrl_hi or ctrl_lo > evt_hi),
                    }

        side_result["comparison"] = comparison
        results[side] = side_result

    return {
        "symbol": symbol, "days": days, "candles": n,
        "total_episodes": len(episodes),
        "results": results,
    }
