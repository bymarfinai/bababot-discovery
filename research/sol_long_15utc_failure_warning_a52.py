#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_EVENTS = ROOT / "SOL_LONG_15UTC_LOSS_TRIGGER_A51_EVENTS.csv"
OUT_SUM = ROOT / "SOL_LONG_15UTC_FAILURE_WARNING_A52_SUMMARY.csv"
OUT_BLOCK = ROOT / "SOL_LONG_15UTC_FAILURE_WARNING_A52_DEV_BLOCKS.csv"
OUT_LEGACY = ROOT / "SOL_LONG_15UTC_FAILURE_WARNING_A52_M2_LEGACY.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_FAILURE_WARNING_A52_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_FAILURE_WARNING_A52_Status.txt"

PARTS = ("development", "external", "reference_validation")
EXPECTED = {
    "development": (601, 244, 357),
    "external": (281, 115, 166),
    "reference_validation": (337, 150, 187),
}
EXPECTED_MECH = {"M0_REFERENCE_INVALIDATION": 76, "M1_TIME_NO_STRUCTURAL_FAIL": 95, "M2_FAILED_BREAK": 539}

WARNINGS = {
    "M2_FAILED_BREAK": [
        ("POST_H10", "warn_post_H10_ts", "warn_post_H10_lead_min", "timestamp"),
        ("POST_H05", "warn_post_H05_ts", "warn_post_H05_lead_min", "timestamp"),
        ("NO_EXT_005R_BY_5M", "no_ext_005R_by_5m", None, "bool"),
        ("NO_EXT_010R_BY_10M", "no_ext_010R_by_10m", None, "bool"),
    ],
    "M0_REFERENCE_INVALIDATION": [
        ("PRE_L25", "warn_pre_L25_ts", "warn_pre_L25_lead_min", "timestamp"),
        ("PRE_L10", "warn_pre_L10_ts", "warn_pre_L10_lead_min", "timestamp"),
        *[(f"NO_BREAK_{m}M", f"no_break_{m}m", None, "bool") for m in (30,60,120,180,240,360)],
    ],
    "M1_TIME_NO_STRUCTURAL_FAIL": [
        ("PRE_L25", "warn_pre_L25_ts", "warn_pre_L25_lead_min", "timestamp"),
        ("PRE_L10", "warn_pre_L10_ts", "warn_pre_L10_lead_min", "timestamp"),
        *[(f"NO_BREAK_{m}M", f"no_break_{m}m", None, "bool") for m in (30,60,120,180,240,360)],
    ],
}


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"

def hit_mask(q, col, typ):
    if typ == "timestamp":
        return q[col].notna()
    return q[col].fillna(False).astype(bool)

def safe_ratio(a, b):
    if b == 0:
        return np.inf if a > 0 else np.nan
    return a / b


def load_events():
    e = pd.read_csv(IN_EVENTS)
    for c in ["execution_start", "entry_ts", "exit_ts", "break_ts", "trigger_ts",
              "warn_pre_L25_ts", "warn_pre_L10_ts", "warn_post_H10_ts", "warn_post_H05_ts"]:
        if c in e.columns:
            e[c] = pd.to_datetime(e[c], utc=True, errors="coerce")
    return e


def validate(e):
    errors=[]
    for p,(n,w,l) in EXPECTED.items():
        q=e[e.partition==p]
        got=(len(q), int((q.outcome=="WIN").sum()), int((q.outcome=="LOSS").sum()))
        if got!=(n,w,l): errors.append(f"{p}: {got} != {(n,w,l)}")
    if len(e)!=1219 or int((e.outcome=="WIN").sum())!=509 or int((e.outcome=="LOSS").sum())!=710:
        errors.append("pooled reconciliation failed")
    losses=e[e.outcome=="LOSS"]
    for mech,n in EXPECTED_MECH.items():
        got=int((losses.mechanism==mech).sum())
        if got!=n: errors.append(f"{mech}: {got} != {n}")
    return errors


def metric_row(e, part, mech, warning, col, leadcol, typ):
    q=e[e.partition==part]
    bad=q[(q.outcome=="LOSS") & (q.mechanism==mech)]
    win=q[q.outcome=="WIN"]
    bh=hit_mask(bad,col,typ); wh=hit_mask(win,col,typ)
    br=float(bh.mean()) if len(bad) else np.nan
    wr=float(wh.mean()) if len(win) else np.nan
    gap=br-wr if pd.notna(br) and pd.notna(wr) else np.nan
    rr=safe_ratio(br,wr) if pd.notna(br) and pd.notna(wr) else np.nan
    lead=np.nan
    if leadcol:
        z=pd.to_numeric(bad.loc[bh,leadcol], errors="coerce").dropna()
        if len(z): lead=float(z.median())
    warn_from_break=np.nan
    if typ=="timestamp" and warning.startswith("POST_H"):
        z=bad.loc[bh,[col,"break_ts"]].dropna()
        if len(z):
            warn_from_break=float(((z[col]-z.break_ts)/pd.Timedelta(minutes=1)).median())
    return {
        "partition":part,"mechanism":mech,"warning":warning,
        "loss_n":len(bad),"loss_hit_n":int(bh.sum()),"loss_hit_rate":br,
        "winner_n":len(win),"winner_hit_n":int(wh.sum()),"winner_hit_rate":wr,
        "gap":gap,"hit_rate_ratio":rr,"median_loss_lead_min":lead,
        "median_warning_from_break_min":warn_from_break,
    }


def dev_blocks(e, mech, warning, col, typ):
    rows=[]
    d=e[e.partition=="development"].copy()
    for bi in range(6):
        q=d[pd.to_numeric(d.dev_block,errors="coerce")==bi]
        bad=q[(q.outcome=="LOSS")&(q.mechanism==mech)]
        win=q[q.outcome=="WIN"]
        bh=hit_mask(bad,col,typ); wh=hit_mask(win,col,typ)
        br=float(bh.mean()) if len(bad) else np.nan
        wr=float(wh.mean()) if len(win) else np.nan
        rows.append({"mechanism":mech,"warning":warning,"dev_block":bi+1,
                     "loss_n":len(bad),"winner_n":len(win),"loss_hit_rate":br,
                     "winner_hit_rate":wr,"same_direction":bool(pd.notna(br) and pd.notna(wr) and br>wr)})
    return rows


def legacy_m2(e):
    rows=[]
    for part in PARTS:
        q=e[(e.partition==part)&(e.outcome=="LOSS")&e.loss_class.astype(str).str.startswith(("L2_","L3_","L4_","L5_"))]
        for lc,z in q.groupby("loss_class",sort=False):
            for name,col,leadcol,typ in WARNINGS["M2_FAILED_BREAK"][:2]:
                h=hit_mask(z,col,typ)
                lead=pd.to_numeric(z.loc[h,leadcol],errors="coerce").dropna()
                rows.append({"partition":part,"loss_class":lc,"warning":name,"n":len(z),"hit_n":int(h.sum()),
                             "hit_rate":float(h.mean()),"median_lead_min":float(lead.median()) if len(lead) else np.nan})
    return pd.DataFrame(rows)


def main():
    e=load_events(); errors=validate(e)
    if errors:
        raise RuntimeError("; ".join(errors))

    rows=[]; blocks=[]
    meta={}
    for mech, ws in WARNINGS.items():
        for name,col,leadcol,typ in ws:
            meta[(mech,name)]=(col,leadcol,typ)
            for p in PARTS:
                rows.append(metric_row(e,p,mech,name,col,leadcol,typ))
            blocks.extend(dev_blocks(e,mech,name,col,typ))
    s=pd.DataFrame(rows); b=pd.DataFrame(blocks)

    # Development candidate gate, frozen in preregistration.
    same_counts=b.groupby(["mechanism","warning"],as_index=False).same_direction.sum().rename(columns={"same_direction":"dev_same_direction_blocks"})
    s=s.merge(same_counts,on=["mechanism","warning"],how="left")
    s["dev_candidate"]=False
    for key,g in s.groupby(["mechanism","warning"],sort=False):
        d=g[g.partition=="development"].iloc[0]
        cand=bool(d.loss_hit_rate>=0.50 and d.gap>=0.25 and d.hit_rate_ratio>=1.50 and int(d.dev_same_direction_blocks)>=5)
        if key[0]=="M2_FAILED_BREAK" and key[1] in ("POST_H10","POST_H05"):
            cand=cand and pd.notna(d.median_loss_lead_min) and float(d.median_loss_lead_min)>=5.0
        s.loc[(s.mechanism==key[0])&(s.warning==key[1]),"dev_candidate"]=cand

    # OOS replication only for Development candidates.
    s["replicated"]=False
    candidate_keys=[]
    for key,g in s.groupby(["mechanism","warning"],sort=False):
        if not bool(g.dev_candidate.iloc[0]): continue
        candidate_keys.append(key)
        ok=True
        for p in ("external","reference_validation"):
            r=g[g.partition==p].iloc[0]
            ok=ok and bool(r.loss_hit_rate>r.winner_hit_rate and r.gap>=0.15 and r.hit_rate_ratio>=1.25)
        s.loc[(s.mechanism==key[0])&(s.warning==key[1]),"replicated"]=ok

    legacy=legacy_m2(e)
    s.to_csv(OUT_SUM,index=False); b.to_csv(OUT_BLOCK,index=False); legacy.to_csv(OUT_LEGACY,index=False)

    repl=s[s.replicated].drop_duplicates(["mechanism","warning"])[["mechanism","warning"]]
    supported=len(repl)>0
    status="SOL_LONG_15UTC_FAILURE_WARNING_A52_SUPPORTED_FOR_A53" if supported else "SOL_LONG_15UTC_FAILURE_WARNING_A52_INCONCLUSIVE"

    lines=[
        "# SOL LONG 15:00 UTC Failure Early-Warning Validation — A52 Result","",
        "A52 uses only warning definitions frozen in A51. No new threshold or exit was optimized.","",
        "## Reconciliation","",
        "A51 source reconciled exactly: **1219 trades / 509 winners / 710 losses**, with M0=76, M1=95, M2=539.","",
        "## Development discrimination","",
        "| Mechanism | Warning | Bad hit | Winner hit | Gap | Ratio | Blocks | Lead | Candidate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    d=s[s.partition=="development"].copy()
    for _,r in d.sort_values(["mechanism","gap"],ascending=[True,False]).iterrows():
        lines.append(f"| {r.mechanism} | {r.warning} | {pct(r.loss_hit_rate)} | {pct(r.winner_hit_rate)} | {pct(r.gap)} | {fmt(r.hit_rate_ratio,2)}x | {int(r.dev_same_direction_blocks)}/6 | {fmt(r.median_loss_lead_min,0)}m | {'YES' if r.dev_candidate else 'no'} |")

    lines += ["","## OOS confirmation for Development candidates","",
              "| Mechanism | Warning | Partition | Bad hit | Winner hit | Gap | Ratio | Replicated |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
    if candidate_keys:
        for mech,warn in candidate_keys:
            g=s[(s.mechanism==mech)&(s.warning==warn)]
            rep=bool(g.replicated.iloc[0])
            for p in ("external","reference_validation"):
                r=g[g.partition==p].iloc[0]
                lines.append(f"| {mech} | {warn} | {p} | {pct(r.loss_hit_rate)} | {pct(r.winner_hit_rate)} | {pct(r.gap)} | {fmt(r.hit_rate_ratio,2)}x | {'YES' if rep else 'no'} |")
    else:
        lines.append("| - | - | - | - | - | - | - | no Development candidates |")

    lines += ["","## M2 primary warning by legacy latency class","",
              "| Partition | Class | Warning | N | Hit | Lead |","|---|---|---|---:|---:|---:|"]
    for _,r in legacy.iterrows():
        lines.append(f"| {r.partition} | {r.loss_class} | {r.warning} | {int(r.n)} | {pct(r.hit_rate)} | {fmt(r.median_lead_min,0)}m |")

    lines += ["","## Decision","",f"Replicated fixed warnings: **{len(repl)}**."]
    if len(repl):
        lines.append("Replicated warnings: **" + ", ".join(f"{r.mechanism}/{r.warning}" for _,r in repl.iterrows()) + "**.")
    lines += ["",f"**Status: {status}**","",
              "A52 does not authorize an exit change. If supported, A53 must simulate only the replicated warning(s) as causal executable guards against the untouched parent and report raw + 5bps portfolio economics.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    print(status)

if __name__=="__main__":
    main()
