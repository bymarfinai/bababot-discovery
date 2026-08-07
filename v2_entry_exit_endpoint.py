"""Entry×Exit Matrix — 3 entries × 4 exits on V2 Mode B signal stream.
GET /v2_entry_exit/matrix?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math, traceback
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
        vahs[i]=float(np.percentile(H[i-w:i],85))
        vals[i]=float(np.percentile(L[i-w:i],15))
        vs=V[i-w:i]; tv=sum(vs) or 1
        tp=[(H[j]+L[j]+C[j])/3 for j in range(i-w,i)]
        pocs[i]=sum(tp[k]*vs[k] for k in range(w))/tv
    return vahs,vals,pocs

class SignalCollector(Switcher):
    def __init__(self, config, det):
        super().__init__(config); self.det=det; self.signals=[]
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        prot = self.det.swing.protected_low
        self.signals.append({"bar":bar_idx,"side":"LONG","price":float(entry_price),"prot":float(prot) if prot else None})
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        prot = self.det.swing.protected_high
        self.signals.append({"bar":bar_idx,"side":"SHORT","price":float(entry_price),"prot":float(prot) if prot else None})
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

def _sim(eb, ep, side, ex_mode, H, L, C, ef, atr_arr, n, tp_pct, sl_pct, prot, cost, mx=100):
    if ex_mode == 1:
        if side=="LONG": tp=ep*(1+tp_pct); sl=ep*(1-sl_pct)
        else: tp=ep*(1-tp_pct); sl=ep*(1+sl_pct)
    elif ex_mode == 2:
        ae = atr_arr[eb] if atr_arr[eb]>0 else ep*0.01
        if side=="LONG": sl=(prot-0.5*ae) if prot and prot<ep else ep*(1-sl_pct); tp=ep*(1+tp_pct)
        else: sl=(prot+0.5*ae) if prot and prot>ep else ep*(1+sl_pct); tp=ep*(1-tp_pct)
    elif ex_mode == 3: tp=None; sl=None
    elif ex_mode == 4:
        if side=="LONG": tp=ep*(1+tp_pct); sl=ep*(1-sl_pct)
        else: tp=ep*(1-tp_pct); sl=ep*(1+sl_pct)
        be=False
    mfe=0;mae=0;mfb=0;mab=0
    end=min(eb+mx+1,n)
    for j in range(eb+1,end):
        bi=j-eb
        if side=="LONG": fv=(H[j]-ep)/ep;av=(ep-L[j])/ep
        else: fv=(ep-L[j])/ep;av=(H[j]-ep)/ep
        if fv>mfe:mfe=fv;mfb=bi
        if av>mae:mae=av;mab=bi
        if ex_mode in(1,2):
            if side=="LONG":hs=L[j]<=sl;ht=H[j]>=tp
            else:hs=H[j]>=sl;ht=L[j]<=tp
            if hs:return{"x":"SL","b":bi,"p":round((-abs(ep-sl)/ep-cost)*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
            if ht:return{"x":"TP","b":bi,"p":round((abs(tp-ep)/ep-cost)*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
        elif ex_mode==3:
            if side=="LONG" and C[j]<ef[j]:return{"x":"EMA","b":bi,"p":round(((C[j]-ep)/ep-cost)*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
            elif side=="SHORT" and C[j]>ef[j]:return{"x":"EMA","b":bi,"p":round(((ep-C[j])/ep-cost)*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
        elif ex_mode==4:
            if not be:
                if side=="LONG" and H[j]>=ep*1.005:sl=ep;be=True
                elif side=="SHORT" and L[j]<=ep*0.995:sl=ep;be=True
            if side=="LONG":hs=L[j]<=sl;ht=H[j]>=tp
            else:hs=H[j]>=sl;ht=L[j]<=tp
            if hs:
                pp=(sl-ep)/ep if side=="LONG" else(ep-sl)/ep;pp-=cost
                return{"x":"BE" if be and abs(sl-ep)<0.001*ep else "SL","b":bi,"p":round(pp*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
            if ht:return{"x":"TP","b":bi,"p":round((abs(tp-ep)/ep-cost)*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}
    pp=(C[end-1]-ep)/ep if side=="LONG" else(ep-C[end-1])/ep;pp-=cost
    return{"x":"TO","b":mx,"p":round(pp*100,3),"mfe":round(mfe*100,2),"mae":round(mae*100,2)}

@router.get("/matrix")
def entry_exit_matrix(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_period:int=Query(7),ema_slow:int=Query(20),
    tp_pct:float=Query(0.013),sl_pct:float=Query(0.013),
    bull_body:float=Query(0.5),bear_body:float=Query(0.6),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
):
    try:
        rows=_load(symbol,"1h",days)
        if len(rows)<max(ema_period,ema_slow)+60:return{"error":"not enough"}
        O=np.array([r[1] for r in rows],dtype=float);H=np.array([r[2] for r in rows],dtype=float)
        L=np.array([r[3] for r in rows],dtype=float);C=np.array([r[4] for r in rows],dtype=float)
        V=np.array([r[5] for r in rows],dtype=float);n=len(rows)
        ef=_ema(C,ema_period);es=_ema(C,ema_slow);at=_atr(H,L,C,14)
        vahs,vals,pocs=_va(H,L,C,V,50)
        cost=fee_pct+slippage_pct;notional=500.0

        cfg=Mode3BBCConfig()
        cfg.ema_period=ema_period;cfg.tp_pct=tp_pct;cfg.sl_pct=sl_pct
        cfg.bull_body_ratio_min=bull_body;cfg.bear_body_ratio_min=bear_body
        cfg.bull_mtf_15m_enabled=False;cfg.bear_mtf_15m_enabled=False
        cfg.sideways_mtf_15m_enabled=False;cfg.enable_sideways_trades=False
        cfg.direct_transition_enabled=True
        cfg.fee_pct_roundtrip=fee_pct;cfg.slippage_pct=slippage_pct

        det=ContinuationDetectorV2(ema_period,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        sc=SignalCollector(cfg,det)
        for i in range(n):
            det.process(i,O,H,L,C,ef,es,at)
            sc.process_candle(i,O[i],H[i],L[i],C[i],ef[i],vahs[i],vals[i],pocs[i])

        sigs=sc.signals
        for s in sigs:
            i=s["bar"];s["dist"]=round(100*abs(s["price"]-ef[i])/ef[i],3) if ef[i]>0 else 0

        mid=n//2
        td=[s["dist"] for s in sigs if s["bar"]<mid]
        thr=round(float(np.median(td)),2) if td else 0.3
        exn={1:"fixTP",2:"protSL",3:"EMAx",4:"trail"}
        res={}

        for em in["A","B","C"]:
            for ex in[1,2,3,4]:
                k=f"{em}_{ex}";tds=[];fl=0;sk=0
                for s in sigs:
                    i=s["bar"];sd=s["side"];pr=s.get("prot")
                    if em=="A":ep=s["price"]
                    elif em=="B":
                        if i+1>=n:continue
                        ea=ef[i]
                        if sd=="LONG":ok=L[i+1]<=ea
                        else:ok=H[i+1]>=ea
                        if not ok:sk+=1;continue
                        ep=ea;i=i+1
                    elif em=="C":
                        if s["dist"]>thr:sk+=1;continue
                        ep=s["price"]
                    fl+=1
                    r=_sim(i,ep,sd,ex,H,L,C,ef,at,n,tp_pct,sl_pct,pr,cost)
                    r["sd"]=sd;r["eb"]=i;tds.append(r)
                nt=len(tds)
                if nt==0:res[k]={"e":em,"x":exn[ex],"n":0,"sk":sk};continue
                w=sum(1 for t in tds if t["p"]>0)
                gr=sum((t["p"]+cost*100)/100*notional for t in tds)
                ne=sum(t["p"]/100*notional for t in tds)
                tt=[t for t in tds if t["eb"]<mid];te=[t for t in tds if t["eb"]>=mid]
                tn=sum(t["p"]/100*notional for t in tt) if tt else 0
                ten=sum(t["p"]/100*notional for t in te) if te else 0
                eq=0;pk=0;dd=0
                for t in tds:
                    eq+=t["p"]/100*notional
                    if eq>pk:pk=eq
                    if pk-eq>dd:dd=pk-eq
                eb={}
                for t in tds:eb[t["x"]]=eb.get(t["x"],0)+1
                lo=[t for t in tds if t["sd"]=="LONG"];sh=[t for t in tds if t["sd"]=="SHORT"]
                res[k]={"e":em,"x":exn[ex],"n":nt,"fl":fl,"sk":sk,
                    "fr":round(100*fl/(fl+sk),1) if fl+sk else 0,
                    "wr":round(100*w/nt,1),"gr":round(gr,2),"ne":round(ne,2),
                    "ge":round(gr/nt,3),"nee":round(ne/nt,3),"dd":round(dd,2),
                    "mfe":round(np.mean([t["mfe"] for t in tds]),2),
                    "mae":round(np.mean([t["mae"] for t in tds]),2),
                    "eb":eb,
                    "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                    "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                    "wf":{"trN":len(tt),"trP":round(tn,2),"teN":len(te),"teP":round(ten,2),
                          "ok":(tn>0 and ten>0)or(tn<0 and ten<0)},
                }
        ds=[s["dist"] for s in sigs]
        return{"symbol":symbol,"days":days,"n":n,"sigs":len(sigs),"cost":cost,"thr":thr,
            "dist":{"m":round(np.mean(ds),2) if ds else 0,"md":round(float(np.median(ds)),2) if ds else 0},
            "res":res}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
