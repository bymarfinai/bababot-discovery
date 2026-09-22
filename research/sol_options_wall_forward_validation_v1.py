#!/usr/bin/env python3
"""Causal forward validation for SOL Options Liquidity Map V1.

Reads only prospectively saved map snapshots, collapses repeated identical maps
into regimes, then evaluates SOLUSDT spot 1m candles after regime start.

No historical candle is allowed to use a later options snapshot.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "research" / "data" / "sol_options_v1"
OUT_CSV = ROOT / "SOL_OPTIONS_WALL_FORWARD_VALIDATION_V1_Observations.csv"
OUT_MD = ROOT / "SOL_OPTIONS_WALL_FORWARD_VALIDATION_V1_Result.md"

SPOT_KLINES = "https://api.binance.com/api/v3/klines"
SYMBOL = "SOLUSDT"
INTERVAL = "1m"
HORIZON_MIN = 240
BANDS = (0.0025, 0.0050, 0.0100)
POST_TOUCH_WINDOWS = (15, 30, 60)


def _to_ms(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    return int(float(v))


def load_snapshots() -> list[dict]:
    out = []
    for p in sorted(SNAP_DIR.glob("*.json")):
        x = json.loads(p.read_text(encoding="utf-8"))
        if x.get("map_version") != "SOL_OPTIONS_LIQUIDITY_MAP_V1":
            continue
        x["_path"] = str(p.relative_to(ROOT))
        x["snapshot_time_ms"] = _to_ms(x["snapshot_time_ms"])
        out.append(x)
    out.sort(key=lambda x: x["snapshot_time_ms"])
    return out


def regime_key(x: dict) -> tuple:
    expiries = tuple(e["code"] for e in x["expiries"])
    lower = tuple(float(z["strike"]) for z in x["lower_put_concentration"][:3])
    upper = tuple(float(z["strike"]) for z in x["upper_call_concentration"][:3])
    return expiries, lower, upper


def collapse_regimes(snaps: list[dict]) -> list[dict]:
    regimes = []
    prev = None
    for s in snaps:
        k = regime_key(s)
        if k != prev:
            regimes.append(s)
            prev = k
    return regimes


def fetch_klines(start_ms: int, end_ms: int) -> list[dict]:
    rows: list[dict] = []
    cursor = start_ms
    while cursor <= end_ms:
        params = {
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        r = requests.get(SPOT_KLINES, params=params, timeout=20)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for k in batch:
            rows.append(
                {
                    "open_time_ms": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                }
            )
        nxt = int(batch[-1][0]) + 60_000
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < 1000:
            break
        time.sleep(0.05)
    return rows


def first_touch(candles: list[dict], level: float) -> int | None:
    for i, c in enumerate(candles):
        if c["low"] <= level <= c["high"]:
            return i
    return None


def side_metrics(candles: list[dict], touch_i: int, level: float, side: str, mins: int | None):
    xs = candles[touch_i:] if mins is None else candles[touch_i : touch_i + mins]
    if not xs:
        return None
    hi = max(c["high"] for c in xs)
    lo = min(c["low"] for c in xs)
    last = xs[-1]["close"]

    if side == "LOWER":
        mfe = (hi / level - 1.0) * 100.0
        mae = max(0.0, (1.0 - lo / level) * 100.0)
        close_disp = (last / level - 1.0) * 100.0
    else:
        mfe = (1.0 - lo / level) * 100.0
        mae = max(0.0, (hi / level - 1.0) * 100.0)
        close_disp = (1.0 - last / level) * 100.0

    denom = mfe + mae
    ratio = mfe / denom if denom > 0 else None
    return {
        "mfe_pct": mfe,
        "mae_pct": mae,
        "close_disp_pct": close_disp,
        "fav_ratio": ratio,
    }


def first_passage(candles: list[dict], touch_i: int, level: float, side: str, band: float) -> str:
    fav = level * (1.0 + band) if side == "LOWER" else level * (1.0 - band)
    adv = level * (1.0 - band) if side == "LOWER" else level * (1.0 + band)

    for c in candles[touch_i:]:
        fav_hit = c["high"] >= fav if side == "LOWER" else c["low"] <= fav
        adv_hit = c["low"] <= adv if side == "LOWER" else c["high"] >= adv

        if fav_hit and adv_hit:
            return "SAME_BAR_BOTH"
        if fav_hit:
            return "FAVORABLE_FIRST"
        if adv_hit:
            return "ADVERSE_FIRST"
    return "NONE"


def level_row(regime: dict, candles: list[dict], level_obj: dict, side: str, rank: int, end_ms: int, censored: bool) -> dict:
    level = float(level_obj["strike"])
    ti = first_touch(candles, level)
    row = {
        "regime_start_utc": datetime.fromtimestamp(regime["snapshot_time_ms"] / 1000, tz=timezone.utc).isoformat(),
        "regime_snapshot_id": regime["snapshot_id"],
        "snapshot_path": regime["_path"],
        "side": side,
        "rank": rank,
        "strike": level,
        "concentration_score": float(level_obj["concentration_score"]),
        "mean_oi_share": float(level_obj["mean_oi_share"]),
        "mean_gamma_share": float(level_obj["mean_gamma_share"]),
        "iv_confluence": level_obj.get("confluence_label"),
        "nearest_iv_expiry": (level_obj.get("nearest_iv_band") or {}).get("expiry"),
        "nearest_iv_distance_pct_spot": (level_obj.get("nearest_iv_band") or {}).get("distance_pct_spot"),
        "window_end_utc": datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc).isoformat(),
        "censored": censored,
        "touched": ti is not None,
        "touch_time_utc": "",
    }

    if ti is None:
        return row

    row["touch_time_utc"] = datetime.fromtimestamp(candles[ti]["open_time_ms"] / 1000, tz=timezone.utc).isoformat()

    for m in POST_TOUCH_WINDOWS:
        z = side_metrics(candles, ti, level, side, m)
        if z is not None:
            row[f"mfe_{m}m_pct"] = z["mfe_pct"]
            row[f"mae_{m}m_pct"] = z["mae_pct"]
            row[f"fav_ratio_{m}m"] = z["fav_ratio"]
            row[f"close_disp_{m}m_pct"] = z["close_disp_pct"]

    z = side_metrics(candles, ti, level, side, None)
    if z is not None:
        row["mfe_end_pct"] = z["mfe_pct"]
        row["mae_end_pct"] = z["mae_pct"]
        row["fav_ratio_end"] = z["fav_ratio"]
        row["close_disp_end_pct"] = z["close_disp_pct"]

    for b in BANDS:
        tag = str(b * 100).rstrip("0").rstrip(".").replace(".", "p")
        row[f"first_passage_{tag}pct"] = first_passage(candles, ti, level, side, b)

    return row


def main() -> int:
    snaps = load_snapshots()
    if not snaps:
        print("NO_PROSPECTIVE_SNAPSHOTS")
        return 2

    regimes = collapse_regimes(snaps)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    obs = []

    for i, regime in enumerate(regimes):
        natural_end = regime["snapshot_time_ms"] + HORIZON_MIN * 60_000
        next_start = regimes[i + 1]["snapshot_time_ms"] if i + 1 < len(regimes) else None
        end_ms = min(natural_end, next_start if next_start is not None else natural_end, now_ms)
        censored = end_ms < natural_end and next_start is None

        candles = fetch_klines(regime["snapshot_time_ms"], end_ms)
        for side, key in (("LOWER", "lower_put_concentration"), ("UPPER", "upper_call_concentration")):
            for rank, level_obj in enumerate(regime[key][:3], start=1):
                obs.append(level_row(regime, candles, level_obj, side, rank, end_ms, censored))

    keys = []
    for r in obs:
        for k in r:
            if k not in keys:
                keys.append(k)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(obs)

    touched = [r for r in obs if r["touched"]]
    complete = [r for r in obs if not r["censored"]]
    if not complete:
        status = "FORWARD_SAMPLE_CENSORED"
    elif not touched:
        status = "FORWARD_NO_TOUCH"
    else:
        status = "FORWARD_TOUCH_OBSERVED"

    lines = [
        "# SOL Options Wall Forward Validation V1 — Result",
        "",
        f"**Status: {status}**",
        "",
        f"- Prospective snapshots: {len(snaps)}",
        f"- Map regimes: {len(regimes)}",
        f"- Level observations: {len(obs)}",
        f"- Touched observations: {len(touched)}",
        f"- Completed observations: {len(complete)}",
        "",
        "This result is causal only for price action occurring after each saved map snapshot.",
        "Censored observations are not counted as failures.",
        "No READY_TO_TRADE conclusion is permitted from this pilot result.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(status)
    print("snapshots", len(snaps), "regimes", len(regimes), "observations", len(obs), "touched", len(touched))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
