"""A+C Frozen TP/SL Sweep + Integrated Rerun.

Phase 1: Frozen exit sweep — same entries, vary TP/SL independently (no position blocking)
Phase 2: Integrated rerun — top configs with one-position-per-pair

GET /v25/sweep?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v25", tags=["v25_sweep"])
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

# Import V25Detector
from v25_detector_endpoint import V25Detector

@router.get("/sweep")
def ac_sweep(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
    impulse_atr:float=Query(1.5),body_min:float=Query(0.3),
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
        n5=len(r15m);T5=[r[0] for r in r15m]
        ef5=_ema(C5,ema_15m)
        t5_idx={T5[i]:i for i in range(n5)}
        not_=500.0

        # V2.5 regime
        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_arr=[]
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_arr.append(s)

        # Generate frozen A+C 15m_reclaim candidates
        cands=[];M=15*60*1000
        for i in range(max(ema_slow*2,60),n1):
            if tiers[i] not in("A","C"):continue
            sd=sides_arr[i]
            if sd is None:continue
            side="LONG" if sd=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is None or j<ema_15m*2:continue
                o5,h5,l5,c5=O5[j],H5[j],L5[j],C5[j];e5=ef5[j]
                br=h5-l5;bd=abs(c5-o5);bdy=bd/br if br>0 else 0
                if side=="LONG":ok=(l5<=e5)and(c5>e5)and(c5>o5)and(bdy>=body_min)
                else:ok=(h5>=e5)and(c5<e5)and(c5<o5)and(bdy>=body_min)
                if ok:cands.append({"j":j,"sd":side,"ep":float(c5),"tier":tiers[i]});break

        n_cand=len(cands)
        tps=[0.004,0.006,0.008,0.010,0.013,0.015,0.020,0.025,0.030]
        sls=[0.004,0.006,0.008,0.010,0.013,0.015,0.020,0.025]
        fees=[0.0010,0.0015]  # 0.10% and 0.15% round-trip
        third=n5//3

        # ═══ PHASE 1: Frozen exit sweep (no position blocking) ═══
        # Pre-compute per-entry: for each entry, find first TP/SL touch at each level
        # This avoids redundant scanning
        entry_data=[]
        for c in cands:
            j=c["j"];ep=c["ep"];sd=c["sd"]
            # Track price path for 200 bars
            mfe=0;mae=0
            # For each TP/SL level, find first touch bar
            tp_bars={};sl_bars={}
            for tp in tps:
                tp_l=ep*(1+tp) if sd=="LONG" else ep*(1-tp)
                found=False
                for jj in range(j+1,min(j+200,n5)):
                    if sd=="LONG" and H5[jj]>=tp_l:tp_bars[tp]=jj-j;found=True;break
                    elif sd=="SHORT" and L5[jj]<=tp_l:tp_bars[tp]=jj-j;found=True;break
                if not found:tp_bars[tp]=999
            for sl in sls:
                sl_l=ep*(1-sl) if sd=="LONG" else ep*(1+sl)
                found=False
                for jj in range(j+1,min(j+200,n5)):
                    if sd=="LONG" and L5[jj]<=sl_l:sl_bars[sl]=jj-j;found=True;break
                    elif sd=="SHORT" and H5[jj]>=sl_l:sl_bars[sl]=jj-j;found=True;break
                if not found:sl_bars[sl]=999
            # MFE/MAE
            for jj in range(j+1,min(j+50,n5)):
                if sd=="LONG":fv=(H5[jj]-ep)/ep;av=(ep-L5[jj])/ep
                else:fv=(ep-L5[jj])/ep;av=(H5[jj]-ep)/ep
                if fv>mfe:mfe=fv
                if av>mae:mae=av
            entry_data.append({"j":j,"sd":sd,"ep":ep,"tier":c["tier"],
                "tp_bars":tp_bars,"sl_bars":sl_bars,"mfe":round(mfe*100,3),"mae":round(mae*100,3)})

        # Sweep: for each TP×SL×fee, compute stats from pre-computed touch bars
        frozen=[]
        for tp in tps:
            for sl in sls:
                for fee in fees:
                    cost=fee+0.0005  # slippage always 0.05%
                    wins=0;losses=0;tos=0;pnls=[];bars_list=[]
                    lo_w=0;lo_n=0;sh_w=0;sh_n=0
                    f_pnls=[[],[],[]]  # per fold
                    for ed in entry_data:
                        tb=ed["tp_bars"][tp];sb=ed["sl_bars"][sl]
                        if sb<=tb:  # SL first (or same bar = SL wins)
                            if sb<999:
                                p=(-sl-cost)*100;losses+=1;bars_list.append(sb)
                            else:
                                p=0;tos+=1;bars_list.append(200)
                        else:
                            if tb<999:
                                p=(tp-cost)*100;wins+=1;bars_list.append(tb)
                            else:
                                p=0;tos+=1;bars_list.append(200)
                        pnls.append(p)
                        if ed["sd"]=="LONG":lo_n+=1;lo_w+=(1 if p>0 else 0)
                        else:sh_n+=1;sh_w+=(1 if p>0 else 0)
                        # Fold assignment
                        fi=0 if ed["j"]<third else(1 if ed["j"]<2*third else 2)
                        f_pnls[fi].append(p)

                    nt=len(pnls)
                    if nt==0:continue
                    gr=sum((p+cost*100)/100*not_ for p in pnls)
                    ne=sum(p/100*not_ for p in pnls)
                    w_pnls=[p/100*not_ for p in pnls if p>0]
                    l_pnls=[p/100*not_ for p in pnls if p<=0]
                    aw=round(np.mean(w_pnls),2) if w_pnls else 0
                    al=round(np.mean(l_pnls),2) if l_pnls else 0
                    # Drawdown + loss streak
                    eq=0;pk=0;dd=0;ms=0;cs=0
                    for p in pnls:
                        eq+=p/100*not_;pk=max(pk,eq);dd=max(dd,pk-eq)
                        if p<=0:cs+=1;ms=max(ms,cs)
                        else:cs=0
                    # WF
                    fp=[round(sum(f)/100*not_,2) for f in f_pnls]
                    fn=[len(f) for f in f_pnls]
                    pos_f=sum(1 for p in fp if p>0)
                    be_wr=round(100*(sl+cost)/(tp+sl),1)

                    frozen.append({
                        "tp":round(tp*100,1),"sl":round(sl*100,1),"fee":round(fee*100,2),
                        "n":nt,"tpd_frozen":round(nt/days,3),"be":be_wr,
                        "wr":round(100*wins/nt,1),"edge":round(100*wins/nt-be_wr,1),
                        "gr":round(gr,2),"ne":round(ne,2),"nee":round(ne/nt,3),
                        "aw":aw,"al":al,"R":round(aw/abs(al),2) if al else 0,
                        "dd":round(dd,2),"mls":ms,"avg_h":round(np.mean(bars_list),1),
                        "tp_rate":round(100*wins/nt,1),
                        "L":{"n":lo_n,"wr":round(100*lo_w/lo_n,1) if lo_n else 0},
                        "S":{"n":sh_n,"wr":round(100*sh_w/sh_n,1) if sh_n else 0},
                        "wf":{"F1":{"n":fn[0],"p":fp[0]},"F2":{"n":fn[1],"p":fp[1]},"F3":{"n":fn[2],"p":fp[2]},"pos":pos_f},
                    })

        frozen.sort(key=lambda x:x["ne"],reverse=True)

        # ═══ PHASE 2: Integrated rerun for top 10 net-positive configs ═══
        top_configs=[(r["tp"],r["sl"],r["fee"]) for r in frozen[:15] if r["ne"]>0]
        integrated=[]
        for tp_pct100,sl_pct100,fee_pct100 in top_configs:
            tp=tp_pct100/100;sl=sl_pct100/100;cost=fee_pct100/100+0.0005
            trades=[];pos_end=-1
            for c in cands:
                j=c["j"];sd=c["sd"];ep=c["ep"]
                if j<=pos_end:continue  # one position at a time
                if sd=="LONG":tp_l=ep*(1+tp);sl_l=ep*(1-sl)
                else:tp_l=ep*(1-tp);sl_l=ep*(1+sl)
                res=None
                for jj in range(j+1,min(j+200,n5)):
                    if sd=="LONG":hs=L5[jj]<=sl_l;ht=H5[jj]>=tp_l
                    else:hs=H5[jj]>=sl_l;ht=L5[jj]<=tp_l
                    if hs and ht:ht=False
                    if hs:res={"x":"SL","b":jj-j,"p":round((-sl-cost)*100,3),"sd":sd,"j":j};pos_end=jj;break
                    if ht:res={"x":"TP","b":jj-j,"p":round((tp-cost)*100,3),"sd":sd,"j":j};pos_end=jj;break
                if not res:
                    eb=min(j+200,n5)-1;pp=(C5[eb]-ep)/ep if sd=="LONG" else (ep-C5[eb])/ep;pp-=cost
                    res={"x":"TO","b":200,"p":round(pp*100,3),"sd":sd,"j":j};pos_end=eb
                trades.append(res)
            nt=len(trades)
            if nt==0:continue
            ws=[t for t in trades if t["p"]>0]
            gr=sum((t["p"]+cost*100)/100*not_ for t in trades)
            ne=sum(t["p"]/100*not_ for t in trades)
            w_p=[t["p"]/100*not_ for t in ws];l_p=[t["p"]/100*not_ for t in trades if t["p"]<=0]
            eq=0;pk=0;dd=0;ms=0;cs=0
            for t in trades:eq+=t["p"]/100*not_;pk=max(pk,eq);dd=max(dd,pk-eq)
            for t in trades:
                if t["p"]<=0:cs+=1;ms=max(ms,cs)
                else:cs=0
            lo=[t for t in trades if t["sd"]=="LONG"];sh=[t for t in trades if t["sd"]=="SHORT"]
            fp=[[],[],[]];
            for t in trades:
                fi=0 if t["j"]<third else(1 if t["j"]<2*third else 2)
                fp[fi].append(t["p"]/100*not_)
            fps=[round(sum(f),2) for f in fp];fns=[len(f) for f in fp]
            integrated.append({
                "tp":tp_pct100,"sl":sl_pct100,"fee":fee_pct100,
                "n":nt,"tpd":round(nt/days,3),
                "wr":round(100*len(ws)/nt,1),"gr":round(gr,2),"ne":round(ne,2),"nee":round(ne/nt,3),
                "aw":round(np.mean(w_p),2) if w_p else 0,"al":round(np.mean(l_p),2) if l_p else 0,
                "dd":round(dd,2),"mls":ms,"avg_h":round(np.mean([t["b"] for t in trades]),1),
                "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                "wf":{"F1":{"n":fns[0],"p":fps[0]},"F2":{"n":fns[1],"p":fps[1]},"F3":{"n":fns[2],"p":fps[2]},"pos":sum(1 for p in fps if p>0)},
            })

        return{
            "symbol":symbol,"days":days,"n_cand":n_cand,"n_15m":n5,
            "frozen_top20":frozen[:20],"frozen_bottom5":frozen[-5:],
            "frozen_total":len(frozen),
            "frozen_net_positive":sum(1 for r in frozen if r["ne"]>0),
            "integrated":integrated,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
