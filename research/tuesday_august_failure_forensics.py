#!/usr/bin/env python3
"""Tuesday August failure-to-develop forensic.

Research only; live BBC untouched.

Question:
Why did the frozen Tuesday 06:00 WIB SELL fail to develop on Aug 4/11/18 2026,
and is there a causal PRE-ENTRY state that could be used as a WAIT guard?

Guardrails:
- Frozen A5.11 replay/parity is imported unchanged.
- No TP/SL/hold/management retuning.
- All candidate features are known before Tuesday 06:00 WIB.
- Continuous candidate thresholds are only discovery quartiles (Q25/Q75), not
  thresholds chosen to fit August.
- Natural binary states are predeclared before August scoring.
- Discovery = first 83 historical Tuesdays; validation = last 56 report-only.
- August is scored only after historical candidate tables are constructed.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("TUEAUGF_OUT", "tueaugf_out"))
OUT.mkdir(parents=True, exist_ok=True)
DISC_N = 83

CONT_FEATURES = [
    "ret1h","ret3h","ret6h","ret12h","ret24h","mon_ret","overnight_ret",
    "ema_spread","dist_ema20","ema20_slope1h","loc24","range6","range24",
    "taker1h","taker4h",
]


def close_before(k, t):
    x = k[k.index < t]
    if x.empty:
        return np.nan
    return float(x.iloc[-1].close)


def ema_before(k, t, col):
    x = k[k.index < t]
    if x.empty:
        return np.nan
    return float(x.iloc[-1][col])


def ret_between(k, a, b):
    pa = close_before(k, a + pd.Timedelta(minutes=5))
    pb = close_before(k, b)
    if not np.isfinite(pa) or not np.isfinite(pb) or pa == 0:
        return np.nan
    return pb / pa - 1.0


def taker_window(k, t, hours):
    x = k[(k.index >= t-pd.Timedelta(hours=hours)) & (k.index < t)]
    q = float(x.quote_volume.sum())
    tb = float(x.taker_buy_quote.sum())
    return (2.0*tb/q - 1.0) if q > 0 else np.nan


def range_window(k, t, hours):
    x = k[(k.index >= t-pd.Timedelta(hours=hours)) & (k.index < t)]
    if x.empty:
        return np.nan
    lo=float(x.low.min()); hi=float(x.high.max())
    return hi/lo-1.0 if lo>0 else np.nan


def feature_row(k, t):
    pre = k[k.index < t].iloc[-1]
    local = t + pd.Timedelta(hours=7)
    tue00_local = local.normalize()
    tue00 = tue00_local - pd.Timedelta(hours=7)
    mon00 = tue00 - pd.Timedelta(days=1)

    ret = {}
    for h in [1,3,6,12,24]:
        p0 = close_before(k, t-pd.Timedelta(hours=h)+pd.Timedelta(minutes=5))
        p1 = float(pre.close)
        ret[f"ret{h}h"] = p1/p0-1.0 if np.isfinite(p0) and p0 else np.nan

    mon_start = close_before(k, mon00+pd.Timedelta(minutes=5))
    mon_end = close_before(k, tue00)
    mon_ret = mon_end/mon_start-1.0 if np.isfinite(mon_start) and np.isfinite(mon_end) and mon_start else np.nan
    ov_start = close_before(k, tue00+pd.Timedelta(minutes=5))
    ov_end = float(pre.close)
    overnight_ret = ov_end/ov_start-1.0 if np.isfinite(ov_start) and ov_start else np.nan

    e20_prev = ema_before(k, t-pd.Timedelta(hours=1), "ema20")
    ema20_slope = float(pre.ema20)/e20_prev-1.0 if np.isfinite(e20_prev) and e20_prev else np.nan
    spread = float(pre.ema7)/float(pre.ema20)-1.0
    dist20 = float(pre.close)/float(pre.ema20)-1.0

    x24 = k[(k.index>=t-pd.Timedelta(hours=24))&(k.index<t)]
    lo24=float(x24.low.min()); hi24=float(x24.high.max())
    loc24=(float(pre.close)-lo24)/(hi24-lo24) if hi24>lo24 else 0.5

    f = {
        **ret,
        "mon_ret":mon_ret,
        "overnight_ret":overnight_ret,
        "ema_spread":spread,
        "dist_ema20":dist20,
        "ema20_slope1h":ema20_slope,
        "loc24":loc24,
        "range6":range_window(k,t,6),
        "range24":range_window(k,t,24),
        "taker1h":taker_window(k,t,1),
        "taker4h":taker_window(k,t,4),
    }

    # Predeclared natural binary states. No August values are used to define them.
    f.update({
        "ret1h_up": f["ret1h"] >= 0,
        "ret3h_up": f["ret3h"] >= 0,
        "ret6h_up": f["ret6h"] >= 0,
        "ret12h_up": f["ret12h"] >= 0,
        "ret24h_up": f["ret24h"] >= 0,
        "monday_up": f["mon_ret"] >= 0,
        "overnight_up": f["overnight_ret"] >= 0,
        "above_ema20": f["dist_ema20"] >= 0,
        "ema_bull": f["ema_spread"] >= 0,
        "ema20_rising": f["ema20_slope1h"] >= 0,
        "upper_half24": f["loc24"] >= 0.5,
        "taker1h_buy": f["taker1h"] >= 0,
        "taker4h_buy": f["taker4h"] >= 0,
    })
    f.update({
        "uptrend_pressure": bool(f["ret6h_up"] and f["above_ema20"] and f["ema_bull"]),
        "overnight_up_pressure": bool(f["overnight_up"] and f["above_ema20"]),
        "bearish_alignment": bool((not f["ret3h_up"]) and (not f["ema_bull"]) and (not f["taker1h_buy"])),
        "extended_down_state": bool((not f["ret6h_up"]) and (not f["ema_bull"]) and (not f["upper_half24"])),
    })
    return f


def met(df):
    if len(df)==0:
        return {"n":0,"develop_rate":None,"wr":None,"pnl":0.0,"mfe_med":None}
    return {
        "n":int(len(df)),
        "develop_rate":float(df.developed.mean()),
        "wr":float((df.a511_pnl>0).mean()),
        "pnl":float(df.a511_pnl.sum()),
        "mfe_med":float(df.mfe.median()),
    }


def natural_tables(hist, binary_cols):
    out=[]
    for feat in binary_cols:
        for skip_value in [True,False]:
            row={"feature":feat,"skip_when":bool(skip_value)}
            for name, part in [("D",hist.iloc[:DISC_N]),("V",hist.iloc[DISC_N:]),("F",hist)]:
                skip=part[part[feat]==skip_value]
                keep=part[part[feat]!=skip_value]
                row[name+"_skip"]=met(skip); row[name+"_keep"]=met(keep)
                row[name+"_delta_wait"]=float(-skip.a511_pnl.sum())
            row["robust_bad_state"] = bool(
                row["D_skip"]["n"]>=10 and row["V_skip"]["n"]>=5 and
                row["D_skip"]["pnl"]<0 and row["V_skip"]["pnl"]<0 and
                row["D_skip"]["develop_rate"] < row["D_keep"]["develop_rate"] and
                row["V_skip"]["develop_rate"] < row["V_keep"]["develop_rate"]
            )
            out.append(row)
    return out


def quartile_tables(hist):
    D=hist.iloc[:DISC_N]
    out=[]
    for feat in CONT_FEATURES:
        q25=float(D[feat].quantile(.25)); q75=float(D[feat].quantile(.75))
        for side,thr in [("LOW_Q25",q25),("HIGH_Q75",q75)]:
            row={"feature":feat,"side":side,"threshold":thr}
            for name,part in [("D",hist.iloc[:DISC_N]),("V",hist.iloc[DISC_N:]),("F",hist)]:
                mask=(part[feat]<=thr) if side=="LOW_Q25" else (part[feat]>=thr)
                skip=part[mask]; keep=part[~mask]
                row[name+"_skip"]=met(skip); row[name+"_keep"]=met(keep)
                row[name+"_delta_wait"]=float(-skip.a511_pnl.sum())
            row["robust_bad_state"] = bool(
                row["D_skip"]["n"]>=15 and row["V_skip"]["n"]>=5 and
                row["D_skip"]["pnl"]<0 and row["V_skip"]["pnl"]<0 and
                row["D_skip"]["develop_rate"] < row["D_keep"]["develop_rate"] and
                row["V_skip"]["develop_rate"] < row["V_keep"]["develop_rate"]
            )
            out.append(row)
    return out


def main():
    k=tue.load_extended()
    parity=tue.historical_parity(k)
    if not parity["pass"]:
        raise RuntimeError("Tuesday parity failed: "+json.dumps(parity,default=str))

    hes=tue.entries(k)
    hrows=[]
    for i,t in enumerate(hes):
        tr=tue.simulate_parent(k,t); lr=tue.layered(k,tr)
        f=feature_row(k,t)
        hrows.append({"i":i,"date":str((t+pd.Timedelta(hours=7)).date()),"entry_t":str(t),
                      "mfe":float(tr["mfe"]),"mae":float(tr["mae"]),"developed":bool(tr["mfe"]>=tue.HINGE),
                      "parent_pnl":float(tr["pnl"]),"a511_pnl":float(lr["a511_pnl"]),**f})
    hist=pd.DataFrame(hrows)

    binary_cols=[c for c in hist.columns if c in {
        "ret1h_up","ret3h_up","ret6h_up","ret12h_up","ret24h_up","monday_up","overnight_up",
        "above_ema20","ema_bull","ema20_rising","upper_half24","taker1h_buy","taker4h_buy",
        "uptrend_pressure","overnight_up_pressure","bearish_alignment","extended_down_state"
    }]

    nt=natural_tables(hist,binary_cols)
    qt=quartile_tables(hist)
    robust_nat=[x for x in nt if x["robust_bad_state"]]
    robust_q=[x for x in qt if x["robust_bad_state"]]

    # Rank robust diagnostics without using August: worst skipped full PnL first, then larger N.
    robust_nat=sorted(robust_nat,key=lambda x:(x["F_skip"]["pnl"],-x["F_skip"]["n"]))
    robust_q=sorted(robust_q,key=lambda x:(x["F_skip"]["pnl"],-x["F_skip"]["n"]))

    aes=tue.entries(k,pd.Timestamp("2026-08-01",tz="UTC"),pd.Timestamp("2026-08-19",tz="UTC"))
    arows=[]
    for t in aes:
        tr=tue.simulate_parent(k,t); lr=tue.layered(k,tr); f=feature_row(k,t)
        r={"date":str((t+pd.Timedelta(hours=7)).date()),"entry_t":str(t),"mfe":float(tr["mfe"]),
           "mae":float(tr["mae"]),"developed":bool(tr["mfe"]>=tue.HINGE),"parent_pnl":float(tr["pnl"]),
           "a511_pnl":float(lr["a511_pnl"]),**f}
        # Historical percentiles are descriptive only.
        for feat in CONT_FEATURES:
            vals=hist[feat].dropna().to_numpy(float)
            r[feat+"_hist_pctile"]=float((vals<=float(r[feat])).mean()) if len(vals) else np.nan
        hits=[]
        for x in robust_nat:
            if bool(r[x["feature"]])==bool(x["skip_when"]):
                hits.append("NAT:"+x["feature"]+"="+str(x["skip_when"]))
        for x in robust_q:
            v=float(r[x["feature"]])
            hit=v<=x["threshold"] if x["side"]=="LOW_Q25" else v>=x["threshold"]
            if hit:hits.append("Q:"+x["feature"]+":"+x["side"])
        r["robust_bad_gate_hits"]=" | ".join(hits); r["robust_bad_gate_count"]=len(hits)
        arows.append(r)
    aug=pd.DataFrame(arows)

    # Feature medians for developed vs nondeveloped are descriptive, not candidate fitting.
    cont_atlas=[]
    for feat in CONT_FEATURES:
        cont_atlas.append({
            "feature":feat,
            "developed_median":float(hist[hist.developed][feat].median()),
            "nondeveloped_median":float(hist[~hist.developed][feat].median()),
            "D_q25":float(hist.iloc[:DISC_N][feat].quantile(.25)),
            "D_q75":float(hist.iloc[:DISC_N][feat].quantile(.75)),
        })

    summary={
        "status":"COMPLETE_TUESDAY_AUGUST_FAILURE_FORENSICS",
        "parity":parity,
        "historical":{"n":int(len(hist)),"developed_n":int(hist.developed.sum()),"develop_rate":float(hist.developed.mean()),
                      "a511_pnl":float(hist.a511_pnl.sum()),"a511_wr":float((hist.a511_pnl>0).mean())},
        "august":{"n":int(len(aug)),"developed_n":int(aug.developed.sum()),"develop_rate":float(aug.developed.mean()),
                  "a511_pnl":float(aug.a511_pnl.sum()),"a511_wr":float((aug.a511_pnl>0).mean())},
        "robust_natural_bad_states":robust_nat,
        "robust_discovery_quartile_bad_states":robust_q,
        "continuous_atlas":cont_atlas,
        "guardrail":"Robust labels require negative skipped PnL and lower develop-rate in both D and V. V is same-sample report-only, not untouched OOS. August is not used to define feature signs or quartile thresholds. Do not deploy a new gate solely because it catches N=3 August losses; freeze any candidate and forward-test it first."
    }

    hist.to_csv(OUT/"tuesday_august_forensic_historical.csv",index=False)
    aug.to_csv(OUT/"tuesday_august_forensic_august.csv",index=False)
    (OUT/"tuesday_august_failure_forensics_summary.json").write_text(json.dumps(summary,indent=2,default=str))

    md=["# Tuesday August Failure-to-Develop Forensics","",
        "**Status: COMPLETE — forensic only; frozen A5.11 unchanged; live BBC untouched.**","",
        "## Reproduction gate",
        f"- Historical A5.11 parity: **{'PASS' if parity['pass'] else 'FAIL'}**; {parity['a511']['wins']}/{parity['a511']['n']} wins, PnL **${parity['a511']['pnl']:+.2f}**.","",
        "## Headline",
        f"- Historical +0.50% development rate: **{100*hist.developed.mean():.1f}%** ({int(hist.developed.sum())}/{len(hist)}).",
        f"- August development rate: **{100*aug.developed.mean():.1f}%** ({int(aug.developed.sum())}/{len(aug)}).",
        f"- August frozen PnL: **${aug.a511_pnl.sum():+.2f}**.","",
        "## August pre-entry state","",
        "| Date | MFE | PnL | 6h ret | Overnight | EMA spread | vs EMA20 | EMA20 1h slope | 24h loc | 24h range | Taker1h | Robust bad-state hits |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in aug.iterrows():
        md.append(f"| {r.date} | {100*r.mfe:.3f}% | ${r.a511_pnl:+.2f} | {100*r.ret6h:+.3f}% | {100*r.overnight_ret:+.3f}% | {100*r.ema_spread:+.3f}% | {100*r.dist_ema20:+.3f}% | {100*r.ema20_slope1h:+.3f}% | {r.loc24:.3f} | {100*r.range24:.3f}% | {r.taker1h:+.3f} | {int(r.robust_bad_gate_count)} |")

    md += ["","## Natural binary states that were bad in BOTH chronology slices","",
           "A state is listed only when its skipped subgroup had negative PnL and lower +0.50% development rate in both D and V.",""]
    if robust_nat:
        md += ["| WAIT state | D skip N | D dev | D PnL | V skip N | V dev | V PnL | Full skip N/PnL |",
               "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for x in robust_nat:
            md.append(f"| {x['feature']} = {x['skip_when']} | {x['D_skip']['n']} | {100*x['D_skip']['develop_rate']:.1f}% | ${x['D_skip']['pnl']:+.2f} | {x['V_skip']['n']} | {100*x['V_skip']['develop_rate']:.1f}% | ${x['V_skip']['pnl']:+.2f} | {x['F_skip']['n']} / ${x['F_skip']['pnl']:+.2f} |")
    else:
        md.append("- **None.** No predeclared natural binary state met the strict cross-slice bad-state rule.")

    md += ["","## Discovery-quartile states that were bad in BOTH chronology slices","",
           "Thresholds are Q25/Q75 from the first 83 Tuesdays only; no August tuning.",""]
    if robust_q:
        md += ["| Feature/side | Frozen D threshold | D skip N/PnL | V skip N/PnL | Full skip N/PnL |",
               "|---|---:|---:|---:|---:|"]
        for x in robust_q:
            md.append(f"| {x['feature']} {x['side']} | {x['threshold']:.6f} | {x['D_skip']['n']} / ${x['D_skip']['pnl']:+.2f} | {x['V_skip']['n']} / ${x['V_skip']['pnl']:+.2f} | {x['F_skip']['n']} / ${x['F_skip']['pnl']:+.2f} |")
    else:
        md.append("- **None.** No discovery-quartile tail met the strict cross-slice rule.")

    md += ["","## August historical percentiles","",
           "These percentiles are descriptive only; they are useful for seeing whether August was structurally unusual.",""]
    for _,r in aug.iterrows():
        md.append(f"### {r.date}")
        vals=sorted([(feat,100*r[feat+"_hist_pctile"]) for feat in CONT_FEATURES], key=lambda z:min(z[1],100-z[1]))[:6]
        md.append("- Most extreme pre-entry features: "+", ".join(f"{a} {b:.0f}th pct" for a,b in vals)+".")
        md.append(f"- Strict robust bad-state gate hits: **{int(r.robust_bad_gate_count)}**"+(f" — {r.robust_bad_gate_hits}" if r.robust_bad_gate_hits else "."))

    md += ["","## Execution interpretation","",
           "- A deployable WAIT guard must be based only on pre-entry information and should first survive D/V chronology without using August to choose its numeric threshold.",
           "- If a robust historical gate also catches August, it becomes a **candidate shadow guard**, not an immediately deployable live rule.",
           "- If no strict gate exists, the correct action is to keep Tuesday frozen and treat August as a regime warning rather than manufacture a filter from three losses.","",
           "## Guardrail",summary["guardrail"]]
    (OUT/"TUESDAY_AUGUST_FAILURE_FORENSICS.md").write_text("\n".join(md)+"\n")
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=="__main__":
    main()
