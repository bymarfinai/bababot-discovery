#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G1_GEOMETRY"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedSessionAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR_MIN = 5
BAR = pd.Timedelta(minutes=BAR_MIN)
CLOCKS = tuple(range(0, 24 * 60, 30))
REFS = (180, 240, 300, 360, 420)
EXES = (240, 300, 360, 420, 480)
SIDES = ("LONG", "SHORT")
MAJOR = ("external", "development", "reference_validation")


def hhmm(m: int) -> str:
    m %= 1440
    return f"{m//60:02d}:{m%60:02d}"


def wib(m: int) -> str:
    return hhmm(m + 7 * 60)


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = k / n
    zz = z*z
    den = 1.0 + zz/n
    center = p + zz/(2*n)
    rad = z * math.sqrt((p*(1-p) + zz/(4*n))/n)
    return (center-rad)/den


def part_for_window(rs: pd.Timestamp, ee: pd.Timestamp):
    for name, (a,z) in base.PARTS.items():
        if name == "august":
            continue
        if a <= rs and ee <= z:
            return name
    return None


def candidate_sessions(idx: pd.DatetimeIndex, clock: int, ref_min: int, exe_min: int, wanted_part: str):
    anchors = pd.date_range(base.START.normalize(), base.END.normalize(), freq="D", tz="UTC")
    rs = anchors + pd.Timedelta(minutes=clock)
    re = rs + pd.Timedelta(minutes=ref_min)
    ee = re + pd.Timedelta(minutes=exe_min)

    keep = np.array([t.weekday() < 5 for t in re], dtype=bool)
    pa,pz = base.PARTS[wanted_part]
    keep &= np.array([(a >= pa and z <= pz) for a,z in zip(rs,ee)], dtype=bool)
    keep &= np.array([z <= base.END for z in ee], dtype=bool)
    rs = rs[keep]; re = re[keep]; ee = ee[keep]
    if len(rs) == 0:
        return pd.DataFrame(columns=["rs","re","ee","start_pos"])

    starts = idx.get_indexer(rs)
    lasts = idx.get_indexer(ee - BAR)
    nbar = (ref_min + exe_min)//BAR_MIN
    complete = (starts >= 0) & (lasts >= 0) & (lasts == starts + nbar - 1)
    return pd.DataFrame({"rs":rs[complete],"re":re[complete],"ee":ee[complete],"start_pos":starts[complete]})


def first_true_index(mask: np.ndarray) -> np.ndarray:
    # mask shape N x M. Return M when never true.
    if mask.shape[1] == 0:
        return np.full(mask.shape[0], 0, dtype=int)
    any_ = mask.any(axis=1)
    out = np.argmax(mask, axis=1).astype(int)
    out[~any_] = mask.shape[1]
    return out


def analyze_geometry(x5: pd.DataFrame, clock: int, ref_min: int, exe_min: int, part: str, return_audit: bool=False):
    idx = x5.index
    sess = candidate_sessions(idx, clock, ref_min, exe_min, part)
    n = len(sess)
    if n == 0:
        empty = {s: pd.DataFrame() for s in SIDES}
        return empty if return_audit else {s: summary_empty(clock,ref_min,exe_min,s,part,0) for s in SIDES}

    o = x5.open.to_numpy(float)
    h = x5.high.to_numpy(float)
    l = x5.low.to_numpy(float)
    c = x5.close.to_numpy(float)
    ref_n = ref_min//BAR_MIN
    exe_n = exe_min//BAR_MIN
    starts = sess.start_pos.to_numpy(int)

    ref_ix = starts[:,None] + np.arange(ref_n)[None,:]
    exe_ix = starts[:,None] + ref_n + np.arange(exe_n)[None,:]
    H = h[ref_ix].max(axis=1)
    L = l[ref_ix].min(axis=1)
    if not np.all(H > L):
        raise AssertionError("invalid H/L")

    eh, el, ec = h[exe_ix], l[exe_ix], c[exe_ix]
    strict_up = ec > H[:,None]
    strict_dn = ec < L[:,None]
    hit_hi = (eh >= H[:,None]) & (ec <= H[:,None])
    hit_lo = (el <= L[:,None]) & (ec >= L[:,None])
    both = hit_hi & hit_lo

    pre_break = strict_up | strict_dn
    # First decisive pre-signal event. Signal only if the earliest event is the side touch alone.
    first_break = first_true_index(pre_break)
    first_hi = first_true_index(hit_hi & ~both)
    first_lo = first_true_index(hit_lo & ~both)
    first_both = first_true_index(both)

    out = {}
    audits = {}
    for side in SIDES:
        if side == "LONG":
            first_side, first_opp = first_hi, first_lo
            target_mask, opp_mask = strict_up, strict_dn
        else:
            first_side, first_opp = first_lo, first_hi
            target_mask, opp_mask = strict_dn, strict_up

        sig = (first_side < first_opp) & (first_side < first_break) & (first_side < first_both) & (first_side < exe_n)
        sig_idx = first_side.copy()
        rows = np.arange(n)[:,None]
        bar_ix = np.arange(exe_n)[None,:]
        after = bar_ix > sig_idx[:,None]
        t_idx = first_true_index(target_mask & after)
        o_idx = first_true_index(opp_mask & after)
        a_idx = first_true_index(both & after)
        first_term = np.minimum(np.minimum(t_idx,o_idx),a_idx)
        target = sig & (t_idx == first_term) & (t_idx < exe_n)
        opposite = sig & (o_idx == first_term) & (o_idx < exe_n)
        ambiguous = sig & (a_idx == first_term) & (a_idx < exe_n)
        no_break = sig & ~(target | opposite | ambiguous)
        minutes = np.where(target, (t_idx - sig_idx) * BAR_MIN, np.nan)

        if return_audit:
            term = np.full(n, "NO_SIGNAL", dtype=object)
            term[sig & no_break] = "NO_BREAK"
            term[target] = "SAME_SIDE"
            term[opposite] = "OPPOSITE"
            term[ambiguous] = "AMBIGUOUS"
            signal_ts = pd.Series(pd.NaT, index=np.arange(n), dtype="datetime64[ns, UTC]")
            target_ts = pd.Series(pd.NaT, index=np.arange(n), dtype="datetime64[ns, UTC]")
            sig_rows = np.where(sig)[0]
            if len(sig_rows):
                signal_ts.iloc[sig_rows] = idx[exe_ix[sig_rows, sig_idx[sig_rows]]] + BAR
            tar_rows = np.where(target)[0]
            if len(tar_rows):
                target_ts.iloc[tar_rows] = idx[exe_ix[tar_rows, t_idx[tar_rows]]] + BAR
            audits[side] = pd.DataFrame({
                "partition":part,
                "side":side,
                "clock_start_min_utc":clock,
                "reference_min":ref_min,
                "execution_min":exe_min,
                "reference_start":sess.rs,
                "execution_start":sess.re,
                "execution_end":sess.ee,
                "H":H,"L":L,"R":H-L,
                "signal":sig,
                "signal_ts":signal_ts,
                "terminal":term,
                "target_ts":target_ts,
                "minutes_to_target":minutes,
            })
        else:
            out[side] = summarize_arrays(clock,ref_min,exe_min,side,part,sess.re,sig,target,opposite,ambiguous,no_break,minutes)

    return audits if return_audit else out


def summary_empty(clock,ref_min,exe_min,side,part,complete):
    return {
        "partition":part,"side":side,"clock_start_min_utc":clock,
        "reference_min":ref_min,"execution_min":exe_min,"complete_sessions":complete,
        "signals":0,"signal_rate":np.nan,"same_side":0,"opposite":0,"ambiguous":0,"no_break":0,
        "continuation_rate":np.nan,"resolved_same_side_rate":np.nan,"wilson_lb95":np.nan,
        "median_minutes_to_target":np.nan,
        "block1_n":0,"block1_cont":np.nan,"block1_resolved":np.nan,
        "block2_n":0,"block2_cont":np.nan,"block2_resolved":np.nan,
        "block3_n":0,"block3_cont":np.nan,"block3_resolved":np.nan,
        "block4_n":0,"block4_cont":np.nan,"block4_resolved":np.nan,
        "positive_blocks":0,"min_qualified_block_cont":np.nan,
    }


def summarize_arrays(clock,ref_min,exe_min,side,part,execution_starts,sig,target,opposite,ambiguous,no_break,minutes):
    n_complete = len(sig)
    sn = int(sig.sum())
    tn = int(target.sum()); on = int(opposite.sum()); an=int(ambiguous.sum()); nn=int(no_break.sum())
    row = summary_empty(clock,ref_min,exe_min,side,part,n_complete)
    row.update({
        "signals":sn,
        "signal_rate":sn/n_complete if n_complete else np.nan,
        "same_side":tn,"opposite":on,"ambiguous":an,"no_break":nn,
        "continuation_rate":tn/sn if sn else np.nan,
        "resolved_same_side_rate":tn/(tn+on) if (tn+on) else np.nan,
        "wilson_lb95":wilson_lb(tn,sn),
        "median_minutes_to_target":float(np.nanmedian(minutes[target])) if tn else np.nan,
    })

    if part == "development":
        blocks = np.array_split(np.arange(n_complete),4)
        positive = 0; qualified_conts=[]
        for bi,ix in enumerate(blocks,1):
            bsig = sig[ix]; btar=target[ix]; bopp=opposite[ix]
            bn=int(bsig.sum()); bt=int(btar.sum()); bo=int(bopp.sum())
            cont=bt/bn if bn else np.nan
            resolved=bt/(bt+bo) if (bt+bo) else np.nan
            row[f"block{bi}_n"] = bn
            row[f"block{bi}_cont"] = cont
            row[f"block{bi}_resolved"] = resolved
            if bn >= 15:
                qualified_conts.append(cont)
                if cont >= .68 and resolved >= .75:
                    positive += 1
        row["positive_blocks"] = positive
        row["min_qualified_block_cont"] = min(qualified_conts) if qualified_conts else np.nan
    return row


def dev_scan(x5):
    rows=[]
    total=0
    for clock in CLOCKS:
        for ref_min in REFS:
            for exe_min in EXES:
                res=analyze_geometry(x5,clock,ref_min,exe_min,"development",False)
                for side in SIDES:
                    rows.append(res[side]); total += 1
    D=pd.DataFrame(rows)
    if total != 2400:
        raise AssertionError(f"expected 2400 directional candidates, got {total}")
    return D


def neighbor_keys(r):
    keys=[]
    c=int(r.clock_start_min_utc); ref=int(r.reference_min); exe=int(r.execution_min); side=r.side
    keys.append(((c-30)%1440,ref,exe,side)); keys.append(((c+30)%1440,ref,exe,side))
    if ref-60 in REFS: keys.append((c,ref-60,exe,side))
    if ref+60 in REFS: keys.append((c,ref+60,exe,side))
    if exe-60 in EXES: keys.append((c,ref,exe-60,side))
    if exe+60 in EXES: keys.append((c,ref,exe+60,side))
    return keys


def build_leaderboard(D):
    D=D.copy()
    D["dev_gate"]=(
        (D.signals>=80)&(D.continuation_rate>=.75)&(D.resolved_same_side_rate>=.80)&
        (D.wilson_lb95>=.65)&(D.positive_blocks>=3)
    )
    lookup={(int(r.clock_start_min_utc),int(r.reference_min),int(r.execution_min),r.side):r for r in D.itertuples(index=False)}
    n_av=[]; n_sup=[]; stable=[]
    for r in D.itertuples(index=False):
        keys=neighbor_keys(r); support=0
        for k in keys:
            x=lookup[k]
            if int(x.signals)>=60 and float(x.continuation_rate)>=.70 and float(x.resolved_same_side_rate)>=.77:
                support += 1
        nav=len(keys)
        need=max(2,math.ceil(.60*nav))
        if nav>=5: need=max(3,need)
        n_av.append(nav); n_sup.append(support); stable.append(support>=need)
    D["neighbors_available"]=n_av; D["neighbors_supportive"]=n_sup; D["local_stable"]=stable
    D["candidate_eligible"]=D.dev_gate & D.local_stable
    D["total_span_min"]=D.reference_min + D.execution_min
    D["side_tie"]=D.side.map({"LONG":0,"SHORT":1})
    C=D[D.candidate_eligible].copy()
    C=C.sort_values(
        ["wilson_lb95","min_qualified_block_cont","continuation_rate","resolved_same_side_rate","signals","median_minutes_to_target","total_span_min","clock_start_min_utc","reference_min","execution_min","side_tie"],
        ascending=[False,False,False,False,False,True,True,True,True,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def holdout_scan_selected(x5,sel):
    rows=[]; audits=[]; all_ok=True
    for part in ("external","reference_validation"):
        res=analyze_geometry(x5,int(sel.clock_start_min_utc),int(sel.reference_min),int(sel.execution_min),part,False)[sel.side]
        ok=(
            int(res["signals"])>=40 and float(res["continuation_rate"])>=.70 and
            float(res["resolved_same_side_rate"])>=.78 and int(res["same_side"])>int(res["opposite"]) and
            float(res["wilson_lb95"])>=.58
        )
        res["replication_pass"]=bool(ok); rows.append(res); all_ok=all_ok and bool(ok)
        A=analyze_geometry(x5,int(sel.clock_start_min_utc),int(sel.reference_min),int(sel.execution_min),part,True)[sel.side]
        audits.append(A)
    Adev=analyze_geometry(x5,int(sel.clock_start_min_utc),int(sel.reference_min),int(sel.execution_min),"development",True)[sel.side]
    audits.insert(1,Adev)
    return pd.DataFrame(rows),pd.concat(audits,ignore_index=True),all_ok


def pct(x): return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")

    D=dev_scan(x5)
    D2,C=build_leaderboard(D)
    D2.to_csv(OUT_DEV,index=False)
    C.to_csv(OUT_LEADER,index=False)

    if len(C)==0:
        status="ETH_DISCOVERY2_RESET_G1_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status+"\n")
        lines=["# ETH Discovery 2 Reset — G1 Pair-Native Geometry Result","",f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.","Scanned **1,200** coarse geometries × **2 directions** = **2,400** Development candidates.","","No candidate passed the preregistered Development + local-stability gates.","",f"**Status: {status}**"]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]
    H,A,supported=holdout_scan_selected(x5,sel)
    H.to_csv(OUT_OOS,index=False); A.to_csv(OUT_AUDIT,index=False)
    status="ETH_DISCOVERY2_RESET_G1_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G1_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# ETH Discovery 2 Reset — G1 Pair-Native Geometry Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Scanned **1,200** coarse geometries × **2 directions** = **2,400** Development candidates.",
        "No prior ETH clock/duration/side was privileged in selection.","",
        "## Development-selected geometry","",
        f"**{sel.side} / reference start {hhmm(int(sel.clock_start_min_utc))} UTC ({wib(int(sel.clock_start_min_utc))} WIB) / reference {int(sel.reference_min)}m / execution {int(sel.execution_min)}m**","",
        f"Execution starts {hhmm(int(sel.clock_start_min_utc)+int(sel.reference_min))} UTC ({wib(int(sel.clock_start_min_utc)+int(sel.reference_min))} WIB).",
        f"Signals **{int(sel.signals)}**; continuation **{pct(sel.continuation_rate)}**; resolved same-side **{pct(sel.resolved_same_side_rate)}**; Wilson LB **{pct(sel.wilson_lb95)}**.",
        f"Median signal→continuation **{float(sel.median_minutes_to_target):.0f}m**; stable neighbors **{int(sel.neighbors_supportive)}/{int(sel.neighbors_available)}**; positive Development blocks **{int(sel.positive_blocks)}/4**.","",
        "Development blocks:","",
        "| Block | Signals | Continuation | Resolved |","|---:|---:|---:|---:|"
    ]
    for b in range(1,5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {pct(sel[f'block{b}_cont'])} | {pct(sel[f'block{b}_resolved'])} |")
    lines += ["","## Historical replication","","| Partition | Signals | Continuation | Resolved | Wilson LB | Same/Opp | Gate |","|---|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.same_side)}/{int(r.opposite)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += ["","## Top Development candidates","","| # | Side | Ref start UTC | Ref m | Exe m | Signals | Cont. | Resolved | Wilson | Neigh. | Blocks |","|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in C.head(15).iterrows():
        lines.append(f"| {int(r.dev_rank)} | {r.side} | {hhmm(int(r.clock_start_min_utc))} | {int(r.reference_min)} | {int(r.execution_min)} | {int(r.signals)} | {pct(r.continuation_rate)} | {pct(r.resolved_same_side_rate)} | {pct(r.wilson_lb95)} | {int(r.neighbors_supportive)}/{int(r.neighbors_available)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","G1 validates geometry/side only. Previous Z2/Z3 structure and Z5 L06 entry are not promoted automatically.","Research/shadow only. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())

if __name__=="__main__":
    main()
