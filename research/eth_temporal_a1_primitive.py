#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_TEMPORAL_A1_PRIMITIVE"
OUT_GRID = ROOT / f"{PFX}_Grid.csv"
OUT_REP = ROOT / f"{PFX}_24H_Representatives.csv"
OUT_YEAR = ROOT / f"{PFX}_Yearly.csv"
OUT_MD = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BASE = "https://data.binance.vision/data/futures/um/monthly/klines/ETHUSDT/5m"
START = pd.Timestamp("2022-01-01T00:00:00Z")
END = pd.Timestamp("2025-01-01T00:00:00Z")
HOLDS = (60, 120, 240, 360, 720, 960)
DIRECTIONS = ("LONG", "SHORT")
NOTIONAL = 500.0
FEE = 0.75


def month_urls():
    out = []
    m = START
    while m < END:
        ym = m.strftime("%Y-%m")
        out.append(f"{BASE}/ETHUSDT-5m-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return out


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-eth-temporal-a1/1.0"})
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"no csv in {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4],
                names=["ts", "open", "high", "low", "close"],
            )


def load5():
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_one, u) for u in month_urls()]
        for fut in as_completed(futs):
            frames.append(fut.result())
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= START) & (x.ts < END)].set_index("ts")
    expected = int((END - START) / pd.Timedelta(minutes=5))
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"ETHUSDT 5m coverage too low: {coverage:.6f}")
    return x, coverage


def max_loss_streak(pnl: np.ndarray) -> int:
    best = cur = 0
    for v in pnl:
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(pnl: np.ndarray):
    pnl = np.asarray(pnl, dtype=float)
    n = len(pnl)
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    wr = float((pnl > 0).mean() * 100.0) if n else np.nan
    net = float(pnl.sum()) if n else np.nan
    exp = float(pnl.mean()) if n else np.nan
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    pf = gross_win / gross_loss if gross_loss > 0 else np.inf
    if n:
        eq = np.cumsum(pnl)
        peaks = np.maximum.accumulate(np.r_[0.0, eq])
        dd = float(np.max(peaks[1:] - eq))
    else:
        dd = np.nan
    ls = max_loss_streak(pnl) if n else 0
    return dict(N=n, WR=wr, net=net, exp=exp, PF=float(pf), DD=dd, LS=ls)


def build_observations(x: pd.DataFrame, hour: int, hold: int, direction: str):
    anchors = pd.date_range(START, END - pd.Timedelta(days=1), freq="D", tz="UTC") + pd.Timedelta(hours=hour)
    exits = anchors + pd.Timedelta(minutes=hold)
    valid = exits < END
    anchors = anchors[valid]
    exits = exits[valid]

    en = x["open"].reindex(anchors)
    ex = x["open"].reindex(exits)
    ok = en.notna().to_numpy() & ex.notna().to_numpy()
    anchors = anchors[ok]
    en_v = en.to_numpy()[ok].astype(float)
    ex_v = ex.to_numpy()[ok].astype(float)

    if direction == "LONG":
        gross = NOTIONAL * (ex_v / en_v - 1.0)
    else:
        gross = NOTIONAL * (en_v / ex_v - 1.0)
    pnl = gross - FEE
    return pd.DataFrame({"ts": anchors, "year": anchors.year, "pnl": pnl})


def main():
    x, coverage = load5()
    rows = []
    yrows = []

    for hour in range(24):
        for direction in DIRECTIONS:
            for hold in HOLDS:
                obs = build_observations(x, hour, hold, direction)
                m = metrics(obs.pnl.to_numpy())
                yr = {}
                for year in (2022, 2023, 2024):
                    q = obs[obs.year == year]
                    ym = metrics(q.pnl.to_numpy())
                    yr[year] = ym
                    yrows.append({
                        "hour_utc": hour,
                        "hour_wib": (hour + 7) % 24,
                        "direction": direction,
                        "hold_min": hold,
                        "year": year,
                        **ym,
                    })
                row = {
                    "hour_utc": hour,
                    "hour_wib": (hour + 7) % 24,
                    "direction": direction,
                    "hold_min": hold,
                    **m,
                    "all3_year_net_positive": all(yr[y]["net"] > 0 for y in (2022, 2023, 2024)),
                    "min_year_exp": min(yr[y]["exp"] for y in (2022, 2023, 2024)),
                    "min_year_wr": min(yr[y]["WR"] for y in (2022, 2023, 2024)),
                }
                for year in (2022, 2023, 2024):
                    row[f"exp_{year}"] = yr[year]["exp"]
                    row[f"net_{year}"] = yr[year]["net"]
                    row[f"wr_{year}"] = yr[year]["WR"]
                    row[f"pf_{year}"] = yr[year]["PF"]
                rows.append(row)

    grid = pd.DataFrame(rows)
    yearly = pd.DataFrame(yrows)
    grid.to_csv(OUT_GRID, index=False)
    yearly.to_csv(OUT_YEAR, index=False)

    reps = []
    for hour in range(24):
        q = grid[grid.hour_utc == hour].copy()
        q["dir_tie"] = q.direction.map({"LONG": 0, "SHORT": 1})
        q = q.sort_values(
            by=["all3_year_net_positive", "min_year_exp", "exp", "PF", "WR", "DD", "LS", "hold_min", "dir_tie"],
            ascending=[False, False, False, False, False, True, True, True, True],
            kind="mergesort",
        )
        reps.append(q.iloc[0].drop(labels=["dir_tie"]).to_dict())
    rep = pd.DataFrame(reps).sort_values("hour_wib").reset_index(drop=True)
    rep.to_csv(OUT_REP, index=False)

    all3_count = int(rep.all3_year_net_positive.sum())
    long_count = int((rep.direction == "LONG").sum())
    short_count = int((rep.direction == "SHORT").sum())
    best = rep.sort_values(
        ["all3_year_net_positive", "min_year_exp", "exp", "PF", "WR"],
        ascending=[False, False, False, False, False],
    ).iloc[0]

    lines = [
        "# ETH Temporal A1 — Primitive Time/Horizon Discovery — Result",
        "",
        f"- ETHUSDT 5m Development coverage: **{coverage:.6%}**",
        f"- Scan: 24 UTC hours × 2 directions × {len(HOLDS)} holds = **{24*2*len(HOLDS)} combinations**",
        f"- 24h representatives positive-net in all 3 years: **{all3_count}/24**",
        f"- Representative direction split: **LONG {long_count} / SHORT {short_count}**",
        f"- Global robustness-ranked representative: **{int(best.hour_wib):02d}:00 WIB / {best.direction} / H{int(best.hold_min)}**; N={int(best.N)}, WR={best.WR:.2f}%, net=${best.net:.2f}, exp=${best.exp:.4f}, PF={best.PF:.3f}, DD=${best.DD:.2f}, LS={int(best.LS)}, min-year-exp=${best.min_year_exp:.4f}",
        "",
        "## 24-hour primitive temporal representatives (sorted WIB)",
        "",
        "| WIB | UTC | Dir | Hold | All3+ | N | WR | Net | Exp | PF | DD | LS | MinYrExp |",
        "|---:|---:|:---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in rep.iterrows():
        lines.append(
            f"| {int(r.hour_wib):02d}:00 | {int(r.hour_utc):02d}:00 | {r.direction} | {int(r.hold_min)}m | {'YES' if r.all3_year_net_positive else 'NO'} | {int(r.N)} | {r.WR:.2f}% | ${r.net:.2f} | ${r.exp:.4f} | {r.PF:.3f} | ${r.DD:.2f} | {int(r.LS)} | ${r.min_year_exp:.4f} |"
        )
    lines += [
        "",
        "## Interpretation boundary",
        "These are unconditional temporal probes, not production setups. Overlap is allowed and no structural state filter is used. Cross-check against E12/E13/E15 is performed only after this map is frozen.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text("PASS\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
