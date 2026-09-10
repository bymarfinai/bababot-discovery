#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_discovery2_reset_g4_entry_discovery as g4

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G6_PAYOFF_ATLAS"
OUT_TRADE = ROOT / f"{PFX}_TradeAtlas.csv"
OUT_TARGET = ROOT / f"{PFX}_TargetAtlas.csv"
OUT_HORIZON = ROOT / f"{PFX}_HorizonAtlas.csv"
OUT_FIRST = ROOT / f"{PFX}_FirstHitAtlas.csv"
OUT_BLOCKS = ROOT / f"{PFX}_DevelopmentBlocks.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR_MIN = 5
NOTIONAL = 500.0
FEE = 0.75
FEE_RATE = FEE / NOTIONAL
PARTS = ("development", "external", "reference_validation")
EXPECTED = {"development": 184, "external": 88, "reference_validation": 91}
TARGETS = (0.05,0.08,0.10,0.12,0.15,0.20,0.30,0.40,0.60,0.80,1.00,1.25,1.50,2.00,2.50,3.00,4.00,5.00)
HORIZONS = (15,30,60,120,240,480,720)
FIRST_T = (0.15,0.20,0.30,0.40,0.60,0.80,1.00,1.50,2.00)
FIRST_A = (0.05,0.08,0.10,0.12,0.15,0.20,0.30,0.40,0.60,0.80,1.00)
MAJOR_T = (0.30,0.60,1.00,1.50,2.00)


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def qv(a, q):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return np.nan if len(a) == 0 else float(np.quantile(a, q))


def build_entries(x5: pd.DataFrame, part: str) -> pd.DataFrame:
    C = g4.build_b00_cases(x5, part)
    rows = []
    for c in C.itertuples(index=False):
        ent = g4.next_open_entry(x5, c)
        if ent is None or not ent.get("available", False):
            continue
        rows.append({
            "partition": part,
            "reference_start": c.reference_start,
            "execution_start": c.execution_start,
            "execution_end": c.execution_end,
            "H": float(c.H), "L": float(c.L), "R": float(c.R),
            "signal_ts": c.signal_ts,
            "b00_complete_ts": c.b00_complete_ts,
            "entry_j": int(ent["entry_j"]),
            "exe_start_pos": int(c.exe_start_pos),
            "exe_n": int(c.exe_n),
            "entry_ts": pd.Timestamp(ent["entry_ts"]),
            "entry_price": float(ent["entry_price"]),
        })
    E = pd.DataFrame(rows)
    if len(E) != EXPECTED[part]:
        raise AssertionError(f"frozen G4 entry mismatch {part}: {len(E)} vs {EXPECTED[part]}")
    return E.sort_values("entry_ts").reset_index(drop=True)


def path_for(x5: pd.DataFrame, r):
    start_ix = int(r.exe_start_pos) + int(r.entry_j)
    entry_ts = pd.Timestamp(r.entry_ts)
    cap = min(pd.Timestamp(r.execution_end), entry_ts + pd.Timedelta(minutes=720))
    # Include bars whose starts are >= entry and whose completions are <= cap.
    nmax = max(0, int((cap - entry_ts) / pd.Timedelta(minutes=BAR_MIN)))
    if nmax <= 0:
        return x5.iloc[0:0].copy()
    end_ix = min(len(x5), start_ix + nmax)
    P = x5.iloc[start_ix:end_ix].copy()
    if len(P) and (P.index[0] != entry_ts):
        raise AssertionError("entry path index mismatch")
    return P


def trade_atlas_row(x5: pd.DataFrame, r):
    P = path_for(x5, r)
    if len(P) == 0:
        raise AssertionError("empty frozen post-entry path")
    ep, R = float(r.entry_price), float(r.R)
    highs = P.high.to_numpy(float); lows = P.low.to_numpy(float)
    mfe_r = float((np.max(highs) - ep) / R)
    mae_r = float(max(0.0, (ep - np.min(lows)) / R))
    last_close = float(P.close.iloc[-1])
    gross_ret = last_close / ep - 1.0
    net_pnl = NOTIONAL * gross_ret - FEE
    fee_be_r = FEE_RATE * ep / R
    return {
        "partition": r.partition,
        "entry_ts": r.entry_ts,
        "execution_end": r.execution_end,
        "entry_price": ep,
        "R": R,
        "R_over_entry_pct": 100.0 * R / ep,
        "fee_be_R": fee_be_r,
        "path_bars": len(P),
        "path_minutes": len(P) * BAR_MIN,
        "full_mfe_R": mfe_r,
        "full_mae_R": mae_r,
        "clears_fee_by_mfe": bool(mfe_r >= fee_be_r),
        "mfe_excess_fee_R": mfe_r - fee_be_r,
        "terminal_close": last_close,
        "terminal_gross_return": gross_ret,
        "terminal_net_pnl": net_pnl,
        "terminal_net_positive": bool(net_pnl > 0),
    }


def target_rows(x5: pd.DataFrame, E: pd.DataFrame):
    rows = []
    for part in PARTS:
        Q = E[E.partition == part]
        for T in TARGETS:
            reached=[]; times=[]; maes=[]; fee_prof=[]
            for r in Q.itertuples(index=False):
                P = path_for(x5, r)
                ep,R=float(r.entry_price),float(r.R)
                target=ep+T*R
                hit_i=None
                for i,b in enumerate(P.itertuples(index=False)):
                    if float(b.high) >= target:
                        hit_i=i; break
                hit = hit_i is not None
                reached.append(hit)
                fee_be = FEE_RATE*ep/R
                fee_prof.append(bool(hit and T > fee_be))
                if hit:
                    times.append((hit_i+1)*BAR_MIN)
                    # Only completed bars strictly before the target-touch bar can be ordered before target.
                    if hit_i == 0:
                        maes.append(0.0)
                    else:
                        prior_min=float(P.low.iloc[:hit_i].min())
                        maes.append(max(0.0,(ep-prior_min)/R))
            n=len(Q); k=int(sum(reached))
            rows.append({
                "partition":part,"target_R":T,"entries":n,"reaches":k,
                "reach_rate":k/n if n else np.nan,
                "fee_profitable_reaches":int(sum(fee_prof)),
                "fee_profitable_reach_rate":sum(fee_prof)/n if n else np.nan,
                "median_time_min":qv(times,.50),"p75_time_min":qv(times,.75),
                "median_MAE_before_T_R":qv(maes,.50),"p75_MAE_before_T_R":qv(maes,.75),"p90_MAE_before_T_R":qv(maes,.90),
            })
    return pd.DataFrame(rows)


def horizon_rows(x5: pd.DataFrame, E: pd.DataFrame):
    rows=[]
    for part in PARTS:
        Q=E[E.partition==part]
        for H in HORIZONS:
            mfes=[]; maes=[]; fee_clear=[]; mtm_pos=[]; available=0
            bars=H//BAR_MIN
            for r in Q.itertuples(index=False):
                P=path_for(x5,r)
                if len(P)<bars:
                    continue
                P=P.iloc[:bars]
                ep,R=float(r.entry_price),float(r.R)
                mfe=(float(P.high.max())-ep)/R
                mae=max(0.0,(ep-float(P.low.min()))/R)
                last=float(P.close.iloc[-1])
                net=NOTIONAL*(last/ep-1.0)-FEE
                be=FEE_RATE*ep/R
                mfes.append(mfe); maes.append(mae); fee_clear.append(mfe>=be); mtm_pos.append(net>0); available+=1
            rows.append({
                "partition":part,"horizon_min":H,"available":available,"entries":len(Q),
                "mfe_p25_R":qv(mfes,.25),"mfe_median_R":qv(mfes,.50),"mfe_p75_R":qv(mfes,.75),"mfe_p90_R":qv(mfes,.90),
                "mae_p25_R":qv(maes,.25),"mae_median_R":qv(maes,.50),"mae_p75_R":qv(maes,.75),"mae_p90_R":qv(maes,.90),
                "fee_clear_rate":float(np.mean(fee_clear)) if fee_clear else np.nan,
                "terminal_net_positive_rate":float(np.mean(mtm_pos)) if mtm_pos else np.nan,
            })
    return pd.DataFrame(rows)


def first_hit_rows(x5: pd.DataFrame, E: pd.DataFrame):
    rows=[]
    for part in PARTS:
        Q=E[E.partition==part]
        for T in FIRST_T:
            for A in FIRST_A:
                counts={"FAVORABLE":0,"ADVERSE":0,"AMBIGUOUS":0,"NEITHER":0}
                for r in Q.itertuples(index=False):
                    P=path_for(x5,r); ep,R=float(r.entry_price),float(r.R)
                    tp=ep+T*R; sl=ep-A*R; outcome="NEITHER"
                    for b in P.itertuples(index=False):
                        ht=float(b.high)>=tp; ha=float(b.low)<=sl
                        if ht and ha: outcome="AMBIGUOUS"; break
                        if ht: outcome="FAVORABLE"; break
                        if ha: outcome="ADVERSE"; break
                    counts[outcome]+=1
                n=len(Q)
                rows.append({"partition":part,"target_R":T,"adverse_R":A,"entries":n,
                    "favorable_first":counts["FAVORABLE"],"favorable_first_rate":counts["FAVORABLE"]/n,
                    "adverse_first":counts["ADVERSE"],"adverse_first_rate":counts["ADVERSE"]/n,
                    "ambiguous":counts["AMBIGUOUS"],"ambiguous_rate":counts["AMBIGUOUS"]/n,
                    "neither":counts["NEITHER"],"neither_rate":counts["NEITHER"]/n,
                    "fav_minus_adv":(counts["FAVORABLE"]-counts["ADVERSE"])/n})
    return pd.DataFrame(rows)


def dev_blocks(TA: pd.DataFrame):
    Q=TA[TA.partition=="development"].sort_values("entry_ts").reset_index(drop=True)
    rows=[]
    for bi,ix in enumerate(np.array_split(np.arange(len(Q)),4),1):
        B=Q.iloc[ix]
        row={"block":bi,"n":len(B),
             "median_fee_be_R":float(B.fee_be_R.median()),
             "median_full_mfe_R":float(B.full_mfe_R.median()),
             "median_full_mae_R":float(B.full_mae_R.median()),
             "fee_clear_rate":float(B.clears_fee_by_mfe.mean()),
             "terminal_net_positive_rate":float(B.terminal_net_positive.mean())}
        for T in MAJOR_T:
            row[f"mfe_ge_{T:.2f}R"] = float((B.full_mfe_R>=T).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def dist_summary(TA, part):
    Q=TA[TA.partition==part]
    return {
        "n":len(Q),
        "R_entry_med":float(Q.R_over_entry_pct.median()),
        "R_entry_p25":float(Q.R_over_entry_pct.quantile(.25)),
        "R_entry_p75":float(Q.R_over_entry_pct.quantile(.75)),
        "be_med":float(Q.fee_be_R.median()),
        "be_p25":float(Q.fee_be_R.quantile(.25)),
        "be_p75":float(Q.fee_be_R.quantile(.75)),
        "mfe_med":float(Q.full_mfe_R.median()),"mfe_p75":float(Q.full_mfe_R.quantile(.75)),"mfe_p90":float(Q.full_mfe_R.quantile(.90)),
        "mae_med":float(Q.full_mae_R.median()),"mae_p75":float(Q.full_mae_R.quantile(.75)),"mae_p90":float(Q.full_mae_R.quantile(.90)),
        "clear":float(Q.clears_fee_by_mfe.mean()),
        "term_pos":float(Q.terminal_net_positive.mean()),
        "excess_med":float(Q.loc[Q.clears_fee_by_mfe,"mfe_excess_fee_R"].median()),
        "terminal_net_sum":float(Q.terminal_net_pnl.sum()),
        "terminal_net_exp":float(Q.terminal_net_pnl.mean()),
    }


def main():
    g4.g1.base.synthetic_tests()
    x5,coverage=g4.g1.base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low {coverage}")

    Es=[]
    for p in PARTS: Es.append(build_entries(x5,p))
    E=pd.concat(Es,ignore_index=True)
    TA=pd.DataFrame([trade_atlas_row(x5,r) for r in E.itertuples(index=False)])
    TG=target_rows(x5,E); HZ=horizon_rows(x5,E); FH=first_hit_rows(x5,E); DB=dev_blocks(TA)
    TA.to_csv(OUT_TRADE,index=False); TG.to_csv(OUT_TARGET,index=False); HZ.to_csv(OUT_HORIZON,index=False); FH.to_csv(OUT_FIRST,index=False); DB.to_csv(OUT_BLOCKS,index=False)

    # Descriptive cross-partition target stability flags.
    stability=[]
    for T in MAJOR_T:
        q=TG[np.isclose(TG.target_R,T)]
        rates=q.reach_rate.to_numpy(float); reaches=q.reaches.to_numpy(int)
        spread=float(rates.max()-rates.min())
        stable=bool(spread<=.15 and (reaches>=20).all())
        stability.append((T,spread,stable,q))

    # Broad first-hit cells where favorable beats adverse in every partition.
    robust=[]
    for T in FIRST_T:
        for A in FIRST_A:
            q=FH[np.isclose(FH.target_R,T)&np.isclose(FH.adverse_R,A)]
            if len(q)!=3: continue
            margins=q.fav_minus_adv.to_numpy(float)
            if (margins>0).all():
                robust.append((float(margins.min()),float(margins.mean()),T,A,q))
    robust.sort(reverse=True,key=lambda z:(z[0],z[1]))

    lines=["# ETH Discovery 2 Reset — G6 Fee-Adjusted Payoff Atlas Result","",
           f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Frozen lineage: **LONG / 01:30 UTC / R180 / E720 / HIGH-side pressure → DIRECT B00 → NEXT_OPEN**.",
           f"Frozen entries: Development **{EXPECTED['development']}**, External **{EXPECTED['external']}**, Reference Validation **{EXPECTED['reference_validation']}**.",
           "G6 is descriptive only: no TP/SL/hold strategy is selected.","",
           "## Fee-survival and full-window excursion","",
           "| Partition | N | Median R/entry | Median fee BE | MFE med / p75 / p90 | MAE med / p75 / p90 | MFE clears fee | Terminal net+ | Terminal net sum |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    summaries={}
    for p in PARTS:
        s=dist_summary(TA,p); summaries[p]=s
        lines.append(f"| {p} | {s['n']} | {s['R_entry_med']:.3f}% | {s['be_med']:.3f}R | {s['mfe_med']:.3f}/{s['mfe_p75']:.3f}/{s['mfe_p90']:.3f}R | {s['mae_med']:.3f}/{s['mae_p75']:.3f}/{s['mae_p90']:.3f}R | {pct(s['clear'])} | {pct(s['term_pos'])} | ${s['terminal_net_sum']:+.2f} |")

    lines += ["","## Favorable target ladder","",
              "| Target | Dev reach | Ext reach | Ref-val reach | Dev med time | Dev p75 MAE-before | Shape |",
              "|---:|---:|---:|---:|---:|---:|---|"]
    for T in TARGETS:
        q=TG[np.isclose(TG.target_R,T)]
        d=q[q.partition=="development"].iloc[0]; e=q[q.partition=="external"].iloc[0]; v=q[q.partition=="reference_validation"].iloc[0]
        st="-"
        for mt,spread,stable,_ in stability:
            if abs(mt-T)<1e-9: st="STABLE" if stable else f"UNSTABLE ({100*spread:.1f}pp spread)"
        lines.append(f"| {T:.2f}R | {int(d.reaches)}/{int(d.entries)} {pct(d.reach_rate)} | {int(e.reaches)}/{int(e.entries)} {pct(e.reach_rate)} | {int(v.reaches)}/{int(v.entries)} {pct(v.reach_rate)} | {d.median_time_min:.0f}m | {d.p75_MAE_before_T_R:.3f}R | {st} |")

    lines += ["","## Time-sliced Development path","",
              "| Horizon | Available | MFE med / p75 / p90 | MAE med / p75 / p90 | MFE clears fee | MTM net+ |",
              "|---:|---:|---:|---:|---:|---:|"]
    for r in HZ[HZ.partition=="development"].itertuples(index=False):
        lines.append(f"| {int(r.horizon_min)}m | {int(r.available)}/{int(r.entries)} | {r.mfe_median_R:.3f}/{r.mfe_p75_R:.3f}/{r.mfe_p90_R:.3f}R | {r.mae_median_R:.3f}/{r.mae_p75_R:.3f}/{r.mae_p90_R:.3f}R | {pct(r.fee_clear_rate)} | {pct(r.terminal_net_positive_rate)} |")

    lines += ["","## Development chronological blocks","",
              "| Block | N | Fee BE med | MFE med | MAE med | Clears fee | >=0.30R | >=0.60R | >=1.00R | >=1.50R | >=2.00R | Terminal net+ |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in DB.itertuples(index=False):
        lines.append(f"| {int(r.block)} | {int(r.n)} | {r.median_fee_be_R:.3f}R | {r.median_full_mfe_R:.3f}R | {r.median_full_mae_R:.3f}R | {pct(r.fee_clear_rate)} | {pct(getattr(r,'mfe_ge_0_30R'))} | {pct(getattr(r,'mfe_ge_0_60R'))} | {pct(getattr(r,'mfe_ge_1_00R'))} | {pct(getattr(r,'mfe_ge_1_50R'))} | {pct(getattr(r,'mfe_ge_2_00R'))} | {pct(r.terminal_net_positive_rate)} |")

    lines += ["","## Robust first-hit regions — descriptive","",
              "A cell appears here only when favorable-first > adverse-first in **all three** partitions. Ranked by worst-partition margin.","",
              "| # | Target | Adverse | Worst margin | Dev F/A | Ext F/A | Ref-val F/A |",
              "|---:|---:|---:|---:|---:|---:|---:|"]
    if robust:
        for i,(mn,av,T,A,q) in enumerate(robust[:15],1):
            vals={r.partition:r for r in q.itertuples(index=False)}
            lines.append(f"| {i} | {T:.2f}R | {A:.2f}R | {mn:+.1%} | {pct(vals['development'].favorable_first_rate)}/{pct(vals['development'].adverse_first_rate)} | {pct(vals['external'].favorable_first_rate)}/{pct(vals['external'].adverse_first_rate)} | {pct(vals['reference_validation'].favorable_first_rate)}/{pct(vals['reference_validation'].adverse_first_rate)} |")
    else:
        lines.append("| - | - | - | - | - | - | - |")

    stable_targets=[T for T,sp,st,q in stability if st]
    lines += ["","## Cross-partition target-shape flags","",
              f"Stable major target reach levels by preregistered descriptive rule: **{', '.join(f'{x:.2f}R' for x in stable_targets) if stable_targets else 'NONE'}**.",
              f"Robust favorable-first cells across all three partitions: **{len(robust)}**.","",
              "**Status: ETH_DISCOVERY2_RESET_G6_ATLAS_COMPLETE**","",
              "This atlas does not promote a strategy. G7, if justified, must preregister a finite economic family from broad cross-partition payoff regions rather than from a single best cell.",
              "Research/shadow only. No live promotion or profit guarantee."]
    OUT_STATUS.write_text("ETH_DISCOVERY2_RESET_G6_ATLAS_COMPLETE\n")
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
