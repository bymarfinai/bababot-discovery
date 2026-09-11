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
PFX = "ETH_TEMPORAL_A2_23WIB_MINIMAL_STATE"
OUT_CAND = ROOT / f"{PFX}_Candidates.csv"
OUT_YEAR = ROOT / f"{PFX}_Yearly.csv"
OUT_THRESH = ROOT / f"{PFX}_Thresholds.csv"
OUT_FAMILY = ROOT / f"{PFX}_Family_Best.csv"
OUT_MD = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BASE = "https://data.binance.vision/data/futures/um/monthly/klines/ETHUSDT/5m"
START = pd.Timestamp("2022-01-01T00:00:00Z")
END = pd.Timestamp("2025-01-01T00:00:00Z")
ENTRY_HOUR_UTC = 16  # 23:00 WIB
LOOKBACKS = (15, 30, 60, 120, 240, 360)
HOLDS = (60, 120, 240, 360, 720, 960)
FAMILIES = ("TREND", "EFFICIENCY", "RV", "RANGE_POS", "DRIVE")
BINS = ("LOW", "MID", "HIGH")
NOTIONAL = 500.0
FEE = 0.75
BAR = pd.Timedelta(minutes=5)


def month_urls():
    out = []
    m = START
    while m < END:
        ym = m.strftime("%Y-%m")
        out.append(f"{BASE}/ETHUSDT-5m-{ym}.zip")
        m += pd.offsets.MonthBegin(1)
    return out


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={"User-Agent": "bababot-eth-temporal-a2/1.0"})
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
    expected = int((END - START) / BAR)
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
    return dict(N=n, WR=wr, net=net, exp=exp, PF=float(pf), DD=dd, LS=max_loss_streak(pnl) if n else 0)


def feature_values(x: pd.DataFrame, anchor: pd.Timestamp, lb: int):
    first_close_ts = anchor - pd.Timedelta(minutes=lb) - BAR
    last_close_ts = anchor - BAR
    closes = x.loc[first_close_ts:last_close_ts, "close"]
    bars = x.loc[anchor - pd.Timedelta(minutes=lb):last_close_ts, ["high", "low", "close"]]
    expected_returns = lb // 5
    if len(closes) != expected_returns + 1 or len(bars) != expected_returns:
        return None

    cv = closes.to_numpy(dtype=float)
    diffs = np.diff(cv)
    abs_path = float(np.abs(diffs).sum())
    net_diff = float(cv[-1] - cv[0])
    trend = float(cv[-1] / cv[0] - 1.0)
    efficiency = abs(net_diff) / abs_path if abs_path > 0 else 0.0
    logret = np.diff(np.log(cv))
    rv = float(np.std(logret, ddof=0)) if len(logret) else 0.0
    hi = float(bars.high.max())
    lo = float(bars.low.min())
    range_pos = float((cv[-1] - lo) / (hi - lo)) if hi > lo else 0.5
    drive = net_diff / abs_path if abs_path > 0 else 0.0
    return {
        "TREND": trend,
        "EFFICIENCY": efficiency,
        "RV": rv,
        "RANGE_POS": range_pos,
        "DRIVE": drive,
    }


def build_base(x: pd.DataFrame):
    days = pd.date_range(START.normalize(), (END - pd.Timedelta(days=1)).normalize(), freq="D", tz="UTC")
    rows = []
    for day in days:
        anchor = day + pd.Timedelta(hours=ENTRY_HOUR_UTC)
        if anchor >= END:
            continue
        entry = x["open"].get(anchor, np.nan)
        if pd.isna(entry):
            continue
        row = {"ts": anchor, "year": anchor.year, "entry": float(entry)}
        ok = True
        for lb in LOOKBACKS:
            fv = feature_values(x, anchor, lb)
            if fv is None:
                ok = False
                break
            for fam, val in fv.items():
                row[f"{fam}_{lb}"] = val
        if not ok:
            continue
        for hold in HOLDS:
            exit_ts = anchor + pd.Timedelta(minutes=hold)
            if exit_ts >= END:
                row[f"pnl_{hold}"] = np.nan
                continue
            exit_px = x["open"].get(exit_ts, np.nan)
            if pd.isna(exit_px):
                row[f"pnl_{hold}"] = np.nan
            else:
                row[f"pnl_{hold}"] = NOTIONAL * (float(exit_px) / float(entry) - 1.0) - FEE
        rows.append(row)
    return pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)


def assign_bin(v: pd.Series, q33: float, q67: float):
    return np.where(v <= q33, "LOW", np.where(v <= q67, "MID", "HIGH"))


def formal_gate(m, yrs):
    pooled = (
        m["N"] >= 160 and
        m["WR"] >= 55.0 and
        m["net"] > 0 and
        m["exp"] >= 0.50 and
        m["PF"] >= 1.20 and
        m["DD"] <= 125.0 and
        m["LS"] <= 8
    )
    era_ok = True
    wr55 = 0
    for y in (2022, 2023, 2024):
        z = yrs[y]
        era_ok = era_ok and (
            z["N"] >= 40 and
            z["WR"] >= 52.0 and
            z["net"] > 0 and
            z["exp"] > 0 and
            z["PF"] >= 1.05
        )
        wr55 += int(z["WR"] >= 55.0)
    return bool(pooled and era_ok and wr55 >= 2), bool(pooled), bool(era_ok and wr55 >= 2), wr55


def main():
    x, coverage = load5()
    base = build_base(x)
    if len(base) < 1000:
        raise RuntimeError(f"too few complete 23WIB anchors: {len(base)}")

    thresholds = []
    state_bins = {}
    for fam in FAMILIES:
        for lb in LOOKBACKS:
            col = f"{fam}_{lb}"
            cal = base.loc[base.year == 2022, col].dropna()
            if len(cal) < 300:
                raise RuntimeError(f"insufficient 2022 calibration for {col}: {len(cal)}")
            q33 = float(cal.quantile(1.0 / 3.0))
            q67 = float(cal.quantile(2.0 / 3.0))
            thresholds.append({"family": fam, "lookback_min": lb, "q33_2022": q33, "q67_2022": q67, "n_cal_2022": len(cal)})
            state_bins[(fam, lb)] = assign_bin(base[col], q33, q67)
    pd.DataFrame(thresholds).to_csv(OUT_THRESH, index=False)

    rows = []
    yrows = []
    for fam in FAMILIES:
        for lb in LOOKBACKS:
            labels = state_bins[(fam, lb)]
            for bin_name in BINS:
                mask = labels == bin_name
                for hold in HOLDS:
                    q = base.loc[mask, ["ts", "year", f"pnl_{hold}"]].dropna().copy()
                    q = q.rename(columns={f"pnl_{hold}": "pnl"})
                    m = metrics(q.pnl.to_numpy())
                    yrs = {}
                    for year in (2022, 2023, 2024):
                        z = q[q.year == year]
                        ym = metrics(z.pnl.to_numpy())
                        yrs[year] = ym
                        yrows.append({
                            "family": fam,
                            "lookback_min": lb,
                            "state_bin": bin_name,
                            "hold_min": hold,
                            "year": year,
                            **ym,
                        })
                    passed, pooled_ok, era_ok, wr55_years = formal_gate(m, yrs)
                    row = {
                        "family": fam,
                        "lookback_min": lb,
                        "state_bin": bin_name,
                        "hold_min": hold,
                        **m,
                        "formal_pass": passed,
                        "pooled_gate": pooled_ok,
                        "era_gate": era_ok,
                        "wr55_years": wr55_years,
                        "min_forward_exp": min(yrs[2023]["exp"], yrs[2024]["exp"]),
                        "min_year_exp": min(yrs[y]["exp"] for y in (2022, 2023, 2024)),
                        "min_year_wr": min(yrs[y]["WR"] for y in (2022, 2023, 2024)),
                    }
                    for year in (2022, 2023, 2024):
                        for k in ("N", "WR", "net", "exp", "PF", "DD", "LS"):
                            row[f"{k}_{year}"] = yrs[year][k]
                    rows.append(row)

    cand = pd.DataFrame(rows)
    yearly = pd.DataFrame(yrows)
    cand = cand.sort_values(
        by=["formal_pass", "min_forward_exp", "min_year_exp", "exp", "PF", "WR", "DD", "LS", "hold_min", "lookback_min", "family", "state_bin"],
        ascending=[False, False, False, False, False, False, True, True, True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    cand.to_csv(OUT_CAND, index=False)
    yearly.to_csv(OUT_YEAR, index=False)

    family_best = cand.groupby("family", sort=False, as_index=False).head(1).copy()
    family_best.to_csv(OUT_FAMILY, index=False)

    # Unconditional 23WIB LONG controls for all holds.
    controls = []
    for hold in HOLDS:
        q = base[["ts", "year", f"pnl_{hold}"]].dropna().rename(columns={f"pnl_{hold}": "pnl"})
        controls.append((hold, metrics(q.pnl.to_numpy())))

    passers = cand[cand.formal_pass].copy()
    best = cand.iloc[0]
    lines = [
        "# ETH Temporal A2 — 23:00 WIB Minimal-State Discovery — Result",
        "",
        f"- ETHUSDT 5m Development coverage: **{coverage:.6%}**",
        f"- Complete 23:00 WIB anchors: **{len(base)}**",
        f"- Search: 5 families × 6 lookbacks × 3 bins × 6 holds = **{len(cand)} candidates**",
        f"- 2022-calibrated quantile thresholds frozen before 2023/2024 application: **YES**",
        f"- Formal pass candidates: **{len(passers)}**",
        f"- Formal pass families: **{passers.family.nunique() if len(passers) else 0}**",
        "",
        "## Unconditional 23:00 WIB LONG controls",
        "",
        "| Hold | N | WR | Net | Exp | PF | DD | LS |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for hold, m in controls:
        lines.append(f"| {hold}m | {m['N']} | {m['WR']:.2f}% | ${m['net']:.2f} | ${m['exp']:.4f} | {m['PF']:.3f} | ${m['DD']:.2f} | {m['LS']} |")

    lines += [
        "",
        "## Best candidate per one-dimensional state family",
        "",
        "| Family | LB | Bin | Hold | PASS | N | WR | Net | Exp | PF | DD | LS | MinFwdExp | WR22/23/24 |",
        "|---|---:|:---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in family_best.iterrows():
        lines.append(
            f"| {r.family} | {int(r.lookback_min)}m | {r.state_bin} | {int(r.hold_min)}m | {'YES' if r.formal_pass else 'NO'} | {int(r.N)} | {r.WR:.2f}% | ${r.net:.2f} | ${r.exp:.4f} | {r.PF:.3f} | ${r.DD:.2f} | {int(r.LS)} | ${r.min_forward_exp:.4f} | {r.WR_2022:.2f}/{r.WR_2023:.2f}/{r.WR_2024:.2f}% |"
        )

    lines += ["", "## Formal pass candidates", ""]
    if len(passers):
        lines += [
            "| Rank | Family | LB | Bin | Hold | N | WR | Net | Exp | PF | DD | LS | MinFwdExp | Exp22/23/24 |",
            "|---:|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for i, (_, r) in enumerate(passers.iterrows(), start=1):
            lines.append(
                f"| {i} | {r.family} | {int(r.lookback_min)}m | {r.state_bin} | {int(r.hold_min)}m | {int(r.N)} | {r.WR:.2f}% | ${r.net:.2f} | ${r.exp:.4f} | {r.PF:.3f} | ${r.DD:.2f} | {int(r.LS)} | ${r.min_forward_exp:.4f} | {r.exp_2022:.3f}/{r.exp_2023:.3f}/{r.exp_2024:.3f} |"
            )
    else:
        lines.append("No candidate passed the frozen formal gate. Near-misses remain diagnostic only.")

    lines += [
        "",
        "## Overall robustness-ranked candidate",
        f"**{best.family} / LB{int(best.lookback_min)} / {best.state_bin} / H{int(best.hold_min)}** — formal_pass={bool(best.formal_pass)}; N={int(best.N)}, WR={best.WR:.2f}%, net=${best.net:.2f}, exp=${best.exp:.4f}, PF={best.PF:.3f}, DD=${best.DD:.2f}, LS={int(best.LS)}, min-forward-exp=${best.min_forward_exp:.4f}.",
        "",
        "## Interpretation boundary",
        "A2 is a one-dimensional state-discovery experiment at one exact clock. A PASS identifies a minimal conditional state worth advancing; it is not a production strategy. No state-family combinations were tested and OOS was not opened.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(("FORMAL_PASS\n" if len(passers) else "NO_FORMAL_PASS\n"), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
