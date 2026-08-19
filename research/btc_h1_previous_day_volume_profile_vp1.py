#!/usr/bin/env python3
"""BTC H1 Previous-Day Volume Profile VP1.

Frozen before result:
- signal timeframe 1H, no 1m
- previous UTC day profile from completed 5m BTCUSDT USD-M klines
- 100 equal-width bins, overlap-weighted base volume
- contiguous 70% value area expanded from POC
- fixed event clocks 04/08/18/19 UTC
- VAL failed auction -> LONG, VAH failed auction -> SHORT
- POC magnet, full-value rotation, and net-RR1:1 diagnostics
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

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_PreviousDay_VolumeProfile_VP1_Result.md"
OUT_JSON = ROOT / "BTC_H1_PreviousDay_VolumeProfile_VP1_Result.json"
OUT_EVENTS = ROOT / "BTC_H1_PreviousDay_VolumeProfile_VP1_Events.csv"
OUT_AUG = ROOT / "BTC_H1_PreviousDay_VolumeProfile_VP1_August.csv"
OUT_PROFILES = ROOT / "BTC_H1_PreviousDay_VolumeProfile_VP1_Profiles.csv"

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
TF = "5m"
LOAD_START = pd.Timestamp("2019-12-31T00:00:00Z")
EXTERNAL_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_START = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")
EVENT_HOURS = [4, 8, 18, 19]
BINS = 100
VA_FRAC = 0.70
FEE = 0.0015
NOTIONAL = 500.0
MAX_HOLD = 6


def fetch_zip(url: str) -> list[list[float]]:
    r = requests.get(url, timeout=60, headers={"User-Agent": "bababot-vp1/1.0"})
    if r.status_code == 404:
        return []
    r.raise_for_status()
    rows: list[list[float]] = []
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return []
        with zf.open(names[0]) as fh:
            reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
            for row in reader:
                if len(row) < 6:
                    continue
                try:
                    ts = int(row[0])
                except Exception:
                    continue
                if ts > 100_000_000_000_000:
                    ts //= 1000
                try:
                    rows.append([
                        ts,
                        float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]),
                    ])
                except Exception:
                    continue
    return rows


def archive_urls() -> list[str]:
    jobs: list[str] = []
    cur = pd.Timestamp("2019-12-01T00:00:00Z")
    stop = pd.Timestamp("2026-08-01T00:00:00Z")
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


def load_5m() -> pd.DataFrame:
    jobs = archive_urls()
    rows: list[list[float]] = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(fetch_zip, u): u for u in jobs}
        done = 0
        for fut in as_completed(futs):
            rows.extend(fut.result())
            done += 1
            if done % 10 == 0:
                print(f"downloaded {done}/{len(jobs)} archives")
    if not rows:
        raise RuntimeError("no Binance 5m data downloaded")
    x = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    x["ts"] = pd.to_datetime(pd.to_numeric(x.ts), unit="ms", utc=True)
    x = x.dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    x = x[(x.ts >= LOAD_START) & (x.ts < AUG_END)].reset_index(drop=True)
    return x


def aggregate_1h(x5: pd.DataFrame) -> pd.DataFrame:
    y = x5.set_index("ts")
    z = y.resample("1h", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"), count=("close", "count"),
    ).dropna().reset_index()
    z = z[z["count"] == 12].reset_index(drop=True)
    return z


def exact_day(z: pd.DataFrame, day: pd.Timestamp) -> bool:
    if len(z) != 288:
        return False
    expected = pd.date_range(day, day + pd.Timedelta(days=1) - pd.Timedelta(minutes=5), freq="5min", tz="UTC")
    return list(z.ts) == list(expected)


def make_profile(z: pd.DataFrame, day: pd.Timestamp) -> dict | None:
    if not exact_day(z, day):
        return None
    lo = float(z.low.min())
    hi = float(z.high.max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return None
    edges = np.linspace(lo, hi, BINS + 1)
    vap = np.zeros(BINS, dtype=float)
    width = (hi - lo) / BINS

    for r in z.itertuples(index=False):
        l = float(r.low); h = float(r.high); v = float(r.volume)
        if not np.isfinite(v) or v <= 0:
            continue
        if h <= l:
            j = int(np.clip(math.floor((float(r.close) - lo) / width), 0, BINS - 1))
            vap[j] += v
            continue
        start = int(np.clip(math.floor((l - lo) / width), 0, BINS - 1))
        end = int(np.clip(math.floor((h - lo) / width), 0, BINS - 1))
        denom = h - l
        allocated = 0.0
        for j in range(start, end + 1):
            overlap = max(0.0, min(h, edges[j + 1]) - max(l, edges[j]))
            if overlap > 0:
                add = v * overlap / denom
                vap[j] += add
                allocated += add
        # Numeric endpoint fallback only.
        if allocated <= 0:
            j = int(np.clip(math.floor(((l + h) * 0.5 - lo) / width), 0, BINS - 1))
            vap[j] += v

    total = float(vap.sum())
    if total <= 0:
        return None
    poc_idx = int(np.argmax(vap))
    target = VA_FRAC * total
    left = right = poc_idx
    cum = float(vap[poc_idx])
    while cum < target and (left > 0 or right < BINS - 1):
        lv = float(vap[left - 1]) if left > 0 else -1.0
        rv = float(vap[right + 1]) if right < BINS - 1 else -1.0
        # Lower side wins exact tie, as preregistered.
        if left > 0 and (right >= BINS - 1 or lv >= rv):
            left -= 1
            cum += float(vap[left])
        elif right < BINS - 1:
            right += 1
            cum += float(vap[right])
        else:
            break

    poc = float((edges[poc_idx] + edges[poc_idx + 1]) * 0.5)
    val = float(edges[left])
    vah = float(edges[right + 1])
    return {
        "profile_day": day,
        "day_low": lo,
        "day_high": hi,
        "poc": poc,
        "val": val,
        "vah": vah,
        "poc_bin": poc_idx,
        "val_bin": left,
        "vah_bin": right,
        "va_coverage": float(cum / total),
        "total_volume": total,
    }


def build_profiles(x5: pd.DataFrame) -> pd.DataFrame:
    work = x5.copy()
    work["day"] = work.ts.dt.floor("D")
    rows = []
    for day, z in work.groupby("day", sort=True):
        p = make_profile(z.reset_index(drop=True), pd.Timestamp(day))
        if p is not None:
            rows.append(p)
    return pd.DataFrame(rows)


def signed_return(direction: str, entry: float, final: float) -> float:
    raw = final / entry - 1.0
    return raw if direction == "LONG" else -raw


def build_events(x1: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    pmap = {pd.Timestamp(r.profile_day): r for r in profiles.itertuples(index=False)}
    idx = {pd.Timestamp(t): i for i, t in enumerate(x1.ts)}
    rows = []
    for i, cur in x1.iterrows():
        ts = pd.Timestamp(cur.ts)
        if int(ts.hour) not in EVENT_HOURS:
            continue
        if i + MAX_HOLD >= len(x1):
            continue
        # Require exact next six completed 1H bars.
        ok = True
        for j in range(1, MAX_HOLD + 1):
            if pd.Timestamp(x1.ts.iloc[i + j]) != ts + pd.Timedelta(hours=j):
                ok = False
                break
        if not ok:
            continue
        prev_day = ts.floor("D") - pd.Timedelta(days=1)
        p = pmap.get(prev_day)
        if p is None:
            continue
        val = float(p.val); vah = float(p.vah); poc = float(p.poc)
        low = float(cur.low); high = float(cur.high); close = float(cur.close)
        direction = None
        if low < val and high <= vah and val < close <= vah:
            direction = "LONG"
        elif high > vah and low >= val and val <= close < vah:
            direction = "SHORT"
        if direction is None:
            continue
        entry = float(x1.open.iloc[i + 1])
        close1 = float(x1.close.iloc[i + 1])
        close3 = float(x1.close.iloc[i + 3])
        s1 = signed_return(direction, entry, close1)
        s3 = signed_return(direction, entry, close3)
        rows.append({
            "event_ts": ts,
            "utc_date": ts.strftime("%Y-%m-%d"),
            "event_hour_utc": int(ts.hour),
            "event_hour_wib": int((ts.hour + 7) % 24),
            "direction": direction,
            "profile_day": prev_day,
            "poc": poc,
            "val": val,
            "vah": vah,
            "event_open": float(cur.open),
            "event_high": high,
            "event_low": low,
            "event_close": close,
            "entry_ts": ts + pd.Timedelta(hours=1),
            "entry_price": entry,
            "signed1h": s1,
            "signed3h": s3,
            "positive1h": int(s1 > 0),
            "positive3h": int(s3 > 0),
            "source_index": int(i),
        })
    return pd.DataFrame(rows)


def first_hit_outcome(x1: pd.DataFrame, r: pd.Series, target: float, adverse: float) -> str:
    i = int(r.source_index)
    f = x1.iloc[i + 1:i + 1 + MAX_HOLD]
    direction = str(r.direction)
    if direction == "LONG":
        target_hits = np.flatnonzero(f.high.to_numpy(float) >= target)
        adverse_hits = np.flatnonzero(f.low.to_numpy(float) <= adverse)
    else:
        target_hits = np.flatnonzero(f.low.to_numpy(float) <= target)
        adverse_hits = np.flatnonzero(f.high.to_numpy(float) >= adverse)
    ti = int(target_hits[0]) if target_hits.size else 10**9
    ai = int(adverse_hits[0]) if adverse_hits.size else 10**9
    if ai <= ti:
        return "ADVERSE"
    if ti < 10**9:
        return "TARGET"
    return "TIME"


def add_rotation_outcomes(x1: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    if ev.empty:
        return ev.copy()
    y = ev.copy()
    poc_eligible = []
    poc_outcome = []
    va_eligible = []
    va_outcome = []
    exec_outcome = []
    exec_net = []
    exec_pnl = []
    exec_risk = []

    for _, r in y.iterrows():
        direction = str(r.direction)
        entry = float(r.entry_price)
        poc = float(r.poc); val = float(r.val); vah = float(r.vah)
        if direction == "LONG":
            adverse = float(r.event_low)
            pe = entry < poc
            ve = entry < vah
            po = first_hit_outcome(x1, r, poc, adverse) if pe else "INELIGIBLE"
            vo = first_hit_outcome(x1, r, vah, adverse) if ve else "INELIGIBLE"
            valid_exec = entry > adverse
            if valid_exec:
                risk = (entry - adverse) / entry
                target_dist = risk + 2.0 * FEE
                target = entry * (1.0 + target_dist)
                eo = first_hit_outcome(x1, r, target, adverse)
                if eo == "TARGET":
                    raw = target_dist
                    label = "TP"
                elif eo == "ADVERSE":
                    raw = -risk
                    label = "SL"
                else:
                    final = float(x1.close.iloc[int(r.source_index) + MAX_HOLD])
                    raw = final / entry - 1.0
                    label = "TIME"
            else:
                risk = np.nan; raw = np.nan; label = "INVALID"
        else:
            adverse = float(r.event_high)
            pe = entry > poc
            ve = entry > val
            po = first_hit_outcome(x1, r, poc, adverse) if pe else "INELIGIBLE"
            vo = first_hit_outcome(x1, r, val, adverse) if ve else "INELIGIBLE"
            valid_exec = entry < adverse
            if valid_exec:
                risk = (adverse - entry) / entry
                target_dist = risk + 2.0 * FEE
                target = entry * (1.0 - target_dist)
                eo = first_hit_outcome(x1, r, target, adverse)
                if eo == "TARGET":
                    raw = target_dist
                    label = "TP"
                elif eo == "ADVERSE":
                    raw = -risk
                    label = "SL"
                else:
                    final = float(x1.close.iloc[int(r.source_index) + MAX_HOLD])
                    raw = -(final / entry - 1.0)
                    label = "TIME"
            else:
                risk = np.nan; raw = np.nan; label = "INVALID"

        net = raw - FEE if np.isfinite(raw) else np.nan
        poc_eligible.append(bool(pe)); poc_outcome.append(po)
        va_eligible.append(bool(ve)); va_outcome.append(vo)
        exec_outcome.append(label); exec_net.append(net)
        exec_pnl.append(net * NOTIONAL if np.isfinite(net) else np.nan)
        exec_risk.append(risk)

    y["poc_eligible"] = poc_eligible
    y["poc_outcome"] = poc_outcome
    y["va_eligible"] = va_eligible
    y["va_outcome"] = va_outcome
    y["exec_outcome"] = exec_outcome
    y["exec_net_ret"] = exec_net
    y["exec_pnl"] = exec_pnl
    y["exec_risk"] = exec_risk
    return y


def direction_stats(z: pd.DataFrame) -> dict:
    if z.empty:
        return {"n": 0, "pos1h": None, "pos3h": None, "avg3h": None, "median3h": None}
    return {
        "n": int(len(z)),
        "pos1h": float(z.positive1h.mean()),
        "pos3h": float(z.positive3h.mean()),
        "avg3h": float(z.signed3h.mean()),
        "median3h": float(z.signed3h.median()),
    }


def rotation_stats(z: pd.DataFrame, which: str) -> dict:
    elig_col = f"{which}_eligible"
    out_col = f"{which}_outcome"
    if z.empty:
        return {"events": 0, "eligible": 0, "target": 0, "adverse": 0, "time": 0, "hit_rate": None}
    q = z[z[elig_col] == True]
    if q.empty:
        return {"events": int(len(z)), "eligible": 0, "target": 0, "adverse": 0, "time": 0, "hit_rate": None}
    t = int((q[out_col] == "TARGET").sum())
    a = int((q[out_col] == "ADVERSE").sum())
    tm = int((q[out_col] == "TIME").sum())
    decisive = t + a
    return {
        "events": int(len(z)), "eligible": int(len(q)), "target": t, "adverse": a, "time": tm,
        "hit_rate": float(t / decisive) if decisive else None,
    }


def execution_stats(z: pd.DataFrame) -> dict:
    q = z[z.exec_outcome.isin(["TP", "SL", "TIME"])].copy() if not z.empty else z.copy()
    if q.empty:
        return {"n": 0, "tp": 0, "sl": 0, "time": 0, "wr": None, "pnl": 0.0, "expectancy": None, "median_risk": None}
    tp = int((q.exec_outcome == "TP").sum())
    sl = int((q.exec_outcome == "SL").sum())
    tm = int((q.exec_outcome == "TIME").sum())
    decisive = tp + sl
    return {
        "n": int(len(q)), "tp": tp, "sl": sl, "time": tm,
        "wr": float(tp / decisive) if decisive else None,
        "pnl": float(q.exec_pnl.sum()),
        "expectancy": float(q.exec_pnl.mean()),
        "median_risk": float(q.exec_risk.median()),
    }


def all_stats(z: pd.DataFrame) -> dict:
    return {
        "direction": direction_stats(z),
        "poc": rotation_stats(z, "poc"),
        "value_rotation": rotation_stats(z, "va"),
        "execution": execution_stats(z),
    }


def split_partitions(ev: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cut = REFERENCE_START + (REFERENCE_END - REFERENCE_START) * 0.70
    return {
        "external": ev[(ev.event_ts >= EXTERNAL_START) & (ev.event_ts < EXTERNAL_END)].copy(),
        "development": ev[(ev.event_ts >= REFERENCE_START) & (ev.event_ts < cut)].copy(),
        "reference_validation": ev[(ev.event_ts >= cut) & (ev.event_ts < REFERENCE_END)].copy(),
        "reference_full": ev[(ev.event_ts >= REFERENCE_START) & (ev.event_ts < REFERENCE_END)].copy(),
        "august": ev[(ev.event_ts >= AUG_START) & (ev.event_ts < AUG_END)].copy(),
    }


def external_blocks(z: pd.DataFrame, side: str) -> list[dict]:
    q = z[z.direction == side].sort_values("event_ts").reset_index(drop=True)
    if q.empty:
        return []
    bounds = np.linspace(0, len(q), 5, dtype=int)
    rows = []
    for j in range(4):
        p = q.iloc[bounds[j]:bounds[j + 1]]
        rows.append({"block": f"B{j+1}", "n": int(len(p)), "poc": rotation_stats(p, "poc")})
    return rows


def side_supported(parts: dict[str, pd.DataFrame], side: str, blocks: list[dict]) -> tuple[bool, bool, bool]:
    val = parts["reference_validation"][parts["reference_validation"].direction == side]
    ext = parts["external"][parts["external"].direction == side]
    vr = rotation_stats(val, "poc")
    er = rotation_stats(ext, "poc")
    good_blocks = sum(1 for b in blocks if b["poc"]["eligible"] >= 8 and b["poc"]["hit_rate"] is not None and b["poc"]["hit_rate"] >= 0.60)
    good80_blocks = sum(1 for b in blocks if b["poc"]["eligible"] >= 8 and b["poc"]["hit_rate"] is not None and b["poc"]["hit_rate"] >= 0.70)
    supported = bool(vr["eligible"] >= 30 and vr["hit_rate"] is not None and vr["hit_rate"] >= 0.70 and er["eligible"] >= 50 and er["hit_rate"] is not None and er["hit_rate"] >= 0.70 and good_blocks >= 3)
    cand80 = bool(vr["eligible"] >= 25 and vr["hit_rate"] is not None and vr["hit_rate"] >= 0.80 and er["eligible"] >= 40 and er["hit_rate"] is not None and er["hit_rate"] >= 0.80 and good80_blocks >= 3)
    vx = execution_stats(val); ex = execution_stats(ext)
    exec_supported = bool(vx["n"] > 0 and ex["n"] > 0 and vx["pnl"] > 0 and ex["pnl"] > 0 and vx["wr"] is not None and ex["wr"] is not None and vx["wr"] > 0.50 and ex["wr"] > 0.50)
    return supported, cand80, exec_supported


def pct(v) -> str:
    return "-" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{100.0 * float(v):.2f}%"


def money(v) -> str:
    return f"${float(v):+.2f}"


def main() -> None:
    x5 = load_5m()
    x1 = aggregate_1h(x5)
    profiles = build_profiles(x5)
    profiles.to_csv(OUT_PROFILES, index=False)
    raw_events = build_events(x1, profiles)
    ev = add_rotation_outcomes(x1, raw_events)
    ev.to_csv(OUT_EVENTS, index=False)
    parts = split_partitions(ev)
    parts["august"].to_csv(OUT_AUG, index=False)

    stats: dict[str, dict] = {}
    for pname, z in parts.items():
        stats[pname] = {
            "ALL": all_stats(z),
            "LONG": all_stats(z[z.direction == "LONG"]),
            "SHORT": all_stats(z[z.direction == "SHORT"]),
        }
        for h in EVENT_HOURS:
            for side in ("LONG", "SHORT"):
                key = f"{(h + 7) % 24:02d}:00_{side}"
                stats[pname][key] = all_stats(z[(z.event_hour_utc == h) & (z.direction == side)])

    ext_blocks = {side: external_blocks(parts["external"], side) for side in ("LONG", "SHORT")}
    labels = {}
    for side in ("LONG", "SHORT"):
        s, c80, ex = side_supported(parts, side, ext_blocks[side])
        labels[side] = {"poc_supported": s, "candidate80": c80, "execution_supported": ex}

    result = {
        "protocol": "BTC_H1_PREVIOUS_DAY_VOLUME_PROFILE_VP1",
        "coverage": {"first5m": str(x5.ts.min()), "last5m": str(x5.ts.max()), "rows5m": int(len(x5)), "rows1h": int(len(x1)), "profiles": int(len(profiles))},
        "fixed": {"bins": BINS, "value_area_fraction": VA_FRAC, "event_hours_utc": EVENT_HOURS, "fee": FEE, "max_hold_hours": MAX_HOLD},
        "event_count": int(len(ev)),
        "partition_counts": {k: int(len(v)) for k, v in parts.items()},
        "stats": stats,
        "external_blocks": ext_blocks,
        "labels": labels,
        "VP1_POC_ROTATION_SUPPORTED": any(v["poc_supported"] for v in labels.values()),
        "VP1_80_CANDIDATE": any(v["candidate80"] for v in labels.values()),
        "VP1_EXECUTION_SUPPORTED": any(v["execution_supported"] for v in labels.values()),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC H1 Previous-Day Volume Profile VP1 — Result",
        "",
        "Signal timeframe **1H**; no 1m. Previous-day POC/VAH/VAL constructed from completed 5m BTCUSDT USD-M candles using 100 equal-width bins and a contiguous 70% value area.",
        "",
        f"Coverage: **{x5.ts.min()} -> {x5.ts.max()}**, 5m rows **{len(x5):,}**, complete 1H rows **{len(x1):,}**, complete daily profiles **{len(profiles):,}**, qualifying events **{len(ev):,}**.",
        "",
        "## Side aggregates",
        "",
        "POC rate = target POC before event extreme, among POC-eligible next1H entries. VA rate = opposite value-area boundary before event extreme. Execution uses net RR1:1 after 0.15% fee, max6H.",
        "",
        "| Partition | Side | N | +3H | POC elig/hit | POC rate | VA elig/hit | VA rate | Net1:1 N/WR | PnL |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pname in ("development", "reference_validation", "external", "august"):
        for side in ("LONG", "SHORT"):
            s = stats[pname][side]
            d = s["direction"]; p = s["poc"]; v = s["value_rotation"]; e = s["execution"]
            md.append(
                f"| {pname} | {side} | {d['n']} | {pct(d['pos3h'])} | {p['eligible']}/{p['target']} | {pct(p['hit_rate'])} | {v['eligible']}/{v['target']} | {pct(v['hit_rate'])} | {e['n']}/{pct(e['wr'])} | {money(e['pnl'])} |"
            )

    md += ["", "## Fixed clock x side cells — reference validation", "", "| WIB | Side | N | +3H | POC elig/hit/rate | VA elig/hit/rate | Net1:1 N/WR/PnL |", "|---:|---|---:|---:|---:|---:|---:|"]
    for h in EVENT_HOURS:
        for side in ("LONG", "SHORT"):
            key = f"{(h + 7) % 24:02d}:00_{side}"
            s = stats["reference_validation"][key]
            d=s["direction"]; p=s["poc"]; v=s["value_rotation"]; e=s["execution"]
            md.append(f"| {(h+7)%24:02d}:00 | {side} | {d['n']} | {pct(d['pos3h'])} | {p['eligible']}/{p['target']}/{pct(p['hit_rate'])} | {v['eligible']}/{v['target']}/{pct(v['hit_rate'])} | {e['n']}/{pct(e['wr'])}/{money(e['pnl'])} |")

    md += ["", "## Fixed clock x side cells — external 2020-2021", "", "| WIB | Side | N | +3H | POC elig/hit/rate | VA elig/hit/rate | Net1:1 N/WR/PnL |", "|---:|---|---:|---:|---:|---:|---:|"]
    for h in EVENT_HOURS:
        for side in ("LONG", "SHORT"):
            key = f"{(h + 7) % 24:02d}:00_{side}"
            s = stats["external"][key]
            d=s["direction"]; p=s["poc"]; v=s["value_rotation"]; e=s["execution"]
            md.append(f"| {(h+7)%24:02d}:00 | {side} | {d['n']} | {pct(d['pos3h'])} | {p['eligible']}/{p['target']}/{pct(p['hit_rate'])} | {v['eligible']}/{v['target']}/{pct(v['hit_rate'])} | {e['n']}/{pct(e['wr'])}/{money(e['pnl'])} |")

    md += ["", "## External chronological POC blocks", ""]
    for side in ("LONG", "SHORT"):
        md += [f"### {side}", "", "| Block | Events | POC eligible | Target | Adverse | Time | POC rate |", "|---|---:|---:|---:|---:|---:|---:|"]
        for b in ext_blocks[side]:
            p=b["poc"]
            md.append(f"| {b['block']} | {b['n']} | {p['eligible']} | {p['target']} | {p['adverse']} | {p['time']} | {pct(p['hit_rate'])} |")
        md.append("")

    md += [
        "## Verdicts",
        "",
        f"**VP1_POC_ROTATION_SUPPORTED: {'PASS' if result['VP1_POC_ROTATION_SUPPORTED'] else 'FAIL'}**",
        f"**VP1_80_CANDIDATE: {'PASS' if result['VP1_80_CANDIDATE'] else 'FAIL'}**",
        f"**VP1_EXECUTION_SUPPORTED: {'PASS' if result['VP1_EXECUTION_SUPPORTED'] else 'FAIL'}**",
        "",
        "No bin-count, value-area percentage, clock, side, distance, weekday, or execution parameter is reselected after result.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps({"events": len(ev), "profiles": len(profiles), "labels": labels}, indent=2))


if __name__ == "__main__":
    main()
