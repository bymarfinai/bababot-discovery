"""V2 Final Audit — side-specific labels, MAE, time-to-invalidation, 3-timestamp comparison.

Labels:
  BULL: HH (higher high vs close), EMA hold above slow, protected low intact, MFE/MAE
  BEAR: LL (lower low vs close), EMA hold below slow, protected high intact, MFE/MAE

3 timestamps per episode:
  A. pullback_start — first bar entering pullback
  B. reclaim_event — bullish reclaim / bearish reject
  C. structure_confirm — first bar where H > swing_high (BULL) or L < swing_low (BEAR)

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

def _wilson(s, n, z=1.96):
    if n == 0: return 0, 0, 0
    p = s/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    sp = z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return round(100*p,1), round(100*max(0,c-sp),1), round(100*min(1,c+sp),1)

from continuation_detector_endpoint import ContinuationDetectorV2

def _eval_at(i, side, H, L, C, ef, es, atr_arr, prot, swing_tgt, n):
    """Evaluate all labels at bar i for given side. Returns dict with horizons 1,2,4,8."""
    out = {}
    atr_i = atr_arr[i] if atr_arr[i] > 0 else 1.0
    for hz in [1, 2, 4, 8]:
        end = min(i+hz+1, n)
        if i+1 >= n:
            out[hz] = None; continue
        r = {}
        if side == "BULL":
            # HH: any future high > current close
            r["hh"] = any(H[j] > C[i] for j in range(i+1, end))
            # EMA hold: all future closes > EMA slow
            r["ema_hold"] = all(C[j] > es[j] for j in range(i+1, end))
            # Protected low intact
            r["prot_intact"] = all(L[j] >= prot for j in range(i+1, end)) if prot else True
            # MFE (max favorable = upside)
            mfe = 0
            for j in range(i+1, end):
                exc = (H[j] - C[i]) / atr_i
                if exc > mfe: mfe = exc
            r["mfe"] = round(mfe, 3)
            # MAE (max adverse = downside before end)
            mae = 0
            for j in range(i+1, end):
                adv = (C[i] - L[j]) / atr_i
                if adv > mae: mae = adv
            r["mae"] = round(mae, 3)
            # Time to invalidation: bars until L[j] < prot (or hz if never)
            tti = hz
            if prot:
                for j in range(i+1, end):
                    if L[j] < prot: tti = j - i; break
            r["tti"] = tti
        else:  # BEAR
            # LL: any future low < current close
            r["ll"] = any(L[j] < C[i] for j in range(i+1, end))
            # EMA hold: all future closes < EMA slow
            r["ema_hold"] = all(C[j] < es[j] for j in range(i+1, end))
            # Protected high intact
            r["prot_intact"] = all(H[j] <= prot for j in range(i+1, end)) if prot else True
            # MFE (max favorable = downside)
            mfe = 0
            for j in range(i+1, end):
                exc = (C[i] - L[j]) / atr_i
                if exc > mfe: mfe = exc
            r["mfe"] = round(mfe, 3)
            # MAE (max adverse = upside)
            mae = 0
            for j in range(i+1, end):
                adv = (H[j] - C[i]) / atr_i
                if adv > mae: mae = adv
            r["mae"] = round(mae, 3)
            # Time to invalidation: bars until H[j] > prot
            tti = hz
            if prot:
                for j in range(i+1, end):
                    if H[j] > prot: tti = j - i; break
            r["tti"] = tti
        out[hz] = r
    return out

def _find_struct_confirm(i, side, H, L, swing_tgt, n, max_bars=20):
    """Find first bar after i where price breaks swing target. Returns bar or None."""
    if swing_tgt is None: return None
    end = min(i + max_bars + 1, n)
    for j in range(i+1, end):
        if side == "BULL" and H[j] > swing_tgt: return j
        if side == "BEAR" and L[j] < swing_tgt: return j
    return None


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
    n=len(rows)
    ef=_ema(C,ema_fast); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)

    det = ContinuationDetectorV2(ema_fast, ema_slow, swing_lb, swing_atr, slope_lb, min_pb_bars=1)

    events_by_bar = {}
    bar_state = []

    for i in range(n):
        det.process(i, O, H, L, C, ef, es, atr_arr)
        bar_state.append((det.regime, det.phase))
        # Collect events with exact protected/target levels AT the moment they fire
        if det.events:
            for ev in det.events:
                if "CONTINUATION" in ev:
                    side = "BULL" if "BULL" in ev else "BEAR"
                    events_by_bar[i] = {
                        "side": side,
                        "prot": det.swing.protected_low if side=="BULL" else det.swing.protected_high,
                        "tgt": det.swing.last_swing_high if side=="BULL" else det.swing.last_swing_low,
                    }

    # Build episodes
    episodes = []
    in_pb = False; pb_start = None; pb_side = None
    for i in range(n):
        regime, phase = bar_state[i]
        if regime in ("BULL","BEAR") and phase == "PULLBACK":
            if not in_pb:
                in_pb = True; pb_start = i; pb_side = "BULL" if regime=="BULL" else "BEAR"
        else:
            if in_pb:
                episodes.append({"start": pb_start, "end": i, "side": pb_side})
                in_pb = False
    if in_pb:
        episodes.append({"start": pb_start, "end": n-1, "side": pb_side})

    # Match events + find structure confirmation
    for ep in episodes:
        ep["event_bar"] = None; ep["prot"] = None; ep["tgt"] = None; ep["confirm_bar"] = None
        for bar in range(ep["start"], ep["end"] + 1):
            if bar in events_by_bar and events_by_bar[bar]["side"] == ep["side"]:
                ep["event_bar"] = bar
                ep["prot"] = events_by_bar[bar]["prot"]
                ep["tgt"] = events_by_bar[bar]["tgt"]
                ep["confirm_bar"] = _find_struct_confirm(bar, ep["side"], H, L, ep["tgt"], n)
                break

    # For control prot/tgt: approximate from 20-bar lookback at pullback start
    for ep in episodes:
        bi = ep["start"]
        if ep["prot"] is None:
            if ep["side"]=="BULL": ep["prot"] = float(min(L[max(0,bi-20):bi+1]))
            else: ep["prot"] = float(max(H[max(0,bi-20):bi+1]))
        if ep["tgt"] is None:
            if ep["side"]=="BULL": ep["tgt"] = float(max(H[max(0,bi-20):bi+1]))
            else: ep["tgt"] = float(min(L[max(0,bi-20):bi+1]))

    # Evaluate 3 timestamps per episode
    results = {}
    bool_labels = ["hh","ema_hold","prot_intact"] if True else ["ll","ema_hold","prot_intact"]

    for side in ["BULL","BEAR"]:
        side_eps = [ep for ep in episodes if ep["side"]==side]
        has_event = [ep for ep in side_eps if ep["event_bar"] is not None]
        has_confirm = [ep for ep in has_event if ep["confirm_bar"] is not None]

        # Evaluate at each timestamp
        ts_data = {"A_pullback": [], "B_reclaim": [], "C_confirm": []}
        for ep in side_eps:
            bi = ep["start"]
            if bi + 9 >= n: continue
            ts_data["A_pullback"].append(_eval_at(bi, side, H, L, C, ef, es, atr_arr, ep["prot"], ep["tgt"], n))
        for ep in has_event:
            bi = ep["event_bar"]
            if bi + 9 >= n: continue
            ts_data["B_reclaim"].append(_eval_at(bi, side, H, L, C, ef, es, atr_arr, ep["prot"], ep["tgt"], n))
        for ep in has_confirm:
            bi = ep["confirm_bar"]
            if bi + 9 >= n: continue
            ts_data["C_confirm"].append(_eval_at(bi, side, H, L, C, ef, es, atr_arr, ep["prot"], ep["tgt"], n))

        # Aggregate per timestamp × horizon × label
        cont_label = "hh" if side == "BULL" else "ll"
        bool_keys = [cont_label, "ema_hold", "prot_intact"]
        float_keys = ["mfe", "mae", "tti"]

        comparison = {}
        for hz in [1, 2, 4, 8]:
            row = {}
            for ts_name, ts_list in ts_data.items():
                valid = [d[hz] for d in ts_list if d.get(hz) is not None]
                ts_row = {"n": len(valid)}
                for k in bool_keys:
                    vals = [v[k] for v in valid if k in v]
                    true_c = sum(1 for v in vals if v)
                    acc, lo, hi = _wilson(true_c, len(vals))
                    ts_row[k] = {"acc": acc, "ci": [lo, hi], "n": len(vals), "true": true_c}
                for k in float_keys:
                    vals = [v[k] for v in valid if k in v]
                    ts_row[k] = {"mean": round(np.mean(vals),3) if vals else 0,
                                 "med": round(float(np.median(vals)),3) if vals else 0,
                                 "n": len(vals)}
                row[ts_name] = ts_row
            comparison[f"h{hz}"] = row

        results[side] = {
            "total_episodes": len(side_eps),
            "with_event": len(has_event),
            "with_confirm": len(has_confirm),
            "event_rate": round(100*len(has_event)/len(side_eps),1) if side_eps else 0,
            "confirm_rate": round(100*len(has_confirm)/len(has_event),1) if has_event else 0,
            "cont_label_name": cont_label,
            "comparison": comparison,
        }

    return {
        "symbol": symbol, "days": days, "candles": n,
        "total_episodes": len(episodes),
        "events_found": len(events_by_bar),
        "label_verification": {
            "BULL_uses": "HH = any(H[j] > C[i]) for j in i+1..i+hz",
            "BEAR_uses": "LL = any(L[j] < C[i]) for j in i+1..i+hz",
            "ema_hold_BULL": "all(C[j] > EMA_slow[j])",
            "ema_hold_BEAR": "all(C[j] < EMA_slow[j])",
            "prot_intact_BULL": "all(L[j] >= protected_low)",
            "prot_intact_BEAR": "all(H[j] <= protected_high)",
            "MFE_BULL": "(H[j] - C[i]) / ATR[i]",
            "MAE_BULL": "(C[i] - L[j]) / ATR[i]",
            "MFE_BEAR": "(C[i] - L[j]) / ATR[i]",
            "MAE_BEAR": "(H[j] - C[i]) / ATR[i]",
            "no_same_bar": "range starts at i+1, not i",
        },
        "results": results,
    }
