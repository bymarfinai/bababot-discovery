#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S1_CAUSAL_STRUCTURAL_WALL_DISCOVERY"

START=pd.Timestamp("2022-01-01T00:00:00Z")
END_DAY=pd.Timestamp("2026-08-26T00:00:00Z")
LOOKBACK=60
RV_LOOKBACK=20
QS=(0.50,0.80,0.95)
YEARS=[2022,2023,2024,2025,2026]

def build_daily(raw: pd.DataFrame) -> pd.DataFrame:
    x=raw.copy()
    # b31 timestamps are 5m bar-close timestamps; assign bars by interval start.
    x["session_day"]=(x.index-pd.Timedelta(minutes=5)).floor("D")
    g=x.groupby("session_day",sort=True)
    d=pd.DataFrame({
        "open":g.open.first(),
        "high":g.high.max(),
        "low":g.low.min(),
        "close":g.close.last(),
        "bars":g.close.size(),
    })
    d["up_exc"]=d.high/d.open-1.0
    d["dn_exc"]=1.0-d.low/d.open
    d["log_ret"]=np.log(d.close/d.close.shift(1))
    return d

def qhist(s: pd.Series, q: float) -> pd.Series:
    # shift first is the causal boundary: current session can never enter its wall.
    return s.shift(1).rolling(LOOKBACK,min_periods=LOOKBACK).quantile(q)

def wall_map(d: pd.DataFrame) -> pd.DataFrame:
    m=pd.DataFrame(index=d.index)
    m["session_open"]=d.open
    m["hist_n"]=d.up_exc.shift(1).rolling(LOOKBACK,min_periods=LOOKBACK).count()

    for q,label in [(0.50,"50"),(0.80,"80"),(0.95,"95")]:
        m[f"up_q{label}"]=qhist(d.up_exc,q)
        m[f"dn_q{label}"]=qhist(d.dn_exc,q)

    sigma20=d.log_ret.shift(1).rolling(RV_LOOKBACK,min_periods=RV_LOOKBACK).std(ddof=1)
    m["rv_sigma20"]=sigma20

    m["equilibrium"]=m.session_open
    m["upper_mid"]=m.session_open*(1.0+m.up_q50)
    m["upper_wall"]=m.session_open*(1.0+m.up_q80)
    m["upper_extreme"]=m.session_open*(1.0+m.up_q95)
    m["lower_mid"]=m.session_open*(1.0-m.dn_q50)
    m["lower_wall"]=m.session_open*(1.0-m.dn_q80)
    m["lower_extreme"]=m.session_open*(1.0-m.dn_q95)
    m["rv1_upper"]=m.session_open*np.exp(m.rv_sigma20)
    m["rv1_lower"]=m.session_open*np.exp(-m.rv_sigma20)

    for c in ["upper_mid","upper_wall","upper_extreme","lower_mid","lower_wall","lower_extreme","rv1_upper","rv1_lower"]:
        m[c+"_dist_pct"]=(m[c]/m.session_open-1.0)*100.0

    m["up_down_wall_ratio"]=(
        (m.upper_wall/m.session_open-1.0) /
        (1.0-m.lower_wall/m.session_open).replace(0,np.nan)
    )
    return m

def summarize(m: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]
    for period,mask in [
        ("DEV",m.index.year<=2024),
        ("REF",m.index.year>=2025),
        ("ALL",np.ones(len(m),dtype=bool)),
    ]:
        z=m.loc[mask]
        rows.append({
            "period":period,
            "n":len(z),
            "upper_mid_med_pct":float(z.upper_mid_dist_pct.median()),
            "upper_wall_med_pct":float(z.upper_wall_dist_pct.median()),
            "upper_extreme_med_pct":float(z.upper_extreme_dist_pct.median()),
            "lower_mid_med_abs_pct":float((-z.lower_mid_dist_pct).median()),
            "lower_wall_med_abs_pct":float((-z.lower_wall_dist_pct).median()),
            "lower_extreme_med_abs_pct":float((-z.lower_extreme_dist_pct).median()),
            "rv1_med_pct":float(z.rv1_upper_dist_pct.median()),
            "wall_asymmetry_ratio_median":float(z.up_down_wall_ratio.median()),
            "wall_asymmetry_ratio_q10":float(z.up_down_wall_ratio.quantile(.10)),
            "wall_asymmetry_ratio_q90":float(z.up_down_wall_ratio.quantile(.90)),
        })
    by_period=pd.DataFrame(rows)

    yr=[]
    for y in YEARS:
        z=m[m.index.year==y]
        yr.append({
            "year":y,"n":len(z),
            "upper_wall_med_pct":float(z.upper_wall_dist_pct.median()),
            "lower_wall_med_abs_pct":float((-z.lower_wall_dist_pct).median()),
            "upper_extreme_med_pct":float(z.upper_extreme_dist_pct.median()),
            "lower_extreme_med_abs_pct":float((-z.lower_extreme_dist_pct).median()),
            "rv1_med_pct":float(z.rv1_upper_dist_pct.median()),
            "asymmetry_median":float(z.up_down_wall_ratio.median()),
        })
    return by_period,pd.DataFrame(yr)

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:
        raise RuntimeError(f"raw coverage too low: {diag}")

    d=build_daily(raw)
    m=wall_map(d)
    m=m[(m.index>=START)&(m.index<=END_DAY)&(m.hist_n==LOOKBACK)].copy()

    empirical_cols=[
        "equilibrium","upper_mid","upper_wall","upper_extreme",
        "lower_mid","lower_wall","lower_extreme"
    ]
    finite=bool(np.isfinite(m[empirical_cols].to_numpy(dtype=float)).all())
    ordering=(
        (m.lower_extreme<=m.lower_wall)&
        (m.lower_wall<=m.lower_mid)&
        (m.lower_mid<m.equilibrium)&
        (m.equilibrium<m.upper_mid)&
        (m.upper_mid<=m.upper_wall)&
        (m.upper_wall<=m.upper_extreme)
    )
    ordering_rate=float(ordering.mean()) if len(m) else 0.0

    year_counts={y:int((m.index.year==y).sum()) for y in YEARS}
    all_years_ge100=all(year_counts[y]>=100 for y in YEARS)
    expected_days=int((END_DAY-START)/pd.Timedelta(days=1))+1
    eligible_rate=len(m)/expected_days

    signature=hashlib.sha256(json.dumps({
        "instrument":"BNBUSDT",
        "session":"UTC_DAY",
        "source":"BINANCE_FUTURES_5M",
        "research_start":str(START),
        "research_end_day":str(END_DAY),
        "empirical_lookback_sessions":LOOKBACK,
        "upside_excursion":"HIGH/OPEN-1",
        "downside_excursion":"1-LOW/OPEN",
        "quantiles":QS,
        "rv_lookback_sessions":RV_LOOKBACK,
        "rv_definition":"STD_DAILY_LOG_RETURN",
        "causal_shift_sessions":1,
        "outcome_metrics_in_s1":False,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    ready=bool(len(m)==expected_days and finite and ordering_rate==1.0 and all_years_ge100)
    status="BNB_B41_S1_WALL_LIBRARY_READY" if ready else "BNB_B41_S1_WALL_LIBRARY_NOT_READY"

    per,yr=summarize(m)

    out=m.reset_index().rename(columns={"session_day":"session_day"})
    out["year"]=out.session_day.dt.year
    out["period"]=np.where(out.year<=2024,"DEV","REF")

    out.to_csv(ROOT/f"{PFX}_WallMap.csv.gz",index=False,compression="gzip")
    per.to_csv(ROOT/f"{PFX}_ByPeriod.csv",index=False)
    yr.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)

    freeze=[
        f"WALL_SIGNATURE_SHA256={signature}",
        "INSTRUMENT=BNBUSDT",
        "SESSION=UTC_DAY",
        "PRIMARY_FAMILY=EMPIRICAL_60_SESSION_EXCURSION",
        "QUANTILES=Q50,Q80,Q95",
        "UPSIDE_AND_DOWNSIDE=ASYMMETRIC",
        "EQUILIBRIUM=CURRENT_SESSION_OPEN",
        "SECONDARY_REFERENCE=RV20_1SIGMA",
        "CURRENT_SESSION_OUTCOMES_USED_IN_FORMATION=FALSE",
        "S1_TOUCH_HOD_LOD_MFE_MAE_TRADE_METRICS=PROHIBITED",
    ]
    (ROOT/f"{PFX}_Freeze.txt").write_text("\n".join(freeze)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Integrity.txt").write_text(
        json.dumps({
            "status":status,
            "raw":{k:str(v) for k,v in diag.items()},
            "expected_research_sessions":expected_days,
            "eligible_sessions":len(m),
            "eligible_rate":eligible_rate,
            "finite_empirical":finite,
            "ordering_rate":ordering_rate,
            "year_counts":year_counts,
            "signature":signature,
        },indent=2)+"\n",encoding="utf-8"
    )

    lines=[
        "# BNB B41-S1 — Causal Structural Wall Discovery","",
        f"**Status: {status}**","",
        f"Wall signature: `{signature}`","",
        "S1 constructs the wall library only. It intentionally does not inspect wall touches, future HOD/LOD, reversal/breakout outcomes, MFE/MAE, entries, TP, SL, WR, PF, or expectancy.","",
        "## Integrity","",
        f"- Raw coverage: **{diag['coverage']:.6%}** ({diag['rows']:,} 5m bars).",
        f"- Eligible UTC sessions: **{len(m):,}/{expected_days:,} ({eligible_rate:.2%})**.",
        f"- Empirical wall values finite: **{finite}**.",
        f"- Strict wall ordering valid: **{ordering_rate:.2%}**.",
        f"- Per-year eligible sessions: **{year_counts}**.","",
        "## Frozen wall geometry","",
        "- EQUILIBRIUM = current UTC session open.",
        "- MID = trailing 60-session Q50 excursion.",
        "- WALL = trailing 60-session Q80 excursion.",
        "- EXTREME = trailing 60-session Q95 excursion.",
        "- Upside and downside histories are estimated separately.",
        "- RV20 ±1 sigma is retained only as a reference family.","",
        "## Distance census","",
        "| Period | N | U Mid | U Wall | U Extreme | L Mid | L Wall | L Extreme | RV1 upper | U/L Wall ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in per.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.n} | {r.upper_mid_med_pct:.3f}% | {r.upper_wall_med_pct:.3f}% | "
            f"{r.upper_extreme_med_pct:.3f}% | {r.lower_mid_med_abs_pct:.3f}% | {r.lower_wall_med_abs_pct:.3f}% | "
            f"{r.lower_extreme_med_abs_pct:.3f}% | {r.rv1_med_pct:.3f}% | {r.wall_asymmetry_ratio_median:.3f} |"
        )
    lines += ["","## Annual stability","",
        "| Year | N | U Wall | L Wall | U Extreme | L Extreme | RV1 | U/L ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in yr.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.n} | {r.upper_wall_med_pct:.3f}% | {r.lower_wall_med_abs_pct:.3f}% | "
            f"{r.upper_extreme_med_pct:.3f}% | {r.lower_extreme_med_abs_pct:.3f}% | "
            f"{r.rv1_med_pct:.3f}% | {r.asymmetry_median:.3f} |"
        )
    lines += ["","## S1 boundary",
        "A READY result means only that the causal wall map is well-defined and stable enough to audit.",
        "Predictive importance is deliberately unanswered here and belongs to B41-S2 Wall Importance Audit."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
