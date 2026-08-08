"""Taker-flow forensic audit — Phase 0/1/2/3.

Phase 0: validate taker data
Phase 1: build causal features
Phase 2: winner vs loser forensic
Phase 3: hypothesis testing (if lift exists)

GET /taker/validate?symbol=SOLUSDT
GET /taker/forensic?symbol=SOLUSDT&days=971
"""
import os,sqlite3,numpy as np,random,traceback
from fastapi import APIRouter, Query
from datetime import datetime
from v25_detector_endpoint import V25Detector

router = APIRouter(prefix="/taker", tags=["taker"])
DB_PATH = os.environ.get("DB_PATH","market_data.db")

def _ld_full(sym,tf,days):
    """Load with ALL fields including taker volumes."""
    conn=sqlite3.connect(DB_PATH);now=int(datetime.utcnow().timestamp()*1000);st=now-(days*86400*1000)
    r=conn.cursor().execute(
        "SELECT open_time,open,high,low,close,volume,close_time,quote_volume,trades,taker_buy_volume,taker_buy_quote_volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC",
        (sym,tf,st,now)).fetchall()
    conn.close();return r

def _ema(c,p):
    e=np.zeros(len(c));e[0]=c[0];k=2.0/(p+1)
    for i in range(1,len(c)):e[i]=c[i]*k+e[i-1]*(1-k)
    return e

def _atr(H,L,C,p=14):
    n=len(H);a=np.zeros(n)
    for i in range(1,n):t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]));a[i]=a[i-1]+(t-a[i-1])/min(i,p)
    return a

def _zscore(arr,lb=20):
    n=len(arr);z=np.zeros(n)
    for i in range(lb,n):
        w=arr[i-lb:i];m=np.mean(w);s=np.std(w)
        z[i]=(arr[i]-m)/s if s>0 else 0
    return z

@router.get("/validate")
def validate(symbol:str=Query("SOLUSDT"),days:int=Query(971)):
    try:
        results={}
        for tf in["15m","1h"]:
            rows=_ld_full(symbol,tf,days)
            if not rows:results[tf]={"error":"no data"};continue
            n=len(rows)
            # Extract fields
            vol=[r[5] for r in rows];tbv=[r[9] for r in rows];tbqv=[r[10] for r in rows]
            ts=[r[0] for r in rows];ct=[r[6] for r in rows];trades=[r[8] for r in rows]
            # Checks
            tbv_leq_vol=sum(1 for i in range(n) if tbv[i]<=vol[i]+0.001)
            tbv_null=sum(1 for v in tbv if v is None or v==0)
            vol_null=sum(1 for v in vol if v is None or v==0)
            # Intervals
            intervals=set()
            for i in range(1,min(n,1000)):intervals.add(ts[i]-ts[i-1])
            expected=15*60*1000 if tf=="15m" else 3600*1000
            # Duplicates
            ts_set=set(ts);dupes=n-len(ts_set)
            # Gaps
            gaps=0
            for i in range(1,n):
                if ts[i]-ts[i-1]>expected*1.5:gaps+=1
            # Derive delta
            delta=[tbv[i]-(vol[i]-tbv[i]) for i in range(n)]
            delta_pct=[delta[i]/vol[i]*100 if vol[i]>0 else 0 for i in range(n)]
            
            results[tf]={
                "rows":n,"first_ts":ts[0],"last_ts":ts[-1],
                "days_covered":round((ts[-1]-ts[0])/(86400*1000),1),
                "expected_interval_ms":expected,
                "actual_intervals":sorted(intervals)[:5],
                "interval_consistent":len(intervals)==1 and expected in intervals,
                "duplicates":dupes,"gaps":gaps,
                "taker_buy_vol_present":tbv_null==0,
                "taker_buy_leq_total":tbv_leq_vol==n,
                "taker_buy_null_count":tbv_null,
                "volume_null_count":vol_null,
                "delta_pct_range":[round(min(delta_pct),2),round(max(delta_pct),2)],
                "delta_pct_mean":round(np.mean(delta_pct),3),
                "delta_pct_std":round(np.std(delta_pct),3),
                "sample_first_5":[{"ts":ts[i],"vol":round(vol[i],2),"tbv":round(tbv[i],2),
                    "tsv":round(vol[i]-tbv[i],2),"delta":round(delta[i],2),"delta_pct":round(delta_pct[i],2)} for i in range(min(5,n))],
                "causal_note":"all fields aggregate activity WITHIN candle [open_time, close_time). Available at close_time.",
            }
        return{"symbol":symbol,"validation":results}
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}


@router.get("/forensic")
def forensic(
    symbol:str=Query("SOLUSDT"),days:int=Query(971),
    ema_1h:int=Query(7),ema_slow:int=Query(20),ema_15m:int=Query(7),
    swing_lb:int=Query(10),swing_atr:float=Query(0.5),impulse_atr:float=Query(1.5),
    body_min:float=Query(0.3),tp_pct:float=Query(0.013),sl_pct:float=Query(0.013),
    fee_pct:float=Query(0.001),slippage_pct:float=Query(0.0005),
):
    try:
        r1h=_ld_full(symbol,"1h",days);r15m=_ld_full(symbol,"15m",days)
        if len(r1h)<100:return{"error":"not enough 1h"}
        if not r15m:return{"error":"no 15m"}

        # 1H arrays
        O1=np.array([r[1] for r in r1h],dtype=float);H1=np.array([r[2] for r in r1h],dtype=float)
        L1=np.array([r[3] for r in r1h],dtype=float);C1=np.array([r[4] for r in r1h],dtype=float)
        V1=np.array([r[5] for r in r1h],dtype=float);TBV1=np.array([r[9] for r in r1h],dtype=float)
        T1=[r[0] for r in r1h];n1=len(r1h)
        ef1=_ema(C1,ema_1h);es1=_ema(C1,ema_slow);at1=_atr(H1,L1,C1)
        # 1H delta
        TSV1=V1-TBV1;D1=TBV1-TSV1;DP1=np.where(V1>0,D1/V1*100,0)
        D1_z=_zscore(DP1,20)

        # 15m arrays
        O5=np.array([r[1] for r in r15m],dtype=float);H5=np.array([r[2] for r in r15m],dtype=float)
        L5=np.array([r[3] for r in r15m],dtype=float);C5=np.array([r[4] for r in r15m],dtype=float)
        V5=np.array([r[5] for r in r15m],dtype=float);TBV5=np.array([r[9] for r in r15m],dtype=float)
        T5=[r[0] for r in r15m];n5=len(r15m)
        ef5=_ema(C5,ema_15m);at5=_atr(H5,L5,C5)
        t5_idx={T5[i]:i for i in range(n5)};t1_idx={T1[i]:i for i in range(n1)}
        # 15m delta
        TSV5=V5-TBV5;D5=TBV5-TSV5;DP5=np.where(V5>0,D5/V5*100,0)
        D5_z=_zscore(DP5,20)
        V5_z=_zscore(V5,20)
        # Rolling delta sums
        D5_sum2=np.zeros(n5);D5_sum4=np.zeros(n5);D5_sum8=np.zeros(n5)
        for i in range(2,n5):D5_sum2[i]=D5[i]+D5[i-1]
        for i in range(4,n5):D5_sum4[i]=sum(D5[i-3:i+1])
        for i in range(8,n5):D5_sum8[i]=sum(D5[i-7:i+1])
        # Delta slope (4-bar)
        D5_slope=np.zeros(n5)
        for i in range(4,n5):D5_slope[i]=DP5[i]-DP5[i-4]
        # Taker buy ratio
        TBR5=np.where(V5>0,TBV5/V5,0.5)

        cost=fee_pct+slippage_pct;M=15*60*1000;H1h=3600*1000

        # V2.5 regime
        det=V25Detector(ema_1h,ema_slow,swing_lb,swing_atr,3,impulse_atr)
        tiers=[];sides_a=[]
        for i in range(n1):
            t,s=det.process(i,O1,H1,L1,C1,ef1,es1,at1)
            tiers.append(t);sides_a.append(s)

        # Generate entries with taker features
        entries=[];random.seed(42)
        for i in range(max(ema_slow*2,60),n1):
            if tiers[i] not in("A","C"):continue
            sd=sides_a[i]
            if sd is None:continue
            side="LONG" if sd=="BULL" else "SHORT"
            nxt=T1[i]+H1h
            for k in range(4):
                t15=nxt+k*M;j=t5_idx.get(t15)
                if j is None or j<21:continue
                o,h,l,c=O5[j],H5[j],L5[j],C5[j];e=ef5[j]
                rng=h-l;bdy=abs(c-o)/rng if rng>0 else 0
                if side=="LONG":ok=(l<=e)and(c>e)and(c>o)and(bdy>=body_min)
                else:ok=(h>=e)and(c<e)and(c<o)and(bdy>=body_min)
                if not ok:continue

                # ═══ TAKER FEATURES at entry time ═══
                # 15m features
                dp=float(DP5[j]);dz=float(D5_z[j]);vz=float(V5_z[j])
                ds2=float(D5_sum2[j]);ds4=float(D5_sum4[j]);ds8=float(D5_sum8[j])
                dsl=float(D5_slope[j]);tbr=float(TBR5[j])
                # Price-delta divergence: price up but delta negative (bearish div) or vice versa
                ret4=(c-C5[j-4])/C5[j-4]*100 if j>=4 else 0
                pdiv=ret4*dp  # positive = aligned, negative = divergent

                # 1H completed features (use bar i, which is the completed 1H)
                dp1h=float(DP1[i]);d1h_z=float(D1_z[i])
                # 1H rolling delta
                rd1h=float(sum(DP1[max(0,i-3):i+1])/min(4,i+1))
                # 1H price-delta div
                ret1h=(C1[i]-C1[max(0,i-4)])/C1[max(0,i-4)]*100 if i>=4 else 0
                pdiv1h=ret1h*dp1h

                # 4H completed: aggregate last 4 completed 1H bars
                if i>=4:
                    d4h=float(sum(DP1[i-3:i+1])/4)
                else:d4h=0

                # Delta aligned with direction
                if side=="LONG":delta_aligned=dp>0;d4h_aligned=d4h>0
                else:delta_aligned=dp<0;d4h_aligned=d4h<0

                feat={
                    "j":j,"sd":side,"ep":float(c),"i1h":i,
                    "dp":round(dp,2),"dz":round(dz,2),"vz":round(vz,2),
                    "ds2":round(ds2,2),"ds4":round(ds4,2),"ds8":round(ds8,2),
                    "dsl":round(dsl,2),"tbr":round(tbr,3),
                    "pdiv":round(pdiv,2),"dp1h":round(dp1h,2),"d1h_z":round(d1h_z,2),
                    "rd1h":round(rd1h,2),"pdiv1h":round(pdiv1h,2),"d4h":round(d4h,2),
                    "delta_aligned":delta_aligned,"d4h_aligned":d4h_aligned,
                }

                # ═══ OUTCOME LABELS ═══
                tp_l=c*(1+tp_pct) if side=="LONG" else c*(1-tp_pct)
                sl_l=c*(1-sl_pct) if side=="LONG" else c*(1+sl_pct)
                tb=999;sb=999;mfe=0;mae=0
                for jj in range(j+1,min(j+200,n5)):
                    if side=="LONG":fv=(H5[jj]-c)/c;av=(c-L5[jj])/c
                    else:fv=(c-L5[jj])/c;av=(H5[jj]-c)/c
                    if fv>mfe:mfe=fv
                    if av>mae:mae=av
                    if tb==999:
                        if side=="LONG" and H5[jj]>=tp_l:tb=jj-j
                        elif side=="SHORT" and L5[jj]<=tp_l:tb=jj-j
                    if sb==999:
                        if side=="LONG" and L5[jj]<=sl_l:sb=jj-j
                        elif side=="SHORT" and H5[jj]>=sl_l:sb=jj-j
                if sb<=tb:feat["outcome"]="SL"
                elif tb<999:feat["outcome"]="TP"
                else:feat["outcome"]="TO"
                feat["mfe"]=round(mfe*100,3);feat["mae"]=round(mae*100,3)
                entries.append(feat);break

        # ═══ PHASE 2: Winner vs Loser ═══
        wins=[e for e in entries if e["outcome"]=="TP"]
        losses=[e for e in entries if e["outcome"]=="SL"]
        nt=len(entries);nw=len(wins);nl=len(losses)

        taker_feats=["dp","dz","vz","ds2","ds4","ds8","dsl","tbr","pdiv",
                      "dp1h","d1h_z","rd1h","pdiv1h","d4h"]
        bool_feats=["delta_aligned","d4h_aligned"]

        comparison={}
        for fn in taker_feats:
            wv=[e[fn] for e in wins];lv=[e[fn] for e in losses]
            if not wv or not lv:continue
            wm=round(float(np.median(wv)),3);lm=round(float(np.median(lv)),3)
            lift=round(wm-lm,3)
            comparison[fn]={"win_med":wm,"loss_med":lm,"lift":lift,
                "win_p25":round(float(np.percentile(wv,25)),3),"win_p75":round(float(np.percentile(wv,75)),3),
                "loss_p25":round(float(np.percentile(lv,25)),3),"loss_p75":round(float(np.percentile(lv,75)),3)}
        for fn in bool_feats:
            wv=[e[fn] for e in wins];lv=[e[fn] for e in losses]
            wr=round(100*sum(wv)/len(wv),1);lr=round(100*sum(lv)/len(lv),1)
            comparison[fn]={"win_rate":wr,"loss_rate":lr,"lift":round(wr-lr,1)}

        # Quantile analysis
        quantiles={}
        for fn in["dp","dz","ds4","tbr","pdiv","d4h"]:
            vals=[e[fn] for e in entries]
            if len(vals)<40:continue
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
                qr[qn]={"n":len(ql),"wr":round(100*w/len(ql),1)}
            quantiles[fn]={"cuts":[round(q25,2),round(q50,2),round(q75,2)],"bins":qr}

        # Walk-forward: split entries into thirds
        third=n5//3
        wf_comparison={}
        for fn in["dp","dz","ds4","delta_aligned","d4h_aligned"]:
            folds={}
            for fname,fs,fe in[("F1",0,third),("F2",third,2*third),("F3",2*third,n5)]:
                fe_=[e for e in entries if fs<=e["j"]<fe]
                if len(fe_)<20:folds[fname]={"n":len(fe_)};continue
                w=[e for e in fe_ if e["outcome"]=="TP"]
                if fn in bool_feats:
                    aligned=[e for e in fe_ if e[fn]];not_aligned=[e for e in fe_ if not e[fn]]
                    aw=round(100*sum(1 for e in aligned if e["outcome"]=="TP")/len(aligned),1) if aligned else 0
                    naw=round(100*sum(1 for e in not_aligned if e["outcome"]=="TP")/len(not_aligned),1) if not_aligned else 0
                    folds[fname]={"n":len(fe_),"aligned_wr":aw,"not_aligned_wr":naw,"lift":round(aw-naw,1)}
                else:
                    above_med=[e for e in fe_ if e[fn]>=np.median([x[fn] for x in fe_])]
                    below_med=[e for e in fe_ if e[fn]<np.median([x[fn] for x in fe_])]
                    awr=round(100*sum(1 for e in above_med if e["outcome"]=="TP")/len(above_med),1) if above_med else 0
                    bwr=round(100*sum(1 for e in below_med if e["outcome"]=="TP")/len(below_med),1) if below_med else 0
                    folds[fname]={"n":len(fe_),"above_med_wr":awr,"below_med_wr":bwr,"lift":round(awr-bwr,1)}
            wf_comparison[fn]=folds

        # ═══ PHASE 3: Hypotheses (if lift exists) ═══
        hyp_results={}
        for hname,hfilter in[
            ("A_delta_aligned",lambda e:e["delta_aligned"]),
            ("B_delta_cross",lambda e:(e["dp"]>5 and e["sd"]=="LONG") or (e["dp"]<-5 and e["sd"]=="SHORT")),
            ("C_strong_dz",lambda e:(e["dz"]>1.0 and e["sd"]=="LONG") or (e["dz"]<-1.0 and e["sd"]=="SHORT")),
            ("D_no_divergence",lambda e:e["pdiv"]>=0),
            ("E_4h_aligned",lambda e:e["d4h_aligned"]),
        ]:
            filtered=[e for e in entries if hfilter(e)]
            nf=len(filtered)
            if nf<20:hyp_results[hname]={"n_filtered":nf};continue
            # Integrated one-position sim
            trades=[];pos_end=-1
            for e in sorted(filtered,key=lambda x:x["j"]):
                if e["j"]<=pos_end:continue
                if e["outcome"]=="TP":p=tp_pct-cost;b=e.get("tp_bar",50)
                elif e["outcome"]=="SL":p=-sl_pct-cost;b=e.get("sl_bar",50)
                else:p=-cost;b=200
                # Approximate bar from tb/sb
                trades.append({"p":round(p*100,3),"j":e["j"],"sd":e["sd"]})
                pos_end=e["j"]+50  # approximate hold
            nt_h=len(trades)
            if nt_h==0:hyp_results[hname]={"n_filtered":nf,"n_trades":0};continue
            ws=sum(1 for t in trades if t["p"]>0)
            gr=sum((t["p"]+cost*100)/100*500 for t in trades)
            ne=sum(t["p"]/100*500 for t in trades)
            lo=[t for t in trades if t["sd"]=="LONG"];sh=[t for t in trades if t["sd"]=="SHORT"]
            f1=[t for t in trades if t["j"]<third];f2=[t for t in trades if third<=t["j"]<2*third];f3=[t for t in trades if t["j"]>=2*third]
            fp=[round(sum(t["p"]/100*500 for t in f),2) for f in[f1,f2,f3]]
            hyp_results[hname]={
                "n_filtered":nf,"n_trades":nt_h,"tpd":round(nt_h/days,3),
                "wr":round(100*ws/nt_h,1),"gr":round(gr,2),"ne":round(ne,2),"nee":round(ne/nt_h,3),
                "L":{"n":len(lo),"wr":round(100*sum(1 for t in lo if t["p"]>0)/len(lo),1) if lo else 0},
                "S":{"n":len(sh),"wr":round(100*sum(1 for t in sh if t["p"]>0)/len(sh),1) if sh else 0},
                "wf":{"F1":{"n":len(f1),"p":fp[0]},"F2":{"n":len(f2),"p":fp[1]},"F3":{"n":len(f3),"p":fp[2]},
                      "pos":sum(1 for p in fp if p>0)},
            }

        return{
            "symbol":symbol,"days":days,"n_entries":nt,"n_wins":nw,"n_losses":nl,
            "baseline_wr":round(100*nw/nt,1) if nt else 0,
            "feature_comparison":comparison,
            "quantile_analysis":quantiles,
            "walk_forward":wf_comparison,
            "hypotheses":hyp_results,
        }
    except Exception as e:
        return{"error":str(e),"trace":traceback.format_exc()}
