"""Continuation Detector v2 — Three-layer architecture.

Layer 1: REGIME  (persistent) — BULL / BEAR / SIDEWAYS
Layer 2: PHASE   (within regime) — TREND / PULLBACK / INVALIDATED  
Layer 3: EVENT   (one-shot) — BULL_CONTINUATION_CONFIRM / BEAR_CONTINUATION_CONFIRM

Key fixes from v1:
- Continuation is EVENT not STATE (fires once, doesn't persist)
- ATR-scaled swing significance (no minor noise swings)
- 2 confirmed HH + 2 confirmed HL required for BULL regime
- Swing confirmed only at right-side confirmation bar (no backdating)
- One wick never flips regime
- Pullback needs body ratio check, not just close > EMA

GET /continuation/v2/trace?symbol=SOLUSDT&days=400
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime, timezone

router_v2 = APIRouter(prefix="/continuation/v2", tags=["continuation_v2"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(symbol, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines "
                "WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? "
                "ORDER BY open_time ASC", (symbol, tf, start, now_ms))
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


class CausalSwingTracker:
    """Track swing highs/lows with ATR significance and causal confirmation."""
    
    def __init__(self, lookback=10, min_atr_mult=0.5):
        self.lb = lookback
        self.min_atr = min_atr_mult
        self.confirmed_highs = []  # [(confirm_bar, swing_bar, price)]
        self.confirmed_lows = []
    
    def update(self, i, H, L, ATR):
        """Check if bar (i - lb) is a confirmed swing. Causal: uses data [0..i] only."""
        lb = self.lb
        cand = i - lb
        if cand < lb or cand < 0: return
        
        atr_val = ATR[cand] if ATR[cand] > 0 else 1.0
        min_sig = self.min_atr * atr_val
        
        # Swing high: H[cand] >= all neighbors in [cand-lb, i]
        is_high = True
        for k in range(max(0, cand - lb), min(i + 1, cand + lb + 1)):
            if k == cand: continue
            if H[k] > H[cand]: is_high = False; break
        
        if is_high:
            # Significance: must be meaningfully higher than surrounding lows
            local_low = min(L[max(0,cand-lb):cand+lb+1])
            if H[cand] - local_low >= min_sig:
                # Don't add duplicate
                if not self.confirmed_highs or self.confirmed_highs[-1][2] != H[cand]:
                    self.confirmed_highs.append((i, cand, float(H[cand])))
        
        # Swing low
        is_low = True
        for k in range(max(0, cand - lb), min(i + 1, cand + lb + 1)):
            if k == cand: continue
            if L[k] < L[cand]: is_low = False; break
        
        if is_low:
            local_high = max(H[max(0,cand-lb):cand+lb+1])
            if local_high - L[cand] >= min_sig:
                if not self.confirmed_lows or self.confirmed_lows[-1][2] != L[cand]:
                    self.confirmed_lows.append((i, cand, float(L[cand])))
    
    def count_hh(self):
        """Count consecutive higher-highs in recent confirmed swings."""
        if len(self.confirmed_highs) < 2: return 0
        count = 0
        for j in range(len(self.confirmed_highs)-1, 0, -1):
            if self.confirmed_highs[j][2] > self.confirmed_highs[j-1][2]:
                count += 1
            else: break
        return count
    
    def count_hl(self):
        if len(self.confirmed_lows) < 2: return 0
        count = 0
        for j in range(len(self.confirmed_lows)-1, 0, -1):
            if self.confirmed_lows[j][2] > self.confirmed_lows[j-1][2]:
                count += 1
            else: break
        return count
    
    def count_lh(self):
        if len(self.confirmed_highs) < 2: return 0
        count = 0
        for j in range(len(self.confirmed_highs)-1, 0, -1):
            if self.confirmed_highs[j][2] < self.confirmed_highs[j-1][2]:
                count += 1
            else: break
        return count
    
    def count_ll(self):
        if len(self.confirmed_lows) < 2: return 0
        count = 0
        for j in range(len(self.confirmed_lows)-1, 0, -1):
            if self.confirmed_lows[j][2] < self.confirmed_lows[j-1][2]:
                count += 1
            else: break
        return count
    
    @property
    def protected_low(self):
        return self.confirmed_lows[-1][2] if self.confirmed_lows else None
    
    @property
    def protected_high(self):
        return self.confirmed_highs[-1][2] if self.confirmed_highs else None
    
    @property
    def last_swing_high(self):
        return self.confirmed_highs[-1][2] if self.confirmed_highs else None
    
    @property
    def last_swing_low(self):
        return self.confirmed_lows[-1][2] if self.confirmed_lows else None


class ContinuationDetectorV2:
    def __init__(self, ema_fast_p=7, ema_slow_p=20, swing_lb=10, 
                 swing_atr_mult=0.5, slope_lb=3):
        self.regime = "STARTUP"
        self.phase = "NONE"
        self.swing = CausalSwingTracker(swing_lb, swing_atr_mult)
        self.slope_lb = slope_lb
        self.ema_f_p = ema_fast_p; self.ema_s_p = ema_slow_p
        
        self.ema_cross_below = 0; self.ema_cross_above = 0
        self.pullback_bars = 0
        self.invalidation_bars = 0
        self.regime_duration = 0
        
        self.events = []  # one-shot events this bar
        self.transition_log = []
    
    def process(self, i, O, H, L, C, ef, es, ATR):
        o, h, l, c = O[i], H[i], L[i], C[i]
        e_f, e_s = ef[i], es[i]
        
        self.events = []  # reset events each bar
        self.swing.update(i, H, L, ATR)
        
        # EMA cross tracking
        if e_f > e_s: self.ema_cross_above += 1; self.ema_cross_below = 0
        else: self.ema_cross_below += 1; self.ema_cross_above = 0
        
        # Derived (causal)
        sl = self.slope_lb
        slope_f = (e_f - ef[i-sl]) / e_f if i >= sl and e_f > 0 else 0
        slope_s = (e_s - es[i-sl]) / e_s if i >= sl and e_s > 0 else 0
        bar_range = h - l
        body = abs(c - o)
        body_ratio = body / bar_range if bar_range > 0 else 0
        bull_reclaim = c > e_f and c > o and body_ratio >= 0.3
        bear_reject = c < e_f and c < o and body_ratio >= 0.3
        
        hh = self.swing.count_hh()
        hl = self.swing.count_hl()
        lh = self.swing.count_lh()
        ll = self.swing.count_ll()
        prot_low = self.swing.protected_low
        prot_high = self.swing.protected_high
        
        old_regime = self.regime; old_phase = self.phase
        reason = ""
        warmup = max(self.ema_s_p * 2, self.swing.lb * 4)
        
        self.regime_duration += 1
        
        # ═══ STARTUP ═══
        if self.regime == "STARTUP":
            if i < warmup: return
            if hh >= 2 and hl >= 2 and e_f > e_s and slope_s > 0:
                self.regime = "BULL"; self.phase = "TREND"
                reason = f"2HH+2HL, EMA aligned, slope_s={slope_s:.4f}"
            elif lh >= 2 and ll >= 2 and e_f < e_s and slope_s < 0:
                self.regime = "BEAR"; self.phase = "TREND"
                reason = f"2LH+2LL, EMA aligned, slope_s={slope_s:.4f}"
            else:
                self.regime = "SIDEWAYS"; self.phase = "NONE"
                reason = f"hh={hh} hl={hl} lh={lh} ll={ll} no clear structure"
        
        # ═══ SIDEWAYS ═══
        elif self.regime == "SIDEWAYS":
            if hh >= 2 and hl >= 2 and e_f > e_s and slope_s > 0:
                self.regime = "BULL"; self.phase = "TREND"
                reason = f"structure bullish: {hh}HH+{hl}HL, EMA cross up"
            elif lh >= 2 and ll >= 2 and e_f < e_s and slope_s < 0:
                self.regime = "BEAR"; self.phase = "TREND"
                reason = f"structure bearish: {lh}LH+{ll}LL, EMA cross dn"
        
        # ═══ BULL REGIME ═══
        elif self.regime == "BULL":
            # Regime invalidation checks (applies to all phases)
            if prot_low is not None and c < prot_low:
                self.regime = "SIDEWAYS"; self.phase = "NONE"
                self.invalidation_bars = 0
                reason = f"BULL invalidated: close {c:.2f} < protected_low {prot_low:.2f}"
            elif self.ema_cross_below >= 2:
                self.regime = "SIDEWAYS"; self.phase = "NONE"
                reason = "BULL→SIDEWAYS: EMA_f < EMA_s for 2 bars"
            else:
                # Phase transitions within BULL
                if self.phase == "TREND":
                    if l <= e_f:  # price touches EMA
                        self.phase = "PULLBACK"; self.pullback_bars = 0
                        reason = f"BULL pullback: low {l:.2f} <= EMA_f {e_f:.2f}"
                
                elif self.phase == "PULLBACK":
                    self.pullback_bars += 1
                    if bull_reclaim:
                        # ONE-SHOT EVENT, not state change
                        self.events.append("BULL_CONTINUATION_CONFIRM")
                        self.phase = "TREND"  # back to trend phase
                        reason = f"BULL continuation event: c={c:.2f}>EMA={e_f:.2f}, body={body_ratio:.2f}"
                    elif self.pullback_bars >= 6:
                        self.phase = "INVALIDATED"
                        reason = f"pullback too long: {self.pullback_bars} bars"
                
                elif self.phase == "INVALIDATED":
                    self.invalidation_bars += 1
                    if bull_reclaim and self.invalidation_bars >= 2:
                        self.phase = "TREND"
                        reason = "recovered from invalidation"
                    elif self.invalidation_bars >= 4:
                        self.regime = "SIDEWAYS"; self.phase = "NONE"
                        reason = "BULL regime ended: invalidation timeout"
        
        # ═══ BEAR REGIME ═══
        elif self.regime == "BEAR":
            if prot_high is not None and c > prot_high:
                self.regime = "SIDEWAYS"; self.phase = "NONE"
                reason = f"BEAR invalidated: close {c:.2f} > protected_high {prot_high:.2f}"
            elif self.ema_cross_above >= 2:
                self.regime = "SIDEWAYS"; self.phase = "NONE"
                reason = "BEAR→SIDEWAYS: EMA_f > EMA_s for 2 bars"
            else:
                if self.phase == "TREND":
                    if h >= e_f:
                        self.phase = "PULLBACK"; self.pullback_bars = 0
                        reason = f"BEAR pullback: high {h:.2f} >= EMA_f {e_f:.2f}"
                
                elif self.phase == "PULLBACK":
                    self.pullback_bars += 1
                    if bear_reject:
                        self.events.append("BEAR_CONTINUATION_CONFIRM")
                        self.phase = "TREND"
                        reason = f"BEAR continuation event: c={c:.2f}<EMA={e_f:.2f}, body={body_ratio:.2f}"
                    elif self.pullback_bars >= 6:
                        self.phase = "INVALIDATED"
                        reason = f"pullback too long: {self.pullback_bars} bars"
                
                elif self.phase == "INVALIDATED":
                    self.invalidation_bars += 1
                    if bear_reject and self.invalidation_bars >= 2:
                        self.phase = "TREND"
                        reason = "recovered from invalidation"
                    elif self.invalidation_bars >= 4:
                        self.regime = "SIDEWAYS"; self.phase = "NONE"
                        reason = "BEAR regime ended: invalidation timeout"
        
        # Track regime duration reset
        if self.regime != old_regime:
            self.regime_duration = 0
        
        # Log transition
        if self.regime != old_regime or self.phase != old_phase or self.events:
            return {
                "bar": i, "old_regime": old_regime, "old_phase": old_phase,
                "new_regime": self.regime, "new_phase": self.phase,
                "events": list(self.events), "reason": reason,
                "hh": hh, "hl": hl, "lh": lh, "ll": ll,
                "prot_low": prot_low, "prot_high": prot_high,
            }
        return None


def _forward_label(i, side, H, L, prot_level, swing_target, n, horizon=4):
    if i + 1 >= n or swing_target is None: return "NO_DATA"
    end = min(i + horizon + 1, n)
    if side == "BULL":
        for j in range(i+1, end):
            if prot_level is not None and L[j] < prot_level: return "FALSE"
        for j in range(i+1, end):
            if H[j] > swing_target: return "TRUE"
        return "FALSE"
    else:
        for j in range(i+1, end):
            if prot_level is not None and H[j] > prot_level: return "FALSE"
        for j in range(i+1, end):
            if L[j] < swing_target: return "TRUE"
        return "FALSE"


@router_v2.get("/trace")
def continuation_v2_trace(
    symbol: str = Query("SOLUSDT"), days: int = Query(400, ge=30, le=1500),
    ema_fast: int = Query(7), ema_slow: int = Query(20),
    swing_lb: int = Query(10, ge=5, le=30),
    swing_atr: float = Query(0.5, ge=0.1, le=2.0),
    slope_lb: int = Query(3),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < ema_slow * 2 + 50: return {"error": f"Not enough: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    T = [r[0] for r in rows]
    n = len(rows)
    ef = _ema(C, ema_fast); es = _ema(C, ema_slow)
    atr = _atr(H, L, C, 14)

    det = ContinuationDetectorV2(ema_fast, ema_slow, swing_lb, swing_atr, slope_lb)

    transitions = []
    cont_events = []
    regime_log = []  # (start_bar, end_bar, regime)
    cur_regime_start = 0; cur_regime = "STARTUP"
    
    # Per-bar state tracking
    regime_counts = {}; phase_counts = {}

    for i in range(n):
        result = det.process(i, O, H, L, C, ef, es, atr)
        
        r_key = f"{det.regime}/{det.phase}"
        regime_counts[det.regime] = regime_counts.get(det.regime, 0) + 1
        phase_counts[r_key] = phase_counts.get(r_key, 0) + 1
        
        if result:
            ts = datetime.fromtimestamp(T[i]/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            result["time"] = ts
            result["o"] = round(O[i],2); result["h"] = round(H[i],2)
            result["l"] = round(L[i],2); result["c"] = round(C[i],2)
            result["ema_f"] = round(ef[i],2); result["ema_s"] = round(es[i],2)
            result["atr"] = round(atr[i],2)
            
            if result["old_regime"] != result["new_regime"]:
                dur = i - cur_regime_start
                regime_log.append({"regime": cur_regime, "start": cur_regime_start, "end": i, "duration": dur})
                cur_regime_start = i; cur_regime = result["new_regime"]
            
            transitions.append(result)
            
            for ev in result.get("events", []):
                if "CONTINUATION" in ev:
                    side = "BULL" if "BULL" in ev else "BEAR"
                    prot = det.swing.protected_low if side == "BULL" else det.swing.protected_high
                    tgt = det.swing.last_swing_high if side == "BULL" else det.swing.last_swing_low
                    label = _forward_label(i, side, H, L, prot, tgt, n)
                    ev_entry = dict(result)
                    ev_entry["forward_label"] = label
                    ev_entry["event"] = ev
                    ev_entry["protected"] = round(prot,2) if prot else None
                    ev_entry["target"] = round(tgt,2) if tgt else None
                    cont_events.append(ev_entry)
    
    # Final regime
    regime_log.append({"regime": cur_regime, "start": cur_regime_start, "end": n, "duration": n - cur_regime_start})

    # Regime duration stats
    regime_durations = {}
    for rl in regime_log:
        regime_durations.setdefault(rl["regime"], []).append(rl["duration"])
    
    dur_stats = {}
    for r, durs in regime_durations.items():
        dur_stats[r] = {
            "count": len(durs), "avg": round(np.mean(durs),1),
            "median": round(float(np.median(durs)),1),
            "min": min(durs), "max": max(durs),
        }

    # One-bar transitions
    one_bar = [t for t in transitions if t.get("old_regime") != t.get("new_regime") or t.get("old_phase") != t.get("new_phase")]
    # Count transitions where previous duration was 1
    fast_regimes = [rl for rl in regime_log if rl["duration"] <= 1 and rl["regime"] not in ("STARTUP",)]

    # Event summary
    bull_ev = [e for e in cont_events if "BULL" in e["event"]]
    bear_ev = [e for e in cont_events if "BEAR" in e["event"]]
    bull_true = sum(1 for e in bull_ev if e["forward_label"] == "TRUE")
    bear_true = sum(1 for e in bear_ev if e["forward_label"] == "TRUE")

    # Confirmed swings
    swings_info = {
        "confirmed_highs": len(det.swing.confirmed_highs),
        "confirmed_lows": len(det.swing.confirmed_lows),
        "last_5_highs": [(b, round(p,2)) for _,b,p in det.swing.confirmed_highs[-5:]],
        "last_5_lows": [(b, round(p,2)) for _,b,p in det.swing.confirmed_lows[-5:]],
    }

    return {
        "symbol": symbol, "days": days, "candles": n,
        "config": {"ema_fast": ema_fast, "ema_slow": ema_slow, "swing_lb": swing_lb,
                   "swing_atr_mult": swing_atr, "slope_lb": slope_lb},
        "regime_distribution": regime_counts,
        "phase_distribution": phase_counts,
        "regime_duration_stats": dur_stats,
        "total_transitions": len(transitions),
        "fast_regime_changes": len(fast_regimes),
        "swings": swings_info,
        "continuation_events": {
            "bull": {"total": len(bull_ev), "true": bull_true, "false": len(bull_ev)-bull_true,
                     "accuracy": round(100*bull_true/len(bull_ev),1) if bull_ev else 0},
            "bear": {"total": len(bear_ev), "true": bear_true, "false": len(bear_ev)-bear_true,
                     "accuracy": round(100*bear_true/len(bear_ev),1) if bear_ev else 0},
        },
        "events": cont_events,
        "transitions": transitions[-50:],
        "regime_log": regime_log[-30:],
    }
