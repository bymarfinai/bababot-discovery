"""V2 Excursion + Entry×Exit — bar-by-bar first-touch sequencing.

Three entries on SAME signal stream:
A. Market at 1H close (current)
B. Open of next 15m candle after 1H signal
C. Limit at EMA, valid 1 hour, cancel if not filled

Five exit events tracked per trade (first one wins):
1. TP hit (wick)
2. SL hit (wick)  
3. EMA invalidation (close through EMA fast)
4. Protected swing break (close through protected level)
5. Trailing BE trigger then SL at entry

GET /v2_gated/excursion?symbol=SOLUSDT&days=971&mode=B
GET /v2_gated/entry_matrix?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["v2_gated_excursion"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(sym, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp()*1000)
    start = now_ms - (days*86400*1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (sym, tf, start, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(c, p):
    e = np.zeros(len(c)); e[0]=c[0]; k=2.0/(p+1)
    for i in range(1, len(c)): e[i] = c[i]*k + e[i-1]*(1-k)
    return e

def _atr(H, L, C, period=14):
    n=len(H); atr=np.zeros(n)
    for i in range(1,n):
        tr=max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1]))
        if i<period: atr[i]=(atr[i-1]*(i-1)+tr)/i
        else: atr[i]=atr[i-1]+(tr-atr[i-1])/period
    return atr

def _va(H,L,C,V,w):
    n=len(H); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    hl=H.tolist(); ll=L.tolist(); cl=C.tolist(); vl=V.tolist()
    for i in range(w,n):
        hs=hl[i-w:i]; ls=ll[i-w:i]; cs=cl[i-w:i]
        vahs[i]=float(np.percentile(hs,85)); vals[i]=float(np.percentile(ls,15))
        vs=vl[i-w:i]; tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(w)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(w))/tv
    return vahs,vals,pocs

class SignalCollector(Switcher):
    def __init__(self, config, det):
        super().__init__(config); self.det=det; self.signals=[]
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        self.signals.append({"bar":bar_idx,"side":"LONG","price":float(entry_price),
            "prot":float(self.det.swing.protected_low) if self.det.swing.protected_low else None})
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        self.signals.append({"bar":bar_idx,"side":"SHORT","price":float(entry_price),
            "prot":float(self.det.swing.protected_high) if self.det.swing.protected_high else None})
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)


def _first_touch(eb, ep, side, H, L, C, ef, prot, n, tp_pct, sl_pct, cost, mx=50):
    """Bar-by-bar first-touch simulation. Returns which event happens first."""
    if side=="LONG":
        tp_lvl=ep*(1+tp_pct); sl_lvl=ep*(1-sl_pct)
    else:
        tp_lvl=ep*(1-tp_pct); sl_lvl=ep*(1+sl_pct)
    # Trailing: move SL to entry after 0.5% favorable
    trail_sl = sl_lvl; be_on = False
    mfe=0; mae=0; mfe_b=0; mae_b=0
    events = []  # collect ALL events with bar, then pick first
    
    end = min(eb+mx+1, n)
    for j in range(eb+1, end):
        bi = j - eb
        if side=="LONG":
            fv=(H[j]-ep)/ep; av=(ep-L[j])/ep
            # First-touch within bar: SL checked on low, TP on high
            hit_sl = L[j] <= sl_lvl; hit_tp = H[j] >= tp_lvl
            ema_inv = C[j] < ef[j]  # close-based
            prot_brk = C[j] < prot if prot and prot < ep else False
            # Trailing
            if not be_on and H[j] >= ep*(1+0.005):
                be_on = True; trail_sl = ep
            trail_hit = L[j] <= trail_sl
        else:
            fv=(ep-L[j])/ep; av=(H[j]-ep)/ep
            hit_sl = H[j] >= sl_lvl; hit_tp = L[j] <= tp_lvl
            ema_inv = C[j] > ef[j]
            prot_brk = C[j] > prot if prot and prot > ep else False
            if not be_on and L[j] <= ep*(1-0.005):
                be_on = True; trail_sl = ep
            trail_hit = H[j] >= trail_sl
        
        if fv > mfe: mfe = fv; mfe_b = bi
        if av > mae: mae = av; mae_b = bi
        
        # Record first occurrence of each event type
        if hit_sl and not any(e["type"]=="SL" for e in events):
            p = -sl_pct - cost
            events.append({"type":"SL","bar":bi,"pnl":round(p*100,3)})
        if hit_tp and not any(e["type"]=="TP" for e in events):
            p = tp_pct - cost
            events.append({"type":"TP","bar":bi,"pnl":round(p*100,3)})
        if ema_inv and not any(e["type"]=="EMA" for e in events):
            p = (C[j]-ep)/ep - cost if side=="LONG" else (ep-C[j])/ep - cost
            events.append({"type":"EMA","bar":bi,"pnl":round(p*100,3)})
        if prot_brk and not any(e["type"]=="PROT" for e in events):
            p = (C[j]-ep)/ep - cost if side=="LONG" else (ep-C[j])/ep - cost
            events.append({"type":"PROT","bar":bi,"pnl":round(p*100,3)})
        if trail_hit and be_on and not any(e["type"]=="TRAIL" for e in events):
            p = (trail_sl-ep)/ep - cost if side=="LONG" else (ep-trail_sl)/ep - cost
            events.append({"type":"TRAIL","bar":bi,"pnl":round(p*100,3)})
        
        # For fixed TP/SL: first of SL or TP determines result
        # Within same bar, SL takes priority (conservative)
    
    # Determine winner for each exit strategy
    results = {}
    # Exit 1: fixed TP/SL — first of TP or SL
    tp_ev = next((e for e in events if e["type"]=="TP"), None)
    sl_ev = next((e for e in events if e["type"]=="SL"), None)
    if sl_ev and tp_ev:
        results["fixed"] = sl_ev if sl_ev["bar"] <= tp_ev["bar"] else tp_ev  # same bar = SL wins
    elif sl_ev: results["fixed"] = sl_ev
    elif tp_ev: results["fixed"] = tp_ev
    else: 
        p = (C[end-1]-ep)/ep - cost if side=="LONG" else (ep-C[end-1])/ep - cost
        results["fixed"] = {"type":"TO","bar":mx,"pnl":round(p*100,3)}
    
    # Exit 2: SL at protected swing (use prot level)
    if prot:
        if side=="LONG":
            prot_sl = prot; prot_tp = tp_lvl
        else:
            prot_sl = prot; prot_tp = tp_lvl
        # Check bar-by-bar with prot as SL
        prot_result = None
        for j in range(eb+1, end):
            bi = j - eb
            if side=="LONG":
                if L[j] <= prot: prot_result = {"type":"PROT_SL","bar":bi,"pnl":round(((prot-ep)/ep-cost)*100,3)}; break
                if H[j] >= tp_lvl: prot_result = {"type":"TP","bar":bi,"pnl":round((tp_pct-cost)*100,3)}; break
            else:
                if H[j] >= prot: prot_result = {"type":"PROT_SL","bar":bi,"pnl":round(((ep-prot)/ep-cost)*100,3)}; break
                if L[j] <= tp_lvl: prot_result = {"type":"TP","bar":bi,"pnl":round((tp_pct-cost)*100,3)}; break
        if not prot_result:
            p = (C[end-1]-ep)/ep - cost if side=="LONG" else (ep-C[end-1])/ep - cost
            prot_result = {"type":"TO","bar":mx,"pnl":round(p*100,3)}
        results["prot_sl"] = prot_result
    
    # Exit 3: EMA cross
    ema_ev = next((e for e in events if e["type"]=="EMA"), None)
    if ema_ev: results["ema_exit"] = ema_ev
    else:
        p = (C[end-1]-ep)/ep - cost if side=="LONG" else (ep-C[end-1])/ep - cost
        results["ema_exit"] = {"type":"TO","bar":mx,"pnl":round(p*100,3)}
    
    # Exit 4: trailing BE
    trail_ev = next((e for e in events if e["type"]=="TRAIL"), None)
    tp_ev2 = next((e for e in events if e["type"]=="TP"), None)
    if trail_ev and tp_ev2:
        results["trailing"] = trail_ev if trail_ev["bar"] <= tp_ev2["bar"] else tp_ev2
    elif trail_ev: results["trailing"] = trail_ev
    elif tp_ev2: results["trailing"] = tp_ev2
    elif sl_ev: results["trailing"] = sl_ev
    else:
        p = (C[end-1]-ep)/ep - cost if side=="LONG" else (ep-C[end-1])/ep - cost
        results["trailing"] = {"type":"TO","bar":mx,"pnl":round(p*100,3)}
    
    return {
        "mfe": round(mfe*100, 3), "mae": round(mae*100, 3),
        "mfe_bar": mfe_b, "mae_bar": mae_b,
        "exits": results,
        "first_event": events[0] if events else None,
    }


@router.get("/entry_matrix")
def entry_matrix(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
):
    try:
        rows_1h = _load(symbol, "1h", days)
        rows_15m = _load(symbol, "15m", days)
        if len(rows_1h) < max(ema_period, ema_slow)+60: return {"error": "not enough 1h"}
        
        O=np.array([r[1] for r in rows_1h],dtype=float); H=np.array([r[2] for r in rows_1h],dtype=float)
        L=np.array([r[3] for r in rows_1h],dtype=float); C=np.array([r[4] for r in rows_1h],dtype=float)
        V=np.array([r[5] for r in rows_1h],dtype=float); T1h=[r[0] for r in rows_1h]; n=len(rows_1h)
        ef=_ema(C,ema_period); es=_ema(C,ema_slow); at=_atr(H,L,C,14)
        vahs,vals,pocs = _va(H,L,C,V,50)
        cost = fee_pct + slippage_pct; notional = 500.0

        # 15m data indexed by timestamp
        O15={r[0]:r[1] for r in rows_15m}; H15={r[0]:r[2] for r in rows_15m}
        L15={r[0]:r[3] for r in rows_15m}; C15={r[0]:r[4] for r in rows_15m}

        cfg = Mode3BBCConfig()
        cfg.ema_period=ema_period; cfg.tp_pct=tp_pct; cfg.sl_pct=sl_pct
        cfg.bull_body_ratio_min=bull_body; cfg.bear_body_ratio_min=bear_body
        cfg.bull_mtf_15m_enabled=False; cfg.bear_mtf_15m_enabled=False
        cfg.sideways_mtf_15m_enabled=False; cfg.enable_sideways_trades=False
        cfg.direct_transition_enabled=True
        cfg.fee_pct_roundtrip=fee_pct; cfg.slippage_pct=slippage_pct

        det = ContinuationDetectorV2(ema_period, ema_slow, swing_lb, swing_atr, 3, min_pb_bars=1)
        sc = SignalCollector(cfg, det)
        for i in range(n):
            det.process(i, O, H, L, C, ef, es, at)
            sc.process_candle(i, O[i], H[i], L[i], C[i], ef[i], vahs[i], vals[i], pocs[i])

        signals = sc.signals
        for s in signals:
            i = s["bar"]; s["ema_val"] = float(ef[i]); s["atr_val"] = float(at[i])
            s["dist_pct"] = round(100*abs(s["price"]-ef[i])/ef[i], 3) if ef[i]>0 else 0
            s["dist_atr"] = round(abs(s["price"]-ef[i])/at[i], 3) if at[i]>0 else 0

        mid = n // 2
        exit_modes = ["fixed","prot_sl","ema_exit","trailing"]
        results = {}

        for entry_mode in ["A","B","C"]:
            trades = {em: [] for em in exit_modes}
            filled = 0; skipped = 0; total_sigs = len(signals)

            for s in signals:
                i = s["bar"]; side = s["side"]; prot = s.get("prot")

                # ENTRY A: market at 1H close
                if entry_mode == "A":
                    ep = s["price"]; entry_bar = i

                # ENTRY B: open of NEXT 15m candle after 1H close
                elif entry_mode == "B":
                    t_1h = T1h[i]
                    # Next 15m candle starts at 1H close time + 0 (first 15m of next hour)
                    next_15m_ts = t_1h + 3600*1000  # start of next hour
                    if next_15m_ts in O15:
                        ep = float(O15[next_15m_ts])  # open of next 15m
                        entry_bar = i + 1 if i + 1 < n else i  # approximate: next 1H bar for exit tracking
                    else:
                        skipped += 1; continue

                # ENTRY C: limit at EMA, valid 1 hour
                elif entry_mode == "C":
                    if i + 1 >= n: skipped += 1; continue
                    ema_at = ef[i]
                    if side == "LONG":
                        fill = L[i+1] <= ema_at  # next 1H bar dips to EMA
                    else:
                        fill = H[i+1] >= ema_at
                    if not fill: skipped += 1; continue
                    ep = float(ema_at); entry_bar = i + 1

                filled += 1
                ft = _first_touch(entry_bar, ep, side, H, L, C, ef, prot, n, tp_pct, sl_pct, cost)
                ft["side"] = side; ft["entry_bar"] = entry_bar; ft["entry_price"] = round(ep, 4)
                ft["dist_pct"] = round(100*abs(ep - ef[entry_bar])/ef[entry_bar], 3) if ef[entry_bar]>0 else 0

                for em in exit_modes:
                    if em in ft["exits"]:
                        trades[em].append({**ft["exits"][em], "side":side, "eb":entry_bar, "mfe":ft["mfe"], "mae":ft["mae"]})

            # Aggregate per exit mode
            for em in exit_modes:
                tl = trades[em]
                nt = len(tl)
                if nt == 0:
                    results[f"{entry_mode}_{em}"] = {"entry":entry_mode,"exit":em,"n":0,"filled":filled,"skipped":skipped}
                    continue
                wins = sum(1 for t in tl if t["pnl"]>0)
                gross = sum((t["pnl"]+cost*100)/100*notional for t in tl)
                net = sum(t["pnl"]/100*notional for t in tl)
                mfes = sorted([t["mfe"] for t in tl])
                maes = sorted([t["mae"] for t in tl])
                # Walk-forward
                tr = [t for t in tl if t["eb"]<mid]; te = [t for t in tl if t["eb"]>=mid]
                trn = sum(t["pnl"]/100*notional for t in tr) if tr else 0
                ten = sum(t["pnl"]/100*notional for t in te) if te else 0
                # Exit breakdown
                eb = {}
                for t in tl: eb[t["type"]] = eb.get(t["type"],0)+1
                # Drawdown
                eq=0;pk=0;dd=0
                for t in tl: eq+=t["pnl"]/100*notional; pk=max(pk,eq); dd=max(dd,pk-eq)
                # Per side
                lo=[t for t in tl if t["side"]=="LONG"]; sh=[t for t in tl if t["side"]=="SHORT"]

                results[f"{entry_mode}_{em}"] = {
                    "entry":entry_mode, "exit":em, "n":nt,
                    "filled":filled, "skipped":skipped,
                    "fill_rate":round(100*filled/total_sigs,1),
                    "wr":round(100*wins/nt,1),
                    "gross":round(gross,2), "net":round(net,2),
                    "gross_e":round(gross/nt,3), "net_e":round(net/nt,3),
                    "dd":round(dd,2),
                    "mfe_med":round(mfes[len(mfes)//2],2), "mfe_p25":round(mfes[len(mfes)//4],2), "mfe_p75":round(mfes[3*len(mfes)//4],2),
                    "mae_med":round(maes[len(maes)//2],2), "mae_p25":round(maes[len(maes)//4],2), "mae_p75":round(maes[3*len(maes)//4],2),
                    "exits":eb,
                    "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["pnl"]>0)/len(lo),1) if lo else 0},
                    "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["pnl"]>0)/len(sh),1) if sh else 0},
                    "wf":{"trN":len(tr),"trP":round(trn,2),"teN":len(te),"teP":round(ten,2),"ok":(trn>0)==(ten>0)},
                }

        # Entry distance stats
        dists = [s["dist_pct"] for s in signals]
        return {
            "symbol":symbol,"days":days,"n":n,"sigs":len(signals),"cost":cost,
            "dist":{"mean":round(np.mean(dists),2),"med":round(float(np.median(dists)),2),
                    "p25":round(float(np.percentile(dists,25)),2),"p75":round(float(np.percentile(dists,75)),2)},
            "results":results,
        }
    except Exception as e:
        import traceback
        return {"error":str(e),"trace":traceback.format_exc()}


# Keep original excursion endpoint
@router.get("/excursion")
def v2_gated_excursion(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
    mode: str = Query("B"),
):
    # Delegate to entry_matrix for mode B, fixed exit
    return entry_matrix(symbol, days, ema_period, ema_slow, tp_pct, sl_pct,
                       bull_body, bear_body, fee_pct, slippage_pct, swing_lb, swing_atr)
