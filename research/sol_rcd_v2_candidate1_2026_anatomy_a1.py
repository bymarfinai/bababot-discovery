#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as legacy
import sol_robust_character_discovery_v2_phase1a as p1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RCD_V2_CANDIDATE1_2026_ANATOMY_A1"
BOUNDARIES_FILE = ROOT / "SOL_RCD_V2_PHASE1A_ScaleBoundaries.csv"
FINALISTS_FILE = ROOT / "SOL_RCD_V2_PHASE1A_FrozenFinalists.csv"

RULE = "DRIVE_UP__STR_B0_20"
SCALE = "RAW_RANGE_LB_HIGH"
LOOKBACK = 30
HOLD = 960
PARTITIONS = ("external", "development", "reference_validation")
FEATURES = (
    "ret_24h", "ret_72h", "ret_7d",
    "range_24h", "range_72h", "range_7d",
    "loc_24h", "loc_72h", "loc_7d",
    "range_ratio_24_72",
)
VOL_FEATURES = {"range_24h", "range_72h", "range_7d", "range_ratio_24_72"}
DIRLOC_FEATURES = set(FEATURES) - VOL_FEATURES


def out(name: str) -> Path:
    return ROOT / f"{PFX}_{name}"


def load_phase1_bounds() -> dict[str, tuple[float, float]]:
    x = pd.read_csv(BOUNDARIES_FILE)
    z = x[x.lookback_min == LOOKBACK]
    return {str(r.scale_variable): (float(r.q33), float(r.q67)) for r in z.itertuples(index=False)}


def validate_frozen_candidate() -> None:
    x = pd.read_csv(FINALISTS_FILE).sort_values("freeze_rank")
    r = x.iloc[0]
    expected = (RULE, SCALE, LOOKBACK, HOLD)
    observed = (str(r.shape_rule), str(r.scale_state), int(r.lookback_min), int(r.hold_min))
    if observed != expected:
        raise RuntimeError(f"frozen candidate #1 mismatch: {observed} != {expected}")


def window_context(opens, highs, lows, entry_ix: int, bars: int) -> tuple[float, float, float]:
    start = entry_ix - bars
    if start < 0:
        return np.nan, np.nan, np.nan
    start_open = float(opens[start])
    entry_open = float(opens[entry_ix])
    if start_open <= 0 or entry_open <= 0:
        return np.nan, np.nan, np.nan
    ret = entry_open / start_open - 1.0
    h = float(np.max(highs[start:entry_ix]))
    l = float(np.min(lows[start:entry_ix]))
    width = h - l
    rr = width / start_open if width > 0 else 0.0
    loc = (entry_open - l) / width if width > 0 else np.nan
    return ret, rr, float(np.clip(loc, 0.0, 1.0)) if np.isfinite(loc) else np.nan


def build_partition_frame(x5: pd.DataFrame, part: str) -> pd.DataFrame:
    a, z = base.PARTS[part]
    pieces = []
    for clock in p1.CLOCKS:
        f = p1.enhanced_frame(x5, clock, LOOKBACK)
        et = pd.DatetimeIndex(f.entry_ts)
        pt = pd.DatetimeIndex(f.pre_ts)
        m = (pt >= a) & (et >= a) & (et < z)
        if m.any():
            pieces.append(f.loc[m].copy())
    if not pieces:
        return pd.DataFrame()
    d = pd.concat(pieces, ignore_index=True)
    d["entry_ts"] = pd.to_datetime(d.entry_ts, utc=True)
    d["year"] = d.entry_ts.dt.year.astype(int)
    return d.sort_values(["entry_ts", "clock_min"]).reset_index(drop=True)


def selected_partition_trades(x5: pd.DataFrame, df: pd.DataFrame, part: str, bounds: dict) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame()
    sm = legacy.masks_for_frame(df)[RULE]
    am = p1.scale_masks(df, bounds)[SCALE]
    et = pd.DatetimeIndex(df.entry_ts)
    xt = et + pd.Timedelta(minutes=HOLD)
    xi = x5.index.get_indexer(xt)
    ei = df.entry_ix.to_numpy(int)
    _, part_end = base.PARTS[part]
    valid = (xi >= 0) & ((xi - ei) == HOLD // p1.BAR_MIN) & (xt < part_end)
    idx = np.flatnonzero(sm & am & valid)
    if len(idx) == 0:
        return pd.DataFrame()

    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    rows = []
    for k in idx:
        entry_ix = int(ei[k])
        exit_ix = int(xi[k])
        entry_price = float(opens[entry_ix])
        exit_price = float(opens[exit_ix])
        gross_return = exit_price / entry_price - 1.0
        net = p1.NOTIONAL * gross_return - p1.FEE

        r24, rr24, l24 = window_context(opens, highs, lows, entry_ix, 24 * 60 // p1.BAR_MIN)
        r72, rr72, l72 = window_context(opens, highs, lows, entry_ix, 72 * 60 // p1.BAR_MIN)
        r7d, rr7d, l7d = window_context(opens, highs, lows, entry_ix, 7 * 24 * 60 // p1.BAR_MIN)
        ratio = rr24 / rr72 if np.isfinite(rr24) and np.isfinite(rr72) and rr72 > 0 else np.nan

        future_high = float(np.max(highs[entry_ix:exit_ix]))
        future_low = float(np.min(lows[entry_ix:exit_ix]))
        mfe = future_high / entry_price - 1.0
        mae = future_low / entry_price - 1.0

        rows.append({
            "partition": part,
            "entry_ts": et[k],
            "exit_ts": xt[k],
            "year": int(et[k].year),
            "hour_utc": int(df.hour_utc.iloc[k]),
            "minute_anchor": int(df.minute_anchor.iloc[k]),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "gross_return": gross_return,
            "net": net,
            "ret_24h": r24,
            "ret_72h": r72,
            "ret_7d": r7d,
            "range_24h": rr24,
            "range_72h": rr72,
            "range_7d": rr7d,
            "loc_24h": l24,
            "loc_72h": l72,
            "loc_7d": l7d,
            "range_ratio_24_72": ratio,
            "mfe_pct": mfe,
            "mae_pct": mae,
            "giveback_pct": mfe - gross_return,
        })
    return pd.DataFrame(rows).sort_values(["entry_ts", "minute_anchor"]).reset_index(drop=True)


def qtile(s: pd.Series, q: float) -> float:
    x = pd.to_numeric(s, errors="coerce").dropna().to_numpy(float)
    return float(np.quantile(x, q)) if len(x) else np.nan


def freeze_context_bounds(trades: pd.DataFrame) -> tuple[dict[str, tuple[float, float]], pd.DataFrame]:
    dev = trades[trades.partition == "development"]
    bounds = {}
    rows = []
    for f in FEATURES:
        q1, q2 = qtile(dev[f], 1 / 3), qtile(dev[f], 2 / 3)
        if not np.isfinite(q1) or not np.isfinite(q2):
            raise RuntimeError(f"cannot fit Development terciles for {f}")
        bounds[f] = (q1, q2)
        rows.append({"feature": f, "q33": q1, "q67": q2, "n_fit": int(pd.to_numeric(dev[f], errors="coerce").notna().sum()), "fit_partition": "development_candidate1_only"})
    return bounds, pd.DataFrame(rows)


def label_band(s: pd.Series, q1: float, q2: float) -> pd.Series:
    x = pd.to_numeric(s, errors="coerce")
    o = pd.Series("NA", index=s.index, dtype="object")
    o.loc[np.isfinite(x) & (x <= q1)] = "LOW"
    o.loc[np.isfinite(x) & (x > q1) & (x <= q2)] = "MID"
    o.loc[np.isfinite(x) & (x > q2)] = "HIGH"
    return o


def psi(dev_bands: pd.Series, other_bands: pd.Series) -> float:
    labels = ("LOW", "MID", "HIGH")
    eps = 1e-6
    p = np.array([(dev_bands == b).mean() for b in labels], float)
    q = np.array([(other_bands == b).mean() for b in labels], float)
    p = np.clip(p, eps, None); q = np.clip(q, eps, None)
    p /= p.sum(); q /= q.sum()
    return float(np.sum((q - p) * np.log(q / p)))


def cohort_map(trades: pd.DataFrame) -> dict[str, pd.DataFrame]:
    m = {
        "external": trades[trades.partition == "external"],
        "development": trades[trades.partition == "development"],
        "reference_validation": trades[trades.partition == "reference_validation"],
    }
    for y in range(2020, 2027):
        m[str(y)] = trades[trades.year == y]
    return m


def feature_shift(trades: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    dev = trades[trades.partition == "development"]
    rows = []
    cohorts = cohort_map(trades)
    for f in FEATURES:
        q1, q2 = bounds[f]
        db = label_band(dev[f], q1, q2)
        dev_vals = pd.to_numeric(dev[f], errors="coerce").dropna()
        dev_iqr = float(dev_vals.quantile(.75) - dev_vals.quantile(.25)) if len(dev_vals) else np.nan
        dev_med = float(dev_vals.median()) if len(dev_vals) else np.nan
        for name, g in cohorts.items():
            vals = pd.to_numeric(g[f], errors="coerce").dropna()
            gb = label_band(g[f], q1, q2)
            med = float(vals.median()) if len(vals) else np.nan
            displacement = abs(med - dev_med) / dev_iqr if np.isfinite(med) and np.isfinite(dev_iqr) and dev_iqr > 0 else np.nan
            rows.append({
                "feature": f, "cohort": name, "n": int(len(vals)),
                "median": med,
                "q25": float(vals.quantile(.25)) if len(vals) else np.nan,
                "q75": float(vals.quantile(.75)) if len(vals) else np.nan,
                "dev_q33": q1, "dev_q67": q2,
                "psi_vs_development": 0.0 if name == "development" else psi(db, gb),
                "median_displacement_dev_iqr": displacement,
                "low_share": float((gb == "LOW").mean()) if len(g) else np.nan,
                "mid_share": float((gb == "MID").mean()) if len(g) else np.nan,
                "high_share": float((gb == "HIGH").mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def band_economics(trades: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    rows = []
    groups = [("partition", p, trades[trades.partition == p]) for p in PARTITIONS]
    groups += [("year", str(y), trades[trades.year == y]) for y in range(2020, 2027)]
    for f in FEATURES:
        q1, q2 = bounds[f]
        bands = label_band(trades[f], q1, q2)
        for gt, gv, g in groups:
            for band in ("LOW", "MID", "HIGH"):
                z = g[bands.loc[g.index] == band]
                s = p1.stats(z.net.to_numpy(float), True)
                rows.append({"feature": f, "group_type": gt, "group_value": gv, "band": band, **s})
    return pd.DataFrame(rows)


def path_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in range(2020, 2027):
        z = trades[trades.year == y]
        s = p1.stats(z.net.to_numpy(float), True)
        rows.append({
            "year": y, **s,
            "median_mfe_pct": float(z.mfe_pct.median()) if len(z) else np.nan,
            "median_mae_pct": float(z.mae_pct.median()) if len(z) else np.nan,
            "median_giveback_pct": float(z.giveback_pct.median()) if len(z) else np.nan,
        })
    return pd.DataFrame(rows)


def discriminator_table(trades: pd.DataFrame, bounds: dict, shifts: pd.DataFrame, be: pd.DataFrame) -> pd.DataFrame:
    rows = []
    y2026 = trades[trades.year == 2026]
    y2025 = trades[trades.year == 2025]
    dev = trades[trades.partition == "development"]

    for f in FEATURES:
        q1, q2 = bounds[f]
        b26 = label_band(y2026[f], q1, q2)
        counts26 = {b: int((b26 == b).sum()) for b in ("LOW", "MID", "HIGH")}
        dominant = max(counts26, key=counts26.get) if len(y2026) else "NA"
        dom_n = counts26.get(dominant, 0)
        dom_share = dom_n / len(y2026) if len(y2026) else np.nan

        b25 = label_band(y2025[f], q1, q2)
        share25 = float((b25 == dominant).mean()) if len(y2025) and dominant != "NA" else np.nan

        s26 = shifts[(shifts.feature == f) & (shifts.cohort == "2026")].iloc[0]
        psi26 = float(s26.psi_vs_development)
        displacement = float(s26.median_displacement_dev_iqr)

        def econ(group_type: str, group_value: str, band: str):
            z = be[(be.feature == f) & (be.group_type == group_type) & (be.group_value.astype(str) == str(group_value)) & (be.band == band)]
            return z.iloc[0] if len(z) else None

        ddom = econ("partition", "development", dominant) if dominant != "NA" else None
        other_exps = []
        for b in ("LOW", "MID", "HIGH"):
            if b == dominant:
                continue
            r = econ("partition", "development", b)
            if r is not None and np.isfinite(r.expectancy):
                other_exps.append(float(r.expectancy))
        best_other = max(other_exps) if other_exps else np.nan
        dev_dom_n = int(ddom.trades) if ddom is not None else 0
        dev_dom_exp = float(ddom.expectancy) if ddom is not None else np.nan
        separation = best_other - dev_dom_exp if np.isfinite(best_other) and np.isfinite(dev_dom_exp) else np.nan

        r25 = econ("year", "2025", dominant) if dominant != "NA" else None
        exp25 = float(r25.expectancy) if r25 is not None else np.nan
        n25 = int(r25.trades) if r25 is not None else 0

        c1 = psi26 >= 0.25
        c2 = bool(np.isfinite(dom_share) and dom_share >= 0.55 and dom_n >= 15)
        c3 = bool(dev_dom_n >= 40 and np.isfinite(separation) and separation >= 0.75)
        contradiction25 = bool(np.isfinite(share25) and share25 >= 0.55 and np.isfinite(exp25) and exp25 > 0)
        c4 = not contradiction25
        qualifies = bool(c1 and c2 and c3 and c4)
        family = "volatility" if f in VOL_FEATURES else "direction_location"

        rows.append({
            "feature": f, "family": family, "psi_2026_vs_dev": psi26,
            "median_displacement_dev_iqr": displacement,
            "dominant_2026_band": dominant, "dominant_2026_n": dom_n,
            "dominant_2026_share": dom_share,
            "dev_dominant_band_n": dev_dom_n, "dev_dominant_band_expectancy": dev_dom_exp,
            "best_other_dev_band_expectancy": best_other, "dev_separation": separation,
            "share_2025_same_band": share25, "n_2025_same_band": n25,
            "expectancy_2025_same_band": exp25,
            "psi_gate": c1, "concentration_gate": c2, "economic_separation_gate": c3,
            "not_contradicted_by_2025": c4, "primary_discriminator": qualifies,
        })
    return pd.DataFrame(rows).sort_values(["primary_discriminator", "psi_2026_vs_dev", "median_displacement_dev_iqr"], ascending=[False, False, False]).reset_index(drop=True)


def verdict(discriminators: pd.DataFrame) -> str:
    q = discriminators[discriminators.primary_discriminator]
    has_vol = bool((q.family == "volatility").any())
    has_dir = bool((q.family == "direction_location").any())
    if has_vol and has_dir:
        return "MIXED_BROADER_CONTEXT_SHIFT"
    if has_vol:
        return "BROADER_VOLATILITY_CONTEXT_DOMINANT"
    if has_dir:
        return "BROADER_DIRECTION_LOCATION_CONTEXT_DOMINANT"
    return "NO_CLEAR_BROADER_CONTEXT_MECHANISM"


def main() -> None:
    base.synthetic_tests()
    validate_frozen_candidate()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    phase1_bounds = load_phase1_bounds()
    frames = {p: build_partition_frame(x5, p) for p in PARTITIONS}
    pieces = [selected_partition_trades(x5, frames[p], p, phase1_bounds) for p in PARTITIONS]
    pieces = [x for x in pieces if len(x)]
    if not pieces:
        raise RuntimeError("frozen candidate cohort is empty")
    trades = pd.concat(pieces, ignore_index=True).sort_values(["entry_ts", "minute_anchor"]).reset_index(drop=True)

    context_bounds, boundaries = freeze_context_bounds(trades)
    shifts = feature_shift(trades, context_bounds)
    bands = band_economics(trades, context_bounds)
    paths = path_summary(trades)
    discriminators = discriminator_table(trades, context_bounds, shifts, bands)
    label = verdict(discriminators)

    trades.to_csv(out("Trades.csv"), index=False)
    boundaries.to_csv(out("ContextBoundaries.csv"), index=False)
    shifts.to_csv(out("FeatureShift.csv"), index=False)
    bands.to_csv(out("BandEconomics.csv"), index=False)
    paths.to_csv(out("PathSummary.csv"), index=False)
    discriminators.to_csv(out("Discriminators.csv"), index=False)
    out("Status.txt").write_text(f"SOL_RCD_V2_CANDIDATE1_2026_ANATOMY_A1_{label}\n", encoding="utf-8")

    lines = [
        "# SOL RCD v2 Candidate #1 — 2026 Anatomy A1 Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        f"Frozen candidate: **{RULE} + {SCALE} / LB{LOOKBACK} / Hold{HOLD}m**.",
        "Diagnostic only: no filter, threshold, hold, entry, exit, or candidate was optimized in this experiment.", "",
        f"## Preregistered verdict: **{label}**", "",
        "## 2026 broader-context discriminator ranking", "",
        "| Feature | Family | PSI | 2026 band | Share | Dev band Exp | Best other Dev Exp | Separation | 2025 same-band share | 2025 band Exp | Primary? |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in discriminators.itertuples(index=False):
        lines.append(
            f"| `{r.feature}` | {r.family} | {r.psi_2026_vs_dev:.3f} | {r.dominant_2026_band} | {100*r.dominant_2026_share:.1f}% | "
            f"${r.dev_dominant_band_expectancy:+.2f} | ${r.best_other_dev_band_expectancy:+.2f} | ${r.dev_separation:+.2f} | "
            f"{100*r.share_2025_same_band:.1f}% | ${r.expectancy_2025_same_band:+.2f} | {'YES' if r.primary_discriminator else 'no'} |"
        )

    lines += ["", "## Frozen candidate path by year", "",
              "| Year | N | WR | Net | Exp | PF | DD | LS | Med MFE | Med MAE | Med giveback |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in paths.itertuples(index=False):
        lines.append(
            f"| {int(r.year)} | {int(r.trades)} | {100*r.win_rate:.2f}% | ${r.net_pnl:+.2f} | ${r.expectancy:+.2f} | {r.pf:.3f} | "
            f"${r.max_dd:.2f} | {int(r.max_loss_streak)} | {100*r.median_mfe_pct:.2f}% | {100*r.median_mae_pct:.2f}% | {100*r.median_giveback_pct:.2f}% |"
        )

    lines += ["", "## Stop-rule note", "",
              "Any primary discriminator found here is **diagnostic evidence only**. It is not a promoted trading filter. A future RCD-v3 must be separately preregistered and may not optimize a threshold on exposed 2026 data."]
    out("Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out("Status.txt").read_text(encoding="utf-8").strip())
    print(out("Result.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
