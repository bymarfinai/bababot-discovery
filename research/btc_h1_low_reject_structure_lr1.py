#!/usr/bin/env python3
"""BTC H1 LOW_REJECT Structure LR1.

Frozen before result:
- exact event hours 04/08/18/19 UTC
- 1H only, LOW_REJECT vs completed prior3H range
- six event-candle structural features
- one shallow depth-2 tree selected on reference-development only
- external untouched 2020-2021 validation
- directional 3H target; executable net-RR1:1 diagnostic separately
"""
from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_LowReject_Structure_LR1_Result.md"
OUT_JSON = ROOT / "BTC_H1_LowReject_Structure_LR1_Result.json"
OUT_EVENTS = ROOT / "BTC_H1_LowReject_Structure_LR1_Events.csv"
OUT_AUG = ROOT / "BTC_H1_LowReject_Structure_LR1_August.csv"
OUT_TREE = ROOT / "BTC_H1_LowReject_Structure_LR1_Leafs.csv"

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
TF = "1h"
LOAD_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_START = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
EVENT_HOURS = [4, 8, 18, 19]
FEATURES = [
    "sweep_depth_range",
    "lower_wick_ratio",
    "close_position",
    "body_ratio",
    "range_expansion",
    "reclaim_depth_range",
]
FEE = 0.0015
NOTIONAL = 500.0


def fetch_zip(url: str) -> list[list[float]]:
    r = requests.get(url, timeout=60, headers={"User-Agent": "bababot-h1-lr1/1.0"})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    rows: list[list[float]] = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return []
        with zf.open(names[0]) as fh:
            for row in csv.reader(io.TextIOWrapper(fh, encoding="utf-8")):
                if len(row) < 5:
                    continue
                try:
                    ts = int(row[0])
                except Exception:
                    continue
                if ts > 100_000_000_000_000:
                    ts //= 1000
                try:
                    rows.append([ts, float(row[1]), float(row[2]), float(row[3]), float(row[4])])
                except Exception:
                    continue
    return rows


def archive_urls() -> list[str]:
    jobs: list[str] = []
    cur = pd.Timestamp(2020, 1, 1, tz="UTC")
    stop = pd.Timestamp(2026, 8, 1, tz="UTC")
    while cur < stop:
        ym = cur.strftime("%Y-%m")
        jobs.append(f"{BASE}/monthly/klines/{SYMBOL}/{TF}/{SYMBOL}-{TF}-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    d = AUG_START
    while d < AUG_END:
        ds = d.strftime("%Y-%m-%d")
        jobs.append(f"{BASE}/daily/klines/{SYMBOL}/{TF}/{SYMBOL}-{TF}-{ds}.zip")
        d += pd.Timedelta(days=1)
    return jobs


def load_1h() -> pd.DataFrame:
    jobs = archive_urls()
    rows: list[list[float]] = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(fetch_zip, u): u for u in jobs}
        done = 0
        for f in as_completed(futs):
            rows.extend(f.result())
            done += 1
            if done % 10 == 0:
                print(f"downloaded {done}/{len(jobs)} archives")
    if not rows:
        raise RuntimeError("no 1H Binance data downloaded")
    x = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
    x["ts"] = pd.to_datetime(pd.to_numeric(x.ts), unit="ms", utc=True)
    x = x.dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    x = x[(x.ts >= LOAD_START) & (x.ts < AUG_END)].reset_index(drop=True)
    return x


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i in range(3, len(x) - 6):
        cur = x.iloc[i]
        ts = pd.Timestamp(cur.ts)
        if int(ts.hour) not in EVENT_HOURS:
            continue
        prior = x.iloc[i-3:i]
        expected_prior = [ts - pd.Timedelta(hours=h) for h in (3, 2, 1)]
        if list(prior.ts) != expected_prior:
            continue
        if x.ts.iloc[i+1] != ts + pd.Timedelta(hours=1) or x.ts.iloc[i+6] != ts + pd.Timedelta(hours=6):
            continue
        ph = float(prior.high.max())
        pl = float(prior.low.min())
        pr = ph - pl
        event_range = float(cur.high - cur.low)
        med_prior_range = float(np.median((prior.high - prior.low).to_numpy(float)))
        if pr <= 0 or event_range <= 0 or med_prior_range <= 0:
            continue
        # Exact H1-MAP LOW_REJECT: low side only, closes back inside.
        if not (float(cur.low) < pl and float(cur.high) <= ph and float(cur.close) >= pl):
            continue

        lower_wick = min(float(cur.open), float(cur.close)) - float(cur.low)
        entry = float(x.open.iloc[i+1])
        close1 = float(x.close.iloc[i+1])
        close3 = float(x.close.iloc[i+3])
        ret1 = close1 / entry - 1.0
        ret3 = close3 / entry - 1.0

        rows.append({
            "event_ts": ts,
            "utc_date": ts.strftime("%Y-%m-%d"),
            "event_hour_utc": int(ts.hour),
            "event_hour_wib": int((ts.hour + 7) % 24),
            "prior3_high": ph,
            "prior3_low": pl,
            "event_open": float(cur.open),
            "event_high": float(cur.high),
            "event_low": float(cur.low),
            "event_close": float(cur.close),
            "entry_ts": ts + pd.Timedelta(hours=1),
            "entry_price": entry,
            "sweep_depth_range": (pl - float(cur.low)) / pr,
            "lower_wick_ratio": lower_wick / event_range,
            "close_position": (float(cur.close) - float(cur.low)) / event_range,
            "body_ratio": abs(float(cur.close) - float(cur.open)) / event_range,
            "range_expansion": event_range / med_prior_range,
            "reclaim_depth_range": (float(cur.close) - pl) / pr,
            "ret1h_long": ret1,
            "ret3h_long": ret3,
            "positive1h": int(ret1 > 0),
            "positive3h": int(ret3 > 0),
            "source_index": i,
        })
    return pd.DataFrame(rows)


def tree_leaf_path(clf: DecisionTreeClassifier, leaf_id: int) -> list[str]:
    tree = clf.tree_
    parent: dict[int, tuple[int, str]] = {}
    for node in range(tree.node_count):
        l = int(tree.children_left[node]); r = int(tree.children_right[node])
        if l >= 0:
            fname = FEATURES[int(tree.feature[node])]
            thr = float(tree.threshold[node])
            parent[l] = (node, f"{fname} <= {thr:.8f}")
            parent[r] = (node, f"{fname} > {thr:.8f}")
    path = []
    cur = int(leaf_id)
    while cur in parent:
        p, cond = parent[cur]
        path.append(cond)
        cur = p
    return list(reversed(path))


def direction_stats(z: pd.DataFrame) -> dict:
    if z.empty:
        return {"n":0,"pos1h":None,"pos3h":None,"avg3h":None,"median3h":None}
    return {
        "n": int(len(z)),
        "pos1h": float(z.positive1h.mean()),
        "pos3h": float(z.positive3h.mean()),
        "avg3h": float(z.ret3h_long.mean()),
        "median3h": float(z.ret3h_long.median()),
    }


def execution_rows(x: pd.DataFrame, z: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in z.iterrows():
        i = int(r.source_index)
        entry = float(x.open.iloc[i+1])
        sl = float(r.event_low)
        if entry <= sl:
            continue
        risk = (entry - sl) / entry
        target_dist = risk + 2.0 * FEE
        tp = entry * (1.0 + target_dist)
        f = x.iloc[i+1:i+7]
        if len(f) != 6 or f.ts.iloc[-1] != pd.Timestamp(r.event_ts) + pd.Timedelta(hours=6):
            continue
        highs = f.high.to_numpy(float); lows = f.low.to_numpy(float)
        tp_hits = np.flatnonzero(highs >= tp)
        sl_hits = np.flatnonzero(lows <= sl)
        ti = int(tp_hits[0]) if tp_hits.size else 10**9
        si = int(sl_hits[0]) if sl_hits.size else 10**9
        if si <= ti:
            outcome = "SL"; raw = -risk
        elif ti < 10**9:
            outcome = "TP"; raw = target_dist
        else:
            outcome = "TIME"; raw = float(f.close.iloc[-1]) / entry - 1.0
        net = raw - FEE
        rows.append({
            "event_ts": r.event_ts,
            "event_hour_utc": int(r.event_hour_utc),
            "outcome": outcome,
            "risk_pct": risk,
            "target_pct": target_dist,
            "net_ret": net,
            "pnl": net * NOTIONAL,
        })
    return pd.DataFrame(rows)


def execution_stats(e: pd.DataFrame) -> dict:
    if e.empty:
        return {"n":0,"tp":0,"sl":0,"time":0,"decisive_wr":None,"net_positive_rate":None,"pnl":0.0,"expectancy":None,"median_risk":None,"avg_target":None}
    dec = e[e.outcome.isin(["TP","SL"])]
    return {
        "n": int(len(e)),
        "tp": int((e.outcome=="TP").sum()),
        "sl": int((e.outcome=="SL").sum()),
        "time": int((e.outcome=="TIME").sum()),
        "decisive_wr": float((dec.outcome=="TP").mean()) if len(dec) else None,
        "net_positive_rate": float((e.net_ret>0).mean()),
        "pnl": float(e.pnl.sum()),
        "expectancy": float(e.pnl.mean()),
        "median_risk": float(e.risk_pct.median()),
        "avg_target": float(e.target_pct.mean()),
    }


def block_stats(z: pd.DataFrame) -> list[dict]:
    if z.empty:
        return []
    y = z.sort_values("event_ts").reset_index(drop=True)
    bounds = np.linspace(0, len(y), 5, dtype=int)
    out = []
    for j in range(4):
        p = y.iloc[bounds[j]:bounds[j+1]]
        out.append({"block":f"B{j+1}", **direction_stats(p)})
    return out


def per_hour(z: pd.DataFrame) -> list[dict]:
    out=[]
    for h in EVENT_HOURS:
        q=z[z.event_hour_utc==h]
        out.append({"hour_utc":h,"hour_wib":(h+7)%24,**direction_stats(q)})
    return out


def pct(v):
    return "-" if v is None else f"{100*v:.2f}%"


def main():
    x = load_1h()
    ev = build_events(x)
    ext = ev[(ev.event_ts>=EXTERNAL_START)&(ev.event_ts<EXTERNAL_END)].sort_values("event_ts").reset_index(drop=True)
    ref = ev[(ev.event_ts>=REFERENCE_START)&(ev.event_ts<REFERENCE_END)].sort_values("event_ts").reset_index(drop=True)
    aug = ev[(ev.event_ts>=AUG_START)&(ev.event_ts<AUG_END)].sort_values("event_ts").reset_index(drop=True)
    cut = int(math.floor(len(ref)*0.70))
    dev = ref.iloc[:cut].copy(); val = ref.iloc[cut:].copy()
    if len(dev) < 100:
        raise RuntimeError(f"development sample unexpectedly small: {len(dev)}")

    clf = DecisionTreeClassifier(criterion="gini",max_depth=2,max_leaf_nodes=4,min_samples_leaf=25,random_state=20260819)
    clf.fit(dev[FEATURES].to_numpy(float), dev.positive3h.to_numpy(int))
    dev_leaf = clf.apply(dev[FEATURES].to_numpy(float))
    leaf_rows=[]
    for leaf in sorted(set(int(v) for v in dev_leaf)):
        mask=dev_leaf==leaf; q=dev.loc[mask]
        leaf_rows.append({"leaf":leaf,"n":int(len(q)),"pos3h":float(q.positive3h.mean()),"avg3h":float(q.ret3h_long.mean()),"path":" AND ".join(tree_leaf_path(clf,leaf))})
    eligible=[r for r in leaf_rows if r["n"]>=25]
    if not eligible:
        raise RuntimeError("no eligible development leaf")
    eligible.sort(key=lambda r:(-r["pos3h"],-r["n"],r["leaf"]))
    selected=eligible[0]
    leaf_id=int(selected["leaf"])
    pd.DataFrame(leaf_rows).sort_values(["pos3h","n"],ascending=[False,False]).to_csv(OUT_TREE,index=False)

    def choose(z: pd.DataFrame) -> pd.DataFrame:
        if z.empty: return z.copy()
        leaves=clf.apply(z[FEATURES].to_numpy(float))
        return z.loc[leaves==leaf_id].copy()

    cohorts={
        "development_selected":choose(dev),"reference_validation_selected":choose(val),"external_selected":choose(ext),"august_selected":choose(aug),
        "development_control":dev,"reference_validation_control":val,"external_control":ext,"august_control":aug,
    }
    dirstats={k:direction_stats(v) for k,v in cohorts.items()}
    execstats={k:execution_stats(execution_rows(x,v)) for k,v in cohorts.items()}
    ext_sel=cohorts["external_selected"]
    ext_blocks=block_stats(ext_sel)
    val_sel=cohorts["reference_validation_selected"]
    aug_sel=cohorts["august_selected"]

    qualifying_blocks=sum(1 for b in ext_blocks if b["n"]>=5 and b["pos3h"] is not None and b["pos3h"]>=.60)
    qualifying_blocks80=sum(1 for b in ext_blocks if b["n"]>=5 and b["pos3h"] is not None and b["pos3h"]>=.70)
    supported=bool(len(val_sel)>=20 and dirstats["reference_validation_selected"]["pos3h"] is not None and dirstats["reference_validation_selected"]["pos3h"]>=.70 and len(ext_sel)>=20 and dirstats["external_selected"]["pos3h"] is not None and dirstats["external_selected"]["pos3h"]>=.70 and qualifying_blocks>=3)
    c80=bool(len(val_sel)>=20 and dirstats["reference_validation_selected"]["pos3h"] is not None and dirstats["reference_validation_selected"]["pos3h"]>=.80 and len(ext_sel)>=20 and dirstats["external_selected"]["pos3h"] is not None and dirstats["external_selected"]["pos3h"]>=.80 and qualifying_blocks80>=3)

    all_events=ev.copy()
    all_events["selected_leaf"] = False
    if not ev.empty:
        all_events["selected_leaf"] = clf.apply(ev[FEATURES].to_numpy(float)) == leaf_id
    all_events.to_csv(OUT_EVENTS,index=False)
    if aug_sel.empty: pd.DataFrame(columns=["event_ts"]).to_csv(OUT_AUG,index=False)
    else: aug_sel.to_csv(OUT_AUG,index=False)

    result={
        "protocol":"BTC_H1_LOW_REJECT_STRUCTURE_LR1",
        "coverage":{"first":str(x.ts.min()),"last":str(x.ts.max()),"rows1h":int(len(x))},
        "counts":{"external":len(ext),"reference":len(ref),"development":len(dev),"reference_validation":len(val),"august":len(aug)},
        "selected_leaf":selected,
        "all_development_leafs":leaf_rows,
        "directional":dirstats,
        "execution_net_rr1":execstats,
        "external_blocks":ext_blocks,
        "per_hour":{"validation_selected":per_hour(val_sel),"external_selected":per_hour(ext_sel),"august_selected":per_hour(aug_sel)},
        "LR1_STRUCTURE_SUPPORTED":supported,
        "LR1_80_CANDIDATE":c80,
        "guardrails":{"one_hour_only":True,"event_hours_utc":EVENT_HOURS,"prior_range_hours":3,"august_used_for_selection":False,"external_used_for_selection":False},
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+"\n")

    md=["# BTC H1 LOW_REJECT Structure LR1 — Result","",
        "Four fixed event hours only: **04/08/18/19 UTC = 11:00/15:00/01:00/02:00 WIB**. Event is LOW_REJECT vs completed prior3H range. Timeframe 1H only.","",
        f"Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**. Core LOW_REJECT events: external **{len(ext)}**, reference **{len(ref)}** (dev {len(dev)}, validation {len(val)}), August **{len(aug)}**.","",
        "## Selected structural leaf","",
        f"Development leaf **{leaf_id}**, N **{selected['n']}**, next3H LONG-positive **{pct(selected['pos3h'])}**.",
        f"Exact path: **{selected['path']}**","",
        "## Directional validation","",
        "| Partition | Rule | N | +1H | +3H | Avg 3H | Median 3H |",
        "|---|---|---:|---:|---:|---:|---:|" ]
    for part in ["development","reference_validation","external","august"]:
        for rule in ["selected","control"]:
            s=dirstats[f"{part}_{rule}"]
            md.append(f"| {part} | {rule} | {s['n']} | {pct(s['pos1h'])} | {pct(s['pos3h'])} | {pct(s['avg3h'])} | {pct(s['median3h'])} |")
    md += ["","## Executable net RR 1:1 diagnostic","",
           "LONG next1H open; SL=LOW_REJECT candle low; TP raw distance=risk+0.30%; fee0.15%; max hold6H; same-hour ambiguity adverse-first.","",
           "| Partition | Rule | N | TP | SL | TIME | Decisive WR | Net+ | PnL | Exp/trade | Median risk | Avg target |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for part in ["development","reference_validation","external","august"]:
        for rule in ["selected","control"]:
            s=execstats[f"{part}_{rule}"]
            exp="-" if s["expectancy"] is None else f"${s['expectancy']:.3f}"
            md.append(f"| {part} | {rule} | {s['n']} | {s['tp']} | {s['sl']} | {s['time']} | {pct(s['decisive_wr'])} | {pct(s['net_positive_rate'])} | ${s['pnl']:.2f} | {exp} | {pct(s['median_risk'])} | {pct(s['avg_target'])} |")
    md += ["","## External selected-leaf chronological blocks","","| Block | N | +1H | +3H | Avg3H |","|---|---:|---:|---:|---:|"]
    for b in ext_blocks:
        md.append(f"| {b['block']} | {b['n']} | {pct(b['pos1h'])} | {pct(b['pos3h'])} | {pct(b['avg3h'])} |")
    md += ["","## Selected leaf by clock","","### Reference validation","","| UTC/WIB | N | +3H | Avg3H |","|---|---:|---:|---:|"]
    for q in per_hour(val_sel): md.append(f"| {q['hour_utc']:02d}:00 / {q['hour_wib']:02d}:00 | {q['n']} | {pct(q['pos3h'])} | {pct(q['avg3h'])} |")
    md += ["","### External 2020-2021","","| UTC/WIB | N | +3H | Avg3H |","|---|---:|---:|---:|"]
    for q in per_hour(ext_sel): md.append(f"| {q['hour_utc']:02d}:00 / {q['hour_wib']:02d}:00 | {q['n']} | {pct(q['pos3h'])} | {pct(q['avg3h'])} |")
    md += ["",f"**LR1_STRUCTURE_SUPPORTED: {'PASS' if supported else 'FAIL'}**",f"**LR1_80_CANDIDATE: {'PASS' if c80 else 'FAIL'}**","",
           "The leaf was selected on reference-development only. Validation, untouched 2020-2021, and August were not used to choose the structural thresholds. No post-result tree/feature/time rescue."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps(result,indent=2,default=str))


if __name__ == "__main__":
    main()
