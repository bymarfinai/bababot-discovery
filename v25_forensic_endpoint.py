"""Forensic winner-vs-loser analysis on A+C 15m_reclaim stream.

Features at entry time only. First-touch labels. No future features.
Hypotheses A-D tested with integrated one-position-per-pair.

GET /v25/forensic?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from v25_detector_endpoint import V25Detector

router = APIRouter(prefix="/v25", tags=["forensic"])
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

def _sma(v,p):
    n=len(v);s=np.zeros(n)
    for i in range(p,n):s[i]=np.mean(v[i-p:i])
    return s

def _pct(arr,p):
    if not arr:return 0
    return round(float(np.percentile(arr,p)),4)

@router.get("/forensic")
def forensic(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),ema_15m_slow:int=Query(20),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),impulse_atr:float=Query(1.5),
    body_min:float=Query(0.3),tp_pct:float=Query(0.013),sl_pct:float=Query(0.013),
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
        ef5=_ema(C5,ema_15m);es5=_ema(C5,ema_15m_slow);at5=_atr(H5,L5,C5)
        vol_med=_sma(V5,20)
        t5_idx={T5[i]:i for i in range(n5)}
        cost=fee_pct+slippage_pct;not_=500.0

        # V2.5 regime
        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_a=[];regime_start=[]
        cur_regime=None;cur_start=0
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_a.append(s)
            if t!=cur_regime:cur_regime=t;cur_start=i
            regime_start.append(cur_start)

        # Generate entries + features
        M=15*60*1000;entries=[]
        for i in range(max(ema_slow*2,60),n1):
            if tiers[i] not in("A","C"):continue
            sd=sides_a[i]
            if sd is None:continue
            side="LONG" if sd=="BULL" else "SHORT"
            nxt=T1[i]+3600*1000
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is None or j<max(ema_15m_slow*2,21):continue
                o,h,l,c=O5[j],H5[j],L5[j],C5[j]
                e7=ef5[j];e20=es5[j];atr_v=at5[j]
                rng=h-l;body=abs(c-o);bdy=body/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e7)and(c>e7)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e7)and(c<e7)and(c<o)and(bdy>=body_min)
                if not ok:continue

                # ═══ FEATURES (all at entry time) ═══
                spread=e7-e20
                spread_atr=spread/atr_v if atr_v>0 else 0
                e7_above_e20=e7>e20
                # Slopes (3-bar)
                e7_slope=(e7-ef5[j-3])/atr_v if j>=3 and atr_v>0 else 0
                e20_slope=(e20-es5[j-3])/atr_v if j>=3 and atr_v>0 else 0
                # Fresh cross: EMA7 crossed EMA20 within last N bars
                cross_lb=12  # 3 hours of 15m
                fresh_cross=False
                for jj in range(max(1,j-cross_lb),j):
                    if (ef5[jj-1]<es5[jj-1] and ef5[jj]>=es5[jj]) or (ef5[jj-1]>es5[jj-1] and ef5[jj]<=es5[jj]):
                        fresh_cross=True;break
                # Spread widening
                if j>=4:spread_widening=(abs(e7-e20)-abs(ef5[j-4]-es5[j-4]))/atr_v if atr_v>0 else 0
                else:spread_widening=0
                # Price distance from EMAs
                dist_e7=abs(c-e7)/atr_v if atr_v>0 else 0
                dist_e20=abs(c-e20)/atr_v if atr_v>0 else 0
                # Pullback depth/duration (bars since last swing)
                pb_depth=0;pb_dur=0
                if side=="LONG":
                    for jj in range(j-1,max(j-20,0),-1):
                        if L5[jj]<=ef5[jj]:pb_dur+=1;d=(ef5[jj]-L5[jj])/atr_v if atr_v>0 else 0;pb_depth=max(pb_depth,d)
                        else:break
                else:
                    for jj in range(j-1,max(j-20,0),-1):
                        if H5[jj]>=ef5[jj]:pb_dur+=1;d=(H5[jj]-ef5[jj])/atr_v if atr_v>0 else 0;pb_depth=max(pb_depth,d)
                        else:break
                # Close location
                cl_loc=(c-l)/rng if rng>0 else 0.5
                # Range vs ATR
                rng_atr=rng/atr_v if atr_v>0 else 1
                # Volume vs median
                vol_ratio=V5[j]/vol_med[j] if vol_med[j]>0 else 1
                # Distance to swing high/low (approximate: 20-bar lookback)
                recent_hi=max(H5[max(0,j-20):j+1]);recent_lo=min(L5[max(0,j-20):j+1])
                dist_sh=(recent_hi-c)/atr_v if atr_v>0 else 0
                dist_sl=(c-recent_lo)/atr_v if atr_v>0 else 0
                # Bars since regime started
                bars_in_regime=i-regime_start[i]
                # Prior returns
                ret4=(c-C5[j-4])/C5[j-4]*100 if j>=4 else 0
                ret8=(c-C5[j-8])/C5[j-8]*100 if j>=8 else 0
                ret16=(c-C5[j-16])/C5[j-16]*100 if j>=16 else 0

                feat={
                    "j":j,"sd":side,"ep":float(c),"tier":tiers[i],"i1h":i,
                    "e7_above_e20":e7_above_e20,"spread_atr":round(spread_atr,3),
                    "e7_slope":round(e7_slope,3),"e20_slope":round(e20_slope,3),
                    "fresh_cross":fresh_cross,"spread_widen":round(spread_widening,3),
                    "dist_e7":round(dist_e7,3),"dist_e20":round(dist_e20,3),
                    "pb_depth":round(pb_depth,3),"pb_dur":pb_dur,
                    "body_ratio":round(bdy,3),"cl_loc":round(cl_loc,3),
                    "rng_atr":round(rng_atr,3),"vol_ratio":round(vol_ratio,3),
                    "dist_sh":round(dist_sh,3),"dist_sl":round(dist_sl,3),
                    "bars_regime":bars_in_regime,
                    "ret4":round(ret4,3),"ret8":round(ret8,3),"ret16":round(ret16,3),
                }

                # ═══ OUTCOME LABELS ═══
                tp_l=c*(1+tp_pct) if side=="LONG" else c*(1-tp_pct)
                sl_l=c*(1-sl_pct) if side=="LONG" else c*(1+sl_pct)
                tp_bar=999;sl_bar=999;mfe=0;mae=0
                for jj in range(j+1,min(j+200,n5)):
                    if side=="LONG":fv=(H5[jj]-c)/c;av=(c-L5[jj])/c
                    else:fv=(c-L5[jj])/c;av=(H5[jj]-c)/c
                    if fv>mfe:mfe=fv
                    if av>mae:mae=av
                    if tp_bar==999:
                        if side=="LONG" and H5[jj]>=tp_l:tp_bar=jj-j
                        elif side=="SHORT" and L5[jj]<=tp_l:tp_bar=jj-j
                    if sl_bar==999:
                        if side=="LONG" and L5[jj]<=sl_l:sl_bar=jj-j
                        elif side=="SHORT" and H5[jj]>=sl_l:sl_bar=jj-j
                if sl_bar<=tp_bar:outcome="SL"
                elif tp_bar<999:outcome="TP"
                else:outcome="TO"
                feat["outcome"]=outcome
                feat["mfe"]=round(mfe*100,3);feat["mae"]=round(mae*100,3)
                feat["tp_bar"]=tp_bar;feat["sl_bar"]=sl_bar
                entries.append(feat)
                break  # one per 1H bar

        # ═══ WINNER vs LOSER ANALYSIS ═══
        wins=[e for e in entries if e["outcome"]=="TP"]
        losses=[e for e in entries if e["outcome"]=="SL"]
        nw=len(wins);nl=len(losses);nt=len(entries)

        feat_names=["e7_above_e20","spread_atr","e7_slope","e20_slope","fresh_cross",
                     "spread_widen","dist_e7","dist_e20","pb_depth","pb_dur",
                     "body_ratio","cl_loc","rng_atr","vol_ratio",
                     "dist_sh","dist_sl","bars_regime","ret4","ret8","ret16"]
        
        comparison={}
        for fn in feat_names:
            wv=[e[fn] for e in wins if isinstance(e[fn],(int,float))]
            lv=[e[fn] for e in losses if isinstance(e[fn],(int,float))]
            if not wv or not lv:continue
            if isinstance(wins[0][fn],bool):
                # Boolean feature
                w_rate=round(100*sum(1 for v in wv if v)/len(wv),1)
                l_rate=round(100*sum(1 for v in lv if v)/len(lv),1)
                comparison[fn]={"type":"bool","win_rate":w_rate,"loss_rate":l_rate,"lift":round(w_rate-l_rate,1)}
            else:
                wm=round(float(np.median(wv)),4);lm=round(float(np.median(lv)),4)
                comparison[fn]={
                    "type":"numeric",
                    "win_med":wm,"loss_med":lm,"lift_med":round(wm-lm,4),
                    "win_p25":_pct(wv,25),"win_p75":_pct(wv,75),
                    "loss_p25":_pct(lv,25),"loss_p75":_pct(lv,75),
                }

        # Quantile bin analysis for top features
        quantile_analysis={}
        for fn in["spread_atr","e7_slope","dist_e7","pb_depth","vol_ratio","bars_regime","ret4"]:
            vals=[e[fn] for e in entries if isinstance(e[fn],(int,float))]
            if len(vals)<20:continue
            q25,q50,q75=np.percentile(vals,[25,50,75])
            bins={"Q1":[],"Q2":[],"Q3":[],"Q4":[]}
            for e in entries:
                v=e[fn]
                if v<=q25:bins["Q1"].append(e)
                elif v<=q50:bins["Q2"].append(e)
                elif v<=q75:bins["Q3"].append(e)
                else:bins["Q4"].append(e)
            qr={}
            for qn,ql in bins.items():
                if not ql:continue
                w=sum(1 for e in ql if e["outcome"]=="TP")
                gr=sum((tp_pct if e["outcome"]=="TP" else -sl_pct)*not_ for e in ql)
                ne=sum(((tp_pct if e["outcome"]=="TP" else -sl_pct)-cost)*not_ for e in ql)
                qr[qn]={"n":len(ql),"wr":round(100*w/len(ql),1),"gr":round(gr,2),"ne":round(ne,2)}
            quantile_analysis[fn]={"cuts":[round(q25,4),round(q50,4),round(q75,4)],"bins":qr}

        # ═══ HYPOTHESES A-D: integrated one-position-per-pair ═══
        third=n5//3
        hyp_results={}
        for hyp_name,hyp_filter in[
            ("A_aligned",lambda e:e["e7_above_e20"]==(e["sd"]=="LONG")),
            ("B_fresh_cross",lambda e:e["fresh_cross"] and e["e7_above_e20"]==(e["sd"]=="LONG")),
            ("C_spread_widen",lambda e:e["e7_above_e20"]==(e["sd"]=="LONG") and e["spread_widen"]>0),
            ("D_aligned_only",lambda e:e["e7_above_e20"]==(e["sd"]=="LONG") and abs(e["spread_atr"])>0.3),
        ]:
            filtered=[e for e in entries if hyp_filter(e)]
            # Integrated sim
            trades=[];pos_end=-1
            for e in filtered:
                j=e["j"];sd=e["sd"];ep=e["ep"]
                if j<=pos_end:continue
                if e["outcome"]=="TP":p=tp_pct-cost;b=e["tp_bar"]
                elif e["outcome"]=="SL":p=-sl_pct-cost;b=e["sl_bar"]
                else:p=-cost;b=200
                trades.append({"p":round(p*100,3),"sd":sd,"j":j,"b":b})
                pos_end=j+b
            nt_h=len(trades)
            if nt_h==0:hyp_results[hyp_name]={"n_filtered":len(filtered),"n_trades":0};continue
            ws=sum(1 for t in trades if t["p"]>0)
            gr=sum((t["p"]+cost*100)/100*not_ for t in trades)
            ne=sum(t["p"]/100*not_ for t in trades)
            f1=[t for t in trades if t["j"]<third];f2=[t for t in trades if third<=t["j"]<2*third];f3=[t for t in trades if t["j"]>=2*third]
            fp=[round(sum(t["p"]/100*not_ for t in f),2) for f in[f1,f2,f3]]
            lo=[t for t in trades if t["sd"]=="LONG"];sh=[t for t in trades if t["sd"]=="SHORT"]
            hyp_results[hyp_name]={
                "n_filtered":len(filtered),"n_trades":nt_h,"tpd":round(nt_h/days,3),
                "wr":round(100*ws/nt_h,1),"gr":round(gr,2),"ne":round(ne,2),"nee":round(ne/nt_h,3),
                "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                "wf":{"F1":{"n":len(f1),"p":fp[0]},"F2":{"n":len(f2),"p":fp[1]},"F3":{"n":len(f3),"p":fp[2]},
                      "pos":sum(1 for p in fp if p>0)},
            }

        return{
            "symbol":symbol,"days":days,"n_entries":len(entries),
            "n_wins":nw,"n_losses":nl,"n_timeout":nt-nw-nl,
            "baseline_wr":round(100*nw/nt,1) if nt else 0,
            "feature_comparison":comparison,
            "quantile_analysis":quantile_analysis,
            "hypotheses":hyp_results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
