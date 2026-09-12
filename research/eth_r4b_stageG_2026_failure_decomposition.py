#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT / "ETH_R4B_STAGE_E_2026_YTD_CELLS.csv"
OUT_MONTH = ROOT / "ETH_R4B_STAGE_G_2026_MONTHLY_CELLS.csv"
OUT_PHASE = ROOT / "ETH_R4B_STAGE_G_2026_PHASE_FEATURES.csv"
OUT_SHIFT = ROOT / "ETH_R4B_STAGE_G_2026_FEATURE_SHIFTS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGE_G_2026_FAILURE_Result.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGE_G_2026_FAILURE_Status.txt"
EXPECTED = {(120,240),(180,240),(240,240),(180,360),(240,360)}
HOUR = 4
RULE = "DRIVE_DOWN__STR_B80_100"
START = pd.Timestamp("2026-01-01", tz="UTC")

FEATURES = [
    "pre_ret_60", "pre_ret_240", "rv_60", "rv_240", "atr_pct_60", "atr_pct_240",
    "trend_eff_240", "disp_60", "disp_240", "fwd_ret_60", "fwd_ret_120",
]
PRE_FEATURES = FEATURES[:9]
FOLLOW_FEATURES = FEATURES[9:]

PHASES = [
    ("Q1_JAN_MAR", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-04-01", tz="UTC")),
    ("Q2_APR_JUN", pd.Timestamp("2026-04-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC")),
    ("Q3_JUL_AUG", pd.Timestamp("2026-07-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")),
]


def finite(x): return bool(np.isfinite(x))
def metric(st, key):
    x=float(st[key]); return x if finite(x) else np.nan

def stats(T): return r1.stats_from_df(T[["entry_ts","exit_ts","clock","gross","net"]].copy())

def build_features(x: pd.DataFrame) -> pd.DataFrame:
    c=x["close"].astype(float); h=x["high"].astype(float); l=x["low"].astype(float)
    prev=c.shift(1)
    logc=np.log(c)
    lr=logc.diff()
    tr=pd.concat([(h-l).abs(),(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)/prev
    pre_c=c.shift(1)
    F=pd.DataFrame(index=x.index)
    F["pre_ret_60"]=pre_c/pre_c.shift(12)-1.0
    F["pre_ret_240"]=pre_c/pre_c.shift(48)-1.0
    F["rv_60"]=lr.shift(1).rolling(12,min_periods=12).std(ddof=0)*np.sqrt(12)
    F["rv_240"]=lr.shift(1).rolling(48,min_periods=48).std(ddof=0)*np.sqrt(48)
    F["atr_pct_60"]=tr.shift(1).rolling(12,min_periods=12).mean()
    F["atr_pct_240"]=tr.shift(1).rolling(48,min_periods=48).mean()
    path=lr.abs().shift(1).rolling(48,min_periods=48).sum()
    F["trend_eff_240"]=(logc.shift(1)-logc.shift(49)).abs()/path.replace(0,np.nan)
    F["disp_60"]=F["pre_ret_60"].abs()/(F["rv_60"].replace(0,np.nan))
    F["disp_240"]=F["pre_ret_240"].abs()/(F["rv_240"].replace(0,np.nan))
    # Outcome-side diagnostics only; never candidates for a live entry gate in Stage G.
    F["fwd_ret_60"]=c.shift(-12)/c-1.0
    F["fwd_ret_120"]=c.shift(-24)/c-1.0
    return F


def events(cache, lb, hold, last_ts, F):
    rows=[]
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks=cache[(clock,lb,hold)]
        ent=pd.DatetimeIndex(ent); ex=pd.DatetimeIndex(ex)
        m=valid & (ent>=START) & (ex<=last_ts) & masks[RULE]
        gross=e12.NOTIONAL*np.asarray(delta,float)[m]; net=gross-e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m],ex[m],gross,net):
            row={"entry_ts":entry_ts,"exit_ts":exit_ts,"clock":int(clock),"gross":float(g),"net":float(n)}
            if entry_ts in F.index:
                for f in FEATURES: row[f]=float(F.at[entry_ts,f]) if finite(F.at[entry_ts,f]) else np.nan
            else:
                for f in FEATURES: row[f]=np.nan
            rows.append(row)
    return pd.DataFrame(rows,columns=["entry_ts","exit_ts","clock","gross","net"]+FEATURES)


def summarize(T, label, lb, hold):
    st=stats(T)
    row={"window":label,"lookback_min":lb,"hold_min":hold,"n":int(st["trades"]),
         "wr":metric(st,"win_rate"),"net":float(st["net_pnl"]),"exp":metric(st,"expectancy"),
         "pf":metric(st,"pf"),"dd":metric(st,"max_dd"),"max_loss_streak":int(st["max_loss_streak"])}
    for f in FEATURES: row[f+"_median"]=float(T[f].median()) if len(T) and T[f].notna().any() else np.nan
    return row


def fmt_pct(x): return "NA" if not finite(x) else f"{100*x:.2f}%"
def fmt_num(x,d=3): return "NA" if not finite(x) else f"{x:.{d}f}"
def fmt_money(x): return "NA" if not finite(x) else f"${x:+.2f}"


def main():
    prior=pd.read_csv(PRIOR)
    if len(prior)!=5: raise AssertionError(f"expected 5 frozen cells, got {len(prior)}")
    if set(prior.hour_wib.astype(int))!={HOUR}: raise AssertionError("frozen hour changed")
    if set(prior.character_rule.astype(str))!={RULE}: raise AssertionError("frozen rule changed")
    actual=set(zip(prior.lookback_min.astype(int),prior.hold_min.astype(int)))
    if actual!=EXPECTED: raise AssertionError(f"frozen cells changed: {sorted(actual)}")
    cutoffs=pd.to_datetime(prior.dataset_last_ts_utc,utc=True).unique()
    if len(cutoffs)!=1: raise AssertionError("non-unique Stage-E cutoff")
    last_ts=pd.Timestamp(cutoffs[0])

    e12.base.synthetic_tests(); x5,coverage=e12.base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    if idx.max()<last_ts: raise RuntimeError(f"dataset does not reach frozen cutoff: {idx.max()} < {last_ts}")
    x=x5[idx<=last_ts].copy(); F=build_features(x)
    e12.CLOCKS=r1.clocks_for_hour(HOUR)
    e12.LOOKBACKS=sorted(prior.lookback_min.astype(int).unique().tolist())
    e12.HOLDS=sorted(prior.hold_min.astype(int).unique().tolist())
    cache=e12.prep(x)

    event_map={}
    for c in prior.itertuples(index=False):
        key=(int(c.lookback_min),int(c.hold_min)); event_map[key]=events(cache,*key,last_ts,F)

    monthly=[]
    months=pd.date_range("2026-01-01","2026-08-01",freq="MS",tz="UTC")
    for ms in months:
        me=ms+pd.offsets.MonthBegin(1); label=ms.strftime("%Y-%m")
        for lb,hold in sorted(EXPECTED,key=lambda z:(z[1],z[0])):
            T=event_map[(lb,hold)]; W=T[(T.entry_ts>=ms)&(T.entry_ts<me)]
            monthly.append(summarize(W,label,lb,hold))
    M=pd.DataFrame(monthly); M.to_csv(OUT_MONTH,index=False)

    phase=[]
    for label,s,e in PHASES:
        for lb,hold in sorted(EXPECTED,key=lambda z:(z[1],z[0])):
            T=event_map[(lb,hold)]; W=T[(T.entry_ts>=s)&(T.entry_ts<e)]
            phase.append(summarize(W,label,lb,hold))
    P=pd.DataFrame(phase); P.to_csv(OUT_PHASE,index=False)

    # Fixed feature-shift diagnostic: Q2 vs Q1 and Q2 vs Q3, summarized across all five frozen cells.
    shifts=[]
    for f in FEATURES:
        col=f+"_median"
        q1=P[P.window=="Q1_JAN_MAR"].set_index(["lookback_min","hold_min"])[col]
        q2=P[P.window=="Q2_APR_JUN"].set_index(["lookback_min","hold_min"])[col]
        q3=P[P.window=="Q3_JUL_AUG"].set_index(["lookback_min","hold_min"])[col]
        d21=(q2-q1); d23=(q2-q3)
        same=((np.sign(d21)==np.sign(d23)) & d21.notna() & d23.notna())
        denom=((q1.abs()+q3.abs())/2).replace(0,np.nan)
        rel=(q2-((q1+q3)/2))/denom
        shifts.append({
            "feature":f,
            "feature_role":"follow_through" if f in FOLLOW_FEATURES else "pre_entry",
            "q1_median_across_cells":float(q1.median()),
            "q2_median_across_cells":float(q2.median()),
            "q3_median_across_cells":float(q3.median()),
            "q2_minus_q1_median":float(d21.median()),
            "q2_minus_q3_median":float(d23.median()),
            "same_direction_cells":int(same.sum()),
            "median_relative_shift_q2_vs_flanks":float(rel.median()) if rel.notna().any() else np.nan,
        })
    S=pd.DataFrame(shifts)
    S["abs_relative_shift"]=S.median_relative_shift_q2_vs_flanks.abs()
    S=S.sort_values(["feature_role","abs_relative_shift"],ascending=[True,False]).reset_index(drop=True)
    S.to_csv(OUT_SHIFT,index=False)

    # Failure concentration: months in which all 5 cells have negative expectancy/PF<1.
    month_flags=[]
    for month,W in M.groupby("window",sort=True):
        bad=((W.exp<0)&(W.pf<1)).sum(); good=((W.exp>0)&(W.pf>1)).sum()
        month_flags.append((month,int(bad),int(good),float(W.exp.median()),float(W.pf.median())))
    all_bad=[m for m,b,g,e,p in month_flags if b==5]
    all_good=[m for m,b,g,e,p in month_flags if g==5]

    # Top pre-entry shifts require consistency in at least 4/5 cells; descriptive, not a gate.
    pre=S[(S.feature_role=="pre_entry")&(S.same_direction_cells>=4)].sort_values("abs_relative_shift",ascending=False)
    top_pre=pre.head(3).feature.tolist()
    follow=S[S.feature_role=="follow_through"].sort_values("abs_relative_shift",ascending=False)
    top_follow=follow.head(2).feature.tolist()
    status="Q2_FAILURE_DECOMPOSED"
    if len(all_bad)>=1: status+="__MONTHLY_CONCENTRATION_CONFIRMED"
    if len(top_pre)>=1: status+="__PREENTRY_SHIFT_PRESENT"
    if len(top_follow)>=1: status+="__FOLLOWTHROUGH_SHIFT_PRESENT"

    anchor=M[(M.lookback_min==240)&(M.hold_min==360)]
    lines=[
        "# ETH R4b — Stage G 2026 Failure Decomposition",
        "",
        "**DIAGNOSTIC ONLY. FIVE FROZEN H04 CELLS. NO RESELECTION, RETUNING, OR REGIME-GATE PROMOTION.**",
        "",
        f"Dataset cutoff frozen to Stage E: **{last_ts.isoformat()}**. Coverage **{coverage:.4%}**.",
        "Pre-entry features end one 5m bar before entry. Forward returns are outcome-side diagnostics only.",
        f"Stage G status: **{status}**.",
        f"Months where all 5 frozen cells are weak (Exp<0 and PF<1): **{', '.join(all_bad) if all_bad else 'none'}**.",
        f"Months where all 5 frozen cells are positive (Exp>0 and PF>1): **{', '.join(all_good) if all_good else 'none'}**.",
        "",
        "## Canonical LB240/H360 monthly localization",
        "",
        "| Month | N | WR | Net | Exp | PF | PreRet1H | PreRet4H | RV1H | ATR1H | TrendEff4H | Fwd1H | Fwd2H |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in anchor.itertuples(index=False):
        lines.append(f"| {r.window} | {int(r.n)} | {fmt_pct(float(r.wr))} | {fmt_money(float(r.net))} | {fmt_money(float(r.exp))} | {fmt_num(float(r.pf))} | {fmt_pct(float(r.pre_ret_60_median))} | {fmt_pct(float(r.pre_ret_240_median))} | {fmt_pct(float(r.rv_60_median))} | {fmt_pct(float(r.atr_pct_60_median))} | {fmt_num(float(r.trend_eff_240_median))} | {fmt_pct(float(r.fwd_ret_60_median))} | {fmt_pct(float(r.fwd_ret_120_median))} |")

    lines += ["","## Cross-cell phase feature shifts","", "| Feature | Role | Q1 median | Q2 median | Q3 median | Same-direction cells | Relative Q2 shift vs flanks |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.feature} | {r.feature_role} | {fmt_num(float(r.q1_median_across_cells),5)} | {fmt_num(float(r.q2_median_across_cells),5)} | {fmt_num(float(r.q3_median_across_cells),5)} | {int(r.same_direction_cells)}/5 | {fmt_num(float(r.median_relative_shift_q2_vs_flanks),3)} |")

    lines += ["","## Diagnostic readout","",
              f"- Strongest consistent pre-entry Q2 shifts (>=4/5 cells): **{', '.join(top_pre) if top_pre else 'none'}**.",
              f"- Outcome-side follow-through shifts: **{', '.join(top_follow) if top_follow else 'none'}**.",
              "- These rankings are descriptive failure signatures only. They are not thresholds and cannot be converted into a live filter without a new preregistered validation stage.",
              "- Stage D 2025 remains the final untouched full-year OOS result. Stage E/F/G remain current-regime diagnostics.",
              "- No hour, character rule, lookback, hold, entry, TP/SL, or risk rule changed in Stage G."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); OUT_STATUS.write_text(status+"\n")
    print("\n".join(lines))

if __name__=="__main__": main()
