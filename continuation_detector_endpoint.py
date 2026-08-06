"""Continuation State Detector — diagnostic endpoint.

Causal state machine that identifies BULL/BEAR trend → pullback → continuation.
NOT a trading engine. No positions, no TP/SL, no PnL.
Output: state trace with forward labels for offline evaluation.

GET /continuation/trace?symbol=SOLUSDT&days=200&ema_fast=7&ema_slow=20
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime, timezone

router = APIRouter(prefix="/continuation", tags=["continuation"])
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

class ContinuationDetector:
    def __init__(self, ema_fast_p=7, ema_slow_p=20, swing_lb=5, slope_lb=3):
        self.state = "STARTUP"
        self.swing_lb = swing_lb; self.slope_lb = slope_lb
        self.ema_f_p = ema_fast_p; self.ema_s_p = ema_slow_p
        self.protected_low = None; self.protected_high = None
        self.last_swing_high = None; self.last_swing_low = None
        self.swing_highs = []; self.swing_lows = []
        self.pb_count = 0; self.cont_count = 0; self.inv_count = 0
        self.ema_below_count = 0; self.ema_above_count = 0

    def process(self, i, O, H, L, C, ef_arr, es_arr):
        o, h, l, c = O[i], H[i], L[i], C[i]
        ef, es = ef_arr[i], es_arr[i]
        self._update_swings(i, H, L)

        if ef > es: self.ema_above_count += 1; self.ema_below_count = 0
        else: self.ema_below_count += 1; self.ema_above_count = 0

        slope_f = (ef - ef_arr[i-self.slope_lb]) / ef if i >= self.slope_lb else 0
        slope_s = (es - es_arr[i-self.slope_lb]) / es if i >= self.slope_lb else 0
        bull_candle = c > o and c > ef
        bear_candle = c < o and c < ef
        low_touch = l <= ef
        high_touch = h >= ef
        has_hh_hl = self._bullish_structure()
        has_ll_lh = self._bearish_structure()

        old = self.state; reason = ""
        warmup = max(self.ema_s_p * 2, self.swing_lb * 3)

        if self.state == "STARTUP":
            if i < warmup: return self.state, "warmup", old
            if has_hh_hl and ef > es and slope_s > 0:
                self.state = "BULL_TREND"; reason = "HH/HL + EMA aligned up"
            elif has_ll_lh and ef < es and slope_s < 0:
                self.state = "BEAR_TREND"; reason = "LL/LH + EMA aligned down"
            else:
                self.state = "SIDEWAYS"; reason = "no clear structure"

        elif self.state == "SIDEWAYS":
            if has_hh_hl and ef > es and slope_s > 0:
                self.state = "BULL_TREND"; reason = "structure bullish + EMA cross up"
            elif has_ll_lh and ef < es and slope_s < 0:
                self.state = "BEAR_TREND"; reason = "structure bearish + EMA cross dn"

        elif self.state == "BULL_TREND":
            if self.protected_low is not None and c < self.protected_low:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = f"close {c:.2f} < protected_low {self.protected_low:.2f}"
            elif self.ema_below_count >= 2:
                self.state = "SIDEWAYS"; reason = "EMA_f < EMA_s 2 bars"
            elif low_touch:
                self.state = "BULL_PULLBACK"; self.pb_count = 0; reason = f"low {l:.2f} touched EMA {ef:.2f}"

        elif self.state == "BULL_PULLBACK":
            self.pb_count += 1
            if self.protected_low is not None and c < self.protected_low:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = f"close {c:.2f} < protected_low {self.protected_low:.2f}"
            elif bull_candle:
                self.state = "BULL_CONTINUATION"; self.cont_count = 0; reason = f"bullish reclaim: c={c:.2f} > EMA={ef:.2f}"
            elif self.pb_count >= 4:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = "pullback 4+ bars no reclaim"

        elif self.state == "BULL_CONTINUATION":
            self.cont_count += 1
            if self.protected_low is not None and c < self.protected_low:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = "protected low broken"
            elif self.last_swing_high is not None and h > self.last_swing_high:
                self.state = "BULL_TREND"; reason = f"new HH: {h:.2f} > {self.last_swing_high:.2f}"
            elif low_touch:
                self.state = "BULL_PULLBACK"; self.pb_count = 0; reason = "re-test EMA"
            elif self.cont_count >= 3:
                self.state = "BULL_PULLBACK"; self.pb_count = 0; reason = "stale 3 bars"

        elif self.state == "BEAR_TREND":
            if self.protected_high is not None and c > self.protected_high:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = f"close {c:.2f} > protected_high {self.protected_high:.2f}"
            elif self.ema_above_count >= 2:
                self.state = "SIDEWAYS"; reason = "EMA_f > EMA_s 2 bars"
            elif high_touch:
                self.state = "BEAR_PULLBACK"; self.pb_count = 0; reason = f"high {h:.2f} touched EMA {ef:.2f}"

        elif self.state == "BEAR_PULLBACK":
            self.pb_count += 1
            if self.protected_high is not None and c > self.protected_high:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = "protected high broken"
            elif bear_candle:
                self.state = "BEAR_CONTINUATION"; self.cont_count = 0; reason = f"bearish reject: c={c:.2f} < EMA={ef:.2f}"
            elif self.pb_count >= 4:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = "pullback 4+ bars no reject"

        elif self.state == "BEAR_CONTINUATION":
            self.cont_count += 1
            if self.protected_high is not None and c > self.protected_high:
                self.state = "INVALIDATED"; self.inv_count = 0; reason = "protected high broken"
            elif self.last_swing_low is not None and l < self.last_swing_low:
                self.state = "BEAR_TREND"; reason = f"new LL: {l:.2f} < {self.last_swing_low:.2f}"
            elif high_touch:
                self.state = "BEAR_PULLBACK"; self.pb_count = 0; reason = "re-test EMA"
            elif self.cont_count >= 3:
                self.state = "BEAR_PULLBACK"; self.pb_count = 0; reason = "stale 3 bars"

        elif self.state == "INVALIDATED":
            self.inv_count += 1
            if self.inv_count >= 3:
                self.state = "SIDEWAYS"; reason = "cooldown done"

        return self.state, reason, old

    def _update_swings(self, i, H, L):
        lb = self.swing_lb
        if i < lb * 2: return
        cand = i - lb
        is_sh = all(H[k] <= H[cand] for k in range(max(0, cand-lb), min(i+1, cand+lb+1)) if k != cand)
        is_sl = all(L[k] >= L[cand] for k in range(max(0, cand-lb), min(i+1, cand+lb+1)) if k != cand)
        if is_sh:
            val = float(H[cand])
            if self.last_swing_high is None or val != self.last_swing_high:
                self.swing_highs.append((cand, val))
                self.last_swing_high = val
                self.protected_high = val
        if is_sl:
            val = float(L[cand])
            if self.last_swing_low is None or val != self.last_swing_low:
                self.swing_lows.append((cand, val))
                self.last_swing_low = val
                self.protected_low = val

    def _bullish_structure(self):
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2: return False
        return (self.swing_highs[-1][1] > self.swing_highs[-2][1] and
                self.swing_lows[-1][1] > self.swing_lows[-2][1])

    def _bearish_structure(self):
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2: return False
        return (self.swing_highs[-1][1] < self.swing_highs[-2][1] and
                self.swing_lows[-1][1] < self.swing_lows[-2][1])


def _forward_label(i, side, H, L, protected_level, swing_target, n, horizon=4):
    if i + 1 >= n: return "NO_DATA"
    end = min(i + horizon + 1, n)
    if side == "BULL":
        for j in range(i+1, end):
            if protected_level is not None and L[j] < protected_level: return "FALSE"
        for j in range(i+1, end):
            if swing_target is not None and H[j] > swing_target: return "TRUE"
        return "FALSE"
    else:
        for j in range(i+1, end):
            if protected_level is not None and H[j] > protected_level: return "FALSE"
        for j in range(i+1, end):
            if swing_target is not None and L[j] < swing_target: return "TRUE"
        return "FALSE"


@router.get("/trace")
def continuation_trace(
    symbol: str = Query("SOLUSDT"), days: int = Query(200, ge=30, le=1500),
    ema_fast: int = Query(7), ema_slow: int = Query(20),
    swing_lb: int = Query(5), slope_lb: int = Query(3),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < ema_slow * 2 + 30: return {"error": f"Not enough: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    T = [r[0] for r in rows]
    n = len(rows)
    ef = _ema(C, ema_fast); es = _ema(C, ema_slow)

    det = ContinuationDetector(ema_fast, ema_slow, swing_lb, slope_lb)

    transitions = []
    continuations = []
    state_counts = {}
    state_durations = {}
    last_state = "STARTUP"; last_change_bar = 0

    for i in range(n):
        new_state, reason, old_state = det.process(i, O, H, L, C, ef, es)
        state_counts[new_state] = state_counts.get(new_state, 0) + 1

        if new_state != old_state and reason:
            dur = i - last_change_bar
            state_durations.setdefault(old_state, []).append(dur)
            ts = datetime.fromtimestamp(T[i]/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            trans = {
                "bar": i, "time": ts,
                "from": old_state, "to": new_state, "reason": reason,
                "o": round(O[i],2), "h": round(H[i],2), "l": round(L[i],2), "c": round(C[i],2),
                "ema_f": round(ef[i],2), "ema_s": round(es[i],2),
                "prot_low": round(det.protected_low,2) if det.protected_low else None,
                "prot_high": round(det.protected_high,2) if det.protected_high else None,
                "swing_high": round(det.last_swing_high,2) if det.last_swing_high else None,
                "swing_low": round(det.last_swing_low,2) if det.last_swing_low else None,
                "duration_in_prev": dur,
            }
            transitions.append(trans)
            last_change_bar = i

            if new_state == "BULL_CONTINUATION":
                label = _forward_label(i, "BULL", H, L, det.protected_low, det.last_swing_high, n)
                trans["forward_label"] = label
                continuations.append(trans)
            elif new_state == "BEAR_CONTINUATION":
                label = _forward_label(i, "BEAR", H, L, det.protected_high, det.last_swing_low, n)
                trans["forward_label"] = label
                continuations.append(trans)

    # Summary
    bull_cont = [c for c in continuations if c["to"] == "BULL_CONTINUATION"]
    bear_cont = [c for c in continuations if c["to"] == "BEAR_CONTINUATION"]
    bull_true = sum(1 for c in bull_cont if c.get("forward_label") == "TRUE")
    bull_false = sum(1 for c in bull_cont if c.get("forward_label") == "FALSE")
    bear_true = sum(1 for c in bear_cont if c.get("forward_label") == "TRUE")
    bear_false = sum(1 for c in bear_cont if c.get("forward_label") == "FALSE")

    avg_dur = {s: round(sum(d)/len(d),1) for s, d in state_durations.items() if d}
    too_fast = [t for t in transitions if t["duration_in_prev"] <= 1 and t["from"] not in ("STARTUP","INVALIDATED")]
    too_slow = [t for t in transitions if t["duration_in_prev"] >= 20]

    return {
        "symbol": symbol, "days": days, "candles": n,
        "config": {"ema_fast": ema_fast, "ema_slow": ema_slow, "swing_lb": swing_lb, "slope_lb": slope_lb},
        "state_counts": state_counts,
        "avg_duration_bars": avg_dur,
        "total_transitions": len(transitions),
        "continuation_summary": {
            "bull": {"total": len(bull_cont), "true": bull_true, "false": bull_false,
                     "accuracy": round(100*bull_true/len(bull_cont),1) if bull_cont else 0},
            "bear": {"total": len(bear_cont), "true": bear_true, "false": bear_false,
                     "accuracy": round(100*bear_true/len(bear_cont),1) if bear_cont else 0},
        },
        "too_fast_transitions": len(too_fast),
        "too_slow_transitions": len(too_slow),
        "examples_too_fast": too_fast[:5],
        "examples_too_slow": too_slow[:5],
        "continuations": continuations,
        "transitions": transitions[-50:],
    }
