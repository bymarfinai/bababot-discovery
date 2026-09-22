#!/usr/bin/env python3
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import math
import time
import requests
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_DERIVATIVES_LIQUIDITY_LAYER_V1"
TRADES_FILE = ROOT / "SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1_Trades.csv"
BASE = "https://data.binance.vision/data/futures/um/daily/metrics/SOLUSDT"
TIMEOUT = 30

FEATURES = [
    "oi_value",
    "top_position_ratio",
    "top_account_ratio",
    "global_account_ratio",
    "taker_ratio",
    "oi_change_1h",
    "oi_change_4h",
    "taker_log",
    "global_log",
    "top_position_log",
    "sweep_taker_pressure",
    "sweep_crowd_pressure",
    "sweep_top_position_pressure",
    "oi_trap_interaction_1h",
]

EXPECTED_COLUMNS = {
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
}


def safe_float(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else np.nan
    except Exception:
        return np.nan


def auc_rank(feature, outcome):
    x = pd.to_numeric(feature, errors="coerce")
    y = pd.Series(outcome).astype(float)
    m = x.notna() & y.notna()
    x = x[m]
    y = y[m].astype(int)
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = x.rank(method="average")
    r1 = float(ranks[y == 1].sum())
    return (r1 - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def spearman(x, y):
    a = pd.to_numeric(x, errors="coerce")
    b = pd.to_numeric(y, errors="coerce")
    m = a.notna() & b.notna()
    if int(m.sum()) < 3:
        return np.nan
    return float(a[m].rank(method="average").corr(b[m].rank(method="average")))


def download_day(day: pd.Timestamp):
    d = day.strftime("%Y-%m-%d")
    url = f"{BASE}/SOLUSDT-metrics-{d}.zip"
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=TIMEOUT)
            if r.status_code == 404:
                return None, 404, url
            r.raise_for_status()
            with ZipFile(BytesIO(r.content)) as zf:
                names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not names:
                    return None, 422, url
                with zf.open(names[0]) as fh:
                    df = pd.read_csv(fh)
            return df, 200, url
        except Exception as exc:
            last = exc
            time.sleep(1.0 + attempt)
    return None, -1, f"{url} :: {last}"


def normalize_metrics(df):
    if df is None or df.empty:
        return pd.DataFrame()

    cols = {str(c).strip(): c for c in df.columns}
    missing = sorted(EXPECTED_COLUMNS - set(cols))
    if missing:
        raise RuntimeError(f"Unexpected metrics schema; missing {missing}; got {list(df.columns)}")

    z = pd.DataFrame()
    z["time"] = pd.to_datetime(df[cols["create_time"]], utc=True, errors="coerce")
    for out, src in [
        ("oi_value", "sum_open_interest_value"),
        ("top_account_ratio", "count_toptrader_long_short_ratio"),
        ("top_position_ratio", "sum_toptrader_long_short_ratio"),
        ("global_account_ratio", "count_long_short_ratio"),
        ("taker_ratio", "sum_taker_long_short_vol_ratio"),
    ]:
        z[out] = pd.to_numeric(df[cols[src]], errors="coerce")

    z = z.dropna(subset=["time"]).sort_values("time").drop_duplicates("time")
    return z.reset_index(drop=True)


def load_window(entry_time, cache, archive_log):
    days = [
        (entry_time - pd.Timedelta(days=1)).normalize(),
        entry_time.normalize(),
    ]
    parts = []
    for day in days:
        key = day.strftime("%Y-%m-%d")
        if key not in cache:
            raw, status, url = download_day(day)
            archive_log.append({"date": key, "status": status, "url": url, "rows": 0 if raw is None else len(raw)})
            cache[key] = normalize_metrics(raw) if raw is not None else None
        if cache[key] is not None and not cache[key].empty:
            parts.append(cache[key])

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values("time").drop_duplicates("time").reset_index(drop=True)


def feature_row(trade, metrics):
    if metrics is None or metrics.empty or "time" not in metrics.columns:
        return None
    entry = pd.Timestamp(trade.entry_time)
    prior = metrics[metrics.time < entry].copy()
    if prior.empty:
        return None

    latest = prior.iloc[-1]
    i = len(prior) - 1
    # Frozen positional lookbacks: exactly 12 and 48 completed 5m rows earlier.
    if i < 48:
        return None

    h1 = prior.iloc[i - 12]
    h4 = prior.iloc[i - 48]

    oi = safe_float(latest.oi_value)
    oi1 = safe_float(h1.oi_value)
    oi4 = safe_float(h4.oi_value)
    taker = safe_float(latest.taker_ratio)
    glob = safe_float(latest.global_account_ratio)
    top_pos = safe_float(latest.top_position_ratio)
    top_acct = safe_float(latest.top_account_ratio)

    if not all(np.isfinite(v) and v > 0 for v in [oi, oi1, oi4, taker, glob, top_pos, top_acct]):
        return None

    oi_change_1h = oi / oi1 - 1.0
    oi_change_4h = oi / oi4 - 1.0
    taker_log = math.log(taker)
    global_log = math.log(glob)
    top_position_log = math.log(top_pos)

    # BUY_SIDE = short after upside sweep; SELL_SIDE = long after downside sweep.
    side_sign = 1.0 if str(trade.side) == "BUY_SIDE" else -1.0
    sweep_taker = side_sign * taker_log
    sweep_crowd = side_sign * global_log
    sweep_top = side_sign * top_position_log

    return {
        "metrics_time": latest.time,
        "metrics_lag_min": (entry - latest.time).total_seconds() / 60.0,
        "oi_value": oi,
        "top_position_ratio": top_pos,
        "top_account_ratio": top_acct,
        "global_account_ratio": glob,
        "taker_ratio": taker,
        "oi_change_1h": oi_change_1h,
        "oi_change_4h": oi_change_4h,
        "taker_log": taker_log,
        "global_log": global_log,
        "top_position_log": top_position_log,
        "sweep_taker_pressure": sweep_taker,
        "sweep_crowd_pressure": sweep_crowd,
        "sweep_top_position_pressure": sweep_top,
        "oi_trap_interaction_1h": oi_change_1h * sweep_taker,
    }


def feature_stats(df, feature, group="POOLED"):
    x = df[[feature, "win", "realized_r", "year", "side", "anatomy_score"]].copy()
    x[feature] = pd.to_numeric(x[feature], errors="coerce")
    x = x.dropna(subset=[feature, "win", "realized_r"])
    if x.empty:
        return {
            "group": group, "feature": feature, "n": 0, "wins": 0, "losses": 0,
            "winner_median": np.nan, "loser_median": np.nan, "median_diff": np.nan,
            "auc": np.nan, "spearman_r": np.nan,
        }

    w = x[x.win == 1][feature]
    l = x[x.win == 0][feature]
    return {
        "group": group,
        "feature": feature,
        "n": int(len(x)),
        "wins": int((x.win == 1).sum()),
        "losses": int((x.win == 0).sum()),
        "winner_median": float(w.median()) if len(w) else np.nan,
        "loser_median": float(l.median()) if len(l) else np.nan,
        "median_diff": float(w.median() - l.median()) if len(w) and len(l) else np.nan,
        "auc": float(auc_rank(x[feature], x.win)),
        "spearman_r": float(spearman(x[feature], x.realized_r)),
    }


def candidate_gate(feature, pooled, yearly, side_stats):
    n_ok = int(pooled["n"]) >= 100
    auc = pooled["auc"]
    auc_ok = np.isfinite(auc) and (auc >= 0.58 or auc <= 0.42)
    rho = pooled["spearman_r"]
    rho_ok = np.isfinite(rho) and abs(rho) >= 0.10

    diff = pooled["median_diff"]
    median_ok = np.isfinite(diff) and np.isfinite(auc) and (
        (auc > 0.5 and diff > 0) or (auc < 0.5 and diff < 0)
    )

    qualifying_years = yearly[yearly.n >= 10].copy()
    if np.isfinite(auc) and auc > 0.5:
        same_years = int((qualifying_years.auc > 0.5).sum())
    elif np.isfinite(auc) and auc < 0.5:
        same_years = int((qualifying_years.auc < 0.5).sum())
    else:
        same_years = 0
    year_ok = same_years >= 4

    qualifying_sides = side_stats[side_stats.n >= 30].copy()
    if np.isfinite(auc) and auc > 0.5:
        side_ok = bool((qualifying_sides.auc >= 0.45).all()) if len(qualifying_sides) else False
    elif np.isfinite(auc) and auc < 0.5:
        side_ok = bool((qualifying_sides.auc <= 0.55).all()) if len(qualifying_sides) else False
    else:
        side_ok = False

    passed = bool(n_ok and auc_ok and rho_ok and median_ok and year_ok and side_ok)
    return {
        "feature": feature,
        "n_ge_100": n_ok,
        "auc_extreme_gate": auc_ok,
        "abs_spearman_ge_010": rho_ok,
        "median_direction_agrees": median_ok,
        "same_auc_direction_years_ge_4": year_ok,
        "same_auc_direction_years": same_years,
        "side_noncontradiction": side_ok,
        "passed_all": passed,
    }


def main():
    trades = pd.read_csv(TRADES_FILE)
    trades["entry_time"] = pd.to_datetime(trades.entry_time, utc=True)
    trades["realized_r"] = pd.to_numeric(trades.realized_r, errors="coerce")
    trades["anatomy_score"] = pd.to_numeric(trades.anatomy_score, errors="coerce")
    trades["win"] = (trades.realized_r > 0).astype(int)
    trades["year"] = trades.entry_time.dt.year

    cache = {}
    archive_log = []
    rows = []

    for _, trade in trades.iterrows():
        m = load_window(trade.entry_time, cache, archive_log)
        fr = feature_row(trade, m)
        if fr is None:
            continue
        rows.append({
            "candidate_id": trade.candidate_id,
            "entry_time": trade.entry_time,
            "side": trade.side,
            "anatomy_score": int(trade.anatomy_score),
            "realized_r": float(trade.realized_r),
            "win": int(trade.win),
            "year": int(trade.year),
            **fr,
        })

    feat = pd.DataFrame(rows)
    pd.DataFrame(archive_log).drop_duplicates("date").sort_values("date").to_csv(
        ROOT / f"{PFX}_ArchiveAvailability.csv", index=False
    )

    if feat.empty:
        (ROOT / f"{PFX}_Status.txt").write_text("DERIVATIVES_ARCHIVE_INSUFFICIENT\n", encoding="utf-8")
        (ROOT / f"{PFX}_Result.md").write_text(
            "# SOL Derivatives Liquidity Layer V1 — Result\n\n"
            "**DERIVATIVES_ARCHIVE_INSUFFICIENT**\n\n"
            "No causal feature rows could be constructed from the official archive.\n",
            encoding="utf-8",
        )
        print("DERIVATIVES_ARCHIVE_INSUFFICIENT")
        return

    feat.to_csv(ROOT / f"{PFX}_FeatureRows.csv", index=False)

    stats = []
    yearly_rows = []
    side_rows = []
    score_rows = []

    for f in FEATURES:
        stats.append(feature_stats(feat, f, "POOLED"))

        for year, g in feat.groupby("year"):
            r = feature_stats(g, f, f"YEAR_{year}")
            r["year"] = int(year)
            yearly_rows.append(r)

        for side, g in feat.groupby("side"):
            r = feature_stats(g, f, f"SIDE_{side}")
            r["side"] = side
            side_rows.append(r)

        for score, g in feat.groupby("anatomy_score"):
            r = feature_stats(g, f, f"SCORE_{int(score)}")
            r["anatomy_score"] = int(score)
            score_rows.append(r)

    stats_df = pd.DataFrame(stats)
    yearly_df = pd.DataFrame(yearly_rows)
    side_df = pd.DataFrame(side_rows)
    score_df = pd.DataFrame(score_rows)

    stats_df.to_csv(ROOT / f"{PFX}_FeatureStats.csv", index=False)
    yearly_df.to_csv(ROOT / f"{PFX}_YearlyStats.csv", index=False)
    side_df.to_csv(ROOT / f"{PFX}_SideStats.csv", index=False)
    score_df.to_csv(ROOT / f"{PFX}_ScoreStats.csv", index=False)

    gates = []
    for f in FEATURES:
        pooled = stats_df[stats_df.feature == f].iloc[0].to_dict()
        yr = yearly_df[yearly_df.feature == f]
        sd = side_df[side_df.feature == f]
        gates.append(candidate_gate(f, pooled, yr, sd))
    gates_df = pd.DataFrame(gates)
    gates_df.to_csv(ROOT / f"{PFX}_Gates.csv", index=False)

    passed = gates_df[gates_df.passed_all == True].feature.tolist()
    coverage = len(feat) / len(trades)
    years = sorted(feat.year.unique().tolist())
    archive_dates = pd.DataFrame(archive_log).drop_duplicates("date")
    ok_days = int((archive_dates.status == 200).sum())
    not_found_days = int((archive_dates.status == 404).sum())

    status = "DERIVATIVES_INFORMATION_SIGNAL_FOUND" if passed else "DERIVATIVES_INFORMATION_WEAK_OR_UNSTABLE"
    if len(feat) < 100:
        status = "DERIVATIVES_ARCHIVE_INSUFFICIENT"

    # Rank strongest features by distance from 0.5 AUC, descriptive only.
    rank = stats_df.copy()
    rank["auc_distance"] = (rank.auc - 0.5).abs()
    rank = rank.sort_values(["auc_distance", "n"], ascending=[False, False])

    lines = [
        "# SOL Derivatives Liquidity Layer V1 — Result",
        "",
        f"**Status: {status}**",
        "",
        "## Coverage",
        "",
        f"- Frozen SOL trades: **{len(trades)}**",
        f"- Causal feature rows available: **{len(feat)} ({coverage*100:.2f}%)**",
        f"- Covered years: **{', '.join(map(str, years)) if years else 'none'}**",
        f"- Archive days HTTP 200: **{ok_days}**",
        f"- Archive days HTTP 404: **{not_found_days}**",
        "",
        "## Pooled frozen-feature results",
        "",
        "| Feature | N | Winner median | Loser median | AUC | Spearman R | All gates |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    gate_map = gates_df.set_index("feature").to_dict("index")
    for _, r in rank.iterrows():
        g = gate_map[r.feature]
        lines.append(
            f"| {r.feature} | {int(r.n)} | {r.winner_median:.6f} | {r.loser_median:.6f} | "
            f"{r.auc:.3f} | {r.spearman_r:.3f} | {'PASS' if g['passed_all'] else 'FAIL'} |"
        )

    lines += [
        "",
        "## Gate-passing information signals",
        "",
    ]
    if passed:
        for f in passed:
            lines.append(f"- **{f}**")
    else:
        lines.append("- None.")

    lines += [
        "",
        "## Interpretation",
        "",
        "V1 tests derivatives metrics only as an information layer over the already-frozen SOL detector.",
        "No threshold, entry filter, WR optimization, TP change, or live rule is promoted from this run.",
        "",
        "If a feature passes all frozen gates, the next experiment must preregister a fixed usage rule before testing economics.",
        "If no feature passes, this futures-derivatives proxy is not used to modify the SOL detector.",
        "",
        "This result does not validate or invalidate the options-IV method shown in the video; exact historical option-chain IV snapshots are a separate data problem.",
    ]

    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
