#!/usr/bin/env python3
"""BTC H1 Statistical Band Reclaim SD2.

Frozen before result:
- fixed event hours 04/08/18/19 UTC
- 1H only
- causal prior24 close mean/std bands, k in {1.0,1.5,2.0,2.5}
- must also sweep/reclaim causal prior3H range
- LONG and SHORT evaluated separately
- directional +1H/+3H plus executable net-RR1:1 diagnostic
- external untouched 2020-2021 validation
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

import btc_h1_low_reject_structure_lr1 as lr1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_StatBand_Reclaim_SD2_Result.md"
OUT_JSON = ROOT / "BTC_H1_StatBand_Reclaim_SD2_Result.json"
OUT_EVENTS = ROOT / "BTC_H1_StatBand_Reclaim_SD2_Events.csv"
OUT_AUG = ROOT / "BTC_H1_StatBand_Reclaim_SD2_August.csv"

EXTERNAL_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_START = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
EVENT_HOURS = [4, 8, 18, 19]
KS = [1.0, 1.5, 2.0, 2.5]
FEE = 0.0015
NOTIONAL = 500.0

# Fixed chronological 70/30 time split for the reference window.
REFERENCE_CUT = REFERENCE_START + (REFERENCE_END - REFERENCE_START) * 0.70


def signed_ret(side: str, entry: float, final: float) -> float:
    raw = final / entry - 1.0
    return raw if side == "LONG" else -raw


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for i in range(24, len(x) - 6):
        cur = x.iloc[i]
        ts = pd.Timestamp(cur.ts)
        if int(ts.hour) not in EVENT_HOURS:
            continue

        prior24 = x.iloc[i-24:i]
        expected24 = [ts - pd.Timedelta(hours=h) for h in range(24, 0, -1)]
        if list(prior24.ts) != expected24:
            continue
        prior3 = x.iloc[i-3:i]
        expected3 = [ts - pd.Timedelta(hours=h) for h in (3, 2, 1)]
        if list(prior3.ts) != expected3:
            continue
        if x.ts.iloc[i+1] != ts + pd.Timedelta(hours=1) or x.ts.iloc[i+6] != ts + pd.Timedelta(hours=6):
            continue

        closes24 = prior24.close.to_numpy(float)
        mean24 = float(np.mean(closes24))
        std24 = float(np.std(closes24, ddof=0))
        if not np.isfinite(std24) or std24 <= 0:
            continue

        ph = float(prior3.high.max())
        pl = float(prior3.low.min())
        event_low = float(cur.low)
        event_high = float(cur.high)
        event_close = float(cur.close)
        entry = float(x.open.iloc[i+1])
        close1 = float(x.close.iloc[i+1])
        close3 = float(x.close.iloc[i+3])

        for k in KS:
            lower = mean24 - k * std24
            upper = mean24 + k * std24
            long_cond = (
                event_low < pl
                and event_low < lower
                and event_high <= ph
                and event_close >= pl
                and event_close >= lower
            )
            short_cond = (
                event_high > ph
                and event_high > upper
                and event_low >= pl
                and event_close <= ph
                and event_close <= upper
            )
            if long_cond and short_cond:
                continue
            side: Optional[str] = "LONG" if long_cond else ("SHORT" if short_cond else None)
            if side is None:
                continue

            s1 = signed_ret(side, entry, close1)
            s3 = signed_ret(side, entry, close3)
            band = lower if side == "LONG" else upper
            band_excursion = ((band - event_low) / mean24) if side == "LONG" else ((event_high - band) / mean24)
            prior_excursion = ((pl - event_low) / mean24) if side == "LONG" else ((event_high - ph) / mean24)

            rows.append({
                "event_ts": ts,
                "utc_date": ts.strftime("%Y-%m-%d"),
                "hour_utc": int(ts.hour),
                "hour_wib": int((ts.hour + 7) % 24),
                "k": float(k),
                "side": side,
                "mean24": mean24,
                "std24": std24,
                "lower_band": lower,
                "upper_band": upper,
                "prior3_high": ph,
                "prior3_low": pl,
                "event_open": float(cur.open),
                "event_high": event_high,
                "event_low": event_low,
                "event_close": event_close,
                "entry_ts": ts + pd.Timedelta(hours=1),
                "entry_price": entry,
                "band_excursion_pct": band_excursion,
                "prior3_excursion_pct": prior_excursion,
                "signed1h": s1,
                "signed3h": s3,
                "positive1h": int(s1 > 0),
                "positive3h": int(s3 > 0),
                "source_index": i,
            })
    return pd.DataFrame(rows)


def wilson_lower(wins: int, n: int, z: float = 1.96) -> Optional[float]:
    if n <= 0:
        return None
    p = wins / n
    den = 1 + z*z/n
    ctr = p + z*z/(2*n)
    adj = z * np.sqrt((p*(1-p) + z*z/(4*n))/n)
    return float((ctr-adj)/den)


def direction_stats(z: pd.DataFrame) -> dict:
    if z.empty:
        return {"n":0,"wins1h":0,"wins3h":0,"pos1h":None,"pos3h":None,"wilson3h":None,"avg3h":None,"median3h":None}
    w1 = int(z.positive1h.sum())
    w3 = int(z.positive3h.sum())
    n = int(len(z))
    return {
        "n": n,
        "wins1h": w1,
        "wins3h": w3,
        "pos1h": float(w1/n),
        "pos3h": float(w3/n),
        "wilson3h": wilson_lower(w3,n),
        "avg3h": float(z.signed3h.mean()),
        "median3h": float(z.signed3h.median()),
    }


def execution_rows(x: pd.DataFrame, z: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, r in z.iterrows():
        i = int(r.source_index)
        side = str(r.side)
        entry = float(x.open.iloc[i+1])
        if side == "LONG":
            sl = float(r.event_low)
            if entry <= sl:
                continue
            risk = (entry - sl) / entry
            target_dist = risk + 2.0 * FEE
            tp = entry * (1.0 + target_dist)
        else:
            sl = float(r.event_high)
            if entry >= sl:
                continue
            risk = (sl - entry) / entry
            target_dist = risk + 2.0 * FEE
            tp = entry * (1.0 - target_dist)
        if risk <= 0 or target_dist <= 0:
            continue

        f = x.iloc[i+1:i+7]
        if len(f) != 6 or f.ts.iloc[-1] != pd.Timestamp(r.event_ts) + pd.Timedelta(hours=6):
            continue
        highs = f.high.to_numpy(float)
        lows = f.low.to_numpy(float)
        if side == "LONG":
            tp_hits = np.flatnonzero(highs >= tp)
            sl_hits = np.flatnonzero(lows <= sl)
        else:
            tp_hits = np.flatnonzero(lows <= tp)
            sl_hits = np.flatnonzero(highs >= sl)
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
            final = float(f.close.iloc[-1])
            raw = (final/entry - 1.0) if side == "LONG" else (entry/final - 1.0)

        net = raw - FEE
        rows.append({
            "event_ts": r.event_ts,
            "k": float(r.k),
            "side": side,
            "outcome": outcome,
            "risk_pct": risk,
            "target_pct": target_dist,
            "net_ret": net,
            "pnl": net * NOTIONAL,
        })
    return pd.DataFrame(rows)


def execution_stats(e: pd.DataFrame) -> dict:
    if e.empty:
        return {"n":0,"tp":0,"sl":0,"time":0,"decisive_wr":None,"pnl":0.0,"expectancy":None,"median_risk":None,"avg_target":None}
    dec = e[e.outcome.isin(["TP","SL"])]
    return {
        "n": int(len(e)),
        "tp": int((e.outcome=="TP").sum()),
        "sl": int((e.outcome=="SL").sum()),
        "time": int((e.outcome=="TIME").sum()),
        "decisive_wr": float((dec.outcome=="TP").mean()) if len(dec) else None,
        "pnl": float(e.pnl.sum()),
        "expectancy": float(e.pnl.mean()),
        "median_risk": float(e.risk_pct.median()),
        "avg_target": float(e.target_pct.mean()),
    }


def external_blocks(z: pd.DataFrame) -> list[dict]:
    if z.empty:
        return []
    y = z.sort_values("event_ts").reset_index(drop=True)
    bounds = np.linspace(0, len(y), 5, dtype=int)
    out=[]
    for j in range(4):
        q = y.iloc[bounds[j]:bounds[j+1]]
        out.append({"block":f"B{j+1}", **direction_stats(q)})
    return out


def by_hour(z: pd.DataFrame) -> list[dict]:
    out=[]
    for h in EVENT_HOURS:
        q=z[z.hour_utc==h]
        out.append({"hour_utc":h,"hour_wib":(h+7)%24,**direction_stats(q)})
    return out


def pct(v: Optional[float]) -> str:
    return "-" if v is None else f"{100*v:.2f}%"


def candidate_key(k: float, side: str) -> str:
    return f"{side}_K{k:.1f}"


def main():
    x = lr1.load_1h()
    ev = build_events(x)
    if ev.empty:
        raise RuntimeError("no SD2 events")
    ev.to_csv(OUT_EVENTS,index=False)

    partitions = {
        "development": ev[(ev.event_ts>=REFERENCE_START)&(ev.event_ts<REFERENCE_CUT)],
        "reference_validation": ev[(ev.event_ts>=REFERENCE_CUT)&(ev.event_ts<REFERENCE_END)],
        "external": ev[(ev.event_ts>=EXTERNAL_START)&(ev.event_ts<EXTERNAL_END)],
        "august": ev[(ev.event_ts>=AUG_START)&(ev.event_ts<AUG_END)],
    }
    if partitions["august"].empty:
        pd.DataFrame(columns=["event_ts"]).to_csv(OUT_AUG,index=False)
    else:
        partitions["august"].to_csv(OUT_AUG,index=False)

    candidates=[]
    for k in KS:
        for side in ("LONG","SHORT"):
            key=candidate_key(k,side)
            d={}
            e={}
            for pname,pdf in partitions.items():
                q=pdf[(pdf.k==k)&(pdf.side==side)].copy()
                d[pname]=direction_stats(q)
                e[pname]=execution_stats(execution_rows(x,q))
            extq=partitions["external"][(partitions["external"].k==k)&(partitions["external"].side==side)].copy()
            valq=partitions["reference_validation"][(partitions["reference_validation"].k==k)&(partitions["reference_validation"].side==side)].copy()
            augq=partitions["august"][(partitions["august"].k==k)&(partitions["august"].side==side)].copy()
            blocks=external_blocks(extq)
            block_support=sum(1 for b in blocks if b["n"]>=5 and b["pos3h"] is not None and b["pos3h"]>=.60)
            block80=sum(1 for b in blocks if b["n"]>=5 and b["pos3h"] is not None and b["pos3h"]>=.70)
            direction_supported=bool(
                d["reference_validation"]["n"]>=20 and d["reference_validation"]["pos3h"] is not None and d["reference_validation"]["pos3h"]>=.70
                and d["external"]["n"]>=30 and d["external"]["pos3h"] is not None and d["external"]["pos3h"]>=.65
                and block_support>=3
            )
            cand80=bool(
                d["reference_validation"]["n"]>=20 and d["reference_validation"]["pos3h"] is not None and d["reference_validation"]["pos3h"]>=.80
                and d["external"]["n"]>=30 and d["external"]["pos3h"] is not None and d["external"]["pos3h"]>=.80
                and block80>=3
            )
            exec_supported=bool(
                e["reference_validation"]["n"]>=20 and e["reference_validation"]["decisive_wr"] is not None and e["reference_validation"]["decisive_wr"]>.50 and e["reference_validation"]["pnl"]>0
                and e["external"]["n"]>=30 and e["external"]["decisive_wr"] is not None and e["external"]["decisive_wr"]>.50 and e["external"]["pnl"]>0
            )
            candidates.append({
                "key":key,"k":k,"side":side,"direction":d,"execution":e,
                "external_blocks":blocks,"validation_by_hour":by_hour(valq),"external_by_hour":by_hour(extq),"august_by_hour":by_hour(augq),
                "SD2_DIRECTION_SUPPORTED":direction_supported,
                "SD2_80_CANDIDATE":cand80,
                "SD2_EXECUTION_SUPPORTED":exec_supported,
            })

    result={
        "protocol":"BTC_H1_STATBAND_RECLAIM_SD2",
        "coverage":{"first":str(x.ts.min()),"last":str(x.ts.max()),"rows1h":int(len(x))},
        "reference_cut":str(REFERENCE_CUT),
        "event_rows":int(len(ev)),
        "candidates":candidates,
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+"\n")

    md=[
        "# BTC H1 Statistical Band Reclaim SD2 — Result",
        "",
        "Fixed clocks: **11:00 / 15:00 / 01:00 / 02:00 WIB**. Band = prior24 completed 1H closes mean ± k×population-std. Event must also sweep/reclaim the causal prior3H range.",
        "",
        f"Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x)}**. Reference chronological cut: **{REFERENCE_CUT}**.",
        "",
        "## Directional matrix",
        "",
        "| Candidate | Dev N/+3H | Validation N/+3H | External N/+3H | August N/+3H | Dir supported | 80% |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for c in candidates:
        d=c["direction"]
        md.append(
            f"| `{c['key']}` | {d['development']['n']}/{pct(d['development']['pos3h'])} | "
            f"{d['reference_validation']['n']}/{pct(d['reference_validation']['pos3h'])} | "
            f"{d['external']['n']}/{pct(d['external']['pos3h'])} | "
            f"{d['august']['n']}/{pct(d['august']['pos3h'])} | "
            f"{'PASS' if c['SD2_DIRECTION_SUPPORTED'] else 'FAIL'} | {'PASS' if c['SD2_80_CANDIDATE'] else 'FAIL'} |"
        )

    md += [
        "",
        "## Executable net RR 1:1 matrix",
        "",
        "Next1H open; structural SL at event extreme; target raw distance = risk +0.30%; fee0.15%; max6H; adverse-first same-hour ambiguity.",
        "",
        "| Candidate | Validation N/WR/PnL | External N/WR/PnL | August N/WR/PnL | Exec supported |",
        "|---|---:|---:|---:|---|",
    ]
    for c in candidates:
        e=c["execution"]
        md.append(
            f"| `{c['key']}` | {e['reference_validation']['n']}/{pct(e['reference_validation']['decisive_wr'])}/${e['reference_validation']['pnl']:.2f} | "
            f"{e['external']['n']}/{pct(e['external']['decisive_wr'])}/${e['external']['pnl']:.2f} | "
            f"{e['august']['n']}/{pct(e['august']['decisive_wr'])}/${e['august']['pnl']:.2f} | "
            f"{'PASS' if c['SD2_EXECUTION_SUPPORTED'] else 'FAIL'} |"
        )

    passed=[c for c in candidates if c["SD2_DIRECTION_SUPPORTED"] or c["SD2_80_CANDIDATE"] or c["SD2_EXECUTION_SUPPORTED"]]
    md += ["", f"Directional/execution gate passes: **{len(passed)} candidate(s)**.", ""]

    # Add external blocks for all candidates with enough external observations to interpret.
    md += ["## External chronological blocks", ""]
    for c in candidates:
        if c["direction"]["external"]["n"] < 10:
            continue
        md += [f"### {c['key']}", "", "| Block | N | +3H | Avg3H |", "|---|---:|---:|---:|"]
        for b in c["external_blocks"]:
            md.append(f"| {b['block']} | {b['n']} | {pct(b['pos3h'])} | {pct(b['avg3h'])} |")
        md.append("")

    md += ["No k/side is reselected from validation, external, or August. No post-result rescue."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps(result,indent=2,default=str))


if __name__ == "__main__":
    main()
