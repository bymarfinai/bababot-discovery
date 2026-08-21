#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import btc_h1_amd_fvg_amd1 as amd1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H4_AMD_FVG_PathMap_H4P1_Result.md"
OUT_JSON = ROOT / "BTC_H4_AMD_FVG_PathMap_H4P1_Result.json"
OUT_EVENTS = ROOT / "BTC_H4_AMD_FVG_PathMap_H4P1_Events.csv"
OUT_AUG = ROOT / "BTC_H4_AMD_FVG_PathMap_H4P1_August.csv"

EXT0 = pd.Timestamp("2020-01-01T00:00:00Z")
EXT1 = pd.Timestamp("2022-01-01T00:00:00Z")
DEV0 = pd.Timestamp("2022-01-01T00:00:00Z")
CUT = pd.Timestamp("2025-03-18T00:00:00Z")
REF1 = pd.Timestamp("2026-07-30T00:00:00Z")
AUG0 = pd.Timestamp("2026-08-01T00:00:00Z")
AUG1 = pd.Timestamp("2026-08-20T00:00:00Z")

SESSIONS = {
    0: ("ASIA_OPEN", "07:00"),
    7: ("LONDON_OPEN", "14:00"),
    13: ("NEW_YORK_OPEN", "20:00"),
}


def pct(v):
    if v is None:
        return "-"
    try:
        if math.isnan(float(v)):
            return "-"
    except Exception:
        pass
    return f"{100.0 * float(v):.2f}%"


def load_source():
    x = amd1.dataio.load_1h().copy()
    x["ts"] = pd.to_datetime(x["ts"], utc=True)
    x = x.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)
    return x


def make_h4_builder(x: pd.DataFrame):
    xi = x.set_index("ts", drop=False)
    cache = {}

    def h4(start: pd.Timestamp):
        start = pd.Timestamp(start)
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        else:
            start = start.tz_convert("UTC")
        if start in cache:
            return cache[start]
        ts = [start + pd.Timedelta(hours=j) for j in range(4)]
        if not all(t in xi.index for t in ts):
            cache[start] = None
            return None
        q = xi.loc[ts]
        if isinstance(q, pd.Series):
            cache[start] = None
            return None
        bar = {
            "ts": start,
            "open": float(q.open.iloc[0]),
            "high": float(q.high.max()),
            "low": float(q.low.min()),
            "close": float(q.close.iloc[-1]),
        }
        cache[start] = bar
        return bar

    return h4


def path_signature(firsts: dict[str, int | None]) -> str:
    grouped = {}
    for level, off in firsts.items():
        if off is None:
            continue
        grouped.setdefault(int(off), []).append(level)
    if not grouped:
        return "NONE"
    pieces = []
    for off in sorted(grouped):
        labs = sorted(grouped[off])
        if len(labs) == 1:
            pieces.append(f"+{off}:{labs[0]}")
        else:
            pieces.append(f"+{off}:SAME_BAR{{{','.join(labs)}}}")
    return " -> ".join(pieces)


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    h4 = make_h4_builder(x)
    min_day = x.ts.min().normalize()
    max_day = x.ts.max().normalize()
    days = pd.date_range(min_day, max_day, freq="D", tz="UTC")
    rows = []

    for day in days:
        for hour, (session, wib) in SESSIONS.items():
            anchor = day + pd.Timedelta(hours=hour)
            bars = {k: h4(anchor + pd.Timedelta(hours=4 * k)) for k in range(-3, 9)}
            if any(bars[k] is None for k in range(-3, 9)):
                continue

            prior = [bars[-3], bars[-2], bars[-1]]
            acc_high = max(b["high"] for b in prior)
            acc_low = min(b["low"] for b in prior)
            if not acc_high > acc_low:
                continue
            cur = bars[0]
            high_manip = cur["high"] > acc_high and cur["low"] >= acc_low and acc_low <= cur["close"] <= acc_high
            low_manip = cur["low"] < acc_low and cur["high"] <= acc_high and acc_low <= cur["close"] <= acc_high
            if high_manip == low_manip:
                continue

            if high_manip:
                original_side = "SHORT"
                manip_side = "HIGH_SWEEP"
            else:
                original_side = "LONG"
                manip_side = "LOW_SWEEP"

            b1, b2 = bars[1], bars[2]
            if original_side == "SHORT":
                fvg = b1["close"] < b1["open"] and b2["high"] < cur["low"]
                near = b2["high"] if fvg else np.nan
                far = cur["low"] if fvg else np.nan
                manip_extreme = cur["high"]
                opp = acc_low
            else:
                fvg = b1["close"] > b1["open"] and b2["low"] > cur["high"]
                near = b2["low"] if fvg else np.nan
                far = cur["high"] if fvg else np.nan
                manip_extreme = cur["low"]
                opp = acc_high

            rec = {
                "event_ts": anchor,
                "session": session,
                "session_wib": wib,
                "original_side": original_side,
                "manip_side": manip_side,
                "acc_high": acc_high,
                "acc_low": acc_low,
                "manip_open": cur["open"],
                "manip_high": cur["high"],
                "manip_low": cur["low"],
                "manip_close": cur["close"],
                "fvg": bool(fvg),
                "near": near,
                "far": far,
                "manip_extreme": manip_extreme,
                "opp_boundary": opp,
                "near_first": np.nan,
                "far_first": np.nan,
                "manip_extreme_first": np.nan,
                "opp_first": np.nan,
                "near_touched": False,
                "far_touched": False,
                "manip_extreme_revisited": False,
                "opp_reached": False,
                "both_far_opp": False,
                "both_order": None,
                "path_signature": None,
                "failure_close": False,
                "failure_offset": np.nan,
                "failure_retest_evaluable": False,
                "failure_retest": False,
            }
            if not fvg:
                rows.append(rec)
                continue

            firsts = {"NEAR": None, "FAR": None, "MANIP_EXTREME": None, "OPP_BOUNDARY": None}
            failure_off = None
            for k in range(3, 9):
                b = bars[k]
                if original_side == "SHORT":
                    hits = {
                        "NEAR": b["high"] >= near,
                        "FAR": b["high"] >= far,
                        "MANIP_EXTREME": b["high"] >= manip_extreme,
                        "OPP_BOUNDARY": b["low"] <= opp,
                    }
                    fail = b["close"] > far
                else:
                    hits = {
                        "NEAR": b["low"] <= near,
                        "FAR": b["low"] <= far,
                        "MANIP_EXTREME": b["low"] <= manip_extreme,
                        "OPP_BOUNDARY": b["high"] >= opp,
                    }
                    fail = b["close"] < far
                for level, hit in hits.items():
                    if hit and firsts[level] is None:
                        firsts[level] = k
                if fail and failure_off is None:
                    failure_off = k

            rec["near_first"] = np.nan if firsts["NEAR"] is None else firsts["NEAR"]
            rec["far_first"] = np.nan if firsts["FAR"] is None else firsts["FAR"]
            rec["manip_extreme_first"] = np.nan if firsts["MANIP_EXTREME"] is None else firsts["MANIP_EXTREME"]
            rec["opp_first"] = np.nan if firsts["OPP_BOUNDARY"] is None else firsts["OPP_BOUNDARY"]
            rec["near_touched"] = firsts["NEAR"] is not None
            rec["far_touched"] = firsts["FAR"] is not None
            rec["manip_extreme_revisited"] = firsts["MANIP_EXTREME"] is not None
            rec["opp_reached"] = firsts["OPP_BOUNDARY"] is not None
            rec["both_far_opp"] = firsts["FAR"] is not None and firsts["OPP_BOUNDARY"] is not None
            if rec["both_far_opp"]:
                if firsts["FAR"] < firsts["OPP_BOUNDARY"]:
                    rec["both_order"] = "FAR_FIRST"
                elif firsts["OPP_BOUNDARY"] < firsts["FAR"]:
                    rec["both_order"] = "OPP_FIRST"
                else:
                    rec["both_order"] = "SAME_BAR"
            rec["path_signature"] = path_signature(firsts)

            if failure_off is not None:
                rec["failure_close"] = True
                rec["failure_offset"] = failure_off
                fut = [h4(anchor + pd.Timedelta(hours=4 * k)) for k in range(failure_off + 1, failure_off + 7)]
                if all(b is not None for b in fut):
                    rec["failure_retest_evaluable"] = True
                    if original_side == "SHORT":
                        rec["failure_retest"] = any(b["low"] <= far for b in fut)
                    else:
                        rec["failure_retest"] = any(b["high"] >= far for b in fut)
            rows.append(rec)

    return pd.DataFrame(rows)


def top_paths(f: pd.DataFrame, n=8):
    if f.empty:
        return []
    c = Counter(f.path_signature.fillna("NONE"))
    total = len(f)
    return [{"path": p, "n": int(k), "rate": float(k / total)} for p, k in c.most_common(n)]


def stats(z: pd.DataFrame) -> dict:
    manip_n = int(len(z))
    f = z[z.fvg].copy()
    fvg_n = int(len(f))
    if fvg_n == 0:
        return {
            "manip_n": manip_n, "fvg_n": 0, "fvg_rate": None,
            "near_n": 0, "near_rate": None, "far_n": 0, "far_rate": None,
            "near_to_far_rate": None, "near_to_far_den": 0,
            "manip_extreme_n": 0, "manip_extreme_rate": None,
            "opp_n": 0, "opp_rate": None, "both_n": 0, "both_rate": None,
            "both_order": {}, "failure_n": 0, "failure_rate": None,
            "failure_eval_n": 0, "failure_retest_n": 0, "failure_retest_rate": None,
            "top_paths": [],
        }
    near_n = int(f.near_touched.sum())
    far_n = int(f.far_touched.sum())
    me_n = int(f.manip_extreme_revisited.sum())
    opp_n = int(f.opp_reached.sum())
    both_n = int(f.both_far_opp.sum())
    failure_n = int(f.failure_close.sum())
    fe = f[f.failure_close & f.failure_retest_evaluable].copy()
    fret_n = int(fe.failure_retest.sum()) if len(fe) else 0
    orders = f[f.both_far_opp].both_order.value_counts(dropna=False).to_dict()
    return {
        "manip_n": manip_n,
        "fvg_n": fvg_n,
        "fvg_rate": float(fvg_n / manip_n) if manip_n else None,
        "near_n": near_n,
        "near_rate": float(near_n / fvg_n),
        "far_n": far_n,
        "far_rate": float(far_n / fvg_n),
        "near_to_far_rate": float(far_n / near_n) if near_n else None,
        "near_to_far_den": near_n,
        "manip_extreme_n": me_n,
        "manip_extreme_rate": float(me_n / fvg_n),
        "opp_n": opp_n,
        "opp_rate": float(opp_n / fvg_n),
        "both_n": both_n,
        "both_rate": float(both_n / fvg_n),
        "both_order": {str(k): int(v) for k, v in orders.items()},
        "failure_n": failure_n,
        "failure_rate": float(failure_n / fvg_n),
        "failure_eval_n": int(len(fe)),
        "failure_retest_n": fret_n,
        "failure_retest_rate": float(fret_n / len(fe)) if len(fe) else None,
        "top_paths": top_paths(f),
    }


def transition80(s: dict, key_rate: str, key_den: str) -> bool:
    r = s.get(key_rate)
    d = s.get(key_den)
    return r is not None and d is not None and d >= 20 and r >= 0.80


def main():
    x = load_source()
    ev = build_events(x)
    if ev.empty:
        raise RuntimeError("no H4 manipulation events")

    parts = {
        "development": ev[(ev.event_ts >= DEV0) & (ev.event_ts < CUT)].copy(),
        "reference_validation": ev[(ev.event_ts >= CUT) & (ev.event_ts < REF1)].copy(),
        "external": ev[(ev.event_ts >= EXT0) & (ev.event_ts < EXT1)].copy(),
        "august": ev[(ev.event_ts >= AUG0) & (ev.event_ts < AUG1)].copy(),
    }
    aggregate = {k: stats(v) for k, v in parts.items()}

    matrix = []
    for part, z in parts.items():
        for side in ("LONG", "SHORT"):
            for session in ("ASIA_OPEN", "LONDON_OPEN", "NEW_YORK_OPEN"):
                q = z[(z.original_side == side) & (z.session == session)].copy()
                matrix.append({"partition": part, "side": side, "session": session, **stats(q)})

    val = aggregate["reference_validation"]
    ext = aggregate["external"]
    transitions = {
        "FVG_TO_NEAR": (
            val["near_rate"], val["fvg_n"], ext["near_rate"], ext["fvg_n"]
        ),
        "NEAR_TO_FAR": (
            val["near_to_far_rate"], val["near_to_far_den"], ext["near_to_far_rate"], ext["near_to_far_den"]
        ),
        "FAILURE_TO_RETEST": (
            val["failure_retest_rate"], val["failure_eval_n"], ext["failure_retest_rate"], ext["failure_eval_n"]
        ),
    }
    candidates80 = []
    for name, (vr, vd, er, ed) in transitions.items():
        if vr is not None and er is not None and vd >= 20 and ed >= 20 and vr >= .80 and er >= .80:
            candidates80.append(name)
    flag80 = bool(candidates80)

    ev.to_csv(OUT_EVENTS, index=False)
    parts["august"].to_csv(OUT_AUG, index=False)

    result = {
        "protocol": "BTC_H4_AMD_FVG_PATHMAP_H4P1",
        "coverage": {"first": str(x.ts.min()), "last": str(x.ts.max()), "source_1h_rows": int(len(x))},
        "h4_construction": "session-anchored synthetic 4H from four consecutive official H1 bars",
        "aggregate": aggregate,
        "matrix": matrix,
        "predeclared_transitions": {
            k: {"validation_rate": v[0], "validation_n": int(v[1]), "external_rate": v[2], "external_n": int(v[3])}
            for k, v in transitions.items()
        },
        "H4P1_80_TRANSITION_FOUND": flag80,
        "H4P1_80_TRANSITIONS": candidates80,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC H4 AMD + FVG Path Map H4P1 — Result",
        "",
        "Descriptive only. Session-anchored synthetic 4H bars preserve exact Asia/London/New York opens. Frozen event = 3xH4 accumulation -> first H4 manipulation -> exact opposite 3-bar H4 FVG. Post-confirmation path horizon = 6xH4 / 24H.",
        "",
        f"Source coverage **{x.ts.min()} -> {x.ts.max()}**, official 1H rows **{len(x):,}**.",
        "",
        "## Aggregate",
        "",
        "| Partition | Manip | Exact FVG | FVG rate | NEAR | FAR | NEAR→FAR | Manip extreme | Opp boundary | BOTH far+opp | Failure close | Failure→retest |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in ("development", "reference_validation", "external", "august"):
        s = aggregate[p]
        md.append(
            f"| {p} | {s['manip_n']} | {s['fvg_n']} | {pct(s['fvg_rate'])} | "
            f"{s['near_n']}/{pct(s['near_rate'])} | {s['far_n']}/{pct(s['far_rate'])} | {pct(s['near_to_far_rate'])} | "
            f"{s['manip_extreme_n']}/{pct(s['manip_extreme_rate'])} | {s['opp_n']}/{pct(s['opp_rate'])} | "
            f"{s['both_n']}/{pct(s['both_rate'])} | {s['failure_n']}/{pct(s['failure_rate'])} | "
            f"{s['failure_retest_n']}/{s['failure_eval_n']}={pct(s['failure_retest_rate'])} |"
        )

    md += ["", "## BOTH(FAR + opposite boundary) order", ""]
    for p in ("reference_validation", "external"):
        s = aggregate[p]
        md.append(f"- **{p}**: {s['both_order'] if s['both_order'] else '{}'}")

    for p, title in (("reference_validation", "Reference validation"), ("external", "External 2020-2021")):
        md += [
            "", f"## {title} by fixed side/session", "",
            "| Original side | Session | Manip | FVG | NEAR | FAR | Opp | BOTH | Failure | Failure→retest |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in matrix:
            if r["partition"] != p:
                continue
            md.append(
                f"| {r['side']} | {r['session']} | {r['manip_n']} | {r['fvg_n']} | {pct(r['near_rate'])} | "
                f"{pct(r['far_rate'])} | {pct(r['opp_rate'])} | {pct(r['both_rate'])} | {pct(r['failure_rate'])} | "
                f"{r['failure_retest_n']}/{r['failure_eval_n']}={pct(r['failure_retest_rate'])} |"
            )

    for p in ("reference_validation", "external"):
        md += ["", f"## Top first-touch paths — {p}", ""]
        for q in aggregate[p]["top_paths"]:
            md.append(f"- {q['n']} ({pct(q['rate'])}) — `{q['path']}`")

    md += ["", "## Predeclared 80% transition check", ""]
    for name, d in result["predeclared_transitions"].items():
        md.append(
            f"- **{name}**: validation {d['validation_n']} @ {pct(d['validation_rate'])}; "
            f"external {d['external_n']} @ {pct(d['external_rate'])}."
        )
    md += [
        "",
        f"**H4P1_80_TRANSITION_FOUND: {'YES' if flag80 else 'NO'}**",
        f"Candidates: {', '.join(candidates80) if candidates80 else 'none'}",
        "",
        "No trading rule, TP/SL, session/side selection, horizon retuning, or threshold optimization is authorized by this descriptive map.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()

# no-op workflow retrigger marker; frozen H4P1 logic unchanged
