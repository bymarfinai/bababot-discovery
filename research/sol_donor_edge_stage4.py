#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.sol_donor_transplant_stage3 import (
    load5, indicators5, hourly_context, build_hour_signals,
    TP, SL, FEE
)

OUT_MD = ROOT / "SOL_DONOR_EDGE_STAGE4_Result.md"
OUT_FEATURES = ROOT / "SOL_DONOR_EDGE_STAGE4_Features.csv"
OUT_UNI = ROOT / "SOL_DONOR_EDGE_STAGE4_Univariate.csv"
OUT_PAIR = ROOT / "SOL_DONOR_EDGE_STAGE4_Pairwise.csv"
OUT_CAND = ROOT / "SOL_DONOR_EDGE_STAGE4_Candidates.csv"
OUT_STATUS = ROOT / "SOL_DONOR_EDGE_STAGE4_Status.txt"

SEARCH_A = pd.Timestamp("2023-01-01T00:00:00Z")
SEARCH_B = pd.Timestamp("2024-01-01T00:00:00Z")
VAL_A = pd.Timestamp("2024-01-01T00:00:00Z")
VAL_B = pd.Timestamp("2025-01-01T00:00:00Z")

NUMERIC_FEATURES = [
    "e_count","c_count","shock_count",
    "hour_ret","hour_range","hour_clv","rebound_from_hour_low","close_from_hour_high",
    "lower_wick_frac","upper_wick_frac",
    "ret5","ret15","ret30","rsi4_end","rsi14_end","rsi4_delta15",
    "cci14_end","cci_delta15","ema8_dist",
    "mins_since_last_shock","postshock_close_ret","postshock_rebound","postshock_mfe","postshock_mae",
    "prev1h_ret","ema20_dist","ema20_slope","vol15_vs_prev45",
]
BOOL_FEATURES = [
    "donor_e","donor_c","donor_both","hour_green","regime_ok",
    "rising_lows3","rising_closes3","close_above_prev5_high",
]


def safe_div(a,b):
    return np.nan if b == 0 or pd.isna(b) else a/b


def first_hit(x5, entry_ts, partition_end):
    idx = x5.index
    p = int(idx.searchsorted(entry_ts, side="left"))
    endp = int(idx.searchsorted(partition_end, side="left"))
    if p >= len(idx) or idx[p] != entry_ts or p >= endp:
        return None
    entry = float(x5.open.iloc[p])
    tp_px = entry*(1+TP)
    sl_px = entry*(1-SL)
    for j in range(p, endp):
        hit_tp = float(x5.high.iloc[j]) >= tp_px
        hit_sl = float(x5.low.iloc[j]) <= sl_px
        if hit_tp and hit_sl:
            return "LOSS", idx[j], -SL-FEE
        if hit_sl:
            return "LOSS", idx[j], -SL-FEE
        if hit_tp:
            return "WIN", idx[j], TP-FEE
    return None


def build_events(z5, h, hs):
    h = h.copy()
    h["ema20"] = h.close.ewm(span=20, adjust=False, min_periods=20).mean()
    h["ema20_dist"] = h.close/h.ema20 - 1.0
    h["ema20_slope"] = h.ema20/h.ema20.shift(1) - 1.0

    rows = []
    event_hours = hs.index[(hs.e | hs.c) & (hs.index >= SEARCH_A) & (hs.index < VAL_B)]
    for sh in event_hours:
        entry_ts = sh + pd.Timedelta(hours=1)
        part_end = SEARCH_B if sh < SEARCH_B else VAL_B
        if entry_ts >= part_end:
            continue
        bars = z5[(z5.index >= sh) & (z5.index < entry_ts)]
        if len(bars) != 12:
            continue
        shock = bars[bars.sig_e0v1e | bars.sig_cci]
        if shock.empty:
            continue
        out = first_hit(z5, entry_ts, part_end)
        if out is None:
            continue
        outcome, exit_ts, net = out

        o = float(bars.open.iloc[0]); c = float(bars.close.iloc[-1])
        hi = float(bars.high.max()); lo = float(bars.low.min())
        rng = hi-lo
        lower_w = (min(o,c)-lo)/rng if rng>0 else np.nan
        upper_w = (hi-max(o,c))/rng if rng>0 else np.nan
        last_shock_ts = shock.index[-1]
        last_shock_close = float(shock.close.iloc[-1])
        post = bars[bars.index >= last_shock_ts]

        prevh = h.index[h.index < sh]
        prev_ret = np.nan
        if len(prevh):
            pr = h.loc[prevh[-1]]
            prev_ret = float(pr.close/pr.open - 1.0)

        prev45 = bars.iloc[:9].volume.mean()
        last15 = bars.iloc[9:].volume.mean()

        row = {
            "signal_hour":sh,"entry_ts":entry_ts,"exit_ts":exit_ts,
            "partition":"SEARCH_2023" if sh < SEARCH_B else "INTERNAL_VAL_2024",
            "outcome":outcome,"net_return":net,
            "hold_h":(exit_ts-entry_ts).total_seconds()/3600.0,
            "donor_e":bool(hs.loc[sh,"e"]),"donor_c":bool(hs.loc[sh,"c"]),
            "donor_both":bool(hs.loc[sh,"e"] and hs.loc[sh,"c"]),
            "e_count":int(bars.sig_e0v1e.sum()),"c_count":int(bars.sig_cci.sum()),
            "shock_count":int((bars.sig_e0v1e | bars.sig_cci).sum()),
            "hour_green":bool(c>o),"regime_ok":bool(h.loc[sh,"regime_ok"]),
            "hour_ret":c/o-1.0,"hour_range":hi/lo-1.0,
            "hour_clv":(c-lo)/rng if rng>0 else np.nan,
            "rebound_from_hour_low":c/lo-1.0,
            "close_from_hour_high":c/hi-1.0,
            "lower_wick_frac":lower_w,"upper_wick_frac":upper_w,
            "ret5":c/float(bars.close.iloc[-2])-1.0,
            "ret15":c/float(bars.close.iloc[-4])-1.0,
            "ret30":c/float(bars.close.iloc[-7])-1.0,
            "rsi4_end":float(bars.rsi4.iloc[-1]),"rsi14_end":float(bars.rsi14.iloc[-1]),
            "rsi4_delta15":float(bars.rsi4.iloc[-1]-bars.rsi4.iloc[-4]),
            "cci14_end":float(bars.cci14.iloc[-1]),
            "cci_delta15":float(bars.cci14.iloc[-1]-bars.cci14.iloc[-4]),
            "ema8_dist":c/float(bars.ema8.iloc[-1])-1.0,
            "mins_since_last_shock":(entry_ts-(last_shock_ts+pd.Timedelta(minutes=5))).total_seconds()/60.0,
            "postshock_close_ret":c/last_shock_close-1.0,
            "postshock_rebound":c/float(post.low.min())-1.0,
            "postshock_mfe":float(post.high.max())/last_shock_close-1.0,
            "postshock_mae":float(post.low.min())/last_shock_close-1.0,
            "rising_lows3":bool(np.all(np.diff(bars.low.iloc[-3:].to_numpy(float))>0)),
            "rising_closes3":bool(np.all(np.diff(bars.close.iloc[-3:].to_numpy(float))>0)),
            "close_above_prev5_high":bool(c > float(bars.high.iloc[-2])),
            "prev1h_ret":prev_ret,
            "ema20_dist":float(h.loc[sh,"ema20_dist"]),
            "ema20_slope":float(h.loc[sh,"ema20_slope"]),
            "vol15_vs_prev45":safe_div(last15,prev45),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def rule_text(rule):
    if rule["kind"]=="num":
        return f"{rule['feature']} {rule['op']} {rule['threshold']:.8g}"
    return f"{rule['feature']} == {bool(rule['value'])}"


def rule_mask(df, rule):
    s = df[rule["feature"]]
    if rule["kind"]=="bool":
        return s.fillna(False).astype(bool) == bool(rule["value"])
    if rule["op"]==">=":
        return s.notna() & (s >= rule["threshold"])
    return s.notna() & (s <= rule["threshold"])


def eval_rules(df, rules, a, b):
    q = df[(df.entry_ts>=a)&(df.entry_ts<b)].copy().sort_values("entry_ts")
    if q.empty:
        return {"trades":0,"wins":0,"wr":np.nan,"tpd":0.0,"avg_net":np.nan,"net_sum":0.0}
    m = pd.Series(True,index=q.index)
    for r in rules:
        m &= rule_mask(q,r)
    q = q[m].sort_values("entry_ts")
    active_until = None
    picked = []
    for i,r in q.iterrows():
        if active_until is not None and r.entry_ts <= active_until:
            continue
        picked.append(i)
        active_until = r.exit_ts
    q = q.loc[picked] if picked else q.iloc[0:0]
    days = (b-a).total_seconds()/86400.0
    n = len(q); wins = int((q.outcome=="WIN").sum()) if n else 0
    return {
        "trades":n,"wins":wins,"wr":wins/n if n else np.nan,
        "tpd":n/days,"avg_net":float(q.net_return.mean()) if n else np.nan,
        "net_sum":float(q.net_return.sum()) if n else 0.0,
    }


def anatomy(events):
    q = events[events.partition=="SEARCH_2023"]
    rows=[]
    for f in NUMERIC_FEATURES:
        w=q[q.outcome=="WIN"][f].dropna(); l=q[q.outcome=="LOSS"][f].dropna()
        rows.append({
            "feature":f,
            "win_median":w.median() if len(w) else np.nan,
            "loss_median":l.median() if len(l) else np.nan,
            "median_gap":(w.median()-l.median()) if len(w) and len(l) else np.nan,
        })
    return pd.DataFrame(rows)


def make_univariates(events):
    search = events[(events.entry_ts>=SEARCH_A)&(events.entry_ts<SEARCH_B)]
    rules=[]
    for f in NUMERIC_FEATURES:
        vals=search[f].dropna()
        if len(vals)<100: continue
        for q in (0.20,0.35,0.50,0.65,0.80):
            t=float(vals.quantile(q))
            for op in (">=","<="):
                rules.append({"kind":"num","feature":f,"op":op,"threshold":t,"source_q":q})
    for f in BOOL_FEATURES:
        for v in (True,False):
            rules.append({"kind":"bool","feature":f,"value":v})

    out=[]
    for r in rules:
        e=eval_rules(events,[r],SEARCH_A,SEARCH_B)
        out.append({**r,"rule":rule_text(r),**e})
    return pd.DataFrame(out)


def parse_rule(row):
    if row["kind"]=="bool":
        return {"kind":"bool","feature":row["feature"],"value":bool(row["value"])}
    return {"kind":"num","feature":row["feature"],"op":row["op"],"threshold":float(row["threshold"])}


def main():
    x5, coverage = load5()
    z5 = indicators5(x5)
    h = hourly_context(x5)
    hs = build_hour_signals(z5,h)
    events = build_events(z5,h,hs)
    events.to_csv(OUT_FEATURES,index=False)

    anat=anatomy(events)
    uni=make_univariates(events)
    uni["eligible"]=(uni.trades>=250)&(uni.tpd>=1.0)
    uni=uni.sort_values(["eligible","wr","avg_net","tpd"],ascending=[False,False,False,False])
    uni.to_csv(OUT_UNI,index=False)

    top=uni[uni.eligible].head(10).copy()
    pair_rows=[]
    for i in range(len(top)):
        for j in range(i+1,len(top)):
            a=top.iloc[i]; b=top.iloc[j]
            if a.feature==b.feature:
                continue
            ra=parse_rule(a); rb=parse_rule(b)
            e=eval_rules(events,[ra,rb],SEARCH_A,SEARCH_B)
            pair_rows.append({
                "rule1":rule_text(ra),"rule2":rule_text(rb),
                "f1":ra["feature"],"f2":rb["feature"],
                "rules_json":json.dumps([ra,rb],sort_keys=True),**e
            })
    pairs=pd.DataFrame(pair_rows)
    if len(pairs):
        pairs["eligible"]=(pairs.trades>=250)&(pairs.tpd>=1.0)
        pairs=pairs.sort_values(["eligible","wr","avg_net","tpd"],ascending=[False,False,False,False])
    pairs.to_csv(OUT_PAIR,index=False)

    candidates=[]
    for _,r in uni[uni.eligible].iterrows():
        rr=parse_rule(r)
        candidates.append({"type":"UNI","rules":[rr],"search":eval_rules(events,[rr],SEARCH_A,SEARCH_B)})
    if len(pairs):
        for _,r in pairs[pairs.eligible].iterrows():
            rr=json.loads(r.rules_json)
            candidates.append({"type":"PAIR","rules":rr,"search":eval_rules(events,rr,SEARCH_A,SEARCH_B)})
    candidates=sorted(candidates,key=lambda x:(x["search"]["wr"],x["search"]["avg_net"],x["search"]["tpd"]),reverse=True)[:20]

    rows=[]
    for c in candidates:
        val=eval_rules(events,c["rules"],VAL_A,VAL_B)
        s=c["search"]
        deterioration=s["wr"]-val["wr"] if pd.notna(s["wr"]) and pd.notna(val["wr"]) else np.nan
        promote=bool(
            val["trades"]>=250 and val["tpd"]>=1.0 and
            pd.notna(val["wr"]) and val["wr"]>=0.60 and
            pd.notna(val["avg_net"]) and val["avg_net"]>0 and
            pd.notna(deterioration) and deterioration<=0.07
        )
        rows.append({
            "type":c["type"],"rule":" AND ".join(rule_text(r) for r in c["rules"]),
            "rules_json":json.dumps(c["rules"],sort_keys=True),
            "search_trades":s["trades"],"search_wr":s["wr"],"search_tpd":s["tpd"],"search_avg_net":s["avg_net"],
            "val_trades":val["trades"],"val_wr":val["wr"],"val_tpd":val["tpd"],"val_avg_net":val["avg_net"],
            "wr_deterioration":deterioration,"promote":promote,
        })
    cand=pd.DataFrame(rows)
    if len(cand):
        cand=cand.sort_values(["promote","val_wr","search_wr","val_tpd"],ascending=[False,False,False,False])
    cand.to_csv(OUT_CAND,index=False)

    promoted=cand[cand.promote] if len(cand) else pd.DataFrame()
    winner=promoted.iloc[0] if len(promoted) else None

    def pct(v):
        return "-" if pd.isna(v) else f"{100*float(v):.1f}%"
    lines=[
        "# SOL Donor Post-Shock Edge Extraction — Stage 4 Result","",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "Stage 4 used **2023 SEARCH + 2024 INTERNAL VALIDATION only**. 2025/2026 were not evaluated.","",
        "## Population","",
        f"- Labeled shock-hours: **{len(events)}**.",
        f"- SEARCH events: **{int((events.partition=='SEARCH_2023').sum())}**.",
        f"- INTERNAL VALIDATION events: **{int((events.partition=='INTERNAL_VAL_2024').sum())}**.","",
        "## Strongest raw SEARCH median separations","",
        "| Feature | Win median | Loss median | Gap |","|---|---:|---:|---:|"
    ]
    for _,r in anat.reindex(anat.median_gap.abs().sort_values(ascending=False).index).head(10).iterrows():
        lines.append(f"| {r.feature} | {r.win_median:.6g} | {r.loss_median:.6g} | {r.median_gap:.6g} |")

    lines += ["","## Top frozen candidate rules after 2024 internal validation","",
              "| Rule | 2023 trades/day | 2023 WR | 2024 trades/day | 2024 WR | 2024 avg net | Promote |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for _,r in cand.head(12).iterrows():
        lines.append(
            f"| {r.rule} | {r.search_tpd:.3f} | {pct(r.search_wr)} | "
            f"{r.val_tpd:.3f} | {pct(r.val_wr)} | {pct(r.val_avg_net)} | {'YES' if r.promote else 'NO'} |"
        )
    lines += ["","## Decision",""]
    if winner is not None:
        lines += [
            f"**Status: SOL_DONOR_EDGE_STAGE4_PROMOTED_FOR_STAGE5**","",
            f"Frozen Stage-5 candidate: **{winner.rule}**.",
            f"2023 SEARCH: {int(winner.search_trades)} trades, {winner.search_tpd:.3f}/day, WR {pct(winner.search_wr)}.",
            f"2024 INTERNAL VALIDATION: {int(winner.val_trades)} trades, {winner.val_tpd:.3f}/day, WR {pct(winner.val_wr)}, avg net {pct(winner.val_avg_net)}.",
            "",
            "No 2025/2026 result was used to choose this rule."
        ]
        OUT_STATUS.write_text("SOL_DONOR_EDGE_STAGE4_PROMOTED_FOR_STAGE5\n")
    else:
        best=cand.iloc[0] if len(cand) else None
        lines += ["**Status: SOL_DONOR_EDGE_STAGE4_NO_PROMOTABLE_EDGE**",""]
        if best is not None:
            lines += [
                f"Best internal-validation rule: **{best.rule}**.",
                f"2024: {best.val_tpd:.3f}/day, WR {pct(best.val_wr)}, avg net {pct(best.val_avg_net)}.",
            ]
        lines += ["No rule met all frozen Stage-4 frequency, WR, positive-net, and stability gates. Stage 5 should not test a donor-derived rule unless a new preregistered hypothesis is created."]
        OUT_STATUS.write_text("SOL_DONOR_EDGE_STAGE4_NO_PROMOTABLE_EDGE\n")

    OUT_MD.write_text("\n".join(lines)+"\n")


if __name__=="__main__":
    main()
