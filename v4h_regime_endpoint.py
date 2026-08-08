"""4H Regime Experiment — higher timeframe regime gate.

4H candles constructed from completed 1H candles only.
Regime available after 4H close. Entries on subsequent LTF candles.

GET /v4h/quality?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,math,traceback
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter(prefix="/v4h", tags=["v4h"])
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

def _build_4h(rows_1h):
    """Construct 4H candles from completed 1H candles. Group by 4H boundary."""
    candles_4h=[];buf=[]
    for r in rows_1h:
        ts,o,h,l,c,v=r
        # 4H boundary: ts aligned to 4-hour blocks (0,4,8,12,16,20 UTC)
        hour_ms=3600*1000;block=4*hour_ms
        b_start=(ts//block)*block
        if buf and (ts//block)*block != (buf[0][0]//block)*block:
            # Close previous 4H
            o4=buf[0][1];h4=max(x[2] for x in buf);l4=min(x[3] for x in buf)
            c4=buf[-1][4];v4=sum(x[5] for x in buf);t4=buf[0][0]
            candles_4h.append((t4,o4,h4,l4,c4,v4,buf[-1][0]))  # last field = last 1H ts
            buf=[]
        buf.append(r)
    # Don't flush incomplete last block
    if len(buf)==4:
        o4=buf[0][1];h4=max(x[2] for x in buf);l4=min(x[3] for x in buf)
        c4=buf[-1][4];v4=sum(x[5] for x in buf);t4=buf[0][0]
        candles_4h.append((t4,o4,h4,l4,c4,v4,buf[-1][0]))
    return candles_4h

class Regime4H:
    """ATR-scaled swing regime on 4H candles."""
    def __init__(self,swing_lb=5,swing_atr=0.5,min_regime=2):
        self.slb=swing_lb;self.sa=swing_atr;self.mr=min_regime
        self.hh=0;self.hl=0;self.lh=0;self.ll=0
        self.last_sh=None;self.last_sl=None;self.prev_sh=None;self.prev_sl=None
        self.regime="SIDEWAYS";self.regime_bars=0
    def process(self,i,H,L,C,ef,es,atr):
        if i<self.slb:return self.regime
        mid=i-self.slb//2
        if mid<0:return self.regime
        wh=H[max(0,i-self.slb):i+1];wl=L[max(0,i-self.slb):i+1]
        amin=self.sa*atr[i] if atr[i]>0 else 0
        # Swing high
        if H[mid]==max(wh) and (self.last_sh is None or abs(H[mid]-self.last_sh)>=amin):
            self.prev_sh=self.last_sh;self.last_sh=float(H[mid])
            if self.prev_sh:
                if self.last_sh>self.prev_sh:self.hh+=1
                else:self.lh+=1;self.hh=max(0,self.hh-1)
        # Swing low
        if L[mid]==min(wl) and (self.last_sl is None or abs(L[mid]-self.last_sl)>=amin):
            self.prev_sl=self.last_sl;self.last_sl=float(L[mid])
            if self.prev_sl:
                if self.last_sl>self.prev_sl:self.hl+=1;self.ll=max(0,self.ll-1)
                else:self.ll+=1;self.hl=max(0,self.hl-1)
        # EMA alignment
        bull_ema=ef[i]>es[i] and C[i]>es[i]
        bear_ema=ef[i]<es[i] and C[i]<es[i]
        # Regime
        old=self.regime
        if self.hh>=2 and self.hl>=2 and bull_ema:
            if self.regime!="BULL":self.regime_bars=0
            self.regime="BULL";self.regime_bars+=1
        elif self.lh>=2 and self.ll>=2 and bear_ema:
            if self.regime!="BEAR":self.regime_bars=0
            self.regime="BEAR";self.regime_bars+=1
        else:
            if self.regime!="SIDEWAYS":self.regime_bars=0
            self.regime="SIDEWAYS";self.regime_bars+=1
        return self.regime


def _measure(j, ep, sd, H, L, C, n, horizons=[1,2,4,8]):
    out={}
    for hz in horizons:
        end=min(j+hz+1,n)
        if j+1>=n:out[hz]={"mfe":0,"mae":0,"ret":0,"ff":False};continue
        mfe=0;mae=0;ff_bar=None;fa_bar=None
        for jj in range(j+1,end):
            if sd=="LONG":fv=(H[jj]-ep)/ep*100;av=(ep-L[jj])/ep*100
            else:fv=(ep-L[jj])/ep*100;av=(H[jj]-ep)/ep*100
            if fv>mfe:mfe=fv
            if av>mae:mae=av
            if ff_bar is None and fv>0.3:ff_bar=jj-j
            if fa_bar is None and av>0.3:fa_bar=jj-j
        ret=(C[min(end-1,n-1)]-ep)/ep*100 if sd=="LONG" else (ep-C[min(end-1,n-1)])/ep*100
        ff=ff_bar is not None and (fa_bar is None or ff_bar<fa_bar)
        out[hz]={"mfe":round(mfe,3),"mae":round(mae,3),"ret":round(ret,3),"ff":ff}
    return out


@router.get("/quality")
def v4h_quality(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_4h_fast:int=Query(7),ema_4h_slow:int=Query(20),
    ema_1h:int=Query(7),ema_15m:int=Query(7),
    swing_lb:int=Query(5),swing_atr:float=Query(0.5),
    body_min:float=Query(0.3),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
):
    try:
        r1h=_ld(symbol,"1h",days);r15m=_ld(symbol,"15m",days)
        if len(r1h)<100:return{"error":"not enough 1h"}
        
        # Build 4H from 1H
        c4h=_build_4h(r1h)
        if len(c4h)<ema_4h_slow*2+20:return{"error":f"not enough 4H: {len(c4h)}"}
        
        O4=np.array([c[1] for c in c4h],dtype=float);H4=np.array([c[2] for c in c4h],dtype=float)
        L4=np.array([c[3] for c in c4h],dtype=float);C4=np.array([c[4] for c in c4h],dtype=float)
        T4=[c[0] for c in c4h];T4_last1h=[c[6] for c in c4h];n4=len(c4h)
        ef4=_ema(C4,ema_4h_fast);es4=_ema(C4,ema_4h_slow);at4=_atr(H4,L4,C4)
        
        # 1H arrays
        O1=np.array([r[1] for r in r1h],dtype=float);H1=np.array([r[2] for r in r1h],dtype=float)
        L1=np.array([r[3] for r in r1h],dtype=float);C1=np.array([r[4] for r in r1h],dtype=float)
        T1=[r[0] for r in r1h];n1=len(r1h)
        ef1=_ema(C1,ema_1h)
        t1_idx={T1[i]:i for i in range(n1)}
        
        # 15m arrays
        O5=np.array([r[1] for r in r15m],dtype=float);H5=np.array([r[2] for r in r15m],dtype=float)
        L5=np.array([r[3] for r in r15m],dtype=float);C5=np.array([r[4] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m)
        t5_idx={T5[i]:i for i in range(n5)}
        
        cost=fee_pct+slippage_pct;M=15*60*1000;H1h=3600*1000
        
        # Run 4H regime
        det=Regime4H(swing_lb,swing_atr)
        regimes=[]
        for i in range(n4):
            r=det.process(i,H4,L4,C4,ef4,es4,at4)
            regimes.append(r)
        
        # Regime distribution
        dist={r:sum(1 for x in regimes if x==r) for r in["BULL","BEAR","SIDEWAYS"]}
        dist_pct={r:round(100*v/n4,1) for r,v in dist.items()}
        
        # Transitions + avg duration
        trans=0;durations=[];cur=regimes[0];dur=1
        for i in range(1,n4):
            if regimes[i]!=cur:trans+=1;durations.append(dur);cur=regimes[i];dur=1
            else:dur+=1
        durations.append(dur)
        avg_dur=round(np.mean(durations),1) if durations else 0
        
        # ═══ ENTRY MODES ═══
        # For each 4H bar in BULL/BEAR, entries start AFTER the 4H close
        modes={"A_1h_reclaim":[],"B_15m_reclaim":[],"C_15m_breakout":[],"D_1h_pullback_bo":[],"ctrl_random":[]}
        import random;random.seed(42)
        
        for i4 in range(max(ema_4h_slow*2,10),n4):
            if regimes[i4] not in("BULL","BEAR"):continue
            side="LONG" if regimes[i4]=="BULL" else "SHORT"
            # 4H close timestamp = last 1H bar's open_time + 1H
            t4_close=T4_last1h[i4]+H1h  # start of next period after 4H closes
            
            # MODE A: 1H EMA reclaim in next 4 1H bars
            for k in range(4):
                t1=t4_close+k*H1h;j1=t1_idx.get(t1)
                if j1 is None or j1<ema_1h*2:continue
                o,h,l,c=O1[j1],H1[j1],L1[j1],C1[j1];e=ef1[j1]
                rng=h-l;bdy=abs(c-o)/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e)and(c>e)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e)and(c<e)and(c<o)and(bdy>=body_min)
                if ok:
                    m=_measure(j1,c,side,H1,L1,C1,n1)
                    modes["A_1h_reclaim"].append({"j":j1,"sd":side,"ep":c,"tf":"1h","m":m});break
            
            # MODE B: 15m reclaim in next 16 15m bars (=4 hours)
            for k in range(16):
                t15=t4_close+k*M;j5=t5_idx.get(t15)
                if j5 is None or j5<ema_15m*2:continue
                o,h,l,c=O5[j5],H5[j5],L5[j5],C5[j5];e=ef5[j5]
                rng=h-l;bdy=abs(c-o)/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e)and(c>e)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e)and(c<e)and(c<o)and(bdy>=body_min)
                if ok:
                    m=_measure(j5,c,side,H5,L5,C5,n5)
                    modes["B_15m_reclaim"].append({"j":j5,"sd":side,"ep":c,"tf":"15m","m":m});break
            
            # MODE C: 15m breakout (close > 16-bar high for LONG)
            for k in range(16):
                t15=t4_close+k*M;j5=t5_idx.get(t15)
                if j5 is None or j5<17:continue
                dh=max(H5[j5-16:j5]);dl=min(L5[j5-16:j5])
                c=C5[j5];o=O5[j5];bdy=abs(c-o)/(H5[j5]-L5[j5]) if H5[j5]>L5[j5] else 0
                if side=="LONG":ok=c>dh and c>o and bdy>=0.3
                else:ok=c<dl and c<o and bdy>=0.3
                if ok:
                    m=_measure(j5,c,side,H5,L5,C5,n5)
                    modes["C_15m_breakout"].append({"j":j5,"sd":side,"ep":c,"tf":"15m","m":m});break
            
            # MODE D: 1H pullback then breakout
            # Look for: 1H pulls back to EMA, then breaks above prev 1H high
            for k in range(4):
                t1=t4_close+k*H1h;j1=t1_idx.get(t1)
                if j1 is None or j1<5:continue
                c=C1[j1];o=O1[j1];h=H1[j1];l=L1[j1];e=ef1[j1]
                prev_h=max(H1[max(0,j1-4):j1]);prev_l=min(L1[max(0,j1-4):j1])
                # Pullback: low touched EMA in last 4 bars
                pb=any(L1[jj]<=ef1[jj] for jj in range(max(0,j1-3),j1)) if side=="LONG" else any(H1[jj]>=ef1[jj] for jj in range(max(0,j1-3),j1))
                if side=="LONG":ok=pb and c>prev_h and c>o
                else:ok=pb and c<prev_l and c<o
                if ok:
                    m=_measure(j1,c,side,H1,L1,C1,n1)
                    modes["D_1h_pullback_bo"].append({"j":j1,"sd":side,"ep":c,"tf":"1h","m":m});break
            
            # RANDOM CONTROL
            if random.random()<0.15:
                # Random 15m bar in next 4H window
                rk=random.randint(0,15);t15=t4_close+rk*M;j5=t5_idx.get(t15)
                if j5 is not None and j5+17<n5:
                    m=_measure(j5,C5[j5],side,H5,L5,C5,n5)
                    modes["ctrl_random"].append({"j":j5,"sd":side,"ep":C5[j5],"tf":"15m","m":m})
        
        # ═══ AGGREGATE per mode ═══
        third_1h=n1//3;third_15m=n5//3
        ref_tp=0.013;ref_sl=0.013
        results={}
        
        for mode,entries in modes.items():
            nt=len(entries)
            if nt==0:results[mode]={"n":0};continue
            tf=entries[0]["tf"]
            third=third_15m if tf=="15m" else third_1h
            
            # Choose horizon based on TF
            if tf=="15m":horizons=[1,2,4,8]
            else:horizons=[1,2,4,8]
            
            hz_stats={}
            for hz in horizons:
                ms=[e["m"][hz] for e in entries if hz in e["m"]]
                if not ms:continue
                mfes=[m["mfe"] for m in ms];maes=[m["mae"] for m in ms]
                rets=[m["ret"] for m in ms];ffs=[m["ff"] for m in ms]
                mfe_m=round(float(np.median(mfes)),3);mae_m=round(float(np.median(maes)),3)
                hz_stats[f"h{hz}"]={
                    "mfe_med":mfe_m,"mae_med":mae_m,
                    "ratio":round(mfe_m/mae_m,3) if mae_m>0 else 0,
                    "ret_med":round(float(np.median(rets)),3),
                    "ret_mean":round(float(np.mean(rets)),3),
                    "fav_first":round(100*sum(ffs)/len(ffs),1),
                }
            
            # TP-before-SL at ref
            tp_first=0
            for e in entries:
                ep=e["ep"];sd=e["sd"]
                if tf=="15m":Hx,Lx,Cx,nx=H5,L5,C5,n5
                else:Hx,Lx,Cx,nx=H1,L1,C1,n1
                tp_l=ep*(1+ref_tp) if sd=="LONG" else ep*(1-ref_tp)
                sl_l=ep*(1-ref_sl) if sd=="LONG" else ep*(1+ref_sl)
                tb=999;sb=999
                for jj in range(e["j"]+1,min(e["j"]+200,nx)):
                    if sd=="LONG":
                        if tb==999 and Hx[jj]>=tp_l:tb=jj-e["j"]
                        if sb==999 and Lx[jj]<=sl_l:sb=jj-e["j"]
                    else:
                        if tb==999 and Lx[jj]<=tp_l:tb=jj-e["j"]
                        if sb==999 and Hx[jj]>=sl_l:sb=jj-e["j"]
                if tb<sb:tp_first+=1
            
            # Walk-forward
            f1=[e for e in entries if e["j"]<third]
            f2=[e for e in entries if third<=e["j"]<2*third]
            f3=[e for e in entries if e["j"]>=2*third]
            wf={}
            for fn,fl in[("F1",f1),("F2",f2),("F3",f3)]:
                if not fl:wf[fn]={"n":0};continue
                r4=[e["m"][4]["ret"] for e in fl if 4 in e["m"]]
                ff4=[e["m"][4]["ff"] for e in fl if 4 in e["m"]]
                wf[fn]={"n":len(fl),"ret_med":round(float(np.median(r4)),3) if r4 else 0,
                    "fav_first":round(100*sum(ff4)/len(ff4),1) if ff4 else 0}
            
            # Gross/net expectancy at ref TP/SL
            w=tp_first;l=nt-w
            gr_exp=round((w*ref_tp-l*ref_sl)/nt*100,3)
            ne_exp_10=round((w*(ref_tp-0.0015)-l*(ref_sl+0.0015))/nt*100,3)
            ne_exp_15=round((w*(ref_tp-0.002)-l*(ref_sl+0.002))/nt*100,3)
            
            lo=[e for e in entries if e["sd"]=="LONG"];sh=[e for e in entries if e["sd"]=="SHORT"]
            
            results[mode]={
                "n":nt,"tpd":round(nt/days,3),"tf":tf,
                "tp_before_sl":round(100*tp_first/nt,1),
                "gross_exp_pct":gr_exp,
                "net_exp_010":ne_exp_10,"net_exp_015":ne_exp_15,
                "horizons":hz_stats,
                "L":{"n":len(lo)},
                "S":{"n":len(sh)},
                "wf":wf,
            }

        return{
            "symbol":symbol,"days":days,"n_4h":n4,"n_1h":n1,"n_15m":n5,
            "regime_dist":dist,"regime_pct":dist_pct,
            "transitions":trans,"avg_regime_dur_4h":avg_dur,
            "results":results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
