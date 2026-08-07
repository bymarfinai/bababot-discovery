"""Coverage-preserving exit study — max hold + exit variants on frozen 15m_reclaim.

Tests: TP/SL configs × max_hold limits × exit methods
Max hold forces exit at close of Nth 15m bar if TP/SL not hit.

GET /v2_gated/m15_hold?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v2_gated", tags=["m15_hold"])
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

@router.get("/m15_hold")
def m15_hold_study(
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

        det=ContinuationDetectorV2(ema_1h,ema_slow,swing_lb,swing_atr,3,min_pb_bars=1)
        regime=[]
        for i in range(n1):
            det.process(i,O1,H1,L1,C1,ef1,es1,at1);regime.append(det.regime)

        # Frozen candidates
        cands=[];M=15*60*1000
        for i in range(max(ema_slow*2,60),n1):
            reg=regime[i]
            if reg not in("BULL","BEAR"):continue
            sd="LONG" if reg=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is None or j<ema_15m*2:continue
                o5,h5,l5,c5=O5[j],H5[j],L5[j],C5[j];e5=ef5[j]
                br=h5-l5;bd=abs(c5-o5);bdy=bd/br if br>0 else 0
                if sd=="LONG":ok=(l5<=e5)and(c5>e5)and(c5>o5)and(bdy>=body_min)
                else:ok=(h5>=e5)and(c5<e5)and(c5<o5)and(bdy>=body_min)
                if ok:cands.append({"j":j,"sd":sd,"ep":float(c5)});break

        # Configs to test
        tp_sl_configs=[
            (0.013,0.013,"sym1.3"),
            (0.020,0.013,"tp2_sl1.3"),
            (0.025,0.013,"tp2.5_sl1.3"),
            (0.030,0.013,"tp3_sl1.3"),
            (0.030,0.025,"tp3_sl2.5"),
            (0.025,0.025,"tp2.5_sl2.5"),
        ]
        max_holds=[4,8,16,32,48,200]  # 200=effectively unlimited
        third=n5//3
        results=[]

        for tp,sl,cfg_name in tp_sl_configs:
            for mh in max_holds:
                trades=[];pos_end=-1
                bull_trades=[];bear_trades=[]
                for c in cands:
                    j=c["j"];sd=c["sd"];ep=c["ep"]
                    if j<=pos_end:continue
                    if sd=="LONG":tp_l=ep*(1+tp);sl_l=ep*(1-sl)
                    else:tp_l=ep*(1-tp);sl_l=ep*(1+sl)
                    res=None
                    for jj in range(j+1,min(j+mh+1,n5)):
                        bi=jj-j
                        if sd=="LONG":hs=L5[jj]<=sl_l;ht=H5[jj]>=tp_l
                        else:hs=H5[jj]>=sl_l;ht=L5[jj]<=tp_l
                        if hs and ht:ht=False  # SL first
                        if hs:res={"x":"SL","b":bi,"p":round((-sl-cost)*100,3)};pos_end=jj;break
                        if ht:res={"x":"TP","b":bi,"p":round((tp-cost)*100,3)};pos_end=jj;break
                    if not res:
                        # Max hold timeout — exit at close
                        eb=min(j+mh,n5-1)
                        pp=(C5[eb]-ep)/ep if sd=="LONG" else (ep-C5[eb])/ep;pp-=cost
                        res={"x":"MH","b":min(mh,n5-j-1),"p":round(pp*100,3)};pos_end=eb
                    res["sd"]=sd;res["j"]=j;trades.append(res)
                    if sd=="LONG":bull_trades.append(res)
                    else:bear_trades.append(res)

                nt=len(trades)
                if nt==0:continue

                def _agg(tl,label):
                    nn=len(tl)
                    if nn==0:return{"n":0}
                    ws=[t for t in tl if t["p"]>0]
                    gr=sum((t["p"]+cost*100)/100*notional for t in tl)
                    ne=sum(t["p"]/100*notional for t in tl)
                    wp=[t["p"]/100*notional for t in ws];lp=[t["p"]/100*notional for t in tl if t["p"]<=0]
                    eq=0;pk=0;dd=0;ms=0;cs=0
                    for t in tl:eq+=t["p"]/100*notional;pk=max(pk,eq);dd=max(dd,pk-eq)
                    for t in tl:
                        if t["p"]<=0:cs+=1;ms=max(ms,cs)
                        else:cs=0
                    eb={};[eb.update({t["x"]:eb.get(t["x"],0)+1}) for t in tl]
                    # Walk-forward
                    f1=[t for t in tl if t["j"]<third];f2=[t for t in tl if third<=t["j"]<2*third];f3=[t for t in tl if t["j"]>=2*third]
                    fp=[sum(t["p"]/100*notional for t in f) for f in[f1,f2,f3]]
                    fn=[len(f) for f in[f1,f2,f3]]
                    pos_folds=sum(1 for p in fp if p>0)
                    return{
                        "n":nn,"tpd":round(nn/days,3),
                        "wr":round(100*len(ws)/nn,1),"gr":round(gr,2),"ne":round(ne,2),
                        "nee":round(ne/nn,3),
                        "aw":round(np.mean(wp),2) if wp else 0,"al":round(np.mean(lp),2) if lp else 0,
                        "dd":round(dd,2),"mls":ms,
                        "avg_h":round(np.mean([t["b"] for t in tl]),1),
                        "exits":eb,
                        "wf":{
                            "F1":{"n":fn[0],"p":round(fp[0],2)},"F2":{"n":fn[1],"p":round(fp[1],2)},"F3":{"n":fn[2],"p":round(fp[2],2)},
                            "pos":pos_folds,
                        },
                    }

                r=_agg(trades,"all")
                r["cfg"]=cfg_name;r["mh"]=mh;r["tp"]=round(tp*100,1);r["sl"]=round(sl*100,1)
                r["bull"]=_agg(bull_trades,"bull")
                r["bear"]=_agg(bear_trades,"bear")
                results.append(r)

        # Sort by: coverage >= 1.0 first, then net PnL
        results.sort(key=lambda x:(-1 if x["tpd"]>=1.0 and x["ne"]>0 else 0, x["ne"]),reverse=True)

        return{
            "symbol":symbol,"days":days,"n_1h":n1,"n_15m":n5,
            "frozen_candidates":len(cands),"cost":cost,"notional":notional,
            "total_configs":len(results),
            "results":results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
