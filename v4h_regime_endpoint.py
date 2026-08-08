"""4H Regime Experiment — multiple regime modes.

regime_mode:
  swing      = ATR-scaled swing structure (2HH+2HL)
  ema_simple = close > both EMAs = BULL
  ema_cross  = EMA_fast > EMA_slow = BULL (golden/death cross)
  dual       = EMA_fast > EMA_slow AND close > both EMAs = BULL

GET /v4h/quality?symbol=SOLUSDT&days=971&regime_mode=ema_cross
GET /v4h/quality?symbol=SOLUSDT&days=971&regime_mode=dual
"""
import os,sqlite3,numpy as np,random,traceback
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
    cs=[];buf=[];block=4*3600*1000
    for r in rows_1h:
        if buf and (r[0]//block)!=(buf[0][0]//block):
            cs.append((buf[0][0],buf[0][1],max(x[2] for x in buf),min(x[3] for x in buf),buf[-1][4],sum(x[5] for x in buf),buf[-1][0]))
            buf=[]
        buf.append(r)
    if len(buf)==4:cs.append((buf[0][0],buf[0][1],max(x[2] for x in buf),min(x[3] for x in buf),buf[-1][4],sum(x[5] for x in buf),buf[-1][0]))
    return cs

class SwingRegime:
    def __init__(s,slb=5,sa=0.5):
        s.slb=slb;s.sa=sa;s.hh=0;s.hl=0;s.lh=0;s.ll=0;s.lsh=None;s.lsl=None;s.psh=None;s.psl=None
    def process(s,i,H,L,C,ef,es,atr):
        if i<s.slb:return"SIDEWAYS"
        mid=i-s.slb//2
        if mid<0:return"SIDEWAYS"
        wh=H[max(0,i-s.slb):i+1];wl=L[max(0,i-s.slb):i+1];am=s.sa*atr[i] if atr[i]>0 else 0
        if H[mid]==max(wh) and(s.lsh is None or abs(H[mid]-s.lsh)>=am):
            s.psh=s.lsh;s.lsh=float(H[mid])
            if s.psh:
                if s.lsh>s.psh:s.hh+=1
                else:s.lh+=1;s.hh=max(0,s.hh-1)
        if L[mid]==min(wl) and(s.lsl is None or abs(L[mid]-s.lsl)>=am):
            s.psl=s.lsl;s.lsl=float(L[mid])
            if s.psl:
                if s.lsl>s.psl:s.hl+=1;s.ll=max(0,s.ll-1)
                else:s.ll+=1;s.hl=max(0,s.hl-1)
        if s.hh>=2 and s.hl>=2 and ef[i]>es[i] and C[i]>es[i]:return"BULL"
        if s.lh>=2 and s.ll>=2 and ef[i]<es[i] and C[i]<es[i]:return"BEAR"
        return"SIDEWAYS"

def _measure(j,ep,sd,H,L,C,n,horizons=[1,2,4,8]):
    out={}
    for hz in horizons:
        end=min(j+hz+1,n)
        if j+1>=n:out[hz]={"mfe":0,"mae":0,"ret":0,"ff":False};continue
        mfe=0;mae=0;fb=None;ab=None
        for jj in range(j+1,end):
            if sd=="LONG":fv=(H[jj]-ep)/ep*100;av=(ep-L[jj])/ep*100
            else:fv=(ep-L[jj])/ep*100;av=(H[jj]-ep)/ep*100
            if fv>mfe:mfe=fv
            if av>mae:mae=av
            if fb is None and fv>0.3:fb=jj-j
            if ab is None and av>0.3:ab=jj-j
        ret=(C[min(end-1,n-1)]-ep)/ep*100 if sd=="LONG" else (ep-C[min(end-1,n-1)])/ep*100
        out[hz]={"mfe":round(mfe,3),"mae":round(mae,3),"ret":round(ret,3),"ff":fb is not None and(ab is None or fb<ab)}
    return out

@router.get("/quality")
def v4h_quality(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_4h_fast:int=Query(7),ema_4h_slow:int=Query(20),
    ema_1h:int=Query(7),ema_15m:int=Query(7),
    swing_lb:int=Query(5),swing_atr:float=Query(0.5),body_min:float=Query(0.3),
    regime_mode:str=Query("swing"),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
):
    try:
        r1h=_ld(symbol,"1h",days);r15m=_ld(symbol,"15m",days)
        if len(r1h)<100:return{"error":"not enough 1h"}
        c4h=_build_4h(r1h)
        if len(c4h)<ema_4h_slow*2+20:return{"error":f"not enough 4H"}
        O4=np.array([c[1] for c in c4h],dtype=float);H4=np.array([c[2] for c in c4h],dtype=float)
        L4=np.array([c[3] for c in c4h],dtype=float);C4=np.array([c[4] for c in c4h],dtype=float)
        T4=[c[0] for c in c4h];T4L=[c[6] for c in c4h];n4=len(c4h)
        ef4=_ema(C4,ema_4h_fast);es4=_ema(C4,ema_4h_slow);at4=_atr(H4,L4,C4)
        O1=np.array([r[1] for r in r1h],dtype=float);H1=np.array([r[2] for r in r1h],dtype=float)
        L1=np.array([r[3] for r in r1h],dtype=float);C1=np.array([r[4] for r in r1h],dtype=float)
        T1=[r[0] for r in r1h];n1=len(r1h);ef1=_ema(C1,ema_1h);t1_idx={T1[i]:i for i in range(n1)}
        O5=np.array([r[1] for r in r15m],dtype=float);H5=np.array([r[2] for r in r15m],dtype=float)
        L5=np.array([r[3] for r in r15m],dtype=float);C5=np.array([r[4] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m);ef5=_ema(C5,ema_15m);t5_idx={T5[i]:i for i in range(n5)}
        cost=fee_pct+slippage_pct;M=15*60*1000;H1h=3600*1000

        # Regime
        regimes=[]
        if regime_mode=="swing":
            det=SwingRegime(swing_lb,swing_atr)
            for i in range(n4):regimes.append(det.process(i,H4,L4,C4,ef4,es4,at4))
        elif regime_mode=="ema_simple":
            for i in range(n4):
                if C4[i]>ef4[i] and C4[i]>es4[i]:regimes.append("BULL")
                elif C4[i]<ef4[i] and C4[i]<es4[i]:regimes.append("BEAR")
                else:regimes.append("SIDEWAYS")
        elif regime_mode=="ema_cross":
            # EMA fast > EMA slow = BULL, EMA fast < EMA slow = BEAR
            for i in range(n4):
                if ef4[i]>es4[i]:regimes.append("BULL")
                elif ef4[i]<es4[i]:regimes.append("BEAR")
                else:regimes.append("SIDEWAYS")
        elif regime_mode=="dual":
            # BOTH conditions: EMA fast > EMA slow AND close > both EMAs
            for i in range(n4):
                if ef4[i]>es4[i] and C4[i]>ef4[i] and C4[i]>es4[i]:regimes.append("BULL")
                elif ef4[i]<es4[i] and C4[i]<ef4[i] and C4[i]<es4[i]:regimes.append("BEAR")
                else:regimes.append("SIDEWAYS")
        else:
            return{"error":f"unknown regime_mode: {regime_mode}"}

        dist={r:sum(1 for x in regimes if x==r) for r in["BULL","BEAR","SIDEWAYS"]}
        dist_pct={r:round(100*v/n4,1) for r,v in dist.items()}
        trans=sum(1 for i in range(1,n4) if regimes[i]!=regimes[i-1])

        modes={"A_1h_reclaim":[],"B_15m_reclaim":[],"ctrl_random":[]}
        random.seed(42);ref_tp=0.013;ref_sl=0.013
        for i4 in range(max(ema_4h_slow*2,10),n4):
            if regimes[i4] not in("BULL","BEAR"):continue
            side="LONG" if regimes[i4]=="BULL" else "SHORT"
            t4c=T4L[i4]+H1h
            for k in range(4):
                t1=t4c+k*H1h;j1=t1_idx.get(t1)
                if j1 is None or j1<ema_1h*2:continue
                o,h,l,c=O1[j1],H1[j1],L1[j1],C1[j1];e=ef1[j1]
                rng=h-l;bdy=abs(c-o)/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e)and(c>e)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e)and(c<e)and(c<o)and(bdy>=body_min)
                if ok:modes["A_1h_reclaim"].append({"j":j1,"sd":side,"ep":c,"tf":"1h","m":_measure(j1,c,side,H1,L1,C1,n1)});break
            for k in range(16):
                t15=t4c+k*M;j5=t5_idx.get(t15)
                if j5 is None or j5<ema_15m*2:continue
                o,h,l,c=O5[j5],H5[j5],L5[j5],C5[j5];e=ef5[j5]
                rng=h-l;bdy=abs(c-o)/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e)and(c>e)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e)and(c<e)and(c<o)and(bdy>=body_min)
                if ok:modes["B_15m_reclaim"].append({"j":j5,"sd":side,"ep":c,"tf":"15m","m":_measure(j5,c,side,H5,L5,C5,n5)});break
            if random.random()<0.15:
                rk=random.randint(0,15);t15=t4c+rk*M;j5=t5_idx.get(t15)
                if j5 is not None and j5+17<n5:
                    modes["ctrl_random"].append({"j":j5,"sd":side,"ep":C5[j5],"tf":"15m","m":_measure(j5,C5[j5],side,H5,L5,C5,n5)})

        results={}
        for mode,entries in modes.items():
            nt=len(entries)
            if nt==0:results[mode]={"n":0};continue
            tf=entries[0]["tf"]
            tp_first=0
            for e in entries:
                ep=e["ep"];sd=e["sd"]
                Hx=H5 if tf=="15m" else H1;Lx=L5 if tf=="15m" else L1;nx=n5 if tf=="15m" else n1
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
            hz_stats={}
            for hz in[1,2,4,8]:
                ms=[e["m"][hz] for e in entries if hz in e["m"]]
                if not ms:continue
                mfes=sorted([m["mfe"] for m in ms]);maes=sorted([m["mae"] for m in ms])
                rets=[m["ret"] for m in ms];ffs=[m["ff"] for m in ms]
                mm=round(float(np.median(mfes)),3);am=round(float(np.median(maes)),3)
                hz_stats[f"h{hz}"]={"mfe_med":mm,"mae_med":am,"ratio":round(mm/am,3) if am>0 else 0,
                    "ret_med":round(float(np.median(rets)),3),"ret_mean":round(float(np.mean(rets)),3),
                    "fav_first":round(100*sum(ffs)/len(ffs),1)}
            third=n5//3 if tf=="15m" else n1//3
            wf={}
            for fn,fl in[("F1",[e for e in entries if e["j"]<third]),("F2",[e for e in entries if third<=e["j"]<2*third]),("F3",[e for e in entries if e["j"]>=2*third])]:
                if not fl:wf[fn]={"n":0};continue
                r4=[e["m"][4]["ret"] for e in fl if 4 in e["m"]]
                wf[fn]={"n":len(fl),"ret_med":round(float(np.median(r4)),3) if r4 else 0}
            w=tp_first;l=nt-w
            results[mode]={"n":nt,"tpd":round(nt/days,3),"tf":tf,
                "tp_before_sl":round(100*tp_first/nt,1),
                "gross_exp":round((w*ref_tp-l*ref_sl)/nt*100,3),
                "net_exp_015":round((w*(ref_tp-0.002)-l*(ref_sl+0.002))/nt*100,3),
                "horizons":hz_stats,"wf":wf}
        return{"symbol":symbol,"days":days,"n_4h":n4,
            "config":{"ema_fast":ema_4h_fast,"ema_slow":ema_4h_slow,"mode":regime_mode},
            "regime_pct":dist_pct,"transitions":trans,"results":results}
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
