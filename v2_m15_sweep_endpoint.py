"""Frozen 15m_reclaim TP/SL Sweep — asymmetric sweep on frozen entry stream.

Entries generated ONCE from V2 regime + 15m EMA reclaim.
TP/SL swept independently. One position at a time per run.
First-touch: SL priority on same-bar TP+SL.

GET /v2_gated/m15_sweep?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["m15_sweep"])
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
    for i in range(1,n):t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]));a[i]=a[i-1]+(t-a[i-1])/min(i,p)
    return a

@router.get("/m15_sweep")
def m15_sweep(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),body_min:float=Query(0.3),
):
    try:
        r1h=_ld(symbol,"1h",days);r15m=_ld(symbol,"15m",days)
        if len(r1h)<ema_slow*2+60:return{"error":"not enough 1h"}
        if not r15m:return{"error":"no 15m data"}

        O1=np.array([r[1] for r in r1h],dtype=float);H1=np.array([r[2] for r in r1h],dtype=float)
        L1=np.array([r[3] for r in r1h],dtype=float);C1=np.array([r[4] for r in r1h],dtype=float)
        T1=[r[0] for r in r1h];n1=len(r1h)
        ef1=_ema(C1,ema_1h);es1=_ema(C1,ema_slow);at1=_atr(H1,L1,C1)

        O5=np.array([r[1] for r in r15m],dtype=float);H5=np.array([r[2] for r in r15m],dtype=float)
        L5=np.array([r[3] for r in r15m],dtype=float);C5=np.array([r[4] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m)
        t5_idx={T5[i]:i for i in range(n5)}

        cost=fee_pct+slippage_pct;notional=500.0

        # V2 regime
        det=ContinuationDetectorV2(ema_1h,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        regime=[]
        for i in range(n1):
            det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            regime.append(det.regime)

        # Generate frozen entry candidates (15m_reclaim)
        candidates=[]  # (15m_bar_idx, side, entry_price)
        M=15*60*1000
        for i in range(max(ema_slow*2,60),n1):
            reg=regime[i]
            if reg not in("BULL","BEAR"):continue
            side="LONG" if reg=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is None or j<ema_15m*2:continue
                o5,h5,l5,c5=O5[j],H5[j],L5[j],C5[j];e5=ef5[j]
                br=h5-l5;bd=abs(c5-o5);bdy=bd/br if br>0 else 0
                if side=="LONG":ok=(l5<=e5)and(c5>e5)and(c5>o5)and(bdy>=body_min)
                else:ok=(h5>=e5)and(c5<e5)and(c5<o5)and(bdy>=body_min)
                if ok:
                    candidates.append({"j":j,"sd":side,"ep":float(c5),"t":t15})
                    break  # one per 1H bar

        n_cand=len(candidates)
        # Walk-forward folds
        third=n5//3
        folds=[(0,third,"F1"),(third,2*third,"F2"),(2*third,n5,"F3")]

        # TP/SL sweep
        tps=[0.004,0.006,0.008,0.010,0.013,0.015,0.020,0.025,0.030]
        sls=[0.004,0.006,0.008,0.010,0.013,0.015,0.020,0.025]
        results=[]

        for tp in tps:
            for sl in sls:
                # Simulate with one-position-at-a-time
                trades=[];pos_end=-1
                for c in candidates:
                    j=c["j"];sd=c["sd"];ep=c["ep"]
                    if j<=pos_end:continue  # blocked by open position
                    # First-touch from j+1
                    if sd=="LONG":tp_l=ep*(1+tp);sl_l=ep*(1-sl)
                    else:tp_l=ep*(1-tp);sl_l=ep*(1+sl)
                    result=None
                    for jj in range(j+1,min(j+200,n5)):
                        if sd=="LONG":
                            hit_sl=L5[jj]<=sl_l;hit_tp=H5[jj]>=tp_l
                        else:
                            hit_sl=H5[jj]>=sl_l;hit_tp=L5[jj]<=tp_l
                        # SL first on same bar
                        if hit_sl and hit_tp:hit_tp=False
                        if hit_sl:
                            result={"x":"SL","b":jj-j,"p":round((-sl-cost)*100,3),"sd":sd,"j":j}
                            pos_end=jj;break
                        if hit_tp:
                            result={"x":"TP","b":jj-j,"p":round((tp-cost)*100,3),"sd":sd,"j":j}
                            pos_end=jj;break
                    if not result:
                        eb=min(j+200,n5)-1
                        pp=(C5[eb]-ep)/ep if sd=="LONG" else (ep-C5[eb])/ep;pp-=cost
                        result={"x":"TO","b":200,"p":round(pp*100,3),"sd":sd,"j":j}
                        pos_end=eb
                    trades.append(result)

                nt=len(trades)
                if nt==0:continue
                ws=[t for t in trades if t["p"]>0]
                gr=sum((t["p"]+cost*100)/100*notional for t in trades)
                ne=sum(t["p"]/100*notional for t in trades)
                w_pnl=[t["p"]/100*notional for t in ws]
                l_pnl=[t["p"]/100*notional for t in trades if t["p"]<=0]
                aw=round(np.mean(w_pnl),2) if w_pnl else 0
                al=round(np.mean(l_pnl),2) if l_pnl else 0
                # Drawdown + loss streak
                eq=0;pk=0;dd=0;ms=0;cs=0
                for t in trades:
                    eq+=t["p"]/100*notional;pk=max(pk,eq);dd=max(dd,pk-eq)
                    if t["p"]<=0:cs+=1;ms=max(ms,cs)
                    else:cs=0
                bars=[t["b"] for t in trades]
                eb={};[eb.update({t["x"]:eb.get(t["x"],0)+1}) for t in trades]
                lo=[t for t in trades if t["sd"]=="LONG"];sh=[t for t in trades if t["sd"]=="SHORT"]
                # Walk-forward per fold
                wf={}
                for fs,fe,fn in folds:
                    ft=[t for t in trades if fs<=t["j"]<fe]
                    fn_=sum(t["p"]/100*notional for t in ft)
                    fw=sum(1 for t in ft if t["p"]>0)
                    wf[fn]={"n":len(ft),"wr":round(100*fw/len(ft),1) if ft else 0,"pnl":round(fn_,2)}
                # BE WR
                be_wr=round(100*(sl+cost)/(tp+sl),1)

                results.append({
                    "tp":round(tp*100,1),"sl":round(sl*100,1),"be_wr":be_wr,
                    "n":nt,"tpd":round(nt/days,3),
                    "wr":round(100*len(ws)/nt,1),"edge":round(100*len(ws)/nt-be_wr,1),
                    "gr":round(gr,2),"ne":round(ne,2),
                    "ge":round(gr/nt,3),"nee":round(ne/nt,3),
                    "aw":aw,"al":al,"R":round(aw/abs(al),2) if al else 0,
                    "dd":round(dd,2),"mls":ms,
                    "avg_hold":round(np.mean(bars),1),
                    "tp_rate":round(100*eb.get("TP",0)/nt,1),
                    "exits":eb,
                    "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                    "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                    "wf":wf,
                })

        # Sort by net PnL
        results.sort(key=lambda x:x["ne"],reverse=True)

        return{
            "symbol":symbol,"days":days,"n_1h":n1,"n_15m":n5,
            "frozen_candidates":n_cand,"cost":cost,"notional":notional,
            "top_20":results[:20],
            "bottom_5":results[-5:],
            "all_count":len(results),
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
