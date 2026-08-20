#!/usr/bin/env python3
"""BTC H1 AMD + FVG AMD1.

Frozen before result:
- 3H accumulation immediately before Asia/London/New York session OPEN
- first session 1H candle only = manipulation candidate
- exact FVG triplet = manipulation + next two 1H candles
- decision timeframe 1H only
- compare AMD baseline vs AMD+FVG
- external 2020-2021, reference 2022-2026-07-30, August post-cutoff
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_h1_low_reject_structure_lr1 as dataio

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_AMD_FVG_AMD1_Result.md"
OUT_JSON = ROOT / "BTC_H1_AMD_FVG_AMD1_Result.json"
OUT_EVENTS = ROOT / "BTC_H1_AMD_FVG_AMD1_Events.csv"
OUT_AUG = ROOT / "BTC_H1_AMD_FVG_AMD1_August.csv"

EXTERNAL_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_START = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")

SESSIONS = {
    0: ("ASIA_OPEN", "07:00"),
    7: ("LONDON_OPEN", "14:00"),
    13: ("NEW_YORK_OPEN", "20:00"),
}
FEE = 0.0015
NOTIONAL = 500.0


def signed_ret(direction: str, entry: float, final: float) -> float:
    raw = final / entry - 1.0
    return raw if direction == "LONG" else -raw


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i in range(3, len(x) - 10):
        cur = x.iloc[i]
        ts = pd.Timestamp(cur.ts)
        if int(ts.hour) not in SESSIONS:
            continue
        prior = x.iloc[i-3:i]
        expected_prior = [ts - pd.Timedelta(hours=h) for h in (3, 2, 1)]
        if list(prior.ts) != expected_prior:
            continue
        # Need exact continuity through baseline/FVG diagnostics and 6H executions.
        ok = True
        for j in range(1, 10):
            if pd.Timestamp(x.ts.iloc[i+j]) != ts + pd.Timedelta(hours=j):
                ok = False
                break
        if not ok:
            continue

        acc_high = float(prior.high.max())
        acc_low = float(prior.low.min())
        if acc_high <= acc_low:
            continue

        ch, cl, cc = float(cur.high), float(cur.low), float(cur.close)
        high_manip = ch > acc_high and cl >= acc_low and acc_low <= cc <= acc_high
        low_manip = cl < acc_low and ch <= acc_high and acc_low <= cc <= acc_high
        if high_manip == low_manip:  # neither or both (both impossible under side guards, kept explicit)
            continue

        if high_manip:
            side = "SHORT"
            manip_side = "HIGH_SWEEP"
        else:
            side = "LONG"
            manip_side = "LOW_SWEEP"

        d = x.iloc[i+1]
        c3 = x.iloc[i+2]
        if side == "SHORT":
            displacement_ok = float(d.close) < float(d.open)
            fvg = displacement_ok and float(c3.high) < float(cur.low)
            fvg_low = float(c3.high) if fvg else np.nan
            fvg_high = float(cur.low) if fvg else np.nan
        else:
            displacement_ok = float(d.close) > float(d.open)
            fvg = displacement_ok and float(c3.low) > float(cur.high)
            fvg_low = float(cur.high) if fvg else np.nan
            fvg_high = float(c3.low) if fvg else np.nan

        session, wib = SESSIONS[int(ts.hour)]

        # Baseline AMD entry: next H1 open after manipulation closes.
        be_idx = i + 1
        be = float(x.open.iloc[be_idx])
        b1 = signed_ret(side, be, float(x.close.iloc[be_idx]))
        b3 = signed_ret(side, be, float(x.close.iloc[be_idx+2]))

        # AMD+FVG entry only after third triplet candle has closed.
        fe_idx = i + 3
        fe = float(x.open.iloc[fe_idx])
        f1 = signed_ret(side, fe, float(x.close.iloc[fe_idx])) if fvg else np.nan
        f3 = signed_ret(side, fe, float(x.close.iloc[fe_idx+2])) if fvg else np.nan

        rows.append({
            "event_ts": ts,
            "utc_date": ts.strftime("%Y-%m-%d"),
            "session": session,
            "session_wib": wib,
            "side": side,
            "manip_side": manip_side,
            "acc_high": acc_high,
            "acc_low": acc_low,
            "manip_open": float(cur.open),
            "manip_high": ch,
            "manip_low": cl,
            "manip_close": cc,
            "displacement_ok": bool(displacement_ok),
            "fvg": bool(fvg),
            "fvg_low": fvg_low,
            "fvg_high": fvg_high,
            "baseline_entry_idx": be_idx,
            "baseline_entry_ts": pd.Timestamp(x.ts.iloc[be_idx]),
            "baseline_entry": be,
            "baseline_signed1h": b1,
            "baseline_signed3h": b3,
            "fvg_entry_idx": fe_idx if fvg else np.nan,
            "fvg_entry_ts": pd.Timestamp(x.ts.iloc[fe_idx]) if fvg else pd.NaT,
            "fvg_entry": fe if fvg else np.nan,
            "fvg_signed1h": f1,
            "fvg_signed3h": f3,
        })
    return pd.DataFrame(rows)


def dir_stats(z: pd.DataFrame, cohort: str) -> dict:
    if z.empty:
        return {"n": 0, "pos1h": None, "pos3h": None, "avg3h": None, "median3h": None}
    if cohort == "baseline":
        a = z.baseline_signed1h.astype(float)
        b = z.baseline_signed3h.astype(float)
    else:
        z = z[z.fvg].copy()
        if z.empty:
            return {"n": 0, "pos1h": None, "pos3h": None, "avg3h": None, "median3h": None}
        a = z.fvg_signed1h.astype(float)
        b = z.fvg_signed3h.astype(float)
    return {
        "n": int(len(z)),
        "pos1h": float((a > 0).mean()),
        "pos3h": float((b > 0).mean()),
        "avg3h": float(b.mean()),
        "median3h": float(b.median()),
    }


def execution_rows(x: pd.DataFrame, z: pd.DataFrame, cohort: str) -> pd.DataFrame:
    rows = []
    if cohort == "fvg":
        z = z[z.fvg].copy()
    for _, r in z.iterrows():
        side = str(r.side)
        if cohort == "baseline":
            idx = int(r.baseline_entry_idx)
            entry = float(r.baseline_entry)
        else:
            idx = int(r.fvg_entry_idx)
            entry = float(r.fvg_entry)

        if side == "LONG":
            sl = float(r.manip_low)
            if entry <= sl:
                valid = False
            else:
                valid = True
                risk = (entry - sl) / entry
                target_dist = risk + 2.0 * FEE
                tp = entry * (1.0 + target_dist)
        else:
            sl = float(r.manip_high)
            if entry >= sl:
                valid = False
            else:
                valid = True
                risk = (sl - entry) / entry
                target_dist = risk + 2.0 * FEE
                tp = entry * (1.0 - target_dist)

        if not valid or risk <= 0 or target_dist <= 0:
            rows.append({"event_ts": r.event_ts, "session": r.session, "side": side, "valid": False})
            continue

        f = x.iloc[idx:idx+6]
        if len(f) != 6 or pd.Timestamp(f.ts.iloc[-1]) != pd.Timestamp(x.ts.iloc[idx]) + pd.Timedelta(hours=5):
            continue

        if side == "LONG":
            tp_hits = np.flatnonzero(f.high.to_numpy(float) >= tp)
            sl_hits = np.flatnonzero(f.low.to_numpy(float) <= sl)
        else:
            tp_hits = np.flatnonzero(f.low.to_numpy(float) <= tp)
            sl_hits = np.flatnonzero(f.high.to_numpy(float) >= sl)
        ti = int(tp_hits[0]) if tp_hits.size else 10**9
        si = int(sl_hits[0]) if sl_hits.size else 10**9
        if si <= ti:
            outcome = "SL"
            raw = -risk
        elif ti < 10**9:
            outcome = "TP"
            raw = target_dist
        else:
            outcome = "TIME"
            raw_dir = float(f.close.iloc[-1]) / entry - 1.0
            raw = raw_dir if side == "LONG" else -raw_dir
        net = raw - FEE
        rows.append({
            "event_ts": r.event_ts,
            "session": r.session,
            "side": side,
            "valid": True,
            "outcome": outcome,
            "risk": risk,
            "target_dist": target_dist,
            "net_ret": net,
            "pnl": net * NOTIONAL,
        })
    return pd.DataFrame(rows)


def exec_stats(e: pd.DataFrame) -> dict:
    if e.empty:
        return {"n":0,"invalid":0,"tp":0,"sl":0,"time":0,"wr":None,"pnl":0.0,"expectancy":None,"median_risk":None}
    invalid = int((e.valid == False).sum()) if "valid" in e.columns else 0
    q = e[e.valid == True].copy() if "valid" in e.columns else e.copy()
    if q.empty:
        return {"n":0,"invalid":invalid,"tp":0,"sl":0,"time":0,"wr":None,"pnl":0.0,"expectancy":None,"median_risk":None}
    dec = q[q.outcome.isin(["TP","SL"])]
    return {
        "n": int(len(q)),
        "invalid": invalid,
        "tp": int((q.outcome == "TP").sum()),
        "sl": int((q.outcome == "SL").sum()),
        "time": int((q.outcome == "TIME").sum()),
        "wr": float((dec.outcome == "TP").mean()) if len(dec) else None,
        "pnl": float(q.pnl.sum()),
        "expectancy": float(q.pnl.mean()),
        "median_risk": float(q.risk.median()),
    }


def pct(v):
    return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{100*v:.2f}%"


def money(v):
    return f"${v:+.2f}"


def chronological_blocks(z: pd.DataFrame, cohort: str) -> list[dict]:
    if cohort == "fvg":
        z = z[z.fvg].copy()
    z = z.sort_values("event_ts").reset_index(drop=True)
    if z.empty:
        return []
    bounds = np.linspace(0, len(z), 5, dtype=int)
    out=[]
    for j in range(4):
        q=z.iloc[bounds[j]:bounds[j+1]]
        s=dir_stats(q, cohort)
        out.append({"block":f"B{j+1}", **s})
    return out


def slice_stats(x: pd.DataFrame, z: pd.DataFrame) -> dict:
    out={}
    for cohort in ("baseline","fvg"):
        out[cohort]={
            "direction":dir_stats(z,cohort),
            "execution":exec_stats(execution_rows(x,z,cohort)),
        }
    return out


def main():
    x=dataio.load_1h()
    ev=build_events(x)
    if ev.empty:
        raise RuntimeError("no AMD events")

    external=ev[(ev.event_ts>=EXTERNAL_START)&(ev.event_ts<EXTERNAL_END)].copy()
    reference=ev[(ev.event_ts>=REFERENCE_START)&(ev.event_ts<REFERENCE_END)].sort_values("event_ts").copy()
    august=ev[(ev.event_ts>=AUG_START)&(ev.event_ts<AUG_END)].copy()
    if len(reference) < 50:
        raise RuntimeError(f"reference unexpectedly small: {len(reference)}")
    cut_idx=max(1,min(len(reference)-1,int(math.floor(len(reference)*0.70))))
    cut_ts=pd.Timestamp(reference.iloc[cut_idx].event_ts)
    dev=reference[reference.event_ts<cut_ts].copy()
    val=reference[reference.event_ts>=cut_ts].copy()

    ev.to_csv(OUT_EVENTS,index=False)
    august.to_csv(OUT_AUG,index=False)

    partitions={"development":dev,"reference_validation":val,"external":external,"august":august}
    summary={k:slice_stats(x,v) for k,v in partitions.items()}

    # Side and session matrices.
    matrix=[]
    for part,z in partitions.items():
        for side in ("LONG","SHORT"):
            for session in ("ALL","ASIA_OPEN","LONDON_OPEN","NEW_YORK_OPEN"):
                q=z[z.side==side].copy()
                if session!="ALL": q=q[q.session==session]
                b=dir_stats(q,"baseline"); f=dir_stats(q,"fvg")
                be=exec_stats(execution_rows(x,q,"baseline")); fe=exec_stats(execution_rows(x,q,"fvg"))
                matrix.append({
                    "partition":part,"side":side,"session":session,
                    "baseline_n":b["n"],"baseline_pos3h":b["pos3h"],
                    "fvg_n":f["n"],"fvg_pos3h":f["pos3h"],
                    "conversion":(f["n"]/b["n"] if b["n"] else None),
                    "uplift":((f["pos3h"]-b["pos3h"]) if f["pos3h"] is not None and b["pos3h"] is not None else None),
                    "fvg_exec_n":fe["n"],"fvg_exec_wr":fe["wr"],"fvg_exec_pnl":fe["pnl"],
                })

    ext_blocks=chronological_blocks(external,"fvg")

    def support_for(side=None, session=None):
        def filt(z):
            q=z
            if side is not None:q=q[q.side==side]
            if session is not None:q=q[q.session==session]
            return q
        v=filt(val); e=filt(external)
        vb=dir_stats(v,"baseline"); vf=dir_stats(v,"fvg")
        eb=dir_stats(e,"baseline"); ef=dir_stats(e,"fvg")
        blocks=chronological_blocks(e,"fvg")
        block_support=sum(1 for b in blocks if b["n"]>=8 and b["pos3h"] is not None and b["pos3h"]>=.60)
        direction=bool(vf["n"]>=25 and vf["pos3h"] is not None and vf["pos3h"]>=.65 and ef["n"]>=40 and ef["pos3h"] is not None and ef["pos3h"]>=.65 and (vf["pos3h"]-vb["pos3h"]>=.05) and (ef["pos3h"]-eb["pos3h"]>=.05) and block_support>=3)
        block80=sum(1 for b in blocks if b["n"]>=5 and b["pos3h"] is not None and b["pos3h"]>=.70)
        c80=bool(vf["n"]>=20 and vf["pos3h"] is not None and vf["pos3h"]>=.80 and ef["n"]>=30 and ef["pos3h"] is not None and ef["pos3h"]>=.80 and block80>=3)
        ve=exec_stats(execution_rows(x,v,"fvg")); ee=exec_stats(execution_rows(x,e,"fvg"))
        execution=bool(ve["n"]>0 and ee["n"]>0 and ve["wr"] is not None and ee["wr"] is not None and ve["wr"]>.50 and ee["wr"]>.50 and ve["pnl"]>0 and ee["pnl"]>0 and ve["expectancy"]>0 and ee["expectancy"]>0)
        return direction,c80,execution

    candidates=[(None,None),("LONG",None),("SHORT",None)]
    candidates += [(s,se) for s in ("LONG","SHORT") for se in ("ASIA_OPEN","LONDON_OPEN","NEW_YORK_OPEN")]
    gates=[support_for(s,se) for s,se in candidates]
    direction_supported=any(g[0] for g in gates)
    cand80=any(g[1] for g in gates)
    execution_supported=any(g[2] for g in gates)

    result={
        "protocol":"BTC_H1_AMD_FVG_AMD1",
        "coverage":{"first":str(x.ts.min()),"last":str(x.ts.max()),"rows1h":int(len(x))},
        "counts":{"all":int(len(ev)),"reference":int(len(reference)),"development":int(len(dev)),"reference_validation":int(len(val)),"external":int(len(external)),"august":int(len(august)),"fvg_all":int(ev.fvg.sum())},
        "reference_cut_ts":str(cut_ts),
        "summary":summary,
        "matrix":matrix,
        "external_fvg_blocks":ext_blocks,
        "AMD1_FVG_DIRECTION_SUPPORTED":direction_supported,
        "AMD1_80_CANDIDATE":cand80,
        "AMD1_EXECUTION_SUPPORTED":execution_supported,
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+"\n")

    md=[
        "# BTC H1 AMD + FVG AMD1 — Result","",
        "1H-only causal sequence: 3H accumulation before fixed session open -> first session candle manipulation sweep/reclaim -> exact manipulation+2-bar opposite FVG -> next1H entry. No later FVG search or threshold filters.","",
        f"Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**. Manipulation events **{len(ev):,}**; exact FVG confirmations **{int(ev.fvg.sum()):,}** ({100*ev.fvg.mean():.2f}% conversion). Reference cut **{cut_ts}**.","",
        "## Aggregate AMD baseline vs AMD+FVG","",
        "| Partition | Cohort | N | +1H | +3H | Avg3H | Net1:1 N/WR | PnL | Exp/trade | Median risk |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for part in ("development","reference_validation","external","august"):
        for cohort in ("baseline","fvg"):
            d=summary[part][cohort]["direction"]; e=summary[part][cohort]["execution"]
            md.append(f"| {part} | {cohort.upper()} | {d['n']} | {pct(d['pos1h'])} | {pct(d['pos3h'])} | {pct(d['avg3h'])} | {e['n']}/{pct(e['wr'])} | {money(e['pnl'])} | {('-' if e['expectancy'] is None else money(e['expectancy']))} | {pct(e['median_risk'])} |")

    md += ["","## Fixed side/session cells — reference validation","","| Side | Session | AMD N/+3H | AMD+FVG N/+3H | FVG conversion | Uplift | FVG net1:1 N/WR/PnL |","|---|---|---:|---:|---:|---:|---:|"]
    for r in matrix:
        if r["partition"]!="reference_validation" or r["session"]=="ALL": continue
        md.append(f"| {r['side']} | {r['session']} | {r['baseline_n']}/{pct(r['baseline_pos3h'])} | {r['fvg_n']}/{pct(r['fvg_pos3h'])} | {pct(r['conversion'])} | {pct(r['uplift'])} | {r['fvg_exec_n']}/{pct(r['fvg_exec_wr'])}/{money(r['fvg_exec_pnl'])} |")

    md += ["","## Fixed side/session cells — external 2020-2021","","| Side | Session | AMD N/+3H | AMD+FVG N/+3H | FVG conversion | Uplift | FVG net1:1 N/WR/PnL |","|---|---|---:|---:|---:|---:|---:|"]
    for r in matrix:
        if r["partition"]!="external" or r["session"]=="ALL": continue
        md.append(f"| {r['side']} | {r['session']} | {r['baseline_n']}/{pct(r['baseline_pos3h'])} | {r['fvg_n']}/{pct(r['fvg_pos3h'])} | {pct(r['conversion'])} | {pct(r['uplift'])} | {r['fvg_exec_n']}/{pct(r['fvg_exec_wr'])}/{money(r['fvg_exec_pnl'])} |")

    md += ["","## External AMD+FVG chronological blocks","","| Block | N | +1H | +3H | Avg3H |","|---|---:|---:|---:|---:|"]
    for b in ext_blocks:
        md.append(f"| {b['block']} | {b['n']} | {pct(b['pos1h'])} | {pct(b['pos3h'])} | {pct(b['avg3h'])} |")

    md += ["","## Verdicts","",f"**AMD1_FVG_DIRECTION_SUPPORTED: {'PASS' if direction_supported else 'FAIL'}**",f"**AMD1_80_CANDIDATE: {'PASS' if cand80 else 'FAIL'}**",f"**AMD1_EXECUTION_SUPPORTED: {'PASS' if execution_supported else 'FAIL'}**","","No session, side, accumulation length, later FVG, FVG-size, or execution parameter is reselected after result."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(OUT_MD.read_text())


if __name__=="__main__":
    main()
