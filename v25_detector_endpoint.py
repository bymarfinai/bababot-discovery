"""V2.5 Regime Expansion — tiered regime detector + quality measurement.

Tier A: strict V2 (2 HH+2 HL / 2 LH+2 LL)
Tier B: developing (1 HH+1 HL / 1 LH+1 LL) + EMA alignment + slope + protected swing
Tier C: early transition (ATR impulse + EMA alignment + confirmed pullback)

All decisions use data at candle close only. No future labels.

GET /v25/quality?symbol=SOLUSDT&days=971
GET /v25/coverage?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,math,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from continuation_detector_endpoint import ContinuationDetectorV2

router = APIRouter(prefix="/v25", tags=["v25"])
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

def _wilson(s,n,z=1.96):
    if n==0:return 0,0,0
    p=s/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;sp=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return round(100*p,1),round(100*max(0,c-sp),1),round(100*min(1,c+sp),1)


class V25Detector:
    """Tiered regime detector. Runs V2 internally for Tier A, adds B and C."""
    def __init__(self, ema_fast=7, ema_slow=20, swing_lb=10, swing_atr_min=0.5, slope_lb=3,
                 impulse_atr=1.5, min_regime_bars=3):
        self.ef_p=ema_fast;self.es_p=ema_slow;self.slb=swing_lb;self.sa=swing_atr_min
        self.slope_lb=slope_lb;self.impulse_atr=impulse_atr;self.min_bars=min_regime_bars
        # Swing tracking for Tier B/C
        self.hh_count=0;self.hl_count=0;self.lh_count=0;self.ll_count=0
        self.last_sh=None;self.last_sl=None;self.prev_sh=None;self.prev_sl=None
        self.prot_low=None;self.prot_high=None
        self.tier="SIDEWAYS";self.side=None;self.tier_bars=0
        self.v2=ContinuationDetectorV2(ema_fast,ema_slow,swing_lb,swing_atr_min,slope_lb,min_pb_bars=1)

    def _update_swings(self, i, H, L, atr):
        """Track swing highs/lows with ATR significance."""
        if i < self.slb: return
        lb = self.slb
        atr_min = self.sa * atr[i] if atr[i] > 0 else 0
        # Swing high: H[i-lb//2] is highest in window
        mid = i - lb//2
        if mid < 0 or mid >= len(H): return
        window_h = H[max(0,i-lb):i+1]
        window_l = L[max(0,i-lb):i+1]
        is_sh = H[mid] == max(window_h) and (self.last_sh is None or abs(H[mid]-self.last_sh) >= atr_min)
        is_sl = L[mid] == min(window_l) and (self.last_sl is None or abs(L[mid]-self.last_sl) >= atr_min)
        
        if is_sh:
            self.prev_sh = self.last_sh; self.last_sh = float(H[mid])
            if self.prev_sh is not None:
                if self.last_sh > self.prev_sh: self.hh_count += 1
                else: self.lh_count += 1; self.hh_count = max(0, self.hh_count-1)
            self.prot_high = self.last_sh
        if is_sl:
            self.prev_sl = self.last_sl; self.last_sl = float(L[mid])
            if self.prev_sl is not None:
                if self.last_sl > self.prev_sl: self.hl_count += 1; self.ll_count = max(0, self.ll_count-1)
                else: self.ll_count += 1; self.hl_count = max(0, self.hl_count-1)
            self.prot_low = self.last_sl

    def process(self, i, O, H, L, C, ef, es, atr):
        """Classify bar into tier. Returns (tier, side)."""
        self.v2.process(i, O, H, L, C, ef, es, atr)
        self._update_swings(i, H, L, atr)
        
        # EMA alignment
        bull_ema = ef[i] > es[i] and C[i] > es[i]
        bear_ema = ef[i] < es[i] and C[i] < es[i]
        
        # Slope
        if i >= self.slope_lb:
            slope = (ef[i] - ef[i-self.slope_lb]) / (atr[i] if atr[i]>0 else 1)
        else: slope = 0
        bull_slope = slope > 0.05
        bear_slope = slope < -0.05
        
        # ═══ TIER A: strict V2 ═══
        if self.v2.regime == "BULL":
            self.tier = "A"; self.side = "BULL"; self.tier_bars += 1
            return self.tier, self.side
        if self.v2.regime == "BEAR":
            self.tier = "A"; self.side = "BEAR"; self.tier_bars += 1
            return self.tier, self.side
        
        # ═══ TIER B: developing trend ═══
        # 1 HH + 1 HL + EMA alignment + slope + protected swing
        bull_b = (self.hh_count >= 1 and self.hl_count >= 1 and 
                  bull_ema and bull_slope and self.prot_low is not None)
        bear_b = (self.lh_count >= 1 and self.ll_count >= 1 and 
                  bear_ema and bear_slope and self.prot_high is not None)
        
        if bull_b and not bear_b:
            if self.tier != "B" or self.side != "BULL": self.tier_bars = 0
            self.tier_bars += 1
            if self.tier_bars >= self.min_bars:
                self.tier = "B"; self.side = "BULL"
                return self.tier, self.side
        if bear_b and not bull_b:
            if self.tier != "B" or self.side != "BEAR": self.tier_bars = 0
            self.tier_bars += 1
            if self.tier_bars >= self.min_bars:
                self.tier = "B"; self.side = "BEAR"
                return self.tier, self.side
        
        # ═══ TIER C: early transition ═══
        # Large ATR impulse + EMA alignment + pullback confirmed
        if i >= 4 and atr[i] > 0:
            impulse = (C[i] - C[i-4]) / atr[i]
            # Bullish impulse: price moved > impulse_atr ATRs up in 4 bars
            if impulse > self.impulse_atr and bull_ema:
                # Check for pullback: at some point in last 4 bars, low touched EMA
                pb = any(L[j] <= ef[j] for j in range(max(0,i-3), i+1))
                if pb:
                    if self.tier != "C" or self.side != "BULL": self.tier_bars = 0
                    self.tier_bars += 1
                    if self.tier_bars >= 1:  # C can trigger faster
                        self.tier = "C"; self.side = "BULL"
                        return self.tier, self.side
            # Bearish impulse
            if impulse < -self.impulse_atr and bear_ema:
                pb = any(H[j] >= ef[j] for j in range(max(0,i-3), i+1))
                if pb:
                    if self.tier != "C" or self.side != "BEAR": self.tier_bars = 0
                    self.tier_bars += 1
                    if self.tier_bars >= 1:
                        self.tier = "C"; self.side = "BEAR"
                        return self.tier, self.side
        
        # ═══ SIDEWAYS ═══
        self.tier = "SIDEWAYS"; self.side = None; self.tier_bars = 0
        return self.tier, self.side


@router.get("/quality")
def v25_quality(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_fast:int=Query(7),ema_slow:int=Query(20),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),
    impulse_atr:float=Query(1.5),
):
    try:
        rows=_ld(symbol,"1h",days)
        if len(rows)<ema_slow*2+60:return{"error":"not enough"}
        O=np.array([r[1] for r in rows],dtype=float);H=np.array([r[2] for r in rows],dtype=float)
        L=np.array([r[3] for r in rows],dtype=float);C=np.array([r[4] for r in rows],dtype=float)
        n=len(rows)
        ef=_ema(C,ema_fast);es=_ema(C,ema_slow);at=_atr(H,L,C)

        det=V25Detector(ema_fast,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides=[]
        for i in range(n):
            t,s=det.process(i,O,H,L,C,ef,es,at)
            tiers.append(t);sides.append(s)

        # Regime distribution
        dist={t:sum(1 for x in tiers if x==t) for t in ["A","B","C","SIDEWAYS"]}
        dist_pct={t:round(100*v/n,1) for t,v in dist.items()}

        # Transition counts
        transitions=0;fast_trans=0
        prev_tier=None;prev_dur=0
        for i in range(n):
            if tiers[i]!=prev_tier:
                if prev_tier is not None:
                    transitions+=1
                    if prev_dur<3:fast_trans+=1
                prev_tier=tiers[i];prev_dur=0
            prev_dur+=1

        # Per-tier quality metrics
        quality={}
        for tier in ["A","B","C"]:
            for side_label in ["BULL","BEAR"]:
                bars=[i for i in range(n) if tiers[i]==tier and sides[i]==side_label]
                if not bars:continue
                key=f"{tier}_{side_label}"

                # HH/LL accuracy at horizons
                hh_acc={};ctrl_acc={}
                for hz in [4,8,16]:
                    hh_ok=0;hh_n=0;ctrl_ok=0;ctrl_n=0
                    for bi in bars:
                        if bi+hz>=n:continue
                        hh_n+=1
                        if side_label=="BULL":
                            if any(H[j]>C[bi] for j in range(bi+1,min(bi+hz+1,n))):hh_ok+=1
                        else:
                            if any(L[j]<C[bi] for j in range(bi+1,min(bi+hz+1,n))):hh_ok+=1
                    # Control: random bars in SIDEWAYS
                    sw_bars=[i for i in range(n) if tiers[i]=="SIDEWAYS"]
                    for bi in sw_bars[:min(len(sw_bars),len(bars))]:
                        if bi+hz>=n:continue
                        ctrl_n+=1
                        if side_label=="BULL":
                            if any(H[j]>C[bi] for j in range(bi+1,min(bi+hz+1,n))):ctrl_ok+=1
                        else:
                            if any(L[j]<C[bi] for j in range(bi+1,min(bi+hz+1,n))):ctrl_ok+=1
                    h_a,_,_=_wilson(hh_ok,hh_n)
                    c_a,_,_=_wilson(ctrl_ok,ctrl_n)
                    hh_acc[f"h{hz}"]={"acc":h_a,"n":hh_n}
                    ctrl_acc[f"h{hz}"]={"acc":c_a,"n":ctrl_n}

                # EMA hold (h=4)
                ema_ok=0;ema_n=0
                for bi in bars:
                    if bi+5>=n:continue
                    ema_n+=1
                    if side_label=="BULL":
                        if all(C[j]>es[j] for j in range(bi+1,min(bi+5,n))):ema_ok+=1
                    else:
                        if all(C[j]<es[j] for j in range(bi+1,min(bi+5,n))):ema_ok+=1
                ema_hold,_,_=_wilson(ema_ok,ema_n)

                # Protected swing survival (h=4)
                ps_ok=0;ps_n=0
                for bi in bars:
                    if bi+5>=n:continue
                    if side_label=="BULL" and det.prot_low:
                        ps_n+=1
                        if all(L[j]>=det.prot_low for j in range(bi+1,min(bi+5,n))):ps_ok+=1
                    elif side_label=="BEAR" and det.prot_high:
                        ps_n+=1
                        if all(H[j]<=det.prot_high for j in range(bi+1,min(bi+5,n))):ps_ok+=1
                ps_acc,_,_=_wilson(ps_ok,ps_n)

                # MFE/MAE (h=8)
                mfes=[];maes=[]
                for bi in bars:
                    if bi+9>=n:continue
                    mfe=0;mae=0
                    for j in range(bi+1,min(bi+9,n)):
                        if side_label=="BULL":
                            fv=(H[j]-C[bi])/C[bi];av=(C[bi]-L[j])/C[bi]
                        else:
                            fv=(C[bi]-L[j])/C[bi];av=(H[j]-C[bi])/C[bi]
                        if fv>mfe:mfe=fv
                        if av>mae:mae=av
                    mfes.append(mfe*100);maes.append(mae*100)

                # Walk-forward thirds
                third=n//3
                wf={}
                for fn,fs,fe in[("T1",0,third),("T2",third,2*third),("T3",2*third,n)]:
                    fb=[b for b in bars if fs<=b<fe]
                    wf[fn]={"bars":len(fb),"pct":round(100*len(fb)/(fe-fs),1) if fe>fs else 0}

                quality[key]={
                    "bars":len(bars),"pct":round(100*len(bars)/n,1),
                    "hh_ll":hh_acc,"ctrl":ctrl_acc,
                    "ema_hold":ema_hold,"ema_hold_n":ema_n,
                    "prot_surv":ps_acc,"prot_n":ps_n,
                    "mfe_med":round(float(np.median(mfes)),3) if mfes else 0,
                    "mae_med":round(float(np.median(maes)),3) if maes else 0,
                    "mfe_p75":round(float(np.percentile(mfes,75)),3) if mfes else 0,
                    "mae_p75":round(float(np.percentile(maes,75)),3) if maes else 0,
                    "wf":wf,
                }

        return{
            "symbol":symbol,"days":days,"n":n,
            "regime_dist":dist,"regime_pct":dist_pct,
            "transitions":transitions,"fast_transitions":fast_trans,
            "quality":quality,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}


@router.get("/coverage")
def v25_coverage(
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
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m)
        t5_idx={T5[i]:i for i in range(n5)}
        cost=fee_pct+slippage_pct

        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_arr=[]
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_arr.append(s)

        # Count 15m_reclaim entries per tier combination
        M=15*60*1000
        tier_combos=["A","AB","ABC"]  # cumulative
        results={}
        
        for combo in tier_combos:
            allowed=set(combo) if combo!="ABC" else {"A","B","C"}
            if combo=="AB":allowed={"A","B"}
            elif combo=="A":allowed={"A"}
            
            cands=[]
            for i in range(max(ema_slow*2,60),n1):
                if tiers[i] not in allowed:continue
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

            # Simulate with sym TP/SL 1.3% to measure raw quality
            tp=0.013;sl=0.013
            trades=[];pos_end=-1
            for c in cands:
                j=c["j"];sd=c["sd"];ep=c["ep"]
                if j<=pos_end:continue
                if sd=="LONG":tp_l=ep*(1+tp);sl_l=ep*(1-sl)
                else:tp_l=ep*(1-tp);sl_l=ep*(1+sl)
                res=None
                for jj in range(j+1,min(j+200,n5)):
                    if sd=="LONG":hs=L5[jj]<=sl_l;ht=H5[jj]>=tp_l
                    else:hs=H5[jj]>=sl_l;ht=L5[jj]<=tp_l
                    if hs and ht:ht=False
                    if hs:res={"x":"SL","p":round((-sl-cost)*100,3),"sd":sd,"t":c["tier"]};pos_end=jj;break
                    if ht:res={"x":"TP","p":round((sl-cost)*100,3),"sd":sd,"t":c["tier"]};pos_end=jj;break  # note: TP pnl uses sl since symmetric
                if not res:
                    eb=min(j+200,n5)-1;pp=(C5[eb]-ep)/ep if sd=="LONG" else (ep-C5[eb])/ep;pp-=cost
                    res={"x":"TO","p":round(pp*100,3),"sd":sd,"t":c["tier"]};pos_end=eb
                trades.append(res)

            nt=len(trades)
            tpd=round(nt/days,3)
            ws=sum(1 for t in trades if t["p"]>0)
            gr=sum((t["p"]+cost*100)/100*500 for t in trades)
            ne=sum(t["p"]/100*500 for t in trades)
            # Per tier within combo
            tier_br={}
            for tier in allowed:
                tt=[t for t in trades if t["t"]==tier]
                if not tt:continue
                tw=sum(1 for t in tt if t["p"]>0)
                tier_br[tier]={"n":len(tt),"wr":round(100*tw/len(tt),1),
                    "net":round(sum(t["p"]/100*500 for t in tt),2)}
            # Walk-forward
            third=n5//3
            wf={}
            for fn,fs,fe in[("F1",0,third),("F2",third,2*third),("F3",2*third,n5)]:
                ft=[t for t in trades if fs<=cands[trades.index(t)]["j"]<fe] if trades else []
                # safer way
                ft_pnl=0;ft_n=0
                for idx,t in enumerate(trades):
                    ci=cands[idx] if idx<len(cands) else None
                    if ci and fs<=ci["j"]<fe:ft_pnl+=t["p"]/100*500;ft_n+=1
                wf[fn]={"n":ft_n,"pnl":round(ft_pnl,2)}

            results[combo]={
                "tiers":list(allowed),"candidates":len(cands),"trades":nt,"tpd":tpd,
                "wr":round(100*ws/nt,1) if nt else 0,"gr":round(gr,2),"ne":round(ne,2),
                "nee":round(ne/nt,3) if nt else 0,
                "tier_breakdown":tier_br,"wf":wf,
            }

        # Coverage tier check
        cov_check={}
        for target in [0.25,0.50,0.75,1.00,1.50]:
            best=None
            for combo in tier_combos:
                if results[combo]["tpd"]>=target:
                    if best is None or results[combo]["ne"]>results[best]["ne"]:best=combo
            cov_check[str(target)]={"achievable":best is not None,"best_combo":best,
                "tpd":results[best]["tpd"] if best else 0,"net":results[best]["ne"] if best else 0}

        return{
            "symbol":symbol,"days":days,"n_1h":n1,"n_15m":n5,
            "regime_pct":{t:round(100*sum(1 for x in tiers if x==t)/n1,1) for t in["A","B","C","SIDEWAYS"]},
            "results":results,"coverage_tiers":cov_check,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
