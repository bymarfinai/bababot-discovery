#!/usr/bin/env python3
"""BTC Session Archetype Map V1 — descriptive recurring path study.

Frozen before result:
- six fixed Asia/London/New York open+close anchors
- frozen known daily H/L at anchor
- first 90m on completed 15m candles
- mutually exclusive path archetypes
- no trading optimization / no 1m data
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import btc_aoh1_asia_open_high_failed_acceptance as dataio

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_Session_Archetype_Map_V1_Result.md"
OUT_JSON = ROOT / "BTC_Session_Archetype_Map_V1_Result.json"
OUT_CSV = ROOT / "BTC_Session_Archetype_Map_V1_August.csv"

HIST_START = pd.Timestamp("2022-01-01T00:00:00Z")
HIST_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
WINDOW_MIN = 90

ANCHORS = [
    {"name": "ASIA_OPEN", "hour": 0, "kind": "OPEN", "session": "ASIA", "prev_day": True},
    {"name": "ASIA_CLOSE", "hour": 8, "kind": "CLOSE", "session": "ASIA", "prev_day": False},
    {"name": "LONDON_OPEN", "hour": 7, "kind": "OPEN", "session": "LONDON", "prev_day": False},
    {"name": "LONDON_CLOSE", "hour": 16, "kind": "CLOSE", "session": "LONDON", "prev_day": False},
    {"name": "NEW_YORK_OPEN", "hour": 13, "kind": "OPEN", "session": "NEW_YORK", "prev_day": False},
    {"name": "NEW_YORK_CLOSE", "hour": 22, "kind": "CLOSE", "session": "NEW_YORK", "prev_day": False},
]

DIRECTION = {
    "HIGH_IMMEDIATE_RECLAIM": "SHORT",
    "LOW_IMMEDIATE_RECLAIM": "LONG",
    "HIGH_BREAK_FAIL": "SHORT",
    "LOW_BREAK_FAIL": "LONG",
    "HIGH_ACCEPT": "LONG",
    "LOW_ACCEPT": "SHORT",
}

REJECTION = {
    "HIGH_IMMEDIATE_RECLAIM",
    "LOW_IMMEDIATE_RECLAIM",
    "HIGH_BREAK_FAIL",
    "LOW_BREAK_FAIL",
}


def aggregate_15m(x: pd.DataFrame) -> pd.DataFrame:
    y = x.set_index("ts")
    z = y.resample("15min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        count=("close", "count"),
    ).dropna().reset_index()
    return z[z["count"] == 3].reset_index(drop=True)


def level_for_anchor(x5: pd.DataFrame, day: pd.Timestamp, a: dict) -> Optional[tuple[float, float]]:
    if a["prev_day"]:
        s, e = day - pd.Timedelta(days=1), day
    else:
        s, e = day, day + pd.Timedelta(hours=a["hour"])
    z = x5[(x5.ts >= s) & (x5.ts < e)]
    expected = int((e - s).total_seconds() // 300)
    if expected <= 0 or len(z) != expected:
        return None
    hi, lo = float(z.high.max()), float(z.low.min())
    if not np.isfinite(hi) or not np.isfinite(lo) or hi <= lo:
        return None
    return hi, lo


def anchor_open_price(x5_by_ts: dict, x5: pd.DataFrame, ts: pd.Timestamp) -> Optional[float]:
    i = x5_by_ts.get(ts)
    return None if i is None else float(x5.open.iloc[int(i)])


def classify_window(z: pd.DataFrame, hi: float, lo: float) -> tuple[str, str, pd.Timestamp]:
    """Return archetype, first-sweep side code, completion timestamp (15m bar open)."""
    high_idx = [int(i) for i, r in z.iterrows() if float(r.high) > hi]
    low_idx = [int(i) for i, r in z.iterrows() if float(r.low) < lo]

    if not high_idx and not low_idx:
        return "NO_SWEEP", "N", pd.Timestamp(z.ts.iloc[-1])

    if high_idx and low_idx:
        h0, l0 = high_idx[0], low_idx[0]
        if h0 == l0:
            return "DOUBLE_SAME_15M", "B", pd.Timestamp(z.loc[h0, "ts"])
        if pd.Timestamp(z.loc[h0, "ts"]) < pd.Timestamp(z.loc[l0, "ts"]):
            return "DOUBLE_HIGH_THEN_LOW", "B", pd.Timestamp(z.loc[l0, "ts"])
        return "DOUBLE_LOW_THEN_HIGH", "B", pd.Timestamp(z.loc[h0, "ts"])

    if high_idx:
        h0 = high_idx[0]
        first = z.loc[h0]
        if float(first.close) <= hi:  # exact-level close treated as inside, conservative acceptance test
            return "HIGH_IMMEDIATE_RECLAIM", "H", pd.Timestamp(first.ts)
        # first sweep closes outside; look for later return inside
        later = z[z.index > h0]
        back = later[later.close <= hi]
        if not back.empty:
            r = back.iloc[0]
            return "HIGH_BREAK_FAIL", "H", pd.Timestamp(r.ts)
        return "HIGH_ACCEPT", "H", pd.Timestamp(z.ts.iloc[-1])

    l0 = low_idx[0]
    first = z.loc[l0]
    if float(first.close) >= lo:
        return "LOW_IMMEDIATE_RECLAIM", "L", pd.Timestamp(first.ts)
    later = z[z.index > l0]
    back = later[later.close >= lo]
    if not back.empty:
        r = back.iloc[0]
        return "LOW_BREAK_FAIL", "L", pd.Timestamp(r.ts)
    return "LOW_ACCEPT", "L", pd.Timestamp(z.ts.iloc[-1])


def forward_signed(x5: pd.DataFrame, x5_by_ts: dict, entry_ts: pd.Timestamp, direction: str, minutes: int) -> Optional[float]:
    i = x5_by_ts.get(entry_ts)
    if i is None:
        return None
    i = int(i)
    bars = minutes // 5
    j = i + bars - 1
    if j >= len(x5):
        return None
    if x5.ts.iloc[j] != entry_ts + pd.Timedelta(minutes=5 * (bars - 1)):
        return None
    ep, final = float(x5.open.iloc[i]), float(x5.close.iloc[j])
    return (final - ep) / ep if direction == "LONG" else (ep - final) / ep


def opposite_rotation(x5: pd.DataFrame, x5_by_ts: dict, entry_ts: pd.Timestamp, archetype: str, hi: float, lo: float) -> Optional[bool]:
    if archetype not in REJECTION:
        return None
    i = x5_by_ts.get(entry_ts)
    if i is None:
        return None
    i = int(i)
    j = i + 72 - 1
    if j >= len(x5) or x5.ts.iloc[j] != entry_ts + pd.Timedelta(minutes=355):
        return None
    f = x5.iloc[i:j + 1]
    if archetype.startswith("HIGH_"):
        return bool(float(f.low.min()) <= lo)
    return bool(float(f.high.max()) >= hi)


def build_records(x5: pd.DataFrame, x15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    x5_by_ts = {t: i for i, t in enumerate(x5.ts)}
    day = start.normalize()
    while day < end.normalize():
        for a in ANCHORS:
            anchor_ts = day + pd.Timedelta(hours=a["hour"])
            levels = level_for_anchor(x5, day, a)
            if levels is None:
                continue
            hi, lo = levels
            z = x15[(x15.ts >= anchor_ts) & (x15.ts < anchor_ts + pd.Timedelta(minutes=WINDOW_MIN))]
            if len(z) != 6:
                continue
            archetype, first_side, complete_ts = classify_window(z, hi, lo)
            entry_ts = complete_ts + pd.Timedelta(minutes=15)

            ap = anchor_open_price(x5_by_ts, x5, anchor_ts)
            p60 = anchor_open_price(x5_by_ts, x5, anchor_ts - pd.Timedelta(minutes=60))
            if ap is None or p60 is None:
                continue
            pretrend = "PRE_UP" if ap > p60 else ("PRE_DOWN" if ap < p60 else "PRE_FLAT")
            loc = (ap - lo) / (hi - lo)
            location = "NEAR_HIGH" if loc >= 0.75 else ("NEAR_LOW" if loc <= 0.25 else "MID")

            direction = DIRECTION.get(archetype)
            r60 = r240 = None
            pos60 = pos240 = None
            rotate = None
            if direction is not None:
                r60 = forward_signed(x5, x5_by_ts, entry_ts, direction, 60)
                r240 = forward_signed(x5, x5_by_ts, entry_ts, direction, 240)
                pos60 = None if r60 is None else int(r60 > 0)
                pos240 = None if r240 is None else int(r240 > 0)
                rotate = opposite_rotation(x5, x5_by_ts, entry_ts, archetype, hi, lo)

            rows.append({
                "utc_date": day.strftime("%Y-%m-%d"),
                "anchor": a["name"],
                "anchor_kind": a["kind"],
                "session": a["session"],
                "anchor_ts": anchor_ts,
                "frozen_high": hi,
                "frozen_low": lo,
                "anchor_price": ap,
                "range_location": loc,
                "location_bucket": location,
                "pretrend": pretrend,
                "archetype": archetype,
                "first_sweep_side": first_side,
                "pattern_complete_ts": complete_ts,
                "diagnostic_entry_ts": entry_ts,
                "direction_map": direction,
                "signed_ret60": r60,
                "signed_ret240": r240,
                "positive60": pos60,
                "positive240": pos240,
                "opposite_level_6h": rotate,
            })
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def block_id(ts: pd.Timestamp, start: pd.Timestamp, end: pd.Timestamp) -> str:
    frac = (ts - start).total_seconds() / (end - start).total_seconds()
    n = min(3, max(0, int(frac * 4)))
    return f"B{n+1}"


def anchor_archetype_summary(hist: pd.DataFrame, aug: pd.DataFrame) -> list[dict]:
    out = []
    for anchor in [a["name"] for a in ANCHORS]:
        h = hist[hist.anchor == anchor]
        a = aug[aug.anchor == anchor]
        denom = len(h)
        adenom = len(a)
        for arch, z in h.groupby("archetype"):
            za = a[a.archetype == arch]
            blocks = {}
            for b in ("B1", "B2", "B3", "B4"):
                hb = h[h.block == b]
                zb = z[z.block == b]
                blocks[b] = {"n": int(len(zb)), "share": float(len(zb) / len(hb)) if len(hb) else None}
            recurring = bool(len(z) >= 50 and all(blocks[b]["n"] >= 8 for b in blocks))
            pt = z.pretrend.value_counts().to_dict()
            loc = z.location_bucket.value_counts().to_dict()
            d = {
                "anchor": anchor,
                "archetype": arch,
                "n": int(len(z)),
                "share": float(len(z) / denom) if denom else None,
                "aug_n": int(len(za)),
                "aug_share": float(len(za) / adenom) if adenom else None,
                "recurring_stable": recurring,
                "blocks": blocks,
                "pretrend": {k: int(v) for k, v in pt.items()},
                "location": {k: int(v) for k, v in loc.items()},
                "direction": DIRECTION.get(arch),
                "positive60_rate": float(z.positive60.dropna().mean()) if z.positive60.notna().any() else None,
                "positive240_rate": float(z.positive240.dropna().mean()) if z.positive240.notna().any() else None,
                "avg_signed60": float(z.signed_ret60.dropna().mean()) if z.signed_ret60.notna().any() else None,
                "avg_signed240": float(z.signed_ret240.dropna().mean()) if z.signed_ret240.notna().any() else None,
                "opposite_level_6h_rate": float(z.opposite_level_6h.dropna().astype(float).mean()) if z.opposite_level_6h.notna().any() else None,
            }
            out.append(d)
    return sorted(out, key=lambda q: (q["anchor"], -q["n"]))


def sequence_map(df: pd.DataFrame) -> dict:
    opens = ["ASIA_OPEN", "LONDON_OPEN", "NEW_YORK_OPEN"]
    p = df[df.anchor.isin(opens)].pivot(index="utc_date", columns="anchor", values="first_sweep_side")
    p = p.dropna(subset=opens)
    if p.empty:
        return {"eligible_days": 0, "top_sequences": [], "london_to_ny": {}, "conditional": {}}
    seq = (p["ASIA_OPEN"].astype(str) + "->" + p["LONDON_OPEN"].astype(str) + "->" + p["NEW_YORK_OPEN"].astype(str))
    counts = seq.value_counts()
    top = [{"sequence": k, "n": int(v), "share": float(v / len(p))} for k, v in counts.head(15).items()]

    trans = pd.crosstab(p["LONDON_OPEN"], p["NEW_YORK_OPEN"])
    trans_out = {}
    for l in trans.index:
        row_total = int(trans.loc[l].sum())
        trans_out[str(l)] = {
            str(n): {"n": int(trans.loc[l, n]), "p": float(trans.loc[l, n] / row_total)}
            for n in trans.columns
        }

    cond = {}
    for lside, opposite in [("H", "L"), ("L", "H")]:
        q = p[p["LONDON_OPEN"] == lside]
        if len(q):
            cond[f"London_{lside}_to_NY_{opposite}_only"] = float((q["NEW_YORK_OPEN"] == opposite).mean())
            cond[f"London_{lside}_to_NY_includes_{opposite}"] = float(q["NEW_YORK_OPEN"].isin([opposite, "B"]).mean())
            cond[f"London_{lside}_n"] = int(len(q))
    return {"eligible_days": int(len(p)), "top_sequences": top, "london_to_ny": trans_out, "conditional": cond}


def pct(v: Optional[float]) -> str:
    return "-" if v is None else f"{100*v:.1f}%"


def main() -> None:
    x5 = dataio.load_data()
    x15 = aggregate_15m(x5)
    hist = build_records(x5, x15, HIST_START, HIST_END)
    aug = build_records(x5, x15, AUG_START, AUG_END)
    hist["block"] = hist.anchor_ts.apply(lambda t: block_id(pd.Timestamp(t), HIST_START, HIST_END))
    aug.to_csv(OUT_CSV, index=False)

    summary = anchor_archetype_summary(hist, aug)
    hist_seq = sequence_map(hist)
    aug_seq = sequence_map(aug)

    recurring = [f"{r['anchor']}:{r['archetype']}" for r in summary if r["recurring_stable"]]
    result = {
        "protocol": "BTC_SESSION_ARCHETYPE_MAP_V1",
        "coverage": {"first": str(x5.ts.min()), "last": str(x5.ts.max()), "rows5m": int(len(x5)), "rows15m": int(len(x15))},
        "historical_anchor_days": int(len(hist)),
        "august_anchor_days": int(len(aug)),
        "summary": summary,
        "recurring_stable": recurring,
        "historical_open_sequence": hist_seq,
        "august_open_sequence": aug_seq,
        "guardrails": {"one_minute_used": False, "window_minutes": WINDOW_MIN, "trade_optimization": False},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC Session Archetype Map V1 — Result",
        "",
        "Pure descriptive map: frozen daily H/L at six session anchors, first 90m, completed 15m path. No TP/SL optimization.",
        "",
        f"Coverage **{x5.ts.min()} -> {x5.ts.max()}**. Historical eligible anchor-days **{len(hist):,}**; August **{len(aug):,}**.",
        "",
        "## Most common archetypes by anchor",
        "",
        "| Anchor | Archetype | N | Share | Stable | +60 direction | +240 direction | Opposite level <=6h | Aug N |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for anchor in [a["name"] for a in ANCHORS]:
        rows = [r for r in summary if r["anchor"] == anchor]
        for r in rows[:6]:
            md.append(
                f"| {anchor} | {r['archetype']} | {r['n']} | {pct(r['share'])} | {'YES' if r['recurring_stable'] else 'NO'} | "
                f"{pct(r['positive60_rate'])} | {pct(r['positive240_rate'])} | {pct(r['opposite_level_6h_rate'])} | {r['aug_n']} |"
            )
    md += [
        "",
        "## Stable recurring archetypes",
        "",
        f"{', '.join(recurring) if recurring else 'NONE'}",
        "",
        "## OPEN-session day sequences — historical",
        "",
        f"Eligible days with all three OPEN anchors: **{hist_seq['eligible_days']}**.",
        "",
        "| Asia -> London -> NY | N | Share |",
        "|---|---:|---:|",
    ]
    for q in hist_seq["top_sequences"][:12]:
        md.append(f"| `{q['sequence']}` | {q['n']} | {pct(q['share'])} |")
    md += [
        "",
        "### London -> New York opposite-side diagnostic",
        "",
    ]
    c = hist_seq.get("conditional", {})
    if c:
        md += [
            f"- London H-only days: **{c.get('London_H_n', 0)}**; NY L-only **{pct(c.get('London_H_to_NY_L_only'))}**; NY includes LOW (L or B) **{pct(c.get('London_H_to_NY_includes_L'))}**.",
            f"- London L-only days: **{c.get('London_L_n', 0)}**; NY H-only **{pct(c.get('London_L_to_NY_H_only'))}**; NY includes HIGH (H or B) **{pct(c.get('London_L_to_NY_includes_H'))}**.",
        ]
    md += [
        "",
        "## August OPEN-session sequences",
        "",
        f"Eligible days: **{aug_seq['eligible_days']}**.",
        "",
        "| Asia -> London -> NY | N | Share |",
        "|---|---:|---:|",
    ]
    for q in aug_seq["top_sequences"]:
        md.append(f"| `{q['sequence']}` | {q['n']} | {pct(q['share'])} |")
    md += [
        "",
        "`H`=only frozen high swept; `L`=only frozen low swept; `B`=both swept; `N`=neither swept in first 90m.",
        "",
        "Recurring means repeated occurrence with N>=50 and >=8 observations in every chronological block; it does not mean profitable.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
