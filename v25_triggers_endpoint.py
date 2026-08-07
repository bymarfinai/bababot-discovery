"""Phase 3 — Entry trigger comparison on A+C regime stream.

Six triggers, all causal (decided at 15m candle close only):
A. Baseline 15m EMA reclaim/rejection
B. A + break previous 15m high/low
C. A + close-location + body-strength filter
D. A + ATR/range expansion
E. A + volume confirmation
F. Pullback retest + structural breakout

GET /v25/triggers?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,math,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from v25_detector_endpoint import V25Detector

router = APIRouter(prefix="/v25", tags=["v25_triggers"])
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

def _sma_vol(V,p=20):
    n=len(V);s=np.zeros(n)
    for i in range(p,n):s[i]=np.mean(V[i-p:i])
    return s

def _wilson(s,n):
    if n==0:return 0
    return round(100*s/n,1)

@router.get("/triggers")
def trigger_comparison(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
    impulse_atr:float=Query(1.5),body_min:float=Query(0.3),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
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
        V5=np.array([r[5] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m);at5=_atr(H5,L5,C5);vol_sma=_sma_vol(V5,20)
        t5_idx={T5[i]:i for i in range(n5)}
        cost=fee_pct+slippage_pct;not_=500.0

        # V2.5 regime on 1H
        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_arr=[]
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_arr.append(s)

        # Scan 15m candles during A+C regime
        M=15*60*1000
        # Collect ALL candidate 15m bars during A+C
        regime_15m=[]  # (j, side, 1h_bar_idx)
        for i in range(max(ema_slow*2,60),n1):
            if tiers[i] not in("A","C"):continue
            sd=sides_arr[i]
            if sd is None:continue
            side="LONG" if sd=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is not None and j>=max(ema_15m*2,21):
                    regime_15m.append((j,side,i))

        # For each 15m bar in regime, evaluate all triggers
        triggers={"A":[],"B":[],"C":[],"D":[],"E":[],"F":[]}
        
        for j,side,i1h in regime_15m:
            o,h,l,c=O5[j],H5[j],L5[j],C5[j]
            e5=ef5[j];rng=h-l;body=abs(c-o)
            bdy=body/rng if rng>0 else 0
            
            # ═══ TRIGGER A: baseline 15m EMA reclaim ═══
            if side=="LONG":
                a_ok=(l<=e5)and(c>e5)and(c>o)and(bdy>=body_min)
            else:
                a_ok=(h>=e5)and(c<e5)and(c<o)and(bdy>=body_min)
            
            if not a_ok:continue  # all triggers require A as base
            triggers["A"].append({"j":j,"sd":side,"ep":float(c)})
            
            # ═══ TRIGGER B: A + break prev 15m high/low ═══
            if j>=1:
                if side=="LONG":b_ok=c>H5[j-1]  # close breaks prev high
                else:b_ok=c<L5[j-1]
                if b_ok:triggers["B"].append({"j":j,"sd":side,"ep":float(c)})
            
            # ═══ TRIGGER C: A + close-location + body-strength ═══
            if rng>0:
                if side=="LONG":
                    cl_loc=(c-l)/rng  # close near top of range
                    c_ok=cl_loc>=0.7 and bdy>=0.5
                else:
                    cl_loc=(h-c)/rng
                    c_ok=cl_loc>=0.7 and bdy>=0.5
                if c_ok:triggers["C"].append({"j":j,"sd":side,"ep":float(c)})
            
            # ═══ TRIGGER D: A + ATR/range expansion ═══
            atr_15m=at5[j]
            if atr_15m>0:
                d_ok=rng>=1.2*atr_15m  # range > 1.2× ATR
                if d_ok:triggers["D"].append({"j":j,"sd":side,"ep":float(c)})
            
            # ═══ TRIGGER E: A + volume confirmation ═══
            avg_vol=vol_sma[j]
            if avg_vol>0:
                e_ok=V5[j]>=1.5*avg_vol  # volume > 1.5× avg
                if e_ok:triggers["E"].append({"j":j,"sd":side,"ep":float(c)})
            
            # ═══ TRIGGER F: pullback retest + structural breakout ═══
            if j>=5:
                # Look back 4 bars: was there a pullback (low touched EMA)?
                pb=any(L5[jj]<=ef5[jj] for jj in range(j-4,j)) if side=="LONG" else any(H5[jj]>=ef5[jj] for jj in range(j-4,j))
                # Current bar breaks above 4-bar high (LONG) or below 4-bar low (SHORT)
                if side=="LONG":
                    struct_hi=max(H5[j-4:j])
                    f_ok=pb and c>struct_hi
                else:
                    struct_lo=min(L5[j-4:j])
                    f_ok=pb and c<struct_lo
                if f_ok:triggers["F"].append({"j":j,"sd":side,"ep":float(c)})

        # ═══ EVALUATE each trigger ═══
        third=n5//3
        ref_tp=0.013;ref_sl=0.013  # reference TP/SL for first-touch
        tp_levels=[0.008,0.010,0.013,0.020,0.030]
        results={}
        
        for trig_name,entries in triggers.items():
            nt=len(entries)
            if nt==0:results[trig_name]={"n":0};continue
            
            mfes=[];maes=[];pnls_gross=[];pnls_net=[]
            ema_holds=0;prot_ok=0;tp_first=0
            bars=[];lo_n=0;lo_w=0;sh_n=0;sh_w=0
            # TP-before-SL at multiple levels
            tp_sl_rates={f"{t*100:.1f}":0 for t in tp_levels}
            # Per-fold
            fold_gross=[[],[],[]]
            
            for e in entries:
                j=e["j"];sd=e["sd"];ep=e["ep"]
                mfe=0;mae=0;mfe_b=0
                
                # First-touch at ref TP/SL
                if sd=="LONG":tp_l=ep*(1+ref_tp);sl_l=ep*(1-ref_sl)
                else:tp_l=ep*(1-ref_tp);sl_l=ep*(1+ref_sl)
                hit_tp_bar=999;hit_sl_bar=999
                
                for jj in range(j+1,min(j+200,n5)):
                    bi=jj-j
                    if sd=="LONG":fv=(H5[jj]-ep)/ep;av=(ep-L5[jj])/ep
                    else:fv=(ep-L5[jj])/ep;av=(H5[jj]-ep)/ep
                    if fv>mfe:mfe=fv;mfe_b=bi
                    if av>mae:mae=av
                    if hit_tp_bar==999:
                        if sd=="LONG" and H5[jj]>=tp_l:hit_tp_bar=bi
                        elif sd=="SHORT" and L5[jj]<=tp_l:hit_tp_bar=bi
                    if hit_sl_bar==999:
                        if sd=="LONG" and L5[jj]<=sl_l:hit_sl_bar=bi
                        elif sd=="SHORT" and H5[jj]>=sl_l:hit_sl_bar=bi
                
                mfes.append(mfe*100);maes.append(mae*100)
                
                # First-touch result
                if hit_sl_bar<=hit_tp_bar:  # SL first (or same bar)
                    p_gross=-ref_sl;p_net=-ref_sl-cost
                else:
                    p_gross=ref_tp;p_net=ref_tp-cost
                    tp_first+=1
                pnls_gross.append(p_gross*100);pnls_net.append(p_net*100)
                
                if hit_tp_bar<hit_sl_bar:bars.append(hit_tp_bar)
                elif hit_sl_bar<999:bars.append(hit_sl_bar)
                else:bars.append(200)
                
                # TP-before-SL at multiple TP levels (SL fixed at 1.3%)
                for t in tp_levels:
                    if sd=="LONG":tpl=ep*(1+t)
                    else:tpl=ep*(1-t)
                    tb=999
                    for jj in range(j+1,min(j+200,n5)):
                        if sd=="LONG" and H5[jj]>=tpl:tb=jj-j;break
                        elif sd=="SHORT" and L5[jj]<=tpl:tb=jj-j;break
                    if tb<hit_sl_bar:tp_sl_rates[f"{t*100:.1f}"]+=1
                
                # EMA hold (4 bars)
                end=min(j+5,n5)
                if sd=="LONG":
                    if all(C5[jj]>ef5[jj] for jj in range(j+1,end)):ema_holds+=1
                else:
                    if all(C5[jj]<ef5[jj] for jj in range(j+1,end)):ema_holds+=1
                
                # Protected swing (approximate)
                if sd=="LONG":
                    pl=min(L5[max(0,j-20):j+1])
                    if all(L5[jj]>=pl for jj in range(j+1,end)):prot_ok+=1
                else:
                    ph=max(H5[max(0,j-20):j+1])
                    if all(H5[jj]<=ph for jj in range(j+1,end)):prot_ok+=1
                
                if sd=="LONG":lo_n+=1;lo_w+=(1 if p_net>0 else 0)
                else:sh_n+=1;sh_w+=(1 if p_net>0 else 0)
                
                fi=0 if j<third else(1 if j<2*third else 2)
                fold_gross[fi].append(p_gross*100)
            
            gr_total=sum(p/100*not_ for p in pnls_gross)
            ne_total=sum(p/100*not_ for p in pnls_net)
            fp=[round(sum(f)/100*not_,2) for f in fold_gross]
            fn=[len(f) for f in fold_gross]
            mfes_s=sorted(mfes);maes_s=sorted(maes)
            
            results[trig_name]={
                "n":nt,"tpd":round(nt/days,3),
                "wr":round(100*tp_first/nt,1),
                "gr":round(gr_total,2),"ne":round(ne_total,2),
                "ge":round(gr_total/nt,3),"nee":round(ne_total/nt,3),
                "mfe_p50":round(mfes_s[len(mfes_s)//2],2),
                "mae_p50":round(maes_s[len(maes_s)//2],2),
                "mfe_p25":round(mfes_s[max(0,len(mfes_s)//4)],2),
                "mae_p25":round(maes_s[max(0,len(maes_s)//4)],2),
                "mfe_p75":round(mfes_s[min(len(mfes_s)-1,3*len(mfes_s)//4)],2),
                "mae_p75":round(maes_s[min(len(maes_s)-1,3*len(maes_s)//4)],2),
                "mfe_mae_ratio":round(mfes_s[len(mfes_s)//2]/maes_s[len(maes_s)//2],3) if maes_s[len(maes_s)//2]>0 else 0,
                "tp_before_sl":{k:round(100*v/nt,1) for k,v in tp_sl_rates.items()},
                "ema_hold":round(100*ema_holds/nt,1),
                "prot_surv":round(100*prot_ok/nt,1),
                "avg_hold":round(np.mean(bars),1),
                "L":{"n":lo_n,"wr":round(100*lo_w/lo_n,1) if lo_n else 0},
                "S":{"n":sh_n,"wr":round(100*sh_w/sh_n,1) if sh_n else 0},
                "wf":{"F1":{"n":fn[0],"p":fp[0]},"F2":{"n":fn[1],"p":fp[1]},"F3":{"n":fn[2],"p":fp[2]},
                      "pos":sum(1 for p in fp if p>0)},
            }

        return{
            "symbol":symbol,"days":days,"n_1h":n1,"n_15m":n5,
            "regime_15m_bars":len(regime_15m),
            "cost":cost,"ref_tp_sl":f"{ref_tp*100}/{ref_sl*100}%",
            "results":results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
