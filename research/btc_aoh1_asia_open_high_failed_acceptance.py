#!/usr/bin/env python3
"""BTC AOH1 — Asia Open HIGH failed-acceptance confirmation.

Frozen preregistration:
- previous UTC day HIGH
- Asia Open 00:00 UTC, first 90m
- 15m sweep+reclaim below PDH
- immediately next 15m bearish close below reclaim low
- SHORT next 15m open
- SL reclaim high
- TP sized for modeled NET RR 1:1 after 0.15% round-trip fee
- max hold 6h
- no 1m data
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_AOH1_AsiaOpen_High_FailedAcceptance_Result.md"
OUT_JSON = ROOT / "BTC_AOH1_AsiaOpen_High_FailedAcceptance_Result.json"
OUT_CSV = ROOT / "BTC_AOH1_AsiaOpen_High_FailedAcceptance_August_Events.csv"

BASE = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
TF = "5m"

LOAD_START = pd.Timestamp("2021-12-01T00:00:00Z")
EXTERNAL_START = pd.Timestamp("2022-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2023-12-02T00:00:00Z")
REFERENCE_START = pd.Timestamp("2023-12-02T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")

FEE = 0.0015
NOTIONAL = 500.0
WINDOW_MIN = 90
HOLD_BARS_5M = 72


def fetch_zip(url: str) -> list[list[float]]:
    r = requests.get(url, timeout=60, headers={"User-Agent": "bababot-aoh1/1.0"})
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
    cur = pd.Timestamp(2021, 12, 1, tz="UTC")
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


def load_data() -> pd.DataFrame:
    jobs = archive_urls()
    rows: list[list[float]] = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(fetch_zip, u): u for u in jobs}
        done = 0
        for f in as_completed(futures):
            rows.extend(f.result())
            done += 1
            if done % 10 == 0:
                print(f"downloaded {done}/{len(jobs)} archives")
    if not rows:
        raise RuntimeError("no Binance data downloaded")
    x = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
    x["ts"] = pd.to_datetime(pd.to_numeric(x.ts), unit="ms", utc=True)
    x = x.dropna().drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    x = x[(x.ts >= LOAD_START) & (x.ts < AUG_END)].reset_index(drop=True)
    return x


def aggregate_15m(x: pd.DataFrame) -> pd.DataFrame:
    y = x.set_index("ts")
    z = y.resample("15min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        count=("close", "count"),
    ).dropna().reset_index()
    return z[z["count"] == 3].reset_index(drop=True)


def forward_diag(x: pd.DataFrame, entry_idx: int, minutes: int) -> Optional[dict]:
    bars = minutes // 5
    end_idx = entry_idx + bars - 1
    if end_idx >= len(x):
        return None
    if x.ts.iloc[end_idx] != x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (bars - 1)):
        return None
    ep = float(x.open.iloc[entry_idx])
    final = float(x.close.iloc[end_idx])
    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    return {
        "ret": (ep - final) / ep,
        "mfe": (ep - float(np.min(ls))) / ep,
        "mae": (float(np.max(hs)) - ep) / ep,
    }


def resolve_trade(x: pd.DataFrame, entry_idx: int, sl: float) -> Optional[dict]:
    end_idx = entry_idx + HOLD_BARS_5M - 1
    if end_idx >= len(x):
        return None
    if x.ts.iloc[end_idx] != x.ts.iloc[entry_idx] + pd.Timedelta(minutes=5 * (HOLD_BARS_5M - 1)):
        return None
    ep = float(x.open.iloc[entry_idx])
    risk = sl - ep
    if risk <= 0:
        return None
    risk_pct = risk / ep
    raw_target_pct = risk_pct + 2.0 * FEE
    tp = ep * (1.0 - raw_target_pct)
    if tp <= 0:
        return None

    hs = x.high.iloc[entry_idx:end_idx + 1].to_numpy(float)
    ls = x.low.iloc[entry_idx:end_idx + 1].to_numpy(float)
    tp_hits = np.flatnonzero(ls <= tp)
    sl_hits = np.flatnonzero(hs >= sl)
    ti = int(tp_hits[0]) if tp_hits.size else 10**9
    si = int(sl_hits[0]) if sl_hits.size else 10**9
    if si <= ti:
        outcome = "SL"
        raw_ret = -risk_pct
    elif ti < 10**9:
        outcome = "TP"
        raw_ret = raw_target_pct
    else:
        outcome = "TIME"
        final = float(x.close.iloc[end_idx])
        raw_ret = (ep - final) / ep
    net_ret = raw_ret - FEE
    return {
        "entry_price": ep,
        "sl_price": sl,
        "tp_price": tp,
        "risk_pct": risk_pct,
        "raw_target_pct": raw_target_pct,
        "outcome": outcome,
        "net_ret": net_ret,
        "pnl": net_ret * NOTIONAL,
        "net_positive": int(net_ret > 0),
    }


def detect_partition(x5: pd.DataFrame, x15: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, int]:
    rows = []
    reclaim_candidates = 0
    day = start.normalize()
    x15_by_ts = {t: i for i, t in enumerate(x15.ts)}
    x5_by_ts = {t: i for i, t in enumerate(x5.ts)}

    while day < end.normalize():
        prev_s = day - pd.Timedelta(days=1)
        prev = x5[(x5.ts >= prev_s) & (x5.ts < day)]
        if len(prev) != 288:
            day += pd.Timedelta(days=1)
            continue
        pdh = float(prev.high.max())
        z = x15[(x15.ts >= day) & (x15.ts < day + pd.Timedelta(minutes=WINDOW_MIN))]
        if z.empty:
            day += pd.Timedelta(days=1)
            continue

        reclaim = None
        for idx, r in z.iterrows():
            if float(r.high) > pdh and float(r.close) < pdh:
                reclaim = (int(idx), r)
                break
        if reclaim is None:
            day += pd.Timedelta(days=1)
            continue
        reclaim_candidates += 1
        ridx, rr = reclaim
        reclaim_ts = pd.Timestamp(rr.ts)
        confirm_ts = reclaim_ts + pd.Timedelta(minutes=15)
        cidx = x15_by_ts.get(confirm_ts)
        if cidx is None:
            day += pd.Timedelta(days=1)
            continue
        cr = x15.iloc[int(cidx)]
        # Immediate next completed 15m candle only.
        if not (float(cr.close) < float(cr.open) and float(cr.close) < float(rr.low)):
            day += pd.Timedelta(days=1)
            continue

        entry_ts = confirm_ts + pd.Timedelta(minutes=15)
        entry_idx = x5_by_ts.get(entry_ts)
        if entry_idx is None:
            day += pd.Timedelta(days=1)
            continue
        trade = resolve_trade(x5, int(entry_idx), float(rr.high))
        if trade is None:
            day += pd.Timedelta(days=1)
            continue
        d60 = forward_diag(x5, int(entry_idx), 60)
        d120 = forward_diag(x5, int(entry_idx), 120)
        d240 = forward_diag(x5, int(entry_idx), 240)
        if d60 is None or d120 is None or d240 is None:
            day += pd.Timedelta(days=1)
            continue
        rows.append({
            "utc_date": day.strftime("%Y-%m-%d"),
            "previous_day_high": pdh,
            "reclaim_ts": reclaim_ts,
            "reclaim_high": float(rr.high),
            "reclaim_low": float(rr.low),
            "confirm_ts": confirm_ts,
            "confirm_open": float(cr.open),
            "confirm_close": float(cr.close),
            "entry_ts": entry_ts,
            "entry_wib": entry_ts + pd.Timedelta(hours=7),
            **trade,
            "ret60": d60["ret"], "mfe60": d60["mfe"], "mae60": d60["mae"],
            "ret120": d120["ret"], "mfe120": d120["mfe"], "mae120": d120["mae"],
            "ret240": d240["ret"], "mfe240": d240["mfe"], "mae240": d240["mae"],
        })
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows), reclaim_candidates


def stats(z: pd.DataFrame, reclaim_candidates: int) -> dict:
    if z is None or z.empty:
        return {
            "reclaim_candidates": int(reclaim_candidates), "n": 0, "confirmation_rate": 0.0 if reclaim_candidates else None,
            "tp": 0, "sl": 0, "time": 0, "decisive_n": 0, "decisive_wr": None,
            "net_positive_rate": None, "pnl": 0.0, "avg_risk_pct": None, "median_risk_pct": None,
            "avg_raw_target_pct": None, "avg_ret60": None, "avg_ret120": None, "avg_ret240": None,
        }
    dec = z[z.outcome.isin(["TP", "SL"])]
    return {
        "reclaim_candidates": int(reclaim_candidates),
        "n": int(len(z)),
        "confirmation_rate": float(len(z) / reclaim_candidates) if reclaim_candidates else None,
        "tp": int((z.outcome == "TP").sum()),
        "sl": int((z.outcome == "SL").sum()),
        "time": int((z.outcome == "TIME").sum()),
        "decisive_n": int(len(dec)),
        "decisive_wr": float((dec.outcome == "TP").mean()) if len(dec) else None,
        "net_positive_rate": float(z.net_positive.mean()),
        "pnl": float(z.pnl.sum()),
        "avg_risk_pct": float(z.risk_pct.mean()),
        "median_risk_pct": float(z.risk_pct.median()),
        "avg_raw_target_pct": float(z.raw_target_pct.mean()),
        "avg_ret60": float(z.ret60.mean()),
        "avg_ret120": float(z.ret120.mean()),
        "avg_ret240": float(z.ret240.mean()),
    }


def block_stats(z: pd.DataFrame) -> list[dict]:
    if z.empty:
        return []
    y = z.sort_values("entry_ts").reset_index(drop=True)
    bounds = np.linspace(0, len(y), 5, dtype=int)
    out = []
    for i in range(4):
        part = y.iloc[bounds[i]:bounds[i + 1]].copy()
        s = stats(part, len(part))
        out.append({"block": f"B{i+1}", **s})
    return out


def gate(external: dict, blocks: list[dict]) -> dict:
    positive_blocks = sum(1 for b in blocks if b["pnl"] > 0)
    blocks_wr_gt50 = sum(1 for b in blocks if b["decisive_wr"] is not None and b["decisive_wr"] > 0.50)
    support = bool(
        external["n"] >= 20 and external["decisive_wr"] is not None and external["decisive_wr"] >= 0.65 and
        external["pnl"] > 0 and positive_blocks >= 3
    )
    c80 = bool(
        external["decisive_n"] >= 20 and external["decisive_wr"] is not None and external["decisive_wr"] >= 0.80 and
        external["pnl"] > 0 and blocks_wr_gt50 >= 3
    )
    return {
        "AOH1_EXTERNAL_SUPPORT": support,
        "AOH1_80_CANDIDATE": c80,
        "positive_blocks": positive_blocks,
        "blocks_wr_gt50": blocks_wr_gt50,
    }


def pct(v) -> str:
    return "-" if v is None else f"{100*v:.2f}%"


def main() -> None:
    x5 = load_data()
    x15 = aggregate_15m(x5)
    print(f"coverage {x5.ts.min()} -> {x5.ts.max()} rows5m={len(x5)} rows15m={len(x15)}")

    ext, ext_candidates = detect_partition(x5, x15, EXTERNAL_START, EXTERNAL_END)
    ref, ref_candidates = detect_partition(x5, x15, REFERENCE_START, REFERENCE_END)
    aug, aug_candidates = detect_partition(x5, x15, AUG_START, AUG_END)

    ext_s = stats(ext, ext_candidates)
    ref_s = stats(ref, ref_candidates)
    aug_s = stats(aug, aug_candidates)
    ext_blocks = block_stats(ext)
    gates = gate(ext_s, ext_blocks)

    if aug.empty:
        pd.DataFrame(columns=["utc_date"]).to_csv(OUT_CSV, index=False)
    else:
        aug.to_csv(OUT_CSV, index=False)

    result = {
        "protocol": "BTC_AOH1_ASIA_OPEN_HIGH_FAILED_ACCEPTANCE_NET1R",
        "coverage": {"first_ts": str(x5.ts.min()), "last_ts": str(x5.ts.max()), "rows5m": int(len(x5)), "rows15m": int(len(x15))},
        "external_2022_2023": ext_s,
        "reference_2023_2026": ref_s,
        "august_2026": aug_s,
        "external_blocks": ext_blocks,
        "gate": gates,
        "guardrails": {
            "one_minute_used": False,
            "asia_anchor_utc": "00:00",
            "window_minutes": WINDOW_MIN,
            "fee": FEE,
            "net_rr": "1:1 by target raw_reward=risk+2*fee",
            "max_hold_hours": 6,
        },
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC AOH1 — Asia Open HIGH Failed-Acceptance Confirmation Result",
        "",
        "Frozen sequence: previous-day HIGH sweep/reclaim during first 90m Asia Open -> immediate next 15m bearish close below reclaim low -> SHORT next 15m open -> SL reclaim high -> TP sized for **net RR 1:1 after 0.15% fee**.",
        "",
        f"Coverage: **{x5.ts.min()} -> {x5.ts.max()}**, 5m rows **{len(x5):,}**, 15m complete rows **{len(x15):,}**.",
        "",
        "## Partition results",
        "",
        "| Partition | Reclaim candidates | Confirmed trades | Confirm rate | TP | SL | TIME | Decisive WR | Net+ rate | PnL | Median risk | Avg raw TP distance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, s in [("External 2022-2023", ext_s), ("Reference 2023-2026", ref_s), ("August 2026", aug_s)]:
        md.append(
            f"| {name} | {s['reclaim_candidates']} | {s['n']} | {pct(s['confirmation_rate'])} | {s['tp']} | {s['sl']} | {s['time']} | "
            f"{pct(s['decisive_wr'])} | {pct(s['net_positive_rate'])} | ${s['pnl']:.2f} | {pct(s['median_risk_pct'])} | {pct(s['avg_raw_target_pct'])} |"
        )

    md += [
        "",
        "## External 2022-2023 chronological blocks",
        "",
        "| Block | N | TP | SL | TIME | Decisive WR | PnL | Median risk |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for b in ext_blocks:
        md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['decisive_wr'])} | ${b['pnl']:.2f} | {pct(b['median_risk_pct'])} |")

    md += [
        "",
        "## Directional diagnostics",
        "",
        "| Partition | Avg 60m SHORT ret | Avg 120m | Avg 240m |",
        "|---|---:|---:|---:|",
        f"| External 2022-2023 | {pct(ext_s['avg_ret60'])} | {pct(ext_s['avg_ret120'])} | {pct(ext_s['avg_ret240'])} |",
        f"| Reference 2023-2026 | {pct(ref_s['avg_ret60'])} | {pct(ref_s['avg_ret120'])} | {pct(ref_s['avg_ret240'])} |",
        f"| August 2026 | {pct(aug_s['avg_ret60'])} | {pct(aug_s['avg_ret120'])} | {pct(aug_s['avg_ret240'])} |",
        "",
        "## August event ledger",
        "",
        "| Date | Entry WIB | PDH | Reclaim high | Risk | Raw TP dist | Outcome | Net ret | PnL | 60m | 240m |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    if aug.empty:
        md.append("| - | - | - | - | - | - | - | - | - | - | - |")
    else:
        for _, r in aug.sort_values("entry_ts").iterrows():
            md.append(
                f"| {r.utc_date} | {pd.Timestamp(r.entry_wib).strftime('%Y-%m-%d %H:%M')} | {r.previous_day_high:.2f} | {r.reclaim_high:.2f} | "
                f"{100*r.risk_pct:.3f}% | {100*r.raw_target_pct:.3f}% | {r.outcome} | {100*r.net_ret:.3f}% | ${r.pnl:.2f} | "
                f"{100*r.ret60:.3f}% | {100*r.ret240:.3f}% |"
            )

    md += [
        "",
        f"**AOH1_EXTERNAL_SUPPORT: {'PASS' if gates['AOH1_EXTERNAL_SUPPORT'] else 'FAIL'}**",
        f"**AOH1_80_CANDIDATE: {'PASS' if gates['AOH1_80_CANDIDATE'] else 'FAIL'}**",
        "",
        "Acceptance is determined by the external 2022-2023 partition, not the reference sample. No post-result retuning is allowed.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
