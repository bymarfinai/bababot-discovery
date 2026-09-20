#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b37_s1_h4_demand_h1_twin as s1

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S1B_VISUAL_EQUIVALENT"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")

def first_touch(b1,z):
    q=b1[(b1.index>z.activation_ts)&(b1.index<=END)]
    for t,r in q.iterrows():
        if s1.overlap(r,z.demand_low,z.demand_high):
            return t,r
    return None,None

def classify(b1,zones):
    highs=s1.confirmed_h1_highs(b1)
    strict_checks,strict=s1.scan_twins(b1,zones)
    strict_keys=set()
    if len(strict):
        for r in strict.itertuples(index=False):
            strict_keys.add((str(r.zone_id),pd.Timestamp(r.first_touch_ts)))

    rows=[]
    for z in zones.itertuples(index=False):
        if not (START<=z.activation_ts<=END):
            continue
        touch_ts,touch=first_touch(b1,z)
        got_touch=touch_ts is not None
        hold=False; exp=False; pull2=False; lh=False; ll=False
        visual=False; exp_row=None
        if got_touch:
            hold=float(touch.close)>=float(z.demand_low)
            qh=highs[(highs.pivot_ts>z.activation_ts)&
                     (highs.confirm_ts<touch_ts)&
                     (highs.pivot_high>max(float(z.broken_h4_level),float(z.h4_bos_close)))]
            if not qh.empty:
                # last confirmed expansion high before the corrective return
                exp_row=qh.sort_values(["pivot_ts","confirm_ts"]).iloc[-1]
                exp=True
                seg=b1[(b1.index>exp_row.pivot_ts)&(b1.index<touch_ts)]
                pull2=len(seg)>=2
                if len(seg)>=2:
                    lh=bool((seg.high.diff()<0).any())
                    ll=bool((seg.low.diff()<0).any())
                visual=bool(hold and pull2 and (lh or ll))
        key=(str(z.zone_id),pd.Timestamp(touch_ts) if got_touch else pd.NaT)
        is_strict=bool(got_touch and key in strict_keys)
        rows.append({
            "zone_id":z.zone_id,
            "activation_ts":z.activation_ts,
            "origin_ts":z.origin_ts,
            "h4_bos_ts":z.h4_bos_ts,
            "broken_h4_swing_ts":z.broken_h4_swing_ts,
            "broken_h4_level":z.broken_h4_level,
            "h4_bos_close":z.h4_bos_close,
            "demand_low":z.demand_low,
            "demand_high":z.demand_high,
            "first_touch_ts":pd.NaT if not got_touch else touch_ts,
            "touch_open":np.nan if not got_touch else float(touch.open),
            "touch_high":np.nan if not got_touch else float(touch.high),
            "touch_low":np.nan if not got_touch else float(touch.low),
            "touch_close":np.nan if not got_touch else float(touch.close),
            "retest_exists":got_touch,
            "retest_close_holds":hold,
            "expansion_high_exists":exp,
            "expansion_pivot_ts":pd.NaT if exp_row is None else exp_row.pivot_ts,
            "expansion_confirm_ts":pd.NaT if exp_row is None else exp_row.confirm_ts,
            "expansion_high":np.nan if exp_row is None else float(exp_row.pivot_high),
            "pullback_ge2_h1_bars":pull2,
            "has_lower_high":lh,
            "has_lower_low":ll,
            "has_any_correction":bool(lh or ll),
            "visual_equivalent":visual,
            "strict_exact":is_strict,
            "family":"STRICT_EXACT" if is_strict else ("VISUAL_ONLY" if visual else "OTHER"),
        })
    return pd.DataFrame(rows),strict

def funnel(df):
    stages=[
        ("H4 demand zones activated 2022-2024",pd.Series(True,index=df.index)),
        ("+ first H1 retest",df.retest_exists),
        ("+ retest close holds H4 demand",df.retest_exists & df.retest_close_holds),
        ("+ confirmed H1 expansion/new high",df.retest_exists & df.retest_close_holds & df.expansion_high_exists),
        ("+ >=2 H1 pullback bars",df.retest_exists & df.retest_close_holds & df.expansion_high_exists & df.pullback_ge2_h1_bars),
        ("VISUAL_EQUIVALENT",df.visual_equivalent),
        ("STRICT_EXACT",df.strict_exact),
    ]
    out=[]
    base=len(df)
    prev=None
    for name,mask in stages:
        n=int(mask.sum())
        out.append({"stage":name,"n":n,"share_of_h4_zones":n/base if base else np.nan,
                    "retained_from_previous":np.nan if prev is None or prev==0 else n/prev})
        prev=n
    return pd.DataFrame(out)

def draw_visual_only(b1,r,path):
    # reuse S1 renderer shape by constructing a compatible row-like object
    class R: pass
    x=R()
    for c in ["origin_ts","first_touch_ts","demand_low","demand_high"]:
        setattr(x,c,getattr(r,c))
    x.h1_bos_ts=pd.NaT
    x.new_high_pivot_ts=r.expansion_pivot_ts
    s1.draw_one(b1,x,path)

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    b1=s1.exact_bars(raw,"1h",12)
    b4=s1.exact_bars(raw,"4h",48)
    zones=s1.h4_demand_zones(b4)
    df,strict=s1b_classify_wrapper(b1,zones)
    f=funnel(df)

    visual=df[df.visual_equivalent].copy()
    vonly=df[(df.visual_equivalent)&(~df.strict_exact)].copy()

    df.to_csv(ROOT/f"{PFX}_AllClassified.csv.gz",index=False,compression="gzip")
    visual.to_csv(ROOT/f"{PFX}_VisualFamily.csv",index=False)
    vonly.to_csv(ROOT/f"{PFX}_VisualOnly.csv",index=False)
    f.to_csv(ROOT/f"{PFX}_Funnel.csv",index=False)

    charts=[]
    if len(vonly):
        take=np.unique(np.linspace(0,len(vonly)-1,min(6,len(vonly)),dtype=int))
        for k,ix in enumerate(take,1):
            r=vonly.iloc[int(ix)]
            fn=f"{PFX}_VisualOnly_{k}_{pd.Timestamp(r.first_touch_ts).strftime('%Y%m%d_%H%M')}.png"
            draw_visual_only(b1,r,ROOT/fn)
            charts.append((k,fn,r.first_touch_ts))

    yrs={}
    for y in [2022,2023,2024]:
        q=visual[pd.to_datetime(visual.first_touch_ts,utc=True).dt.year==y] if len(visual) else visual
        qs=df[(df.strict_exact)&(pd.to_datetime(df.first_touch_ts,utc=True).dt.year==y)] if len(df) else df
        yrs[y]=(len(q),len(qs))

    L=["# BNB B37-S1B — Visual-Equivalent Structural Family Result","",
       "**STEP 1 ONLY — STRUCTURE, NOT OUTCOME**","",
       "No forward return, WR, TP/SL, PnL, timing filter, indicator, derivative, or regime signal was opened.","",
       "## Integrity",
       f"- Raw rows **{diag['rows']:,}**, coverage **{diag['coverage']:.6%}**.",
       f"- A1 ret15 diff **{ident['max_ret15_diff']:.12g}**; close-location diff **{ident['max_close_location_diff']:.12g}**.",
       f"- Exact H1 bars **{len(b1):,}**; exact H4 bars **{len(b4):,}**.","",
       "## Family definitions",
       "- **STRICT_EXACT** = frozen B37-S1 machine sequence.",
       "- **VISUAL_EQUIVALENT** = same H4 structural demand and first retest, with confirmed H1 expansion/new high and a visible corrective path, but H1 formal BOS and simultaneous LH+LL are not both mandatory.","",
       "## Structural funnel","",
       "| Stage | N | Share of H4 zones | Retained from prior |",
       "|---|---:|---:|---:|"]
    for r in f.itertuples(index=False):
        share="—" if pd.isna(r.share_of_h4_zones) else f"{100*r.share_of_h4_zones:.1f}%"
        ret="—" if pd.isna(r.retained_from_previous) else f"{100*r.retained_from_previous:.1f}%"
        L.append(f"| {r.stage} | {r.n} | {share} | {ret} |")

    L += ["",
          "## Result",
          f"- Strict exact: **{int(df.strict_exact.sum()):,}**.",
          f"- Visual-equivalent total: **{len(visual):,}**.",
          f"- Visual-only additions beyond strict: **{len(vonly):,}**.",
          f"- Expansion vs strict: **{(len(visual)/max(1,int(df.strict_exact.sum()))):.2f}x**.","",
          "### By first-retest year","",
          "| Year | Visual-equivalent | Strict exact |",
          "|---:|---:|---:|"]
    for y in [2022,2023,2024]:
        L.append(f"| {y} | {yrs[y][0]} | {yrs[y][1]} |")

    if charts:
        L += ["","## Saved visual-only examples"]
        for k,fn,ts in charts:L.append(f"- {k}. `{fn}` — first retest {ts}")

    L += ["","## Step-1B verdict",
          "**VISUAL FAMILY MAPPED.**",
          "This result explains whether the original 147 count came from machine-formal strictness rather than the higher-timeframe structural idea itself.",
          "Stop here. No winner/loser or trade outcome was evaluated."]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(L)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B37_S1B_VISUAL_FAMILY_MAPPED\n",encoding="utf-8")
    print("\n".join(L),flush=True)

# isolated wrapper to keep the scientific classifier callable and explicit
def s1b_classify_wrapper(b1,zones):
    return classify(b1,zones)

if __name__=="__main__":
    main()
