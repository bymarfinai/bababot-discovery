#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S1_LOWER_TF_DEMAND_REBOUND"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")

CONFIGS={
    "D1_H1D_15M_EXEC":{"demand_freq":"1h","demand_n5":12,"exec_freq":"15min","exec_n5":3},
    "D2_15MD_5M_EXEC":{"demand_freq":"15min","demand_n5":3,"exec_freq":"5min","exec_n5":1},
}

def exact_exec(raw,freq,n5):
    if n5==1:
        b=raw[["open","high","low","close"]].copy().astype(float)
        return b
    return s1.exact_bars(raw,freq,n5)

def pivots_df(b):
    hi=b.high.to_numpy(float); lo=b.low.to_numpy(float); idx=b.index
    highs=[]; lows=[]
    for i in range(2,len(b)-2):
        if hi[i] > max(hi[i-2],hi[i-1],hi[i+1],hi[i+2]):
            highs.append({"pivot_ts":idx[i],"confirm_ts":idx[i+2],"level":float(hi[i])})
        if lo[i] < min(lo[i-2],lo[i-1],lo[i+1],lo[i+2]):
            lows.append({"pivot_ts":idx[i],"confirm_ts":idx[i+2],"level":float(lo[i])})
    return pd.DataFrame(highs),pd.DataFrame(lows)

def demand_zones(b):
    hi,_=pivots_df(b)
    cmap={}
    for r in hi.itertuples(index=False):
        cmap.setdefault(r.confirm_ts,[]).append((r.pivot_ts,float(r.level)))
    active=[]; used=set(); rows=[]; prev_close=None
    for i,(t,r) in enumerate(b.iterrows()):
        latest=active[-1] if active else None
        if latest is not None and prev_close is not None:
            pts,level=latest
            if pts not in used and prev_close<=level and float(r.close)>level:
                origin=None
                for j in range(i-1,max(-1,i-7),-1):
                    rr=b.iloc[j]
                    if float(rr.close)<float(rr.open):
                        origin=(b.index[j],rr)
                        break
                if origin is not None:
                    ots,orr=origin
                    zlo=float(orr.low); zhi=float(orr.open)
                    if zhi>zlo:
                        rows.append({
                            "zone_id":f"D_{t.isoformat()}",
                            "activation_ts":t,
                            "origin_ts":ots,
                            "broken_swing_ts":pts,
                            "broken_level":float(level),
                            "bos_close":float(r.close),
                            "demand_low":zlo,
                            "demand_high":zhi,
                        })
                        used.add(pts)
        for ev in cmap.get(t,[]):
            active.append(ev)
        prev_close=float(r.close)
    return pd.DataFrame(rows)

def visual_family(exec_b,zones):
    hp,_=pivots_df(exec_b)
    hp=hp.sort_values("confirm_ts") if len(hp) else hp
    idx=exec_b.index
    highs=exec_b.high.to_numpy(float); lows=exec_b.low.to_numpy(float)
    rows=[]
    for z in zones.itertuples(index=False):
        if z.activation_ts>END or z.activation_ts<START-pd.Timedelta(days=30):
            continue
        start_i=int(idx.searchsorted(z.activation_ts,side="right"))
        end_i=int(idx.searchsorted(END,side="right"))
        touch_i=None
        for i in range(start_i,end_i):
            if lows[i]<=z.demand_high and highs[i]>=z.demand_low:
                touch_i=i; break
        if touch_i is None:
            continue
        t=idx[touch_i]; touch=exec_b.iloc[touch_i]
        qh=hp[(hp.pivot_ts>z.activation_ts)&
              (hp.confirm_ts<t)&
              (hp.level>max(float(z.broken_level),float(z.bos_close)))]
        if qh.empty:
            continue
        er=qh.sort_values(["pivot_ts","confirm_ts"]).iloc[-1]
        p_i=int(idx.get_loc(er.pivot_ts))
        if touch_i-p_i-1<2:
            continue
        seg=exec_b.iloc[p_i+1:touch_i]
        lh=bool((seg.high.diff()<0).any()) if len(seg)>=2 else False
        ll=bool((seg.low.diff()<0).any()) if len(seg)>=2 else False
        hold=float(touch.close)>=float(z.demand_low)
        if not (hold and (lh or ll)):
            continue
        rows.append({
            "zone_id":z.zone_id,
            "activation_ts":z.activation_ts,
            "origin_ts":z.origin_ts,
            "broken_swing_ts":z.broken_swing_ts,
            "broken_level":z.broken_level,
            "bos_close":z.bos_close,
            "demand_low":z.demand_low,
            "demand_high":z.demand_high,
            "demand_width":float(z.demand_high-z.demand_low),
            "expansion_pivot_ts":er.pivot_ts,
            "expansion_confirm_ts":er.confirm_ts,
            "expansion_high":float(er.level),
            "first_touch_ts":t,
            "touch_open":float(touch.open),
            "touch_high":float(touch.high),
            "touch_low":float(touch.low),
            "touch_close":float(touch.close),
            "pullback_bars":int(len(seg)),
            "has_lower_high":lh,
            "has_lower_low":ll,
        })
    return pd.DataFrame(rows)

def outcomes(exec_b,fam):
    idx=exec_b.index
    rows=[]
    for r in fam.itertuples(index=False):
        start_i=int(idx.searchsorted(r.first_touch_ts,side="right"))
        end_i=int(idx.searchsorted(END,side="right"))
        invalid_ts=pd.NaT
        max_close=-np.inf
        R1=R2=R3=R4=False
        r1_level=float(r.touch_high)
        r2_level=float(r.demand_high+r.demand_width)
        r3_level=float(r.demand_high+2*r.demand_width)
        r4_level=float(r.expansion_high)
        for i in range(start_i,end_i):
            c=float(exec_b.close.iloc[i])
            if c<float(r.demand_low):
                invalid_ts=idx[i]
                break
            max_close=max(max_close,c)
            if c>r1_level:R1=True
            if c>r2_level:R2=True
            if c>r3_level:R3=True
            if c>r4_level:R4=True
        if max_close==-np.inf:
            max_close=np.nan
        mfe=np.nan if not np.isfinite(max_close) else (max_close-float(r.demand_high))/float(r.demand_width)
        rows.append({
            **{k:getattr(r,k) for k in fam.columns},
            "invalid_ts":invalid_ts,
            "reaction_R1":R1,
            "rebound_1zw_R2":R2,
            "rebound_2zw_R3":R3,
            "full_continuation_R4":R4,
            "max_close_before_invalid":max_close,
            "mfe_zw":mfe,
        })
    return pd.DataFrame(rows)

def summarize(name,zones,L):
    yrs=pd.to_datetime(L.first_touch_ts,utc=True).dt.year if len(L) else pd.Series(dtype=int)
    def rate(col,df=L):
        return float(df[col].mean()) if len(df) else np.nan
    fail=L[~L.full_continuation_R4].copy() if len(L) else L.copy()
    q=L.mfe_zw.dropna() if len(L) else pd.Series(dtype=float)
    fq=fail.mfe_zw.dropna() if len(fail) else pd.Series(dtype=float)
    return {
        "config":name,
        "demand_zones_activated":int(((pd.to_datetime(zones.activation_ts,utc=True)>=START)&(pd.to_datetime(zones.activation_ts,utc=True)<=END)).sum()) if len(zones) else 0,
        "visual_family":len(L),
        "y2022":int((yrs==2022).sum()) if len(L) else 0,
        "y2023":int((yrs==2023).sum()) if len(L) else 0,
        "y2024":int((yrs==2024).sum()) if len(L) else 0,
        "R1_reaction_rate":rate("reaction_R1"),
        "R2_1zw_rate":rate("rebound_1zw_R2"),
        "R3_2zw_rate":rate("rebound_2zw_R3"),
        "R4_full_cont_rate":rate("full_continuation_R4"),
        "R4_fail_n":len(fail),
        "R4_fail_R1_rate":rate("reaction_R1",fail),
        "R4_fail_R2_rate":rate("rebound_1zw_R2",fail),
        "R4_fail_R3_rate":rate("rebound_2zw_R3",fail),
        "mfe_zw_median":float(q.median()) if len(q) else np.nan,
        "mfe_zw_p25":float(q.quantile(.25)) if len(q) else np.nan,
        "mfe_zw_p75":float(q.quantile(.75)) if len(q) else np.nan,
        "R4_fail_mfe_zw_median":float(fq.median()) if len(fq) else np.nan,
        "R4_fail_mfe_zw_p25":float(fq.quantile(.25)) if len(fq) else np.nan,
        "R4_fail_mfe_zw_p75":float(fq.quantile(.75)) if len(fq) else np.nan,
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    summaries=[]
    for name,cfg in CONFIGS.items():
        db=exact_exec(raw,cfg["demand_freq"],cfg["demand_n5"])
        eb=exact_exec(raw,cfg["exec_freq"],cfg["exec_n5"])
        db=db[db.index<=END].copy()
        eb=eb[eb.index<=END].copy()
        zones=demand_zones(db)
        fam=visual_family(eb,zones)
        if len(fam):
            fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&(pd.to_datetime(fam.first_touch_ts,utc=True)<=END)].copy()
        L=outcomes(eb,fam)
        L.insert(0,"config",name)
        L.to_csv(ROOT/f"{PFX}_{name}_Ledger.csv.gz",index=False,compression="gzip")
        summaries.append(summarize(name,zones,L))

    S=pd.DataFrame(summaries)
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x):
        return "—" if not np.isfinite(x) else f"{x:.2f}"

    lines=[
      "# BNB B38-S1 — Lower-TF Demand Structural Rebound Study","",
      "**EXPLORATORY 2022-2024 — NOT AN OOS CLAIM**","",
      "Two 4:1 timeframe structures were tested: H1-demand/15m-execution and 15m-demand/5m-execution.","",
      "## Frequency and rebound decomposition","",
      "| Config | Demand zones | Visual family | 2022 | 2023 | 2024 | R1 reaction | R2 +1ZW | R3 +2ZW | R4 full continuation |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.config} | {r.demand_zones_activated} | {r.visual_family} | {r.y2022} | {r.y2023} | {r.y2024} | {pct(r.R1_reaction_rate)} | {pct(r.R2_1zw_rate)} | {pct(r.R3_2zw_rate)} | {pct(r.R4_full_cont_rate)} |")

    lines += ["","## What happens inside FULL_CONTINUATION failures?","",
      "| Config | R4 fail N | Still reacts above retest high | Still reaches +1ZW | Still reaches +2ZW | Fail MFE median | Fail MFE IQR |",
      "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.config} | {r.R4_fail_n} | {pct(r.R4_fail_R1_rate)} | {pct(r.R4_fail_R2_rate)} | {pct(r.R4_fail_R3_rate)} | {num(r.R4_fail_mfe_zw_median)}ZW | {num(r.R4_fail_mfe_zw_p25)}–{num(r.R4_fail_mfe_zw_p75)}ZW |")

    lines += ["","## Overall MFE","",
      "| Config | Median MFE | IQR |",
      "|---|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.config} | {num(r.mfe_zw_median)}ZW | {num(r.mfe_zw_p25)}–{num(r.mfe_zw_p75)}ZW |")

    lines += ["","## Interpretation rule",
      "R4 is the old-style strict structural continuation concept. R1-R3 and MFE_ZW reveal whether an R4 failure still produced a meaningful rebound before demand invalidation.",
      "No TP/SL optimization or detector selection is performed in B38-S1."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S1_LOWER_TF_REBOUND_STUDY_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
