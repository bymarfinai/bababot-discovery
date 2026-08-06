"""Continuation Detector v2/v2.1 — Three-layer architecture.

V2.1 change: min_pb_bars=2 (pullback must have >=2 completed candles before reclaim counts)
The reclaim candle itself does NOT count toward pullback_bars.

GET /continuation/v2/diagnostic?symbol=SOLUSDT&days=971&min_pb=1  (V2)
GET /continuation/v2/diagnostic?symbol=SOLUSDT&days=971&min_pb=2  (V2.1)
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone

router_v2 = APIRouter(prefix="/continuation/v2", tags=["continuation_v2"])
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

class CausalSwingTracker:
    def __init__(self, lookback=10, min_atr_mult=0.5):
        self.lb = lookback; self.min_atr = min_atr_mult
        self.confirmed_highs = []; self.confirmed_lows = []
    def update(self, i, H, L, ATR):
        lb = self.lb; cand = i - lb
        if cand < lb or cand < 0: return
        atr_val = ATR[cand] if ATR[cand] > 0 else 1.0
        min_sig = self.min_atr * atr_val
        is_high = all(H[k] <= H[cand] for k in range(max(0,cand-lb), min(i+1,cand+lb+1)) if k != cand)
        if is_high:
            local_low = min(L[max(0,cand-lb):cand+lb+1])
            if H[cand] - local_low >= min_sig:
                if not self.confirmed_highs or self.confirmed_highs[-1][2] != H[cand]:
                    self.confirmed_highs.append((i, cand, float(H[cand])))
        is_low = all(L[k] >= L[cand] for k in range(max(0,cand-lb), min(i+1,cand+lb+1)) if k != cand)
        if is_low:
            local_high = max(H[max(0,cand-lb):cand+lb+1])
            if local_high - L[cand] >= min_sig:
                if not self.confirmed_lows or self.confirmed_lows[-1][2] != L[cand]:
                    self.confirmed_lows.append((i, cand, float(L[cand])))
    def _count_seq(self, arr, ascending):
        if len(arr) < 2: return 0
        count = 0
        for j in range(len(arr)-1, 0, -1):
            if ascending and arr[j][2] > arr[j-1][2]: count += 1
            elif not ascending and arr[j][2] < arr[j-1][2]: count += 1
            else: break
        return count
    def count_hh(self): return self._count_seq(self.confirmed_highs, True)
    def count_hl(self): return self._count_seq(self.confirmed_lows, True)
    def count_lh(self): return self._count_seq(self.confirmed_highs, False)
    def count_ll(self): return self._count_seq(self.confirmed_lows, False)
    @property
    def protected_low(self): return self.confirmed_lows[-1][2] if self.confirmed_lows else None
    @property
    def protected_high(self): return self.confirmed_highs[-1][2] if self.confirmed_highs else None
    @property
    def last_swing_high(self): return self.confirmed_highs[-1][2] if self.confirmed_highs else None
    @property
    def last_swing_low(self): return self.confirmed_lows[-1][2] if self.confirmed_lows else None
    @property
    def protected_low_bar(self): return self.confirmed_lows[-1][1] if self.confirmed_lows else None
    @property
    def protected_high_bar(self): return self.confirmed_highs[-1][1] if self.confirmed_highs else None

class ContinuationDetectorV2:
    def __init__(self, ema_fast_p=7, ema_slow_p=20, swing_lb=10, swing_atr_mult=0.5, slope_lb=3, min_pb_bars=1):
        self.regime = "STARTUP"; self.phase = "NONE"
        self.swing = CausalSwingTracker(swing_lb, swing_atr_mult)
        self.slope_lb = slope_lb; self.ema_f_p = ema_fast_p; self.ema_s_p = ema_slow_p
        self.min_pb_bars = min_pb_bars  # V2=1, V2.1=2
        self.ema_cross_below = 0; self.ema_cross_above = 0
        self.pullback_bars = 0; self.pullback_start_bar = None
        self.invalidation_bars = 0; self.regime_duration = 0
        self.events = []; self.blocked_events = []

    def process(self, i, O, H, L, C, ef, es, ATR):
        o,h,l,c = O[i],H[i],L[i],C[i]; e_f,e_s = ef[i],es[i]
        self.events = []; self.blocked_events = []
        self.swing.update(i, H, L, ATR)
        if e_f > e_s: self.ema_cross_above += 1; self.ema_cross_below = 0
        else: self.ema_cross_below += 1; self.ema_cross_above = 0
        sl = self.slope_lb
        slope_f = (e_f - ef[i-sl])/e_f if i >= sl and e_f > 0 else 0
        slope_s = (e_s - es[i-sl])/e_s if i >= sl and e_s > 0 else 0
        br = h-l; body = abs(c-o); body_r = body/br if br > 0 else 0
        bull_reclaim = c > e_f and c > o and body_r >= 0.3
        bear_reject = c < e_f and c < o and body_r >= 0.3
        hh=self.swing.count_hh(); hl=self.swing.count_hl()
        lh=self.swing.count_lh(); ll=self.swing.count_ll()
        prot_low=self.swing.protected_low; prot_high=self.swing.protected_high
        old_r=self.regime; old_p=self.phase; reason=""
        warmup = max(self.ema_s_p*2, self.swing.lb*4)
        self.regime_duration += 1

        if self.regime == "STARTUP":
            if i < warmup: return None
            if hh>=2 and hl>=2 and e_f>e_s and slope_s>0: self.regime="BULL";self.phase="TREND";reason="2HH+2HL EMA up"
            elif lh>=2 and ll>=2 and e_f<e_s and slope_s<0: self.regime="BEAR";self.phase="TREND";reason="2LH+2LL EMA dn"
            else: self.regime="SIDEWAYS";self.phase="NONE";reason="no structure"
        elif self.regime == "SIDEWAYS":
            if hh>=2 and hl>=2 and e_f>e_s and slope_s>0: self.regime="BULL";self.phase="TREND";reason=f"{hh}HH+{hl}HL EMA up"
            elif lh>=2 and ll>=2 and e_f<e_s and slope_s<0: self.regime="BEAR";self.phase="TREND";reason=f"{lh}LH+{ll}LL EMA dn"
        elif self.regime == "BULL":
            if prot_low is not None and c < prot_low: self.regime="SIDEWAYS";self.phase="NONE";self.invalidation_bars=0;reason="prot_low broken"
            elif self.ema_cross_below >= 2: self.regime="SIDEWAYS";self.phase="NONE";reason="EMA cross dn 2bars"
            else:
                if self.phase=="TREND":
                    if l <= e_f: self.phase="PULLBACK";self.pullback_bars=0;self.pullback_start_bar=i;reason="low<=EMA"
                elif self.phase=="PULLBACK":
                    self.pullback_bars += 1
                    # V2.1: reclaim candle does NOT count toward pb_bars
                    # pullback_bars incremented BEFORE reclaim check = counts completed candles
                    if bull_reclaim:
                        if self.pullback_bars >= self.min_pb_bars:
                            self.events.append("BULL_CONTINUATION_CONFIRM")
                            self.phase="TREND"
                            reason=f"reclaim c={c:.2f} body={body_r:.2f} pb={self.pullback_bars}"
                        else:
                            self.blocked_events.append({"event":"BULL_CONTINUATION_CONFIRM","pb_bars":self.pullback_bars,"min_required":self.min_pb_bars})
                            self.phase="TREND"
                            reason=f"reclaim BLOCKED pb={self.pullback_bars}<{self.min_pb_bars}"
                    elif self.pullback_bars >= 6: self.phase="INVALIDATED";reason="pb 6bars"
                elif self.phase=="INVALIDATED":
                    self.invalidation_bars += 1
                    if bull_reclaim and self.invalidation_bars >= 2: self.phase="TREND";reason="recovered"
                    elif self.invalidation_bars >= 4: self.regime="SIDEWAYS";self.phase="NONE";reason="inv timeout"
        elif self.regime == "BEAR":
            if prot_high is not None and c > prot_high: self.regime="SIDEWAYS";self.phase="NONE";reason="prot_high broken"
            elif self.ema_cross_above >= 2: self.regime="SIDEWAYS";self.phase="NONE";reason="EMA cross up 2bars"
            else:
                if self.phase=="TREND":
                    if h >= e_f: self.phase="PULLBACK";self.pullback_bars=0;self.pullback_start_bar=i;reason="high>=EMA"
                elif self.phase=="PULLBACK":
                    self.pullback_bars += 1
                    if bear_reject:
                        if self.pullback_bars >= self.min_pb_bars:
                            self.events.append("BEAR_CONTINUATION_CONFIRM")
                            self.phase="TREND"
                            reason=f"reject c={c:.2f} body={body_r:.2f} pb={self.pullback_bars}"
                        else:
                            self.blocked_events.append({"event":"BEAR_CONTINUATION_CONFIRM","pb_bars":self.pullback_bars,"min_required":self.min_pb_bars})
                            self.phase="TREND"
                            reason=f"reject BLOCKED pb={self.pullback_bars}<{self.min_pb_bars}"
                    elif self.pullback_bars >= 6: self.phase="INVALIDATED";reason="pb 6bars"
                elif self.phase=="INVALIDATED":
                    self.invalidation_bars += 1
                    if bear_reject and self.invalidation_bars >= 2: self.phase="TREND";reason="recovered"
                    elif self.invalidation_bars >= 4: self.regime="SIDEWAYS";self.phase="NONE";reason="inv timeout"

        if self.regime != old_r: self.regime_duration = 0
        if self.regime != old_r or self.phase != old_p or self.events or self.blocked_events:
            return {"bar":i,"old_r":old_r,"old_p":old_p,"new_r":self.regime,"new_p":self.phase,
                    "events":list(self.events),"blocked":list(self.blocked_events),
                    "reason":reason,"hh":hh,"hl":hl,"lh":lh,"ll":ll,
                    "prot_low":prot_low,"prot_high":prot_high,"slope_f":round(slope_f,5),"slope_s":round(slope_s,5),
                    "pb_bars":self.pullback_bars,"pb_start":self.pullback_start_bar,
                    "body_r":round(body_r,3),"regime_dur":self.regime_duration}
        return None

def _fwd_label(i, side, H, L, prot, tgt, n, horizon):
    if i+1>=n or tgt is None: return "NO_DATA"
    end = min(i+horizon+1, n)
    if side=="BULL":
        for j in range(i+1,end):
            if prot is not None and L[j] < prot: return "FALSE"
        for j in range(i+1,end):
            if H[j] > tgt: return "TRUE"
        return "FALSE"
    else:
        for j in range(i+1,end):
            if prot is not None and H[j] > prot: return "FALSE"
        for j in range(i+1,end):
            if L[j] < tgt: return "TRUE"
        return "FALSE"

@router_v2.get("/diagnostic")
def v2_diagnostic(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=30, le=1500),
    ema_fast: int = Query(7), ema_slow: int = Query(20),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5), slope_lb: int = Query(3),
    min_pb: int = Query(1, ge=1, le=6),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < ema_slow*2+50: return {"error": f"Not enough: {len(rows)}"}
    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    T=[r[0] for r in rows]; n=len(rows)
    ef=_ema(C,ema_fast); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)

    det = ContinuationDetectorV2(ema_fast,ema_slow,swing_lb,swing_atr,slope_lb,min_pb_bars=min_pb)
    regime_counts={}; regime_log=[]; cur_rs=0; cur_r="STARTUP"
    all_events=[]; blocked_log=[]; fast_reg=0
    # Track matched base rate: bars in BULL/PULLBACK or BEAR/PULLBACK
    pb_bars_bull=[]; pb_bars_bear=[]

    for i in range(n):
        result = det.process(i, O, H, L, C, ef, es, atr_arr)
        regime_counts[det.regime] = regime_counts.get(det.regime,0)+1
        # Track pullback bars for matched base rate
        if det.regime=="BULL" and det.phase=="PULLBACK": pb_bars_bull.append(i)
        if det.regime=="BEAR" and det.phase=="PULLBACK": pb_bars_bear.append(i)

        if result:
            ts = datetime.fromtimestamp(T[i]/1000,tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if result["old_r"] != result["new_r"]:
                dur = i - cur_rs
                regime_log.append({"r":cur_r,"s":cur_rs,"e":i,"d":dur})
                if dur <= 1 and cur_r not in ("STARTUP",): fast_reg += 1
                cur_rs=i; cur_r=result["new_r"]
            # Blocked events
            for bl in result.get("blocked",[]):
                blocked_log.append({"bar":i,"time":ts,"event":bl["event"],"pb_bars":bl["pb_bars"],
                    "c":round(C[i],2),"ema_f":round(ef[i],2),"reason":result["reason"]})
            for ev in result.get("events",[]):
                if "CONTINUATION" not in ev: continue
                side = "BULL" if "BULL" in ev else "BEAR"
                prot = det.swing.protected_low if side=="BULL" else det.swing.protected_high
                tgt = det.swing.last_swing_high if side=="BULL" else det.swing.last_swing_low
                prot_bar = det.swing.protected_low_bar if side=="BULL" else det.swing.protected_high_bar
                ema_spread = (ef[i]-es[i])/es[i] if es[i]>0 else 0
                dist_to_tgt = abs(tgt-C[i])/C[i] if tgt else 0
                prot_age = i - prot_bar if prot_bar is not None else 0
                labels = {}
                for hz in [1,2,4,8]: labels[f"h{hz}"] = _fwd_label(i, side, H, L, prot, tgt, n, hz)
                all_events.append({
                    "bar":i,"time":ts,"side":side,"event":ev,
                    "c":round(C[i],2),"ema_f":round(ef[i],2),"ema_s":round(es[i],2),"atr":round(atr_arr[i],2),
                    "prot":round(prot,2) if prot else None,"tgt":round(tgt,2) if tgt else None,
                    "labels":labels,
                    "features":{"ema_spread_pct":round(100*ema_spread,3),"slope_f":result["slope_f"],"slope_s":result["slope_s"],
                        "pb_bars":result["pb_bars"],"pb_start":result["pb_start"],"body_r":result["body_r"],
                        "dist_to_tgt_pct":round(100*dist_to_tgt,3),"prot_age_bars":prot_age,"regime_dur":result["regime_dur"]},
                    "reason":result["reason"],
                    "causality":{"pullback_started_bar":result["pb_start"],"pullback_completed_bars":result["pb_bars"],
                        "event_fired_bar":i,"entry_would_be":"close of bar "+str(i)}
                })
    regime_log.append({"r":cur_r,"s":cur_rs,"e":n,"d":n-cur_rs})

    dur_stats = {}
    for rl in regime_log: dur_stats.setdefault(rl["r"],[]).append(rl["d"])
    dur_summary = {r:{"n":len(d),"avg":round(np.mean(d),1),"med":round(float(np.median(d)),1)} for r,d in dur_stats.items()}

    # Multi-horizon accuracy + CI
    horizons_acc = {}
    for side in ["BULL","BEAR"]:
        evs = [e for e in all_events if e["side"]==side]
        for hz in [1,2,4,8]:
            key = f"h{hz}"
            valid = [e for e in evs if e["labels"][key] != "NO_DATA"]
            true_c = sum(1 for e in valid if e["labels"][key]=="TRUE")
            nv = len(valid); acc = round(100*true_c/nv,1) if nv else 0
            if nv > 0:
                p = true_c/nv; z = 1.96; den = 1+z*z/nv
                ctr = (p+z*z/(2*nv))/den; spr = z*math.sqrt((p*(1-p)+z*z/(4*nv))/nv)/den
                ci_lo=round(100*max(0,ctr-spr),1); ci_hi=round(100*min(1,ctr+spr),1)
            else: ci_lo=0;ci_hi=0
            horizons_acc[f"{side}_h{hz}"] = {"events":nv,"true":true_c,"acc":acc,"ci_lo":ci_lo,"ci_hi":ci_hi}

    # Matched base rate: among bars in BULL/PULLBACK, how often does price make HH in next N bars?
    matched_base = {}
    for side, pb_list in [("BULL",pb_bars_bull),("BEAR",pb_bars_bear)]:
        for hz in [1,2,4,8]:
            count=0; total=0
            for bi in pb_list:
                if bi+hz+1 >= n: continue
                prot = det.swing.protected_low if side=="BULL" else det.swing.protected_high
                tgt = det.swing.last_swing_high if side=="BULL" else det.swing.last_swing_low
                if tgt is None: continue
                lbl = _fwd_label(bi, side, H, L, prot, tgt, n, hz)
                if lbl != "NO_DATA":
                    total += 1
                    if lbl == "TRUE": count += 1
            matched_base[f"{side}_h{hz}"] = round(100*count/total,1) if total else 0
            matched_base[f"{side}_h{hz}_n"] = total

    # Unconditional base rate
    base_rates = {}
    for side in ["BULL","BEAR"]:
        for hz in [1,2,4,8]:
            count=0;total=0;lb=20
            for i in range(lb, n-hz-1):
                sh=max(H[i-lb:i]);sl_v=min(L[i-lb:i]);end=min(i+hz+1,n)
                if side=="BULL":
                    hh=any(H[j]>sh for j in range(i+1,end));intact=all(L[j]>=sl_v for j in range(i+1,end))
                    if hh and intact:count+=1
                else:
                    ll=any(L[j]<sl_v for j in range(i+1,end));intact=all(H[j]<=sh for j in range(i+1,end))
                    if ll and intact:count+=1
                total+=1
            base_rates[f"{side}_h{hz}"] = round(100*count/total,1) if total else 0

    # Rolling thirds
    third = n//3
    rolling = {}
    for wname, ws, we in [("early",0,third),("mid",third,2*third),("late",2*third,n)]:
        for side in ["BULL","BEAR"]:
            evs = [e for e in all_events if e["side"]==side and ws<=e["bar"]<we]
            valid = [e for e in evs if e["labels"]["h4"]!="NO_DATA"]
            true_c = sum(1 for e in valid if e["labels"]["h4"]=="TRUE")
            rolling[f"{side}_{wname}"] = {"events":len(valid),"true":true_c,"acc":round(100*true_c/len(valid),1) if valid else 0}

    false_bull = [e for e in all_events if e["side"]=="BULL" and e["labels"]["h4"]=="FALSE"][:15]
    false_bear = [e for e in all_events if e["side"]=="BEAR" and e["labels"]["h4"]=="FALSE"][:15]

    # pb_bars distribution for events
    pb_dist = {}
    for e in all_events:
        pb = e["features"]["pb_bars"]
        pb_dist[pb] = pb_dist.get(pb, 0) + 1

    return {
        "symbol":symbol,"days":days,"candles":n,"version":f"V2.{'1' if min_pb>=2 else '0'}","min_pb_bars":min_pb,
        "regime_distribution":regime_counts,"regime_duration":dur_summary,
        "fast_regime_changes":fast_reg,"sideways_pct":round(100*regime_counts.get("SIDEWAYS",0)/n,1),
        "horizons":horizons_acc,"base_rates_unconditional":base_rates,"base_rates_matched":matched_base,
        "rolling_h4":rolling,"total_events":len(all_events),
        "blocked_events_count":len(blocked_log),"blocked_events_sample":blocked_log[:15],
        "pb_bars_distribution":pb_dist,
        "false_bull":false_bull,"false_bear":false_bear,"events":all_events,
    }

@router_v2.get("/trace")
def continuation_v2_trace(
    symbol: str = Query("SOLUSDT"), days: int = Query(400, ge=30, le=1500),
    ema_fast: int = Query(7), ema_slow: int = Query(20),
    swing_lb: int = Query(10, ge=5, le=30), swing_atr: float = Query(0.5), slope_lb: int = Query(3),
    min_pb: int = Query(1),
):
    return v2_diagnostic(symbol, days, ema_fast, ema_slow, swing_lb, swing_atr, slope_lb, min_pb)
