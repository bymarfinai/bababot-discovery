#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s1_causal_structural_wall_discovery as s1
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER"
S1_SIG="4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6"
S2_SIG="53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2"
CHARS=[
    "C1_CLEAN_REJECTION",
    "C2_RECLAIM_AFTER_CLOSE",
    "C3_ACCEPTANCE_HOLD",
    "C4_UNSETTLED_BREAK",
]

def verify_parents():
    f1=(ROOT/"results"/"bnb_b41_s1"/"BNB_B41_S1_CAUSAL_STRUCTURAL_WALL_DISCOVERY_Freeze.txt").read_text(encoding="utf-8")
    f2=(ROOT/"results"/"bnb_b41_s2"/"BNB_B41_S2_WALL_IMPORTANCE_AUDIT_Freeze.txt").read_text(encoding="utf-8")
    if f"WALL_SIGNATURE_SHA256={S1_SIG}" not in f1:
        raise RuntimeError("S1 signature mismatch")
    if f"S2_SIGNATURE_SHA256={S2_SIG}" not in f2:
        raise RuntimeError("S2 signature mismatch")

def classify(states):
    a,b,c=[bool(x) for x in states]
    if not (a or b or c):
        return "C1_CLEAN_REJECTION"
    if not c:
        return "C2_RECLAIM_AFTER_CLOSE"
    if b and c:
        return "C3_ACCEPTANCE_HOLD"
    return "C4_UNSETTLED_BREAK"

def signed_close_norm(side, level, wd, close):
    return (level-close)/wd if side=="UPPER" else (close-level)/wd

def build_event(raw5, row, wm_row):
    day=pd.Timestamp(row.session_day)
    touch=pd.Timestamp(row.first_touch_ts)
    side=str(row.side)
    level=float(row.level)
    op=float(row.session_open)
    wd=abs(level-op)
    if wd<=0:
        raise RuntimeError("nonpositive wall distance")

    daybars=raw5[(raw5.session_day==day)].copy()
    if touch not in daybars.index:
        raise RuntimeError(f"touch timestamp missing {touch}")

    i=daybars.index.get_loc(touch)
    if isinstance(i,slice) or not isinstance(i,(int,np.integer)):
        raise RuntimeError("nonunique touch index")

    if i+2>=len(daybars):
        return {
            "eligible_character":False,
            "detector_ts":pd.NaT,
            "character":"INSUFFICIENT_WINDOW",
        }

    obs=daybars.iloc[i:i+3]
    closes=obs.close.to_numpy(dtype=float)
    if side=="UPPER":
        states=closes>level
        penetration=max(0.0,float(obs.high.max())-level)/wd
        inward_obs=max(0.0,level-float(obs.low.min()))/wd
    else:
        states=closes<level
        penetration=max(0.0,level-float(obs.low.min()))/wd
        inward_obs=max(0.0,float(obs.high.max())-level)/wd

    char=classify(states)
    det_ts=obs.index[-1]
    after=daybars[daybars.index>det_ts]

    if len(after):
        if side=="UPPER":
            max_in=max(0.0,level-float(after.low.min()))/wd
            max_out=max(0.0,float(after.high.max())-level)/wd
            eq=bool(float(after.low.min())<=op)
            extreme=float(wm_row.upper_extreme)
            ext=bool(float(after.high.max())>=extreme)
        else:
            max_in=max(0.0,float(after.high.max())-level)/wd
            max_out=max(0.0,level-float(after.low.min()))/wd
            eq=bool(float(after.high.max())>=op)
            extreme=float(wm_row.lower_extreme)
            ext=bool(float(after.low.min())<=extreme)
        close_inside=bool(float(daybars.close.iloc[-1])<=level) if side=="UPPER" else bool(float(daybars.close.iloc[-1])>=level)
    else:
        max_in=max_out=np.nan
        eq=ext=close_inside=False

    c60=np.nan
    c180=np.nan
    t60=det_ts+pd.Timedelta(minutes=60)
    t180=det_ts+pd.Timedelta(minutes=180)
    if t60 in daybars.index:
        c60=signed_close_norm(side,level,wd,float(daybars.loc[t60,"close"]))
    if t180 in daybars.index:
        c180=signed_close_norm(side,level,wd,float(daybars.loc[t180,"close"]))

    return {
        "eligible_character":True,
        "detector_ts":det_ts,
        "character":char,
        "state_code":"".join("1" if x else "0" for x in states),
        "outside_close_count":int(states.sum()),
        "penetration_obs_norm":float(penetration),
        "inward_obs_norm":float(inward_obs),
        "signed_close_60m_norm":float(c60) if np.isfinite(c60) else np.nan,
        "signed_close_180m_norm":float(c180) if np.isfinite(c180) else np.nan,
        "max_inward_post_norm":float(max_in) if np.isfinite(max_in) else np.nan,
        "max_outward_post_norm":float(max_out) if np.isfinite(max_out) else np.nan,
        "inward_dominance":bool(np.isfinite(max_in) and np.isfinite(max_out) and max_in>max_out),
        "equilibrium_reached_post":eq,
        "extreme_reached_post":ext,
        "session_close_inside":close_inside,
    }

def summarize(E):
    rows=[]
    for period in ["DEV","REF","ALL"]:
        q=E if period=="ALL" else E[E.period==period]
        for side in ["UPPER","LOWER"]:
            base=q[(q.side==side)&(q.eligible_character)]
            for char in CHARS:
                z=base[base.character==char]
                rows.append({
                    "period":period,"side":side,"character":char,
                    "n":int(len(z)),
                    "share":float(len(z)/len(base)) if len(base) else np.nan,
                    "median_penetration_obs":float(z.penetration_obs_norm.median()) if len(z) else np.nan,
                    "median_inward_obs":float(z.inward_obs_norm.median()) if len(z) else np.nan,
                    "n60":int(z.signed_close_60m_norm.notna().sum()),
                    "median_signed60":float(z.signed_close_60m_norm.median()) if z.signed_close_60m_norm.notna().any() else np.nan,
                    "n180":int(z.signed_close_180m_norm.notna().sum()),
                    "median_signed180":float(z.signed_close_180m_norm.median()) if z.signed_close_180m_norm.notna().any() else np.nan,
                    "median_max_inward_post":float(z.max_inward_post_norm.median()) if len(z) else np.nan,
                    "median_max_outward_post":float(z.max_outward_post_norm.median()) if len(z) else np.nan,
                    "inward_dominance_rate":float(z.inward_dominance.mean()) if len(z) else np.nan,
                    "equilibrium_rate":float(z.equilibrium_reached_post.mean()) if len(z) else np.nan,
                    "extreme_rate":float(z.extreme_reached_post.mean()) if len(z) else np.nan,
                    "close_inside_rate":float(z.session_close_inside.mean()) if len(z) else np.nan,
                })
    return pd.DataFrame(rows)

def stability(S):
    rows=[]
    for side in ["UPPER","LOWER"]:
        for char in CHARS:
            d=S[(S.period=="DEV")&(S.side==side)&(S.character==char)].iloc[0]
            r=S[(S.period=="REF")&(S.side==side)&(S.character==char)].iloc[0]
            if d.n180<20 or r.n180<20:
                label="INSUFFICIENT"
            elif d.median_signed180>0 and r.median_signed180>0:
                label="STABLE_INWARD"
            elif d.median_signed180<0 and r.median_signed180<0:
                label="STABLE_OUTWARD"
            else:
                label="MIXED"
            rows.append({
                "side":side,"character":char,
                "dev_n":int(d.n),"ref_n":int(r.n),
                "dev_n180":int(d.n180),"ref_n180":int(r.n180),
                "dev_med180":d.median_signed180,"ref_med180":r.median_signed180,
                "dev_inward_dom":d.inward_dominance_rate,"ref_inward_dom":r.inward_dominance_rate,
                "dev_eq":d.equilibrium_rate,"ref_eq":r.equilibrium_rate,
                "dev_extreme":d.extreme_rate,"ref_extreme":r.extreme_rate,
                "stability_label":label,
            })
    return pd.DataFrame(rows)

def main():
    verify_parents()

    s2ledger=ROOT/"results"/"bnb_b41_s2"/"BNB_B41_S2_WALL_IMPORTANCE_AUDIT_EventLedger.csv.gz"
    P=pd.read_csv(s2ledger,compression="gzip",parse_dates=["session_day","first_touch_ts"])
    P=P[(P.family=="WALL")&(P.touched)].copy()

    expected={("DEV","UPPER"):233,("DEV","LOWER"):241,("REF","UPPER"):126,("REF","LOWER"):112}
    for k,n in expected.items():
        got=len(P[(P.period==k[0])&(P.side==k[1])])
        if got!=n:
            raise RuntimeError(f"S2 touch parity drift {k}: {got} != {n}")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(diag)
    xb=s2.session_bars(raw)

    d=s1.build_daily(raw)
    wm=s1.wall_map(d)
    wm=wm[(wm.index>=s1.START)&(wm.index<=s1.END_DAY)&(wm.hist_n==s1.LOOKBACK)].copy()

    rows=[]
    for r in P.itertuples(index=False):
        day=pd.Timestamp(r.session_day)
        a=build_event(xb,r,wm.loc[day])
        rows.append({
            "session_day":day,
            "year":int(r.year),
            "period":str(r.period),
            "side":str(r.side),
            "level":float(r.level),
            "session_open":float(r.session_open),
            "first_touch_ts":pd.Timestamp(r.first_touch_ts),
            **a
        })
    E=pd.DataFrame(rows)

    eligible=E[E.eligible_character]
    if len(eligible):
        bad=eligible.groupby(["period","side"]).size()
    else:
        bad=pd.Series(dtype=int)

    # Character taxonomy must be exhaustive.
    if not set(eligible.character.unique()).issubset(set(CHARS)):
        raise RuntimeError("unknown character")
    if len(eligible)!=sum((eligible.character==c).sum() for c in CHARS):
        raise RuntimeError("character taxonomy is not exhaustive")

    S=summarize(E)
    ST=stability(S)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=eligible[eligible.year==y]
        for side in ["UPPER","LOWER"]:
            base=q[q.side==side]
            for char in CHARS:
                z=base[base.character==char]
                Y.append({
                    "year":y,"side":side,"character":char,"n":len(z),
                    "share":len(z)/len(base) if len(base) else np.nan,
                    "median_signed180":float(z.signed_close_180m_norm.median()) if z.signed_close_180m_norm.notna().any() else np.nan,
                    "inward_dominance_rate":float(z.inward_dominance.mean()) if len(z) else np.nan,
                    "equilibrium_rate":float(z.equilibrium_reached_post.mean()) if len(z) else np.nan,
                    "extreme_rate":float(z.extreme_reached_post.mean()) if len(z) else np.nan,
                })
    Y=pd.DataFrame(Y)

    sig=hashlib.sha256(json.dumps({
        "parent_s1":S1_SIG,
        "parent_s2":S2_SIG,
        "wall":"Q80",
        "observation":"FIRST_TOUCH_BAR_PLUS_NEXT_2_5M_BARS",
        "outside":"CLOSE_BEYOND_WALL",
        "taxonomy":{
            "C1":"000",
            "C2":"ANY_OUTSIDE_THEN_FINAL_INSIDE",
            "C3":"FINAL_TWO_OUTSIDE",
            "C4":"FINAL_OUTSIDE_NOT_C3",
        },
        "outcomes_start":"STRICTLY_AFTER_THIRD_BAR_CLOSE",
        "horizons_min":[60,180],
        "threshold_search":False,
        "trade_metrics":False,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    ST.to_csv(ROOT/f"{PFX}_Stability.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)

    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S1_SIGNATURE_SHA256={S1_SIG}\n"
        f"PARENT_S2_SIGNATURE_SHA256={S2_SIG}\n"
        f"S3_SIGNATURE_SHA256={sig}\n"
        "WALL=Q80_ONLY\n"
        "OBSERVATION_WINDOW=FIRST_TOUCH_PLUS_2_NEXT_5M_BARS\n"
        "OUTCOME_START=STRICTLY_AFTER_DETECTOR_CLOSE\n"
        "CHARACTERS=C1_CLEAN_REJECTION,C2_RECLAIM_AFTER_CLOSE,C3_ACCEPTANCE_HOLD,C4_UNSETTLED_BREAK\n"
        "NO_THRESHOLD_SEARCH=TRUE\nNO_TRADE_METRICS=TRUE\n",
        encoding="utf-8"
    )
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER_COMPLETE\n",encoding="utf-8")

    def pct(x):
        return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x):
        return "—" if not np.isfinite(x) else f"{x:.3f}x"

    insuff=int((~E.eligible_character).sum())
    lines=[
        "# BNB B41-S3 — Q80 Wall Interaction Character Discovery","",
        "**Status: BNB_B41_S3_Q80_WALL_INTERACTION_CHARACTER_COMPLETE**","",
        f"S3 signature: `{sig}`","",
        f"Q80 first-touch events inherited from S2: **{len(E)}**; eligible 15m character windows: **{len(eligible)}**; insufficient: **{insuff}**.","",
        "Positive signed displacement means movement inward from the wall after the character is already known.","",
        "## Character census and post-character path","",
        "| Period | Side | Character | N | Share | Obs penetration | 60m signed | 180m signed | Max inward | Max outward | Inward dom | EQ hit | Extreme hit | Close inside |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.side} | {r.character} | {r.n} | {pct(r.share)} | "
            f"{num(r.median_penetration_obs)} | {num(r.median_signed60)} | {num(r.median_signed180)} | "
            f"{num(r.median_max_inward_post)} | {num(r.median_max_outward_post)} | {pct(r.inward_dominance_rate)} | "
            f"{pct(r.equilibrium_rate)} | {pct(r.extreme_rate)} | {pct(r.close_inside_rate)} |"
        )

    lines += ["","## DEV/REF stability at 180 minutes","",
        "| Side | Character | DEV N180 | REF N180 | DEV med180 | REF med180 | DEV inward-dom | REF inward-dom | DEV EQ | REF EQ | DEV extreme | REF extreme | Label |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in ST.itertuples(index=False):
        lines.append(
            f"| {r.side} | {r.character} | {r.dev_n180} | {r.ref_n180} | {num(r.dev_med180)} | {num(r.ref_med180)} | "
            f"{pct(r.dev_inward_dom)} | {pct(r.ref_inward_dom)} | {pct(r.dev_eq)} | {pct(r.ref_eq)} | "
            f"{pct(r.dev_extreme)} | {pct(r.ref_extreme)} | {r.stability_label} |"
        )

    lines += ["","## Interpretation boundary",
        "S3 discovers causal interaction character only; it does not promote an entry.",
        "Stable inward/outward labels indicate direction of post-character price behavior, not trade profitability.",
        "B41-S4 may convert only robust S3 character evidence into LONG / SHORT / NO-TRADE direction logic while keeping wall formation and the 15m character window frozen."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
