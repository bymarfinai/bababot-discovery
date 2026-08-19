#!/usr/bin/env python3
"""BTC H1 session-offset recurring pattern map.

Frozen before result:
- six fixed session anchors
- offsets -3..+3 hours
- 1H candles only
- event classified vs causal prior-3H range
- next1H/3H descriptive follow-through
- no TP/SL optimization
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
OUT_MD = ROOT / "BTC_H1_Session_Offset_Pattern_Map_Result.md"
OUT_JSON = ROOT / "BTC_H1_Session_Offset_Pattern_Map_Result.json"
OUT_AUG = ROOT / "BTC_H1_Session_Offset_Pattern_Map_August.csv"
OUT_CELLS = ROOT / "BTC_H1_Session_Offset_Pattern_Map_Cells.csv"

HIST_START = pd.Timestamp("2022-01-01T00:00:00Z")
HIST_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
OFFSETS = list(range(-3, 4))

ANCHORS = [
    {"name": "ASIA_OPEN", "hour": 0, "wib": "07:00"},
    {"name": "ASIA_CLOSE", "hour": 8, "wib": "15:00"},
    {"name": "LONDON_OPEN", "hour": 7, "wib": "14:00"},
    {"name": "LONDON_CLOSE", "hour": 16, "wib": "23:00"},
    {"name": "NEW_YORK_OPEN", "hour": 13, "wib": "20:00"},
    {"name": "NEW_YORK_CLOSE", "hour": 22, "wib": "05:00+1"},
]

DIR_MAP = {
    "HIGH_REJECT": "SHORT",
    "LOW_REJECT": "LONG",
    "HIGH_ACCEPT": "LONG",
    "LOW_ACCEPT": "SHORT",
}


def aggregate_1h(x5: pd.DataFrame) -> pd.DataFrame:
    y = x5.set_index("ts")
    z = y.resample("1h", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        count=("close", "count"),
    ).dropna().reset_index()
    z = z[z["count"] == 12].reset_index(drop=True)
    return z


def color(r: pd.Series) -> str:
    if float(r.close) > float(r.open):
        return "U"
    if float(r.close) < float(r.open):
        return "D"
    return "F"


def classify(cur: pd.Series, ph: float, pl: float) -> str:
    hs = float(cur.high) > ph
    ls = float(cur.low) < pl
    if hs and ls:
        return "BOTH"
    if hs:
        return "HIGH_ACCEPT" if float(cur.close) > ph else "HIGH_REJECT"
    if ls:
        return "LOW_ACCEPT" if float(cur.close) < pl else "LOW_REJECT"
    return "INSIDE"


def signed(direction: str, entry: float, final: float) -> float:
    raw = final / entry - 1.0
    return raw if direction == "LONG" else -raw


def block_id(ts: pd.Timestamp) -> str:
    frac = (ts - HIST_START).total_seconds() / (HIST_END - HIST_START).total_seconds()
    n = min(3, max(0, int(frac * 4)))
    return f"B{n+1}"


def build_records(x1: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    idx = {t: i for i, t in enumerate(x1.ts)}
    rows = []
    day = start.normalize()
    while day < end.normalize():
        for a in ANCHORS:
            anchor_ts = day + pd.Timedelta(hours=a["hour"])
            for off in OFFSETS:
                event_ts = anchor_ts + pd.Timedelta(hours=off)
                ci = idx.get(event_ts)
                if ci is None:
                    continue
                ci = int(ci)
                if ci < 3 or ci + 3 >= len(x1):
                    continue
                prior = x1.iloc[ci-3:ci]
                cur = x1.iloc[ci]
                # exact continuity for prior and future diagnostic bars
                expected_prior = [event_ts - pd.Timedelta(hours=h) for h in (3, 2, 1)]
                if list(prior.ts) != expected_prior:
                    continue
                if x1.ts.iloc[ci+1] != event_ts + pd.Timedelta(hours=1) or x1.ts.iloc[ci+3] != event_ts + pd.Timedelta(hours=3):
                    continue

                ph = float(prior.high.max())
                pl = float(prior.low.min())
                event_class = classify(cur, ph, pl)
                pre_seq = "".join(color(r) for _, r in prior.iterrows())
                pre_net = float(prior.close.iloc[-1] / prior.open.iloc[0] - 1.0)
                pre_state = "PRE_UP" if pre_net > 0 else ("PRE_DOWN" if pre_net < 0 else "PRE_FLAT")

                entry_ts = event_ts + pd.Timedelta(hours=1)
                entry = float(x1.open.iloc[ci+1])
                close1 = float(x1.close.iloc[ci+1])
                close3 = float(x1.close.iloc[ci+3])
                raw1 = close1 / entry - 1.0
                raw3 = close3 / entry - 1.0
                post3_state = "UP" if raw3 > 0 else ("DOWN" if raw3 < 0 else "FLAT")

                direction = DIR_MAP.get(event_class)
                s1 = s3 = p1 = p3 = None
                if direction is not None:
                    s1 = signed(direction, entry, close1)
                    s3 = signed(direction, entry, close3)
                    p1 = int(s1 > 0)
                    p3 = int(s3 > 0)

                rows.append({
                    "utc_date": day.strftime("%Y-%m-%d"),
                    "anchor": a["name"],
                    "anchor_hour_utc": a["hour"],
                    "anchor_wib": a["wib"],
                    "offset": off,
                    "event_ts": event_ts,
                    "event_hour_utc": int(event_ts.hour),
                    "event_hour_wib": int((event_ts.hour + 7) % 24),
                    "prior3_high": ph,
                    "prior3_low": pl,
                    "event_class": event_class,
                    "pre_seq": pre_seq,
                    "pre_net3h": pre_net,
                    "pre_state": pre_state,
                    "entry_ts": entry_ts,
                    "post_raw1h": raw1,
                    "post_raw3h": raw3,
                    "post3_state": post3_state,
                    "direction": direction,
                    "signed1h": s1,
                    "signed3h": s3,
                    "positive1h": p1,
                    "positive3h": p3,
                })
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def build_sequences(x1: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    idx = {t: i for i, t in enumerate(x1.ts)}
    rows = []
    day = start.normalize()
    while day < end.normalize():
        for a in ANCHORS:
            anchor_ts = day + pd.Timedelta(hours=a["hour"])
            ai = idx.get(anchor_ts)
            if ai is None:
                continue
            ai = int(ai)
            if ai < 3 or ai + 3 >= len(x1):
                continue
            z = x1.iloc[ai-3:ai+4]
            expected = [anchor_ts + pd.Timedelta(hours=o) for o in OFFSETS]
            if list(z.ts) != expected:
                continue
            seq = "".join(color(r) for _, r in z.iterrows())
            rows.append({"utc_date": day.strftime("%Y-%m-%d"), "anchor": a["name"], "anchor_ts": anchor_ts, "sequence": seq})
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def cell_summaries(hist: pd.DataFrame, aug: pd.DataFrame) -> list[dict]:
    out = []
    classes = ["INSIDE", "HIGH_REJECT", "LOW_REJECT", "HIGH_ACCEPT", "LOW_ACCEPT", "BOTH"]
    for a in [q["name"] for q in ANCHORS]:
        for off in OFFSETS:
            h0 = hist[(hist.anchor == a) & (hist.offset == off)]
            a0 = aug[(aug.anchor == a) & (aug.offset == off)]
            for cls in classes:
                z = h0[h0.event_class == cls]
                za = a0[a0.event_class == cls]
                if z.empty:
                    continue
                blocks = {}
                block_ok_rates = []
                for b in ("B1", "B2", "B3", "B4"):
                    zb = z[z.block == b]
                    rate = float(zb.positive3h.dropna().mean()) if zb.positive3h.notna().any() else None
                    blocks[b] = {"n": int(len(zb)), "positive3h": rate}
                    if len(zb) >= 8 and rate is not None:
                        block_ok_rates.append(rate)
                p1 = float(z.positive1h.dropna().mean()) if z.positive1h.notna().any() else None
                p3 = float(z.positive3h.dropna().mean()) if z.positive3h.notna().any() else None
                n_dir = int(z.positive3h.notna().sum())
                recurring = bool(len(z) >= 50 and all(blocks[b]["n"] >= 8 for b in blocks))
                strong = bool(recurring and p3 is not None and p3 >= .70 and all(r >= .60 for r in block_ok_rates) and len(block_ok_rates) == 4)
                qualifying_blocks80 = sum(1 for b in blocks.values() if b["n"] >= 5 and b["positive3h"] is not None and b["positive3h"] >= .70)
                c80 = bool(n_dir >= 25 and p3 is not None and p3 >= .80 and qualifying_blocks80 >= 3)
                out.append({
                    "anchor": a, "offset": off, "event_class": cls,
                    "n": int(len(z)), "share": float(len(z)/len(h0)) if len(h0) else None,
                    "direction": DIR_MAP.get(cls), "positive1h": p1, "positive3h": p3,
                    "avg_signed1h": float(z.signed1h.dropna().mean()) if z.signed1h.notna().any() else None,
                    "avg_signed3h": float(z.signed3h.dropna().mean()) if z.signed3h.notna().any() else None,
                    "aug_n": int(len(za)),
                    "aug_positive3h": float(za.positive3h.dropna().mean()) if za.positive3h.notna().any() else None,
                    "blocks": blocks, "recurring_stable": recurring,
                    "strong_repeatable_direction": strong, "candidate80": c80,
                })
    return out


def trend_turn(hist: pd.DataFrame, aug: pd.DataFrame) -> list[dict]:
    out=[]
    for a in [q["name"] for q in ANCHORS]:
        for off in OFFSETS:
            h=hist[(hist.anchor==a)&(hist.offset==off)]
            az=aug[(aug.anchor==a)&(aug.offset==off)]
            up=h[h.pre_state=="PRE_UP"]; dn=h[h.pre_state=="PRE_DOWN"]
            aup=az[az.pre_state=="PRE_UP"]; adn=az[az.pre_state=="PRE_DOWN"]
            out.append({
                "anchor":a,"offset":off,
                "pre_up_n":int(len(up)),"pre_up_to_down3h":float((up.post3_state=="DOWN").mean()) if len(up) else None,
                "pre_down_n":int(len(dn)),"pre_down_to_up3h":float((dn.post3_state=="UP").mean()) if len(dn) else None,
                "aug_pre_up_n":int(len(aup)),"aug_pre_up_to_down3h":float((aup.post3_state=="DOWN").mean()) if len(aup) else None,
                "aug_pre_down_n":int(len(adn)),"aug_pre_down_to_up3h":float((adn.post3_state=="UP").mean()) if len(adn) else None,
            })
    return out


def sequence_summary(hist_seq: pd.DataFrame, aug_seq: pd.DataFrame) -> dict:
    result={}
    for a in [q["name"] for q in ANCHORS]:
        h=hist_seq[hist_seq.anchor==a].copy(); az=aug_seq[aug_seq.anchor==a]
        if h.empty:
            result[a]=[]; continue
        h["block"]=h.anchor_ts.apply(block_id)
        c=Counter(h.sequence)
        rows=[]
        for seq,n in c.most_common(15):
            blocks={b:int(((h.sequence==seq)&(h.block==b)).sum()) for b in ("B1","B2","B3","B4")}
            rows.append({"sequence":seq,"n":int(n),"share":float(n/len(h)),"blocks":blocks,"aug_n":int((az.sequence==seq).sum()),
                         "stable":bool(n>=30 and all(v>=4 for v in blocks.values()))})
        result[a]=rows
    return result


def pct(v: Optional[float]) -> str:
    return "-" if v is None else f"{100*v:.1f}%"


def off_label(o:int)->str:
    return f"{o:+d}h" if o else "0h"


def main():
    x5=dataio.load_data(); x1=aggregate_1h(x5)
    hist=build_records(x1,HIST_START,HIST_END); aug=build_records(x1,AUG_START,AUG_END)
    hist["block"]=hist.event_ts.apply(block_id)
    hist_seq=build_sequences(x1,HIST_START,HIST_END); aug_seq=build_sequences(x1,AUG_START,AUG_END)
    if aug.empty: pd.DataFrame(columns=["utc_date"]).to_csv(OUT_AUG,index=False)
    else: aug.to_csv(OUT_AUG,index=False)

    cells=cell_summaries(hist,aug); pd.DataFrame([{k:v for k,v in r.items() if k!="blocks"} for r in cells]).to_csv(OUT_CELLS,index=False)
    turns=trend_turn(hist,aug); seqs=sequence_summary(hist_seq,aug_seq)
    directional=[r for r in cells if r["direction"] is not None and r["positive3h"] is not None]
    top_dir=sorted(directional,key=lambda r:(r["positive3h"],r["n"]),reverse=True)
    strong=[r for r in cells if r["strong_repeatable_direction"]]
    c80=[r for r in cells if r["candidate80"]]
    top_turn=sorted(turns,key=lambda r:max(r["pre_up_to_down3h"] or 0,r["pre_down_to_up3h"] or 0),reverse=True)

    result={
        "protocol":"BTC_H1_SESSION_OFFSET_PATTERN_MAP_V1",
        "coverage":{"first":str(x1.ts.min()),"last":str(x1.ts.max()),"rows1h":int(len(x1))},
        "historical_records":int(len(hist)),"august_records":int(len(aug)),
        "cells":cells,"trend_turn":turns,"sequences":seqs,
        "strong_repeatable_cells":[f"{r['anchor']}:{off_label(r['offset'])}:{r['event_class']}" for r in strong],
        "candidate80_cells":[f"{r['anchor']}:{off_label(r['offset'])}:{r['event_class']}" for r in c80],
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+"\n")

    md=["# BTC H1 Session-Offset Pattern Map — Result","",
        "1H descriptive map around six fixed session anchors; every event candle is classified against its own causal prior-3H range. No TP/SL optimization.","",
        f"Coverage: **{x1.ts.min()} -> {x1.ts.max()}**, complete 1H rows **{len(x1):,}**.",
        f"Historical anchor-offset records: **{len(hist):,}**; August records: **{len(aug):,}**.","",
        "## Strongest directional event cells by 3H follow-through","",
        "| Rank | Anchor | Offset | Event | N | Share | Direction | +1H | +3H | Avg signed 3H | Stable | Strong | 80% | Aug N/+3H |",
        "|---:|---|---:|---|---:|---:|---|---:|---:|---:|---|---|---|---:|"]
    for i,r in enumerate(top_dir[:35],1):
        md.append(f"| {i} | {r['anchor']} | {off_label(r['offset'])} | {r['event_class']} | {r['n']} | {pct(r['share'])} | {r['direction']} | {pct(r['positive1h'])} | {pct(r['positive3h'])} | {pct(r['avg_signed3h'])} | {'Y' if r['recurring_stable'] else 'N'} | {'Y' if r['strong_repeatable_direction'] else 'N'} | {'Y' if r['candidate80'] else 'N'} | {r['aug_n']}/{pct(r['aug_positive3h'])} |")
    md += ["","## Strongest pure trend-turn times (no sweep condition)","",
           "| Rank | Anchor | Offset | PRE_UP N -> DOWN next3H | PRE_DOWN N -> UP next3H |",
           "|---:|---|---:|---:|---:|"]
    for i,r in enumerate(top_turn[:25],1):
        md.append(f"| {i} | {r['anchor']} | {off_label(r['offset'])} | {r['pre_up_n']} -> {pct(r['pre_up_to_down3h'])} | {r['pre_down_n']} -> {pct(r['pre_down_to_up3h'])} |")
    md += ["","## Top exact 7-hour candle-color sequences by anchor",""]
    for a in [q["name"] for q in ANCHORS]:
        md += [f"### {a}","","| Sequence (-3h..+3h) | N | Share | Blocks B1/B2/B3/B4 | Aug N | Stable |","|---|---:|---:|---|---:|---|"]
        for r in seqs.get(a,[])[:8]:
            b=r['blocks']; md.append(f"| `{r['sequence']}` | {r['n']} | {pct(r['share'])} | {b['B1']}/{b['B2']}/{b['B3']}/{b['B4']} | {r['aug_n']} | {'Y' if r['stable'] else 'N'} |")
        md.append("")
    md += [f"Strong repeatable directional cells: **{result['strong_repeatable_cells'] or 'NONE'}**.",
           f"Descriptive 80% cells: **{result['candidate80_cells'] or 'NONE'}**.","",
           "This result maps recurring 1H structure only. It does not change any rejected 15m session-sweep rule and does not modify live BBC."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps({"strong":result['strong_repeatable_cells'],"c80":result['candidate80_cells'],"top":top_dir[:10]},indent=2,default=str))

if __name__=="__main__":
    main()
