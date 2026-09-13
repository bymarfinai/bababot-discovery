#!/usr/bin/env python3
from __future__ import annotations

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
PFX = "BNB_LONG_RESET_V1_H00_PRIMARY"
OUT_EVENTS = ROOT / f"{PFX}_DevelopmentEvents.csv"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_SELECTED = ROOT / f"{PFX}_Selected.json"

BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
SYMBOL = "BNBUSDT"
BAR = "5m"
DATA_START = pd.Timestamp("2021-12-01T00:00:00Z")
DATA_END = pd.Timestamp("2025-01-01T00:00:00Z")  # exclusive; no OOS downloaded
DEV_YEARS = (2022, 2023, 2024)
ANCHOR_MINUTES = (0, 15, 30, 45)  # local WIB inside H00
HORIZONS = (60, 120, 240)
ROLL_N = 60
MIN_HIST = 40
BINS = ("LOW", "MID", "HIGH")

NUMERIC_FEATURES = (
    "drive_15m",
    "drive_60m",
    "drive_240m",
    "ema20_ema50_spread",
    "range_location_240m",
    "range_ratio_60_240",
    "rv_ratio_60_240",
    "efficiency_60m",
    "lower_wick_pressure_15m",
    "swing_slope_30_30",
)
BINARY_FEATURES = ("above_ema20", "ema20_reclaim")


def month_urls() -> list[str]:
    out = []
    m = DATA_START.replace(day=1)
    while m < DATA_END:
        ym = m.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/{BAR}/{SYMBOL}-{BAR}-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return out


def fetch_month(url: str):
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-reset-v1/1.0"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4],
                names=["ts", "open", "high", "low", "close"],
            )


def load5() -> tuple[pd.DataFrame, float]:
    frames = []
    urls = month_urls()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_month, u) for u in urls]
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError("no BNBUSDT 5m data")
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors="coerce")
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x["ts"] = pd.to_datetime(t, unit="ms", utc=True, errors="coerce")
    for c in ("open", "high", "low", "close"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna().drop_duplicates("ts").sort_values("ts")
    x = x[(x.ts >= DATA_START) & (x.ts < DATA_END)].set_index("ts")
    expected = len(pd.date_range(DATA_START, DATA_END - pd.Timedelta(minutes=5), freq="5min", tz="UTC"))
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f"BNBUSDT development-support data coverage too low: {coverage:.6%}")
    return x, coverage


def safe_ratio(a: float, b: float) -> float:
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and b != 0 else np.nan


def drive(closes: pd.Series, bars: int) -> float:
    if len(closes) < bars + 1:
        return np.nan
    a = float(closes.iloc[-(bars + 1)])
    b = float(closes.iloc[-1])
    return b / a - 1.0 if a > 0 else np.nan


def feature_row(x: pd.DataFrame, i: int, ts: pd.Timestamp) -> dict | None:
    if i < 300:
        return None
    hist = x.iloc[i - 300 : i]
    if len(hist) != 300:
        return None
    entry = float(x.iloc[i].open)
    if not entry > 0:
        return None

    closes = hist.close.astype(float)
    ema20s = closes.ewm(span=20, adjust=False).mean()
    ema50s = closes.ewm(span=50, adjust=False).mean()
    ema20 = float(ema20s.iloc[-1])
    ema50 = float(ema50s.iloc[-1])
    last_close = float(closes.iloc[-1])

    w48 = hist.iloc[-48:]
    w12 = hist.iloc[-12:]
    h48, l48 = float(w48.high.max()), float(w48.low.min())
    h12, l12 = float(w12.high.max()), float(w12.low.min())
    width48 = h48 - l48
    width12 = h12 - l12

    c13 = closes.iloc[-13:].to_numpy(float)
    c49 = closes.iloc[-49:].to_numpy(float)
    lr12 = np.diff(np.log(c13))
    lr48 = np.diff(np.log(c49))
    rv12 = float(np.std(lr12, ddof=0)) if len(lr12) else np.nan
    rv48 = float(np.std(lr48, ddof=0)) if len(lr48) else np.nan

    path = c13
    denom = float(np.abs(np.diff(path)).sum())
    efficiency = abs(float(path[-1] - path[0])) / denom if denom > 0 else np.nan

    last3 = hist.iloc[-3:]
    ranges = (last3.high - last3.low).to_numpy(float)
    lower = (np.minimum(last3.open, last3.close) - last3.low).to_numpy(float)
    wick_share = np.divide(lower, ranges, out=np.full(3, np.nan), where=ranges > 0)
    lower_wick_pressure = float(np.nanmean(wick_share)) if np.isfinite(wick_share).any() else np.nan

    a = hist.iloc[-12:-6]
    b = hist.iloc[-6:]
    mid_a = 0.5 * (float(a.high.max()) + float(a.low.min()))
    mid_b = 0.5 * (float(b.high.max()) + float(b.low.min()))
    swing_slope = (mid_b - mid_a) / last_close if last_close > 0 else np.nan

    reclaim = bool(
        float(closes.iloc[-2]) <= float(ema20s.iloc[-2])
        and float(closes.iloc[-1]) > float(ema20s.iloc[-1])
    )

    local = ts + pd.Timedelta(hours=7)
    row = {
        "entry_ts_utc": ts,
        "local_wib": local,
        "local_year": int(local.year),
        "anchor_minute": int(local.minute),
        "entry_price": entry,
        "drive_15m": drive(closes, 3),
        "drive_60m": drive(closes, 12),
        "drive_240m": drive(closes, 48),
        "ema20_ema50_spread": ema20 / ema50 - 1.0 if ema50 > 0 else np.nan,
        "range_location_240m": (last_close - l48) / width48 if width48 > 0 else np.nan,
        "range_ratio_60_240": safe_ratio(width12, width48),
        "rv_ratio_60_240": safe_ratio(rv12, rv48),
        "efficiency_60m": efficiency,
        "lower_wick_pressure_15m": lower_wick_pressure,
        "swing_slope_30_30": swing_slope,
        "above_ema20": bool(last_close > ema20),
        "ema20_reclaim": reclaim,
    }
    for h in HORIZONS:
        ex_ts = ts + pd.Timedelta(minutes=h)
        j = x.index.get_indexer([ex_ts])[0]
        row[f"r{h}"] = float(x.iloc[j].open) / entry - 1.0 if j >= 0 else np.nan
    return row


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idx = x.index
    for i, ts in enumerate(idx):
        local = ts + pd.Timedelta(hours=7)
        if local.year not in DEV_YEARS or local.hour != 0 or local.minute not in ANCHOR_MINUTES:
            continue
        row = feature_row(x, i, ts)
        if row is not None and all(np.isfinite(row[f"r{h}"]) for h in HORIZONS):
            rows.append(row)
    E = pd.DataFrame(rows).sort_values("entry_ts_utc").reset_index(drop=True)
    if len(E) < 3000:
        raise RuntimeError(f"unexpectedly low H00 development event count: {len(E)}")
    E["consensus_return"] = E[[f"r{h}" for h in HORIZONS]].mean(axis=1)
    E["consensus_win"] = E.consensus_return > 0
    return E


def add_causal_percentiles(E: pd.DataFrame) -> pd.DataFrame:
    E = E.copy()
    for feat in NUMERIC_FEATURES:
        out = np.full(len(E), np.nan, float)
        for anchor in ANCHOR_MINUTES:
            pos = np.flatnonzero(E.anchor_minute.to_numpy(int) == anchor)
            vals = E.loc[pos, feat].to_numpy(float)
            for k in range(MIN_HIST, len(pos)):
                prev = vals[max(0, k - ROLL_N) : k]
                prev = prev[np.isfinite(prev)]
                cur = vals[k]
                if len(prev) >= MIN_HIST and np.isfinite(cur):
                    out[pos[k]] = float(np.mean(prev <= cur))
        E[f"{feat}_pct"] = out
    return E


def pf(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0:
        return np.inf if pos > 0 else np.nan
    return pos / neg


def max_loss_streak(x: np.ndarray) -> int:
    best = cur = 0
    for v in np.asarray(x, float):
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def stats(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"n": 0, "wr": np.nan, "mean": np.nan, "median": np.nan, "pf": np.nan, "loss_streak": 0}
    return {
        "n": int(len(x)),
        "wr": float(np.mean(x > 0)),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "pf": float(pf(x)),
        "loss_streak": max_loss_streak(x),
    }


def bin_mask(x: np.ndarray, name: str) -> np.ndarray:
    f = np.isfinite(x)
    if name == "LOW":
        return f & (x >= 0.0) & (x < 1.0 / 3.0)
    if name == "MID":
        return f & (x >= 1.0 / 3.0) & (x < 2.0 / 3.0)
    if name == "HIGH":
        return f & (x >= 2.0 / 3.0) & (x <= 1.0)
    raise ValueError(name)


def masks(E: pd.DataFrame):
    for feat in NUMERIC_FEATURES:
        x = E[f"{feat}_pct"].to_numpy(float)
        for b in BINS:
            yield f"{feat}__{b}", feat, b, bin_mask(x, b)
    for feat in BINARY_FEATURES:
        x = E[feat].astype(bool).to_numpy()
        yield f"{feat}__TRUE", feat, "TRUE", x
        yield f"{feat}__FALSE", feat, "FALSE", ~x


def evaluate(E: pd.DataFrame, rule: str, feat: str, state: str, m: np.ndarray) -> dict:
    q = E.loc[m].copy()
    pooled = stats(q.consensus_return.to_numpy(float))
    row = {
        "rule": rule,
        "feature": feat,
        "state": state,
        "trades": pooled["n"],
        "consensus_wr": pooled["wr"],
        "consensus_mean": pooled["mean"],
        "consensus_median": pooled["median"],
        "consensus_pf": pooled["pf"],
        "max_loss_streak": pooled["loss_streak"],
    }

    supportive_horizons = 0
    for h in HORIZONS:
        s = stats(q[f"r{h}"].to_numpy(float))
        sup = bool(s["n"] >= 160 and s["wr"] >= 0.53 and s["mean"] > 0 and s["pf"] >= 1.10)
        supportive_horizons += int(sup)
        row.update({
            f"h{h}_n": s["n"], f"h{h}_wr": s["wr"], f"h{h}_mean": s["mean"],
            f"h{h}_pf": s["pf"], f"h{h}_supportive": sup,
        })
    row["supportive_horizons"] = supportive_horizons

    years_wr55 = 0
    era_gate = True
    min_year_mean = np.inf
    for y in DEV_YEARS:
        z = q[q.local_year == y]
        s = stats(z.consensus_return.to_numpy(float))
        ok = bool(s["n"] >= 40 and s["wr"] >= 0.52 and s["mean"] > 0 and s["pf"] >= 1.05)
        era_gate &= ok
        years_wr55 += int(np.isfinite(s["wr"]) and s["wr"] > 0.55)
        min_year_mean = min(min_year_mean, s["mean"] if np.isfinite(s["mean"]) else -np.inf)
        row.update({
            f"y{y}_n": s["n"], f"y{y}_wr": s["wr"], f"y{y}_mean": s["mean"],
            f"y{y}_pf": s["pf"], f"y{y}_supportive": ok,
        })
    row["years_wr55"] = years_wr55
    row["min_year_mean"] = float(min_year_mean)
    row["era_gate"] = bool(era_gate and years_wr55 >= 2)

    supportive_anchors = 0
    evaluable_anchors = 0
    for a in ANCHOR_MINUTES:
        z = q[q.anchor_minute == a]
        s = stats(z.consensus_return.to_numpy(float))
        ev = s["n"] >= 40
        sup = bool(ev and s["wr"] >= 0.52 and s["mean"] > 0 and s["pf"] >= 1.05)
        evaluable_anchors += int(ev)
        supportive_anchors += int(sup)
        row.update({
            f"a{a:02d}_n": s["n"], f"a{a:02d}_wr": s["wr"], f"a{a:02d}_mean": s["mean"],
            f"a{a:02d}_pf": s["pf"], f"a{a:02d}_supportive": sup,
        })
    row["evaluable_anchors"] = evaluable_anchors
    row["supportive_anchors"] = supportive_anchors

    row["pooled_gate"] = bool(
        pooled["n"] >= 160
        and np.isfinite(pooled["wr"]) and pooled["wr"] > 0.55
        and np.isfinite(pooled["mean"]) and pooled["mean"] > 0
        and np.isfinite(pooled["pf"]) and pooled["pf"] >= 1.20
    )
    row["horizon_gate"] = supportive_horizons >= 2
    row["anchor_gate"] = evaluable_anchors >= 3 and supportive_anchors >= 3
    row["candidate_gate"] = bool(row["pooled_gate"] and row["horizon_gate"] and row["era_gate"] and row["anchor_gate"])
    return row


def pct(v):
    return "nan" if not np.isfinite(v) else f"{100.0 * float(v):.2f}%"


def main():
    x, coverage = load5()
    E = add_causal_percentiles(build_events(x))
    E.to_csv(OUT_EVENTS, index=False)

    rows = [evaluate(E, rule, feat, state, m) for rule, feat, state, m in masks(E)]
    D = pd.DataFrame(rows)
    if len(D) != len(NUMERIC_FEATURES) * 3 + len(BINARY_FEATURES) * 2:
        raise AssertionError(f"unexpected candidate count {len(D)}")

    sort_cols = [
        "candidate_gate", "min_year_mean", "years_wr55", "supportive_anchors",
        "supportive_horizons", "consensus_mean", "consensus_wr", "consensus_pf", "rule",
    ]
    asc = [False, False, False, False, False, False, False, False, True]
    D = D.sort_values(sort_cols, ascending=asc).reset_index(drop=True)
    C = D[D.candidate_gate].copy().reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# BNB LONG Reset V1 — H00 Primary Character Discovery", "",
        f"Data coverage (2021-12 support + Development through 2024): **{coverage:.4%}**.",
        f"Development H00 events: **{len(E)}**.",
        "Habitat: **00:00–01:00 WIB only**, quarter-hour anchors :00/:15/:30/:45.",
        "OOS: **not downloaded / not evaluated**.",
        "Primary search: **single structural feature/state only**; no pairwise rescue filters.",
        f"Primary candidates evaluated: **{len(D)}**; full-gate passers: **{len(C)}**.", "",
        "## Ranked primary characters", "",
        "| # | Rule | N | Consensus WR | Mean | PF | H support | Anchor support | Years >55% | 2022 WR/Mean | 2023 | 2024 | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(D.head(20).itertuples(index=False), 1):
        lines.append(
            f"| {i} | {r.rule} | {int(r.trades)} | {pct(r.consensus_wr)} | {pct(r.consensus_mean)} | {r.consensus_pf:.3f} | "
            f"{int(r.supportive_horizons)}/3 | {int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | {int(r.years_wr55)}/3 | "
            f"{pct(r.y2022_wr)}/{pct(r.y2022_mean)} | {pct(r.y2023_wr)}/{pct(r.y2023_mean)} | {pct(r.y2024_wr)}/{pct(r.y2024_mean)} | "
            f"{'PASS' if r.candidate_gate else 'FAIL'} |"
        )

    if len(C) == 0:
        status = "PRIMARY_FAIL"
        OUT_STATUS.write_text(status + "\n")
        OUT_SELECTED.write_text(json.dumps({"status": status, "selected": None}, indent=2) + "\n")
        lines += [
            "", f"**Verdict: {status}**", "",
            "No single-feature H00 primary character passed the preregistered pooled + horizon + cross-year + anchor gates.",
            "No gate relaxation and no secondary-filter rescue is permitted for this H00 primary search.",
            "Per Reset V1, persist the negative map before considering H01.", "",
            "Research/shadow only.",
        ]
    else:
        s = C.iloc[0]
        status = "PRIMARY_PASS"
        selected = {
            "status": status,
            "rule": str(s.rule),
            "feature": str(s.feature),
            "state": str(s.state),
            "n": int(s.trades),
            "consensus_wr": float(s.consensus_wr),
            "consensus_mean": float(s.consensus_mean),
            "consensus_pf": float(s.consensus_pf),
            "supportive_horizons": int(s.supportive_horizons),
            "supportive_anchors": int(s.supportive_anchors),
            "evaluable_anchors": int(s.evaluable_anchors),
            "years_wr55": int(s.years_wr55),
            "min_year_mean": float(s.min_year_mean),
        }
        OUT_STATUS.write_text(status + "\n")
        OUT_SELECTED.write_text(json.dumps(selected, indent=2) + "\n")
        lines += [
            "", "## Selected primary character", "",
            f"**{s.rule}**", "",
            f"N **{int(s.trades)}**, consensus WR **{pct(s.consensus_wr)}**, mean consensus return **{pct(s.consensus_mean)}**, PF **{float(s.consensus_pf):.3f}**.",
            f"Supportive diagnostic horizons **{int(s.supportive_horizons)}/3**; supportive quarter-hour anchors **{int(s.supportive_anchors)}/{int(s.evaluable_anchors)}**; years with WR >55% **{int(s.years_wr55)}/3**.", "",
            f"**Verdict: {status}**", "",
            "Stop scanning new hours. The selected primary must be frozen before any secondary confirmation/stress test. OOS remains sealed.", "",
            "Research/shadow only.",
        ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
