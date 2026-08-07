"""V2 Excursion + Entry Matrix — bar-by-bar first-touch sequencing.
GET /v2_gated/entry_matrix?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np, math, traceback
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

def _va(hl, ll, cl, vl, w):
    n=len(hl); vahs=[None]*n; vals=[None]*n; pocs=[None]*n
    for i in range(w,n):
        vahs[i]=float(np.percentile(hl[i-w:i],85))
        vals[i]=float(np.percentile(ll[i-w:i],15))
        vs=vl[i-w:i]; tv=sum(vs) or 1
        tp=[(hl[j]+ll[j]+cl[j])/3 for j in range(i-w,i)]
        pocs[i]=sum(tp[k]*vs[k] for k in range(w))/tv
    return vahs,vals,pocs

class SignalCollector(Switcher):
    def __init__(self, config, det):
        super().__init__(config); self.det=det; self.signals=[]
    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.det.regime != "BULL": return
        pl = self.det.swing.protected_low
        self.signals.append({"bar":bar_idx,"side":"LONG","price":float(entry_price),
            "prot":float(pl) if pl is not None else None})
        super()._open_bull(bar_idx, entry_high, sl_level, entry_price, trigger)
    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        if self.det.regime != "BEAR": return
        ph = self.det.swing.protected_high
        self.signals.append({"bar":bar_idx,"side":"SHORT","price":float(entry_price),
            "prot":float(ph) if ph is not None else None})
        super()._open_bear(bar_idx, entry_high, entry_low, sl_level, entry_price)

def _ft(eb, ep, side, H, L, C, ef, prot, n, tp_pct, sl_pct, cost, mx=50):
    if side=="LONG": tp_l=ep*(1+tp_pct);sl_l=ep*(1-sl_pct)
    else: tp_l=ep*(1-tp_pct);sl_l=ep*(1+sl_pct)
    trail_sl=sl_l;be_on=False;mfe=0;mae=0;mfb=0;mab=0
    evts=[];end=min(eb+mx+1,n)
    for j in range(eb+1,end):
        bi=j-eb
        if side=="LONG":fv=(H[j]-ep)/ep;av=(ep-L[j])/ep;hsl=L[j]<=sl_l;htp=H[j]>=tp_l;einv=C[j]<ef[j];pbrk=C[j]<prot if prot and prot<ep else False
        else:fv=(ep-L[j])/ep;av=(H[j]-ep)/ep;hsl=H[j]>=sl_l;htp=L[j]<=tp_l;einv=C[j]>ef[j];pbrk=C[j]>prot if prot and prot>ep else False
        if fv>mfe:mfe=fv;mfb=bi
        if av>mae:mae=av;mab=bi
        if not be_on:
            if side=="LONG" and H[j]>=ep*1.005:be_on=True;trail_sl=ep
            elif side=="SHORT" and L[j]<=ep*0.995:be_on=True;trail_sl=ep
        th=L[j]<=trail_sl if side=="LONG" else H[j]>=trail_sl
        if hsl and not any(e[0]=="SL" for e in evts):evts.append(("SL",bi,round((-sl_pct-cost)*100,3)))
        if htp and not any(e[0]=="TP" for e in evts):evts.append(("TP",bi,round((tp_pct-cost)*100,3)))
        if einv and not any(e[0]=="EMA" for e in evts):
            p=(C[j]-ep)/ep-cost if side=="LONG" else (ep-C[j])/ep-cost
            evts.append(("EMA",bi,round(p*100,3)))
        if pbrk and not any(e[0]=="PROT" for e in evts):
            p=(C[j]-ep)/ep-cost if side=="LONG" else (ep-C[j])/ep-cost
            evts.append(("PROT",bi,round(p*100,3)))
        if th and be_on and not any(e[0]=="TRAIL" for e in evts):
            p=(trail_sl-ep)/ep-cost if side=="LONG" else (ep-trail_sl)/ep-cost
            evts.append(("TRAIL",bi,round(p*100,3)))
    to_p=(C[min(end-1,n-1)]-ep)/ep-cost if side=="LONG" else (ep-C[min(end-1,n-1)])/ep-cost
    to=("TO",mx,round(to_p*100,3))
    def pick(types):
        candidates=[e for e in evts if e[0] in types]
        if not candidates:return to
        return min(candidates,key=lambda x:x[1])
    return {
        "mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfb":mfb,"mab":mab,
        "fixed":pick(["SL","TP"]),"prot_sl":pick(["PROT","TP"]),
        "ema_exit":pick(["EMA"]),"trailing":pick(["TRAIL","TP","SL"]),
    }

@router.get("/entry_matrix")
def entry_matrix(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_period:int=Query(7),ema_slow:int=Query(20),
    tp_pct:float=Query(0.013),sl_pct:float=Query(0.013),
    bull_body:float=Query(0.5),bear_body:float=Query(0.6),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
):
    try:
        rows_1h=_load(symbol,"1h",days)
        if len(rows_1h)<max(ema_period,ema_slow)+60:return{"error":"not enough"}
        O=np.array([r[1] for r in rows_1h],dtype=float);H=np.array([r[2] for r in rows_1h],dtype=float)
        L=np.array([r[3] for r in rows_1h],dtype=float);C=np.array([r[4] for r in rows_1h],dtype=float)
        V=np.array([r[5] for r in rows_1h],dtype=float);T1h=[r[0] for r in rows_1h];n=len(rows_1h)
        ef=_ema(C,ema_period);es=_ema(C,ema_slow);at=_atr(H,L,C,14)
        hl=H.tolist();ll=L.tolist();cl=C.tolist();vl=V.tolist()
        vahs,vals,pocs=_va(hl,ll,cl,vl,50)
        cost=fee_pct+slippage_pct;notional=500.0
        # 15m data
        rows_15m=_load(symbol,"15m",days)
        O15={r[0]:float(r[1]) for r in rows_15m}

        cfg=Mode3BBCConfig()
        cfg.ema_period=ema_period;cfg.tp_pct=tp_pct;cfg.sl_pct=sl_pct
        cfg.bull_body_ratio_min=bull_body;cfg.bear_body_ratio_min=bear_body
        cfg.bull_mtf_15m_enabled=False;cfg.bear_mtf_15m_enabled=False
        cfg.sideways_mtf_15m_enabled=False;cfg.enable_sideways_trades=False
        cfg.direct_transition_enabled=True;cfg.fee_pct_roundtrip=fee_pct;cfg.slippage_pct=slippage_pct

        det=ContinuationDetectorV2(ema_period,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        sc=SignalCollector(cfg,det)
        for i in range(n):
            det.process(i,O,H,L,C,ef,es,at)
            sc.process_candle(i,O[i],H[i],L[i],C[i],ef[i],vahs[i],vals[i],pocs[i])

        sigs=sc.signals
        for s in sigs:
            i=s["bar"];s["ema_v"]=float(ef[i]);s["dist"]=round(100*abs(s["price"]-ef[i])/ef[i],3) if ef[i]>0 else 0
        mid=n//2;ex_modes=["fixed","prot_sl","ema_exit","trailing"]
        results={}

        for em in["A","B","C"]:
            tds={x:[] for x in ex_modes};fl=0;sk=0
            for s in sigs:
                i=s["bar"];side=s["side"];prot=s.get("prot")
                if em=="A":ep=s["price"];ebi=i
                elif em=="B":
                    t1h=T1h[i];nxt=t1h+3600*1000
                    if nxt not in O15:sk+=1;continue
                    ep=O15[nxt];ebi=i+1 if i+1<n else i
                elif em=="C":
                    if i+1>=n:sk+=1;continue
                    ea=ef[i]
                    if side=="LONG":ok=L[i+1]<=ea
                    else:ok=H[i+1]>=ea
                    if not ok:sk+=1;continue
                    ep=float(ea);ebi=i+1
                fl+=1
                ft=_ft(ebi,ep,side,H,L,C,ef,prot,n,tp_pct,sl_pct,cost)
                for x in ex_modes:
                    r=ft[x]
                    tds[x].append({"t":r[0],"b":r[1],"p":r[2],"sd":side,"eb":ebi,"mfe":ft["mfe"],"mae":ft["mae"]})

            for x in ex_modes:
                tl=tds[x];nt=len(tl)
                if nt==0:results[f"{em}_{x}"]={"e":em,"x":x,"n":0,"sk":sk};continue
                w=sum(1 for t in tl if t["p"]>0)
                gr=sum((t["p"]+cost*100)/100*notional for t in tl)
                ne=sum(t["p"]/100*notional for t in tl)
                mfes=sorted([t["mfe"] for t in tl]);maes=sorted([t["mae"] for t in tl])
                tr=[t for t in tl if t["eb"]<mid];te=[t for t in tl if t["eb"]>=mid]
                trn=sum(t["p"]/100*notional for t in tr) if tr else 0
                ten=sum(t["p"]/100*notional for t in te) if te else 0
                eq=0;pk=0;dd=0
                for t in tl:eq+=t["p"]/100*notional;pk=max(pk,eq);dd=max(dd,pk-eq)
                eb={};[eb.update({t["t"]:eb.get(t["t"],0)+1}) for t in tl]
                lo=[t for t in tl if t["sd"]=="LONG"];sh=[t for t in tl if t["sd"]=="SHORT"]
                results[f"{em}_{x}"]={
                    "e":em,"x":x,"n":nt,"fl":fl,"sk":sk,
                    "fr":round(100*fl/(fl+sk),1) if fl+sk else 0,
                    "wr":round(100*w/nt,1),"gr":round(gr,2),"ne":round(ne,2),
                    "ge":round(gr/nt,3),"nee":round(ne/nt,3),"dd":round(dd,2),
                    "mfe_p50":round(mfes[len(mfes)//2],2),"mfe_p25":round(mfes[max(0,len(mfes)//4)],2),"mfe_p75":round(mfes[min(len(mfes)-1,3*len(mfes)//4)],2),
                    "mae_p50":round(maes[len(maes)//2],2),"mae_p25":round(maes[max(0,len(maes)//4)],2),"mae_p75":round(maes[min(len(maes)-1,3*len(maes)//4)],2),
                    "eb":eb,
                    "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                    "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                    "wf":{"trN":len(tr),"trP":round(trn,2),"teN":len(te),"teP":round(ten,2)},
                }
        ds=[s["dist"] for s in sigs]
        return{"symbol":symbol,"days":days,"n":n,"sigs":len(sigs),"cost":cost,
            "dist":{"mean":round(np.mean(ds),2),"med":round(float(np.median(ds)),2),
                    "p25":round(float(np.percentile(ds,25)),2),"p75":round(float(np.percentile(ds,75)),2)},
            "results":results}
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
