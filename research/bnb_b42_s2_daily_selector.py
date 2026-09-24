#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json, math

import numpy as np
import pandas as pd
import vectorbt as vbt
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier

import bnb_b42_s1_opportunity_atlas as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B42_S2_DAILY_SELECTOR"
S1_SIG="ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd"
THRESHOLDS=[.50,.55,.60,.65,.70,.75,.80,.85,.90]
BAR5=pd.Timedelta(minutes=5)
FEATURES=[
 "signed_ret_5m","signed_ret_15m","signed_ret_30m","signed_ret_60m",
 "signed_ret_120m","signed_ret_240m","signed_clv",
 "signed_range_pos_60m","signed_range_pos_240m","signed_range_pos_24h",
 "trend_eff_60m","trend_eff_240m","realized_vol_60m","realized_vol_240m",
 "atr14_pct","signed_ma7_gap","signed_ma20_gap","signed_ma50_gap",
 "signed_ma20_slope_15m","signed_rsi14","volume_ratio_60m","volume_z_240m",
 "hour_sin","hour_cos","dow_sin","dow_cos","side_long"
]

def verify_parent():
    p=ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Freeze.txt"
    txt=p.read_text()
    if f"S1_SIGNATURE_SHA256={S1_SIG}" not in txt:
        raise RuntimeError("S1 signature mismatch")

def rolling_eff(close,n):
    path=close.diff().abs().rolling(n-1,min_periods=n-1).sum()
    net=(close-close.shift(n-1)).abs()
    return net/path.replace(0,np.nan)

def range_pos(close,high,low,n):
    hi=high.rolling(n,min_periods=n).max()
    lo=low.rolling(n,min_periods=n).min()
    return 2*(close-lo)/(hi-lo).replace(0,np.nan)-1

def feature_base(raw):
    close=raw.close; high=raw.high; low=raw.low; vol=raw.volume
    f=pd.DataFrame(index=raw.index)
    for n,name in [(1,"5m"),(3,"15m"),(6,"30m"),(12,"60m"),(24,"120m"),(48,"240m")]:
        f[f"ret_{name}"]=close/close.shift(n)-1
    rng=(high-low).replace(0,np.nan)
    f["clv"]=((close-low)-(high-close))/rng
    f["range_pos_60m"]=range_pos(close,high,low,12)
    f["range_pos_240m"]=range_pos(close,high,low,48)
    f["range_pos_24h"]=range_pos(close,high,low,288)
    f["trend_eff_60m"]=rolling_eff(close,12)
    f["trend_eff_240m"]=rolling_eff(close,48)
    r=close.pct_change()
    f["realized_vol_60m"]=r.rolling(12,min_periods=12).std(ddof=0)
    f["realized_vol_240m"]=r.rolling(48,min_periods=48).std(ddof=0)

    cs=pd.Series(close.to_numpy(),index=close.index,name="close")
    hs=pd.Series(high.to_numpy(),index=high.index,name="high")
    ls=pd.Series(low.to_numpy(),index=low.index,name="low")
    ma7=vbt.MA.run(cs,window=7).ma
    ma20=vbt.MA.run(cs,window=20).ma
    ma50=vbt.MA.run(cs,window=50).ma
    rsi=vbt.RSI.run(cs,window=14).rsi
    atr=vbt.ATR.run(hs,ls,cs,window=14).atr
    f["ma7_gap"]=close/ma7-1
    f["ma20_gap"]=close/ma20-1
    f["ma50_gap"]=close/ma50-1
    f["ma20_slope_15m"]=ma20/ma20.shift(3)-1
    f["rsi14"]=(rsi-50)/50
    f["atr14_pct"]=atr/close

    medv=vol.rolling(12,min_periods=12).median()
    f["volume_ratio_60m"]=vol/medv.replace(0,np.nan)
    m=vol.rolling(48,min_periods=48).mean()
    sd=vol.rolling(48,min_periods=48).std(ddof=0)
    f["volume_z_240m"]=(vol-m)/sd.replace(0,np.nan)
    return f

def make_matrix(L,base):
    idx=pd.DatetimeIndex(L.decision_ts)
    b=base.reindex(idx).reset_index(drop=True)
    out=L.reset_index(drop=True).copy()
    d=np.where(out.side.eq("LONG"),1.0,-1.0)
    out["side_long"]=(d>0).astype(float)
    for name in ["5m","15m","30m","60m","120m","240m"]:
        out[f"signed_ret_{name}"]=b[f"ret_{name}"].to_numpy()*d
    out["signed_clv"]=b.clv.to_numpy()*d
    for name in ["60m","240m","24h"]:
        out[f"signed_range_pos_{name}"]=b[f"range_pos_{name}"].to_numpy()*d
    for name in ["trend_eff_60m","trend_eff_240m","realized_vol_60m","realized_vol_240m","atr14_pct","volume_ratio_60m","volume_z_240m"]:
        out[name]=b[name].to_numpy()
    for name in ["ma7_gap","ma20_gap","ma50_gap","ma20_slope_15m","rsi14"]:
        out[f"signed_{name}"]=b[name].to_numpy()*d
    minute=idx.hour*60+idx.minute
    out["hour_sin"]=np.sin(2*np.pi*minute/(24*60))
    out["hour_cos"]=np.cos(2*np.pi*minute/(24*60))
    dow=idx.dayofweek.to_numpy()
    out["dow_sin"]=np.sin(2*np.pi*dow/7)
    out["dow_cos"]=np.cos(2*np.pi*dow/7)
    out["y"]=out.outcome.eq("WIN").astype(int)
    out["realized_R"]=np.select(
        [out.outcome.eq("WIN"),out.outcome.eq("LOSS"),out.outcome.eq("AMBIGUOUS")],
        [1.0,-1.0,-1.0],
        default=np.clip(pd.to_numeric(out.timeout_signed_return,errors="coerce").fillna(0).to_numpy()/0.01,-1,1)
    )
    out["entry_ts"]=pd.to_datetime(out.decision_ts,utc=True)+BAR5
    ft=pd.to_numeric(out.first_touch_min,errors="coerce")
    hold=ft.fillna(12*60)
    out["exit_ts"]=out.entry_ts+pd.to_timedelta(hold,unit="m")
    return out

def model():
    return HistGradientBoostingClassifier(
        learning_rate=.05,max_iter=250,max_leaf_nodes=31,max_depth=6,
        min_samples_leaf=200,l2_regularization=1.0,random_state=42
    )

def fit_score(train,test):
    m=model()
    m.fit(train[FEATURES],train.y)
    return m,m.predict_proba(test[FEATURES])[:,1]

def simulate(z,prob,thr):
    q=z.copy()
    q["prob"]=prob
    q=q.sort_values(["decision_ts","side"],kind="stable")
    chosen=[]
    active_until=pd.Timestamp.min.tz_localize("UTC")
    entered_days=set()
    # at each timestamp choose best side known at that timestamp
    for ts,g in q.groupby("decision_ts",sort=True):
        day=pd.Timestamp(ts).floor("D")
        if day in entered_days: continue
        gg=g.sort_values(["prob","side"],ascending=[False,True])
        r=gg.iloc[0]
        if float(r.prob)<thr: continue
        if pd.Timestamp(r.entry_ts)<active_until: continue
        chosen.append(r)
        entered_days.add(day)
        active_until=pd.Timestamp(r.exit_ts)
    if not chosen:
        return pd.DataFrame(columns=list(q.columns))
    return pd.DataFrame(chosen).reset_index(drop=True)

def metrics(s,days,label):
    if len(s)==0:
        return {"period":label,"n":0,"days":days,"trades_per_day":0,"wr":np.nan,"mean_R":np.nan,"sum_R":0}
    return {
      "period":label,"n":len(s),"days":days,"trades_per_day":len(s)/days,
      "wr":float(s.y.mean()),"mean_R":float(s.realized_R.mean()),"sum_R":float(s.realized_R.sum()),
      "long_share":float(s.side.eq("LONG").mean()),
      "median_prob":float(s.prob.median())
    }

def main():
    verify_parent()
    if vbt.__version__!="1.1.0": raise RuntimeError(vbt.__version__)
    if sklearn.__version__!="1.9.1": raise RuntimeError(sklearn.__version__)

    L=pd.read_csv(ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Ledger.csv.gz",
                  compression="gzip",parse_dates=["decision_ts","decision_day"])
    raw,diag=s1.load_raw()
    base=feature_base(raw)
    D=make_matrix(L,base)
    D=D.dropna(subset=FEATURES).copy()
    # purge final 12h of train sets
    train23=D[(D.year<=2023)&(D.decision_ts<pd.Timestamp("2024-01-01T00:00:00Z")-pd.Timedelta(hours=12))].copy()
    cal24=D[D.year.eq(2024)].copy()
    train24=D[(D.year<=2024)&(D.decision_ts<pd.Timestamp("2025-01-01T00:00:00Z")-pd.Timedelta(hours=12))].copy()
    ref=D[D.year>=2025].copy()

    mcal,pcal=fit_score(train23,cal24)
    cal_days=cal24.decision_day.nunique()
    table=[]
    sims={}
    for th in THRESHOLDS:
        s=simulate(cal24,pcal,th); sims[th]=s
        mm=metrics(s,cal_days,"CAL2024"); mm["threshold"]=th
        mm["eligible"]=bool(mm["n"]>=250 and mm["trades_per_day"]>=.80 and mm["wr"]>=.80)
        table.append(mm)
    T=pd.DataFrame(table)
    eligible=T[T.eligible]
    cal_pass=len(eligible)>0
    if cal_pass:
        threshold=float(eligible.sort_values("threshold").iloc[0].threshold)
        selection_rule="LOWEST_CALIBRATION_ELIGIBLE"
    else:
        pool=T[T.n>=150].copy()
        if len(pool):
            row=pool.sort_values(["wr","trades_per_day","threshold"],ascending=[False,False,False]).iloc[0]
        else:
            row=T.sort_values(["n","wr"],ascending=[False,False]).iloc[0]
        threshold=float(row.threshold)
        selection_rule="DESCRIPTIVE_FALLBACK_NO_PROMOTION"

    mref,pref=fit_score(train24,ref)
    S=simulate(ref,pref,threshold)
    allm=metrics(S,ref.decision_day.nunique(),"REF")
    yearly=[]
    for y in [2025,2026]:
        sy=S[S.year.eq(y)]
        days=ref[ref.year.eq(y)].decision_day.nunique()
        yearly.append(metrics(sy,days,str(y)))
    Y=pd.DataFrame(yearly)

    ref_pass=False
    if cal_pass:
        y25=Y[Y.period=="2025"].iloc[0]; y26=Y[Y.period=="2026"].iloc[0]
        ref_pass=bool(
          allm["n"]>=400 and allm["trades_per_day"]>=.80 and allm["wr"]>=.80 and
          y25["wr"]>=.75 and y26["wr"]>=.75 and allm["mean_R"]>=.50
        )
    if not cal_pass:
        status="BNB_B42_S2_SELECTOR_CALIBRATION_NOT_READY"
    elif ref_pass:
        status="BNB_B42_S2_DAILY_1PCT_SELECTOR_VALIDATED"
    else:
        status="BNB_B42_S2_SELECTOR_REF_FAILED"

    # monthly robustness
    S["month"]=pd.to_datetime(S.decision_ts,utc=True).dt.to_period("M").astype(str)
    M=S.groupby("month").agg(n=("y","size"),wr=("y","mean"),mean_R=("realized_R","mean"),sum_R=("realized_R","sum")).reset_index()

    sig=sha256(json.dumps({
      "parent":S1_SIG,"features":FEATURES,
      "model":{"type":"HistGradientBoostingClassifier","learning_rate":.05,"max_iter":250,"max_leaf_nodes":31,
               "max_depth":6,"min_samples_leaf":200,"l2_regularization":1.0,"random_state":42},
      "threshold_grid":THRESHOLDS,"selection":"first_timestamp_ge_threshold_best_side_max1_day_one_active",
      "sklearn":"1.9.1","vectorbt":"1.1.0"
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    T.to_csv(ROOT/f"{PFX}_CalibrationThresholds.csv",index=False)
    S.to_csv(ROOT/f"{PFX}_REF_SelectedTrades.csv.gz",index=False,compression="gzip")
    Y.to_csv(ROOT/f"{PFX}_REF_ByYear.csv",index=False)
    M.to_csv(ROOT/f"{PFX}_REF_ByMonth.csv",index=False)
    pd.DataFrame([allm]).to_csv(ROOT/f"{PFX}_REF_Summary.csv",index=False)
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n")
    (ROOT/f"{PFX}_Freeze.txt").write_text(
      f"S2_SIGNATURE_SHA256={sig}\nPARENT_S1_SIGNATURE_SHA256={S1_SIG}\n"
      f"THRESHOLD={threshold}\nSELECTION_RULE={selection_rule}\n"
      f"VECTORBT_VERSION={vbt.__version__}\nSKLEARN_VERSION={sklearn.__version__}\n"
    )

    def pct(x): return "—" if pd.isna(x) else f"{100*x:.2f}%"
    lines=[
      "# BNB B42-S2 — Causal Daily 1% Fingerprint Selector Result","",
      f"**Status: {status}**","",f"Signature: `{sig}`","",
      f"Selected calibration threshold: **{threshold:.2f}** ({selection_rule})","",
      "## 2024 calibration threshold sweep","",
      "| Threshold | N | Trades/day | WR | Mean R | Eligible |",
      "|---:|---:|---:|---:|---:|---|"
    ]
    for r in T.itertuples(index=False):
        lines.append(f"| {r.threshold:.2f} | {r.n} | {r.trades_per_day:.3f} | {pct(r.wr)} | {r.mean_R:.3f} | {'YES' if r.eligible else 'NO'} |")
    lines += ["","## Untouched REF 2025-2026","",
      f"- N: **{allm['n']}**",
      f"- Trades/day: **{allm['trades_per_day']:.3f}**",
      f"- WIN rate: **{pct(allm['wr'])}**",
      f"- Mean realized R/trade: **{allm['mean_R']:.3f}R**",
      f"- Total gross R: **{allm['sum_R']:.1f}R**",
      f"- LONG share: **{pct(allm.get('long_share',np.nan))}**","",
      "| Year | N | Trades/day | WR | Mean R | Total R |",
      "|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(f"| {r.period} | {r.n} | {r.trades_per_day:.3f} | {pct(r.wr)} | {r.mean_R:.3f} | {r.sum_R:.1f} |")
    lines += ["","## Decision",f"**{status}**","",
      ("The fixed +1%/-1% causal daily selector passed calibration and untouched REF gates."
       if status.endswith("VALIDATED") else
       "The 80% / ~1 trade-per-day target is not validated under this frozen S2 selector. Do not tune REF.")
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
