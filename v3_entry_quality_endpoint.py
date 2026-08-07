"""V3 Entry Quality — fundamentally different entry mechanisms.

A. Donchian breakout (close > N-bar high)
B. Volatility compression then breakout (ATR contracts, range expands)
C. Compression breakout + retest hold
D. Range expansion + strong close
E. Breakout + volume expansion

Plus: baseline EMA reclaim, matched control, random control.
All causal. MFE/MAE at horizons 1,2,4,8,16.

GET /v3/entry_quality?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,random,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from v25_detector_endpoint import V25Detector

router = APIRouter(prefix="/v3", tags=["v3_entry"])
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

def _measure(j, ep, sd, H5, L5, C5, n5):
    """Measure MFE/MAE/returns at multiple horizons. All from j+1 onward."""
    horizons=[1,2,4,8,16]
    out={}
    for hz in horizons:
        end=min(j+hz+1,n5)
        if j+1>=n5:out[hz]={"mfe":0,"mae":0,"ret":0,"fav_first":False,"t_fav":hz,"t_adv":hz};continue
        mfe=0;mae=0;t_fav=hz;t_adv=hz;fav_first=False
        first_fav_bar=None;first_adv_bar=None
        for jj in range(j+1,end):
            bi=jj-j
            if sd=="LONG":fv=(H5[jj]-ep)/ep*100;av=(ep-L5[jj])/ep*100
            else:fv=(ep-L5[jj])/ep*100;av=(H5[jj]-ep)/ep*100
            if fv>mfe:mfe=fv
            if av>mae:mae=av
            if first_fav_bar is None and fv>0.3:first_fav_bar=bi
            if first_adv_bar is None and av>0.3:first_adv_bar=bi
        # Forward return at horizon
        if end-1<n5:
            ret=(C5[end-1]-ep)/ep*100 if sd=="LONG" else (ep-C5[end-1])/ep*100
        else:ret=0
        # Favorable before adverse (at 0.3% threshold)
        if first_fav_bar is not None and (first_adv_bar is None or first_fav_bar<first_adv_bar):
            fav_first=True
        out[hz]={"mfe":round(mfe,3),"mae":round(mae,3),"ret":round(ret,3),
                 "fav_first":fav_first,
                 "t_fav":first_fav_bar if first_fav_bar else hz,
                 "t_adv":first_adv_bar if first_adv_bar else hz}
    return out

@router.get("/entry_quality")
def entry_quality(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),impulse_atr:float=Query(1.5),
    donch_lb:int=Query(12),compress_lb:int=Query(8),vol_mult:float=Query(1.5),
    body_min:float=Query(0.3),
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
        ef5=_ema(C5,ema_15m);at5=_atr(H5,L5,C5)
        vol_sma=np.zeros(n5)
        for i in range(20,n5):vol_sma[i]=np.mean(V5[i-20:i])
        # Donchian channels on 15m
        dh=np.zeros(n5);dl=np.zeros(n5)
        for i in range(donch_lb,n5):
            dh[i]=max(H5[i-donch_lb:i]);dl[i]=min(L5[i-donch_lb:i])
        # Rolling ATR ratio for compression detection
        atr_short=_atr(H5,L5,C5,4);atr_long=_atr(H5,L5,C5,compress_lb)
        t5_idx={T5[i]:i for i in range(n5)}

        # V2.5 regime on 1H
        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_a=[]
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_a.append(s)

        # Collect regime 15m windows
        M=15*60*1000
        regime_bars=[]  # (j_15m, side, i_1h)
        for i in range(max(ema_slow*2,60),n1):
            if tiers[i] not in("A","C"):continue
            sd=sides_a[i]
            if sd is None:continue
            side="LONG" if sd=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is not None and j>=max(donch_lb+2,21):
                    regime_bars.append((j,side,i))

        # ═══ SCAN ENTRIES ═══
        mechanisms={"baseline":[],"A_donchian":[],"B_compress_bo":[],"C_compress_retest":[],
                    "D_range_expand":[],"E_vol_breakout":[],"ctrl_random":[]}
        
        random.seed(42)
        for j,side,i1h in regime_bars:
            o,h,l,c=O5[j],H5[j],L5[j],C5[j]
            e7=ef5[j];atr_v=at5[j];rng=h-l;body=abs(c-o)
            bdy=body/rng if rng>0 else 0
            
            # ═══ BASELINE: EMA reclaim ═══
            if side=="LONG":bl_ok=(l<=e7)and(c>e7)and(c>o)and(bdy>=body_min)
            else:bl_ok=(h>=e7)and(c<e7)and(c<o)and(bdy>=body_min)
            if bl_ok:
                m=_measure(j,c,side,H5,L5,C5,n5)
                mechanisms["baseline"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ A: DONCHIAN BREAKOUT ═══
            # Close breaks above donchian high (LONG) or below donchian low (SHORT)
            # Uses PREVIOUS bars only (dh[j] = max of H[j-lb:j], not including j)
            if side=="LONG":a_ok=c>dh[j] and c>o and bdy>=0.3
            else:a_ok=c<dl[j] and c<o and bdy>=0.3
            if a_ok:
                m=_measure(j,c,side,H5,L5,C5,n5)
                mechanisms["A_donchian"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ B: VOLATILITY COMPRESSION → BREAKOUT ═══
            # Short ATR < 0.7× long ATR on prev bar (compression), current bar range > long ATR (expansion)
            if j>=2 and atr_long[j]>0:
                compressed = atr_short[j-1] < 0.7*atr_long[j-1] if atr_long[j-1]>0 else False
                expanded = rng > atr_long[j]
                if side=="LONG":b_ok=compressed and expanded and c>o and c>(h+l)/2
                else:b_ok=compressed and expanded and c<o and c<(h+l)/2
                if b_ok:
                    m=_measure(j,c,side,H5,L5,C5,n5)
                    mechanisms["B_compress_bo"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ C: COMPRESSION BREAKOUT + RETEST HOLD ═══
            # Previous bar was a breakout (range > ATR), current bar retests and holds
            if j>=2 and atr_long[j]>0:
                prev_bo = (H5[j-1]-L5[j-1]) > atr_long[j-1]
                if side=="LONG":
                    retest_hold = prev_bo and C5[j-1]>O5[j-1] and l<=C5[j-1] and c>C5[j-1]
                else:
                    retest_hold = prev_bo and C5[j-1]<O5[j-1] and h>=C5[j-1] and c<C5[j-1]
                if retest_hold:
                    m=_measure(j,c,side,H5,L5,C5,n5)
                    mechanisms["C_compress_retest"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ D: RANGE EXPANSION + STRONG CLOSE ═══
            # Current range > 1.5× ATR AND close in top/bottom 20% of range
            if atr_v>0 and rng>0:
                range_exp = rng > 1.5*atr_v
                if side=="LONG":strong_close=(c-l)/rng>=0.8 and c>o
                else:strong_close=(h-c)/rng>=0.8 and c<o
                if range_exp and strong_close:
                    m=_measure(j,c,side,H5,L5,C5,n5)
                    mechanisms["D_range_expand"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ E: BREAKOUT + VOLUME EXPANSION ═══
            # Donchian breakout + volume > vol_mult × average
            if vol_sma[j]>0:
                vol_ok = V5[j] >= vol_mult*vol_sma[j]
                if side=="LONG":e_ok=c>dh[j] and c>o and vol_ok
                else:e_ok=c<dl[j] and c<o and vol_ok
                if e_ok:
                    m=_measure(j,c,side,H5,L5,C5,n5)
                    mechanisms["E_vol_breakout"].append({"j":j,"sd":side,"ep":c,"m":m})
            
            # ═══ RANDOM CONTROL ═══
            if random.random()<0.05:  # ~5% sample rate to match sparse triggers
                m=_measure(j,c,side,H5,L5,C5,n5)
                mechanisms["ctrl_random"].append({"j":j,"sd":side,"ep":c,"m":m})

        # ═══ AGGREGATE per mechanism ═══
        horizons=[1,2,4,8,16]
        third=n5//3
        results={}
        
        for mech,entries in mechanisms.items():
            nt=len(entries)
            if nt==0:results[mech]={"n":0};continue
            
            hz_stats={}
            for hz in horizons:
                mfes=[e["m"][hz]["mfe"] for e in entries]
                maes=[e["m"][hz]["mae"] for e in entries]
                rets=[e["m"][hz]["ret"] for e in entries]
                ff=[e["m"][hz]["fav_first"] for e in entries]
                t_favs=[e["m"][hz]["t_fav"] for e in entries]
                t_advs=[e["m"][hz]["t_adv"] for e in entries]
                
                mfe_med=round(float(np.median(mfes)),3);mae_med=round(float(np.median(maes)),3)
                hz_stats[f"h{hz}"]={
                    "mfe_med":mfe_med,"mae_med":mae_med,
                    "mfe_p75":round(float(np.percentile(mfes,75)),3),
                    "mae_p75":round(float(np.percentile(maes,75)),3),
                    "ratio":round(mfe_med/mae_med,3) if mae_med>0 else 0,
                    "ret_med":round(float(np.median(rets)),3),
                    "ret_mean":round(float(np.mean(rets)),3),
                    "fav_first_pct":round(100*sum(ff)/len(ff),1),
                    "t_fav_med":round(float(np.median(t_favs)),1),
                    "t_adv_med":round(float(np.median(t_advs)),1),
                }
            
            # Walk-forward thirds
            f1=[e for e in entries if e["j"]<third]
            f2=[e for e in entries if third<=e["j"]<2*third]
            f3=[e for e in entries if e["j"]>=2*third]
            wf={}
            for fn,fl in[("F1",f1),("F2",f2),("F3",f3)]:
                if not fl:wf[fn]={"n":0};continue
                r8=[e["m"][8]["ret"] for e in fl]
                ff8=[e["m"][8]["fav_first"] for e in fl]
                wf[fn]={"n":len(fl),
                    "ret_med":round(float(np.median(r8)),3),
                    "fav_first":round(100*sum(ff8)/len(ff8),1),
                    "mfe_med":round(float(np.median([e["m"][8]["mfe"] for e in fl])),3),
                    "mae_med":round(float(np.median([e["m"][8]["mae"] for e in fl])),3),
                }
            
            # Per side
            lo=[e for e in entries if e["sd"]=="LONG"];sh=[e for e in entries if e["sd"]=="SHORT"]
            side_stats={}
            for sn,sl in[("LONG",lo),("SHORT",sh)]:
                if not sl:continue
                r8=[e["m"][8]["ret"] for e in sl]
                side_stats[sn]={"n":len(sl),"ret_med":round(float(np.median(r8)),3),
                    "fav_first":round(100*sum(e["m"][8]["fav_first"] for e in sl)/len(sl),1)}
            
            results[mech]={
                "n":nt,"tpd":round(nt/days,3),
                "horizons":hz_stats,"wf":wf,"sides":side_stats,
            }

        return{
            "symbol":symbol,"days":days,"n_15m":n5,
            "regime_bars":len(regime_bars),
            "params":{"donch_lb":donch_lb,"compress_lb":compress_lb,"vol_mult":vol_mult},
            "results":results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
