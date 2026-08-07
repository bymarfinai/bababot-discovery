"""V2 Gated Entry×Exit — comprehensive causal analysis.

Entry: A=market@1H close, B=open next 15m, C=close next 15m, D=limit@EMA(1hr)
Exit: 1=fixed TP/SL, 2=prot swing SL, 3=EMA invalidation, 4=trailing, 5=break-even
Causality: all entries after signal T, no same-bar fill/exit, one position at a time.

GET /v2_gated/entry_matrix?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime,timezone
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["v2_gated_excursion"])
DB_PATH = os.environ.get("DB_PATH","market_data.db")

def _ld(sym,tf,days):
    conn=sqlite3.connect(DB_PATH);now=int(datetime.utcnow().timestamp()*1000);st=now-(days*86400*1000)
    r=conn.cursor().execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC",(sym,tf,st,now)).fetchall()
    conn.close();return r

def _ema(c,p):
    e=np.zeros(len(c));e[0]=c[0];k=2.0/(p+1)
    for i in range(1,len(c)):e[i]=c[i]*k+e[i-1]*(1-k)
    return e

def _atr(H,L,C,p=14):
    n=len(H);a=np.zeros(n)
    for i in range(1,n):
        t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]))
        a[i]=a[i-1]+(t-a[i-1])/(min(i,p))
    return a

def _va(hl,ll,cl,vl,w):
    n=len(hl);vahs=[None]*n;vals=[None]*n;pocs=[None]*n
    for i in range(w,n):
        vahs[i]=float(np.percentile(hl[i-w:i],85));vals[i]=float(np.percentile(ll[i-w:i],15))
        vs=vl[i-w:i];tv=sum(vs)or 1;tp=[(hl[j]+ll[j]+cl[j])/3 for j in range(i-w,i)]
        pocs[i]=sum(tp[k]*vs[k] for k in range(w))/tv
    return vahs,vals,pocs

class SigCollect(Switcher):
    def __init__(s,cfg,det):
        super().__init__(cfg);s.det=det;s.sigs=[]
    def _open_bull(s,bi,eh,sl,ep,trig='ema_reclaim'):
        if s.det.regime!="BULL":return
        pl=s.det.swing.protected_low
        s.sigs.append({"b":bi,"sd":"LONG","p":float(ep),"pr":float(pl) if pl else None})
        super()._open_bull(bi,eh,sl,ep,trig)
    def _open_bear(s,bi,eh,el,sl,ep):
        if s.det.regime!="BEAR":return
        ph=s.det.swing.protected_high
        s.sigs.append({"b":bi,"sd":"SHORT","p":float(ep),"pr":float(ph) if ph else None})
        super()._open_bear(bi,eh,el,sl,ep)

def _run_trade(eb,ep,sd,H,L,C,ef,pr,n,tp_p,sl_p,cost,mx=50):
    """Bar-by-bar from eb+1. Returns results for all 5 exit modes."""
    if sd=="LONG":tp=ep*(1+tp_p);sl=ep*(1-sl_p)
    else:tp=ep*(1-tp_p);sl=ep*(1+sl_p)
    # Prot SL
    if pr:
        if sd=="LONG":psl=pr
        else:psl=pr
    else:psl=sl
    # Trail/BE
    tsl=sl;be=False;mfe=0;mae=0;mfb=0;mab=0
    # First touch per exit mode
    res={k:None for k in["fixed","prot","ema","trail","be"]}
    end=min(eb+mx+1,n)
    for j in range(eb+1,end):
        bi=j-eb
        if sd=="LONG":fv=(H[j]-ep)/ep;av=(ep-L[j])/ep
        else:fv=(ep-L[j])/ep;av=(H[j]-ep)/ep
        if fv>mfe:mfe=fv;mfb=bi
        if av>mae:mae=av;mab=bi
        # Fixed TP/SL (SL first within bar)
        if not res["fixed"]:
            if sd=="LONG":hs=L[j]<=sl;ht=H[j]>=tp
            else:hs=H[j]>=sl;ht=L[j]<=tp
            if hs:res["fixed"]=("SL",bi,round((-sl_p-cost)*100,3))
            elif ht:res["fixed"]=("TP",bi,round((tp_p-cost)*100,3))
        # Prot swing SL
        if not res["prot"]:
            if sd=="LONG":hs=L[j]<=psl;ht=H[j]>=tp
            else:hs=H[j]>=psl;ht=L[j]<=tp
            if hs:
                d=abs(ep-psl)/ep;res["prot"]=("PSL",bi,round((-d-cost)*100,3))
            elif ht:res["prot"]=("TP",bi,round((tp_p-cost)*100,3))
        # EMA exit
        if not res["ema"]:
            if sd=="LONG" and C[j]<ef[j]:
                p=(C[j]-ep)/ep-cost;res["ema"]=("EMA",bi,round(p*100,3))
            elif sd=="SHORT" and C[j]>ef[j]:
                p=(ep-C[j])/ep-cost;res["ema"]=("EMA",bi,round(p*100,3))
        # Trailing (move SL to entry+0.3% after 0.5% profit, keep TP)
        if not res["trail"]:
            if not be:
                if sd=="LONG" and H[j]>=ep*1.005:be=True;tsl=ep*1.003
                elif sd=="SHORT" and L[j]<=ep*0.995:be=True;tsl=ep*0.997
            if sd=="LONG":hs=L[j]<=tsl;ht=H[j]>=tp
            else:hs=H[j]>=tsl;ht=L[j]<=tp
            if hs:
                p=(tsl-ep)/ep if sd=="LONG" else (ep-tsl)/ep;p-=cost
                res["trail"]=("TRL" if be else "SL",bi,round(p*100,3))
            elif ht:res["trail"]=("TP",bi,round((tp_p-cost)*100,3))
        # Break-even only (move SL to entry after 0.5%, no trail further, keep TP)
        if not res["be"]:
            besl=sl;beon=False
            if not beon:
                if sd=="LONG" and H[j]>=ep*1.005:beon=True;besl=ep
                elif sd=="SHORT" and L[j]<=ep*0.995:beon=True;besl=ep
            if sd=="LONG":hs=L[j]<=besl;ht=H[j]>=tp
            else:hs=H[j]>=besl;ht=L[j]<=tp
            if hs:
                p=(besl-ep)/ep if sd=="LONG" else (ep-besl)/ep;p-=cost
                res["be"]=("BE" if beon else "SL",bi,round(p*100,3))
            elif ht:res["be"]=("TP",bi,round((tp_p-cost)*100,3))
    # Timeout
    to_p=(C[min(end-1,n-1)]-ep)/ep if sd=="LONG" else (ep-C[min(end-1,n-1)])/ep;to_p-=cost
    to=("TO",mx,round(to_p*100,3))
    for k in res:
        if not res[k]:res[k]=to
    return {"mfe":round(mfe*100,3),"mae":round(mae*100,3),"mfb":mfb,"mab":mab,**res}


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
        r1h=_ld(symbol,"1h",days)
        if len(r1h)<max(ema_period,ema_slow)+60:return{"error":"not enough 1h"}
        r15m=_ld(symbol,"15m",days)
        if not r15m:return{"error":"no 15m data","detail":"15m candles required for entry B/C"}
        
        O=np.array([r[1] for r in r1h],dtype=float);H=np.array([r[2] for r in r1h],dtype=float)
        L=np.array([r[3] for r in r1h],dtype=float);C=np.array([r[4] for r in r1h],dtype=float)
        V=np.array([r[5] for r in r1h],dtype=float);T=[r[0] for r in r1h];n=len(r1h)
        ef=_ema(C,ema_period);es=_ema(C,ema_slow);at=_atr(H,L,C)
        hl=H.tolist();ll=L.tolist();cl=C.tolist();vl=V.tolist()
        vahs,vals,pocs=_va(hl,ll,cl,vl,50)
        cost=fee_pct+slippage_pct;not_=500.0
        
        # 15m indexed
        m15={r[0]:{"o":float(r[1]),"h":float(r[2]),"l":float(r[3]),"c":float(r[4])} for r in r15m}
        
        cfg=Mode3BBCConfig()
        cfg.ema_period=ema_period;cfg.tp_pct=tp_pct;cfg.sl_pct=sl_pct
        cfg.bull_body_ratio_min=bull_body;cfg.bear_body_ratio_min=bear_body
        cfg.bull_mtf_15m_enabled=False;cfg.bear_mtf_15m_enabled=False
        cfg.sideways_mtf_15m_enabled=False;cfg.enable_sideways_trades=False
        cfg.direct_transition_enabled=True;cfg.fee_pct_roundtrip=fee_pct;cfg.slippage_pct=slippage_pct

        det=ContinuationDetectorV2(ema_period,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        sc=SigCollect(cfg,det)
        for i in range(n):
            det.process(i,O,H,L,C,ef,es,at)
            sc.process_candle(i,O[i],H[i],L[i],C[i],ef[i],vahs[i],vals[i],pocs[i])

        sigs=sc.sigs
        for s in sigs:
            i=s["b"];s["ema"]=float(ef[i]);s["dist"]=round(100*abs(s["p"]-ef[i])/ef[i],3) if ef[i]>0 else 0;s["t"]=T[i]

        mid=n//2;tot_days=days;ex_modes=["fixed","prot","ema","trail","be"]
        results={}

        for em in["A","B","C","D"]:
            tds={x:[] for x in ex_modes};fl=0;sk=0;caus=[]
            for s in sigs:
                i=s["b"];sd=s["sd"];pr=s.get("pr");t1h=s["t"]
                # CAUSALITY: signal known at T = 1H close timestamp
                # All entries must happen AFTER T
                
                if em=="A":
                    # Market at 1H close = entry at T (just after close)
                    ep=s["p"];ebi=i;fill=True
                    caus.append({"signal_bar":i,"entry_bar":i,"entry_after_signal":True,
                        "same_bar_fill":True,"note":"market at close, acceptable"})
                
                elif em=="B":
                    # Open of NEXT 15m candle (first 15m of next hour)
                    nxt=t1h+3600*1000  # start of next hour
                    if nxt not in m15:sk+=1;continue
                    ep=m15[nxt]["o"];ebi=i+1 if i+1<n else i;fill=True
                    caus.append({"signal_bar":i,"entry_bar":ebi,"entry_ts":nxt,
                        "entry_after_signal":True,"15m_open":True})
                
                elif em=="C":
                    # Close of NEXT 15m candle if still valid (close > EMA for LONG)
                    nxt=t1h+3600*1000
                    if nxt not in m15:sk+=1;continue
                    c15=m15[nxt]
                    if sd=="LONG":
                        valid=c15["c"]>s["ema"] and c15["c"]>c15["o"]  # still bullish
                    else:
                        valid=c15["c"]<s["ema"] and c15["c"]<c15["o"]
                    if not valid:sk+=1;continue
                    ep=c15["c"];ebi=i+1 if i+1<n else i;fill=True
                    caus.append({"signal_bar":i,"entry_bar":ebi,"15m_close_valid":True,
                        "entry_after_signal":True})
                
                elif em=="D":
                    # Limit at EMA, placed after signal, valid next 1H bar only
                    if i+1>=n:sk+=1;continue
                    ea=s["ema"]
                    # Fill check: does next 1H bar touch EMA?
                    if sd=="LONG":fill=L[i+1]<=ea  # price dips to EMA
                    else:fill=H[i+1]>=ea
                    if not fill:sk+=1;continue
                    ep=float(ea);ebi=i+1
                    caus.append({"signal_bar":i,"entry_bar":ebi,"limit_at_ema":True,
                        "placed_after_signal":True,"filled_next_bar":True,
                        "signal_bar_NOT_used_for_fill":True})
                
                fl+=1
                r=_run_trade(ebi,ep,sd,H,L,C,ef,pr,n,tp_pct,sl_pct,cost)
                for x in ex_modes:
                    ev=r[x]
                    tds[x].append({"t":ev[0],"b":ev[1],"p":ev[2],"sd":sd,"eb":ebi,
                        "mfe":r["mfe"],"mae":r["mae"],"mfb":r["mfb"],"mab":r["mab"]})

            for x in ex_modes:
                tl=tds[x];nt=len(tl)
                if nt==0:results[f"{em}_{x}"]={"e":em,"x":x,"n":0,"sk":sk};continue
                ws=[t for t in tl if t["p"]>0];ls_=[t for t in tl if t["p"]<=0]
                gr=sum((t["p"]+cost*100)/100*not_ for t in tl)
                ne=sum(t["p"]/100*not_ for t in tl)
                mfes=sorted([t["mfe"] for t in tl]);maes=sorted([t["mae"] for t in tl])
                bars=[t["b"] for t in tl]
                # Per trade PnL for avg win/loss
                w_pnls=[t["p"]/100*not_ for t in ws];l_pnls=[t["p"]/100*not_ for t in ls_]
                avg_w=round(np.mean(w_pnls),2) if w_pnls else 0
                avg_l=round(np.mean(l_pnls),2) if l_pnls else 0
                # R = avg_win / abs(avg_loss)
                r_val=round(avg_w/abs(avg_l),2) if avg_l!=0 else 0
                # Walk-forward
                tr=[t for t in tl if t["eb"]<mid];te=[t for t in tl if t["eb"]>=mid]
                trn=sum(t["p"]/100*not_ for t in tr) if tr else 0
                ten=sum(t["p"]/100*not_ for t in te) if te else 0
                trw=sum(1 for t in tr if t["p"]>0);tew=sum(1 for t in te if t["p"]>0)
                # Drawdown + loss streak
                eq=0;pk=0;dd=0;ms=0;cs=0
                for t in tl:
                    eq+=t["p"]/100*not_;pk=max(pk,eq);dd=max(dd,pk-eq)
                    if t["p"]<=0:cs+=1;ms=max(ms,cs)
                    else:cs=0
                eb={};[eb.update({t["t"]:eb.get(t["t"],0)+1}) for t in tl]
                lo=[t for t in tl if t["sd"]=="LONG"];sh=[t for t in tl if t["sd"]=="SHORT"]
                # Coverage
                tpd=round(nt/tot_days,3)

                results[f"{em}_{x}"]={
                    "e":em,"x":x,"n_sig":len(sigs),"n_filled":fl,"n_closed":nt,
                    "fill_rate":round(100*fl/(fl+sk),1) if fl+sk else 0,
                    "trades_per_day":tpd,
                    "wr":round(100*len(ws)/nt,1),"gr":round(gr,2),"ne":round(ne,2),
                    "ge":round(gr/nt,3),"nee":round(ne/nt,3),
                    "avg_w":avg_w,"avg_l":avg_l,"R":r_val,
                    "dd":round(dd,2),"mls":ms,
                    "avg_hold":round(np.mean(bars),1),"med_hold":round(float(np.median(bars)),1),
                    "mfe_p25":round(mfes[max(0,len(mfes)//4)],2),"mfe_p50":round(mfes[len(mfes)//2],2),"mfe_p75":round(mfes[min(len(mfes)-1,3*len(mfes)//4)],2),
                    "mae_p25":round(maes[max(0,len(maes)//4)],2),"mae_p50":round(maes[len(maes)//2],2),"mae_p75":round(maes[min(len(maes)-1,3*len(maes)//4)],2),
                    "eb":eb,
                    "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                    "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                    "wf":{"trN":len(tr),"trWR":round(100*trw/len(tr),1) if tr else 0,"trP":round(trn,2),
                           "teN":len(te),"teWR":round(100*tew/len(te),1) if te else 0,"teP":round(ten,2)},
                }

        ds=[s["dist"] for s in sigs]
        return{
            "symbol":symbol,"days":days,"n":n,"n_sigs":len(sigs),"n_15m":len(r15m),
            "cost":cost,"notional":not_,
            "dist":{"mean":round(np.mean(ds),2),"med":round(float(np.median(ds)),2),
                    "p25":round(float(np.percentile(ds,25)),2),"p75":round(float(np.percentile(ds,75)),2)},
            "coverage_note":f"{len(sigs)} signals / {days} days = {round(len(sigs)/days,3)} sig/day (target: 1.0)",
            "causality_samples":caus[:5] if caus else [],
            "results":results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
