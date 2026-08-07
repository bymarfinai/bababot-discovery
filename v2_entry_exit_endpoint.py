"""Entry×Exit Matrix — 3 entries × 4 exits on V2 Mode B signal stream.

GET /v2_entry_exit/matrix?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math
from fastapi import APIRouter, Query
from datetime import datetime, timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_entry_exit", tags=["entry_exit"])
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
    for i in range(w,n):
        hs=H[i-w:i];ls=L[i-w:i];cs=C[i-w:i]
        vahs[i]=float(np.percentile(hs,85));vals[i]=float(np.percentile(ls,15))
        vs=V[i-w:i];tv=sum(vs) or 1
        tp=[(hs[j]+ls[j]+cs[j])/3 for j in range(w)]
        pocs[i]=sum(tp[j]*vs[j] for j in range(w))/tv
    return vahs,vals,pocs

class SignalCollector(Switcher):
    def __init__(self, config, det):
        super().__init__(config); self.det=det; self.signals=[]
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        prot = self.det.swing.protected_low  # capture AT signal time
        self.signals.append({"bar":bar_idx,"side":"LONG","price":entry_price,"prot":prot})
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        prot = self.det.swing.protected_high
        self.signals.append({"bar":bar_idx,"side":"SHORT","price":entry_price,"prot":prot})
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

def _sim(entry_bar, ep, side, exit_mode, H, L, C, ef, atr_arr, n,
         tp_pct, sl_pct, prot, cost, max_bars=100):
    try:
        if exit_mode == 1:
            if side=="LONG": tp=ep*(1+tp_pct); sl=ep*(1-sl_pct)
            else: tp=ep*(1-tp_pct); sl=ep*(1+sl_pct)
        elif exit_mode == 2:
            atr_e = atr_arr[entry_bar] if atr_arr[entry_bar]>0 else ep*0.01
            if side=="LONG":
                sl = (prot - 0.5*atr_e) if prot and prot < ep else ep*(1-sl_pct)
                tp = ep*(1+tp_pct)
            else:
                sl = (prot + 0.5*atr_e) if prot and prot > ep else ep*(1+sl_pct)
                tp = ep*(1-tp_pct)
        elif exit_mode == 3:
            tp = None; sl = None
        elif exit_mode == 4:
            if side=="LONG": tp=ep*(1+tp_pct); sl=ep*(1-sl_pct)
            else: tp=ep*(1-tp_pct); sl=ep*(1+sl_pct)
            be_on = False

        mfe=0; mae=0; mfe_b=0; mae_b=0
        end = min(entry_bar+max_bars+1, n)
        for j in range(entry_bar+1, end):
            bi = j - entry_bar
            if side=="LONG": fav=(H[j]-ep)/ep; adv=(ep-L[j])/ep
            else: fav=(ep-L[j])/ep; adv=(H[j]-ep)/ep
            if fav>mfe: mfe=fav; mfe_b=bi
            if adv>mae: mae=adv; mae_b=bi

            if exit_mode in (1,2):
                if side=="LONG": hsl=L[j]<=sl; htp=H[j]>=tp
                else: hsl=H[j]>=sl; htp=L[j]<=tp
                if hsl:
                    p = -abs(ep-sl)/ep - cost
                    return {"exit":"SL","bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
                if htp:
                    p = abs(tp-ep)/ep - cost
                    return {"exit":"TP","bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
            elif exit_mode == 3:
                if side=="LONG" and C[j]<ef[j]:
                    p=(C[j]-ep)/ep - cost
                    return {"exit":"EMA","bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
                elif side=="SHORT" and C[j]>ef[j]:
                    p=(ep-C[j])/ep - cost
                    return {"exit":"EMA","bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
            elif exit_mode == 4:
                if not be_on:
                    if side=="LONG" and H[j]>=ep*(1+0.005): sl=ep; be_on=True
                    elif side=="SHORT" and L[j]<=ep*(1-0.005): sl=ep; be_on=True
                if side=="LONG": hsl=L[j]<=sl; htp=H[j]>=tp
                else: hsl=H[j]>=sl; htp=L[j]<=tp
                if hsl:
                    p=(sl-ep)/ep if side=="LONG" else (ep-sl)/ep; p-=cost
                    ex="BE" if be_on and abs(sl-ep)<0.001*ep else "SL"
                    return {"exit":ex,"bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
                if htp:
                    p=abs(tp-ep)/ep - cost
                    return {"exit":"TP","bars":bi,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}

        p=(C[end-1]-ep)/ep if side=="LONG" else (ep-C[end-1])/ep; p-=cost
        return {"exit":"TIMEOUT","bars":max_bars,"pnl":round(p*100,3),"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfe_b":mfe_b,"mae_b":mae_b}
    except Exception as e:
        return {"exit":"ERROR","bars":0,"pnl":0,"mfe":0,"mae":0,"mfe_b":0,"mae_b":0,"error":str(e)}


@router.get("/matrix")
def entry_exit_matrix(
    symbol: str = Query("SOLUSDT"), days: int = Query(971),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    tp_pct: float = Query(0.013), sl_pct: float = Query(0.013),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    swing_lb: int = Query(10), swing_atr: float = Query(0.5),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow)+60: return {"error": f"Not enough: {len(rows)}"}
    O=np.array([r[1] for r in rows],dtype=float); H=np.array([r[2] for r in rows],dtype=float)
    L=np.array([r[3] for r in rows],dtype=float); C=np.array([r[4] for r in rows],dtype=float)
    V=np.array([r[5] for r in rows],dtype=float); n=len(rows)
    ef=_ema(C,ema_period); es=_ema(C,ema_slow); atr_arr=_atr(H,L,C,14)
    vahs,vals,pocs = _va(H.tolist(),L.tolist(),C.tolist(),V.tolist(),50)
    cost = fee_pct + slippage_pct; notional = 500.0

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
        det.process(i, O, H, L, C, ef, es, atr_arr)
        sc.process_candle(i, O[i], H[i], L[i], C[i], ef[i], vahs[i], vals[i], pocs[i])

    signals = sc.signals
    for s in signals:
        i = s["bar"]
        s["ema"] = float(ef[i]); s["atr_val"] = float(atr_arr[i])
        s["dist_pct"] = round(100*abs(s["price"]-ef[i])/ef[i], 3) if ef[i]>0 else 0

    mid = n // 2
    train_dists = [s["dist_pct"] for s in signals if s["bar"] < mid]
    auto_thr = round(float(np.median(train_dists)),2) if train_dists else 0.3

    results = {}
    ex_names = {1:"fixedTPSL",2:"protSwingSL",3:"EMACrossExit",4:"trailingBE"}

    for em in ["A","B","C"]:
        for ex in [1,2,3,4]:
            key = f"{em}_{ex}"
            trades = []; filled=0; skipped=0
            for s in signals:
                i=s["bar"]; side=s["side"]; prot=s.get("prot")
                if em=="A": ep=s["price"]; fi=True
                elif em=="B":
                    if i+1>=n: continue
                    ea=ef[i]
                    if side=="LONG": fi=L[i+1]<=ea; ep=ea if fi else None
                    else: fi=H[i+1]>=ea; ep=ea if fi else None
                    if not fi: skipped+=1; continue
                    i=i+1
                elif em=="C":
                    if s["dist_pct"]>auto_thr: skipped+=1; continue
                    ep=s["price"]; fi=True
                filled+=1
                r=_sim(i,ep,side,ex,H,L,C,ef,atr_arr,n,tp_pct,sl_pct,prot,cost)
                r["side"]=side; r["entry_bar"]=i; trades.append(r)

            nt=len(trades)
            if nt==0: results[key]={"entry":em,"exit":ex_names[ex],"trades":0,"skipped":skipped}; continue
            wins=sum(1 for t in trades if t["pnl"]>0)
            gross=sum((t["pnl"]+cost*100)/100*notional for t in trades)
            net=sum(t["pnl"]/100*notional for t in trades)
            tr_t=[t for t in trades if t["entry_bar"]<mid]
            te_t=[t for t in trades if t["entry_bar"]>=mid]
            tr_n=sum(t["pnl"]/100*notional for t in tr_t) if tr_t else 0
            te_n=sum(t["pnl"]/100*notional for t in te_t) if te_t else 0
            eq=0;pk=0;mdd=0
            for t in trades:
                eq+=t["pnl"]/100*notional
                if eq>pk:pk=eq
                if pk-eq>mdd:mdd=pk-eq
            eb={}
            for t in trades: eb[t["exit"]]=eb.get(t["exit"],0)+1
            lo=[t for t in trades if t["side"]=="LONG"]; sh=[t for t in trades if t["side"]=="SHORT"]
            results[key]={
                "entry":em,"exit":ex_names[ex],"trades":nt,"filled":filled,"skipped":skipped,
                "fill_rate":round(100*filled/(filled+skipped),1) if filled+skipped else 0,
                "wr":round(100*wins/nt,1),"gross":round(gross,2),"net":round(net,2),
                "gross_e":round(gross/nt,3),"net_e":round(net/nt,3),"dd":round(mdd,2),
                "mfe":round(np.mean([t["mfe"] for t in trades]),2),
                "mae":round(np.mean([t["mae"] for t in trades]),2),
                "exits":eb,
                "long":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["pnl"]>0)/len(lo),1) if lo else 0},
                "short":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["pnl"]>0)/len(sh),1) if sh else 0},
                "wf":{"train_n":len(tr_t),"train_net":round(tr_n,2),"test_n":len(te_t),"test_net":round(te_n,2),
                      "ok":(tr_n>0 and te_n>0) or (tr_n<0 and te_n<0)},
            }

    dists = [s["dist_pct"] for s in signals]
    return {
        "symbol":symbol,"days":days,"candles":n,"signals":len(signals),
        "cost":cost,"notional":notional,"dist_threshold":auto_thr,
        "dist_stats":{"mean":round(np.mean(dists),2) if dists else 0,"med":round(float(np.median(dists)),2) if dists else 0,
                      "p25":round(float(np.percentile(dists,25)),2) if dists else 0,"p75":round(float(np.percentile(dists,75)),2) if dists else 0},
        "results":results,
    }
