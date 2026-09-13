#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_orb_structure_detector_v1 as detector

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_ORB_ENTRY_STRUCTURE_CHARACTER_V1"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv"
OUT_ENTRY = ROOT / f"{PFX}_EntryComparison.csv"
OUT_FEATURE = ROOT / f"{PFX}_FeatureSummary.csv"
OUT_QUART = ROOT / f"{PFX}_FeatureQuartiles.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

DEV_START, DEV_END = base.PARTS["development"]
HOUR = 23
BAR = pd.Timedelta(minutes=5)
HORIZONS = (15, 30, 60, 120)


def row_at(x: pd.DataFrame, ts: pd.Timestamp):
    try:
        r = x.loc[ts]
    except KeyError:
        return None
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    return r


def px_after(x: pd.DataFrame, decision_ts: pd.Timestamp, minutes: int):
    # decision_ts is when entry is known/executable. Return close observed exactly
    # `minutes` later: bar starting at decision_ts + minutes - 5m.
    ts = decision_ts + pd.Timedelta(minutes=minutes) - BAR
    r = row_at(x, ts)
    return np.nan if r is None else float(r.close)


def max_excursion(x: pd.DataFrame, decision_ts: pd.Timestamp, minutes: int, entry: float):
    z = x[(x.index >= decision_ts) & (x.index < decision_ts + pd.Timedelta(minutes=minutes))]
    if z.empty:
        return np.nan, np.nan
    mfe = (float(z.high.max()) / entry - 1.0) * 100.0
    mae = (float(z.low.min()) / entry - 1.0) * 100.0
    return mfe, mae


def pct_ret(exit_px: float, entry: float):
    if not np.isfinite(exit_px) or not np.isfinite(entry) or entry <= 0:
        return np.nan
    return (exit_px / entry - 1.0) * 100.0


def collect(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= DEV_START) & (x5.index < DEV_END)].copy()
    q = q[q.index.weekday < 5]
    qh = q[q.index.hour == HOUR].copy().reset_index()
    qh = qh.rename(columns={qh.columns[0]: "timestamp"})

    rows = []
    for day, g in qh.groupby(qh.timestamp.dt.date):
        d = detector.detect_session(g)
        if d is None or d.structure != "BREAK_RETEST_ACCEPT_LONG":
            continue

        bt = pd.Timestamp(d.breakout_time)
        rt = pd.Timestamp(d.retest_time)
        at = pd.Timestamp(d.acceptance_time)
        et = pd.Timestamp(d.entry_time)
        br = row_at(x5, bt); rr = row_at(x5, rt); ar = row_at(x5, at); er = row_at(x5, et)
        if any(v is None for v in (br, rr, ar, er)):
            continue

        oh, ol = float(d.orb_high), float(d.orb_low)
        rng = oh - ol
        if rng <= 0:
            continue

        # ORB starts at 23:00; completes at 23:15.
        orb_done = pd.Timestamp(f"{day} 23:15:00", tz="UTC")
        breakout_decision = bt + BAR
        retest_fill_clock = rt + BAR  # conservative clock for comparing later returns
        acceptance_decision = at + BAR
        entry_decision = et

        entries = {
            "E1_BREAKOUT_NEXT_OPEN": (breakout_decision, float(row_at(x5, breakout_decision).open) if row_at(x5, breakout_decision) is not None else np.nan),
            "E2_RETEST_LEVEL": (retest_fill_clock, oh),
            "E3_ACCEPTANCE_CLOSE": (acceptance_decision, float(ar.close)),
            "E4_ACCEPTANCE_NEXT_OPEN": (entry_decision, float(er.open)),
        }

        rec = {
            "date": str(day),
            "orb_high": oh,
            "orb_low": ol,
            "orb_range_pct": float(d.orb_range_pct),
            "breakout_time": bt,
            "retest_time": rt,
            "acceptance_time": at,
            "entry_time": et,
            "breakout_extension_r": (float(br.close) - oh) / rng,
            "breakout_body_r": abs(float(br.close) - float(br.open)) / rng,
            "bars_orb_to_break": (bt - orb_done) / BAR,
            "bars_break_to_retest": (rt - bt) / BAR,
            "retest_low_depth_r": (oh - float(rr.low)) / rng,
            "retest_close_r": (float(rr.close) - oh) / rng,
            "bars_retest_to_accept": (at - rt) / BAR,
            "accept_extension_r": (float(ar.close) - oh) / rng,
            "entry_extension_r": (float(er.open) - oh) / rng,
        }

        for name, (ts, ep) in entries.items():
            rec[f"{name}_time"] = ts
            rec[f"{name}_price"] = ep
            for h in HORIZONS:
                rec[f"{name}_ret_{h}m_pct"] = pct_ret(px_after(x5, ts, h), ep)
        mfe, mae = max_excursion(x5, entry_decision, 120, float(er.open))
        rec["E4_mfe_120m_pct"] = mfe
        rec["E4_mae_120m_pct"] = mae
        rows.append(rec)

    return pd.DataFrame(rows)


def summarize_entries(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in ("E1_BREAKOUT_NEXT_OPEN", "E2_RETEST_LEVEL", "E3_ACCEPTANCE_CLOSE", "E4_ACCEPTANCE_NEXT_OPEN"):
        r = {"entry": name, "n": len(ev)}
        for h in HORIZONS:
            s = pd.to_numeric(ev[f"{name}_ret_{h}m_pct"], errors="coerce").dropna()
            r[f"mean_{h}m_pct"] = s.mean()
            r[f"median_{h}m_pct"] = s.median()
            r[f"positive_{h}m"] = (s > 0).mean()
        rows.append(r)
    return pd.DataFrame(rows)


def feature_summary(ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = [
        "orb_range_pct", "breakout_extension_r", "breakout_body_r",
        "bars_orb_to_break", "bars_break_to_retest", "retest_low_depth_r",
        "retest_close_r", "bars_retest_to_accept", "accept_extension_r",
        "entry_extension_r",
    ]
    outcome = pd.to_numeric(ev["E4_ACCEPTANCE_NEXT_OPEN_ret_120m_pct"], errors="coerce")
    pos = outcome > 0
    rows = []
    qrows = []
    for f in features:
        s = pd.to_numeric(ev[f], errors="coerce")
        rows.append({
            "feature": f,
            "n": int(s.notna().sum()),
            "median_all": s.median(),
            "median_positive_120m": s[pos].median(),
            "median_nonpositive_120m": s[~pos].median(),
            "delta_pos_minus_nonpos": s[pos].median() - s[~pos].median(),
        })
        valid = s.notna() & outcome.notna()
        if valid.sum() >= 20 and s[valid].nunique() >= 4:
            try:
                bins = pd.qcut(s[valid], 4, labels=False, duplicates="drop")
                tmp = pd.DataFrame({"bin": bins, "ret60": ev.loc[valid, "E4_ACCEPTANCE_NEXT_OPEN_ret_60m_pct"], "ret120": outcome[valid]})
                for b, g in tmp.groupby("bin"):
                    qrows.append({
                        "feature": f, "quartile": int(b) + 1, "n": len(g),
                        "mean_60m_pct": pd.to_numeric(g.ret60, errors="coerce").mean(),
                        "median_60m_pct": pd.to_numeric(g.ret60, errors="coerce").median(),
                        "positive_60m": (pd.to_numeric(g.ret60, errors="coerce") > 0).mean(),
                        "mean_120m_pct": pd.to_numeric(g.ret120, errors="coerce").mean(),
                        "median_120m_pct": pd.to_numeric(g.ret120, errors="coerce").median(),
                        "positive_120m": (pd.to_numeric(g.ret120, errors="coerce") > 0).mean(),
                    })
            except ValueError:
                pass
    return pd.DataFrame(rows), pd.DataFrame(qrows)


def fmt(x, nd=3):
    return "-" if pd.isna(x) else f"{float(x):.{nd}f}"


def main():
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    ev = collect(x5)
    if len(ev) < 100:
        raise RuntimeError(f"unexpectedly small frozen signal population: {len(ev)}")
    ev.to_csv(OUT_EVENTS, index=False)

    ent = summarize_entries(ev); ent.to_csv(OUT_ENTRY, index=False)
    fs, fq = feature_summary(ev); fs.to_csv(OUT_FEATURE, index=False); fq.to_csv(OUT_QUART, index=False)

    lines = [
        "# SOL ORB Entry Structure Characterization v1 — Development",
        "",
        f"- Data coverage: {coverage:.6%}",
        f"- Frozen BREAK->RETEST->ACCEPT population: **{len(ev)}**",
        "- Partition: Development only, weekdays, H23 UTC; Reference/OOS closed.",
        "- No TP/SL optimization and no threshold promotion.",
        "",
        "## Same-structure entry-coordinate comparison",
        "",
        "| Entry | N | +15m | mean15 | +30m | mean30 | +60m | mean60 | +120m | mean120 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in ent.itertuples(index=False):
        lines.append(
            f"| {r.entry} | {r.n} | {r.positive_15m:.1%} | {r.mean_15m_pct:.3f}% | "
            f"{r.positive_30m:.1%} | {r.mean_30m_pct:.3f}% | {r.positive_60m:.1%} | {r.mean_60m_pct:.3f}% | "
            f"{r.positive_120m:.1%} | {r.mean_120m_pct:.3f}% |"
        )

    lines += [
        "",
        "## Structural feature medians by E4 120m outcome",
        "",
        "| Feature | Median all | Positive 120m | Non-positive 120m | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in fs.itertuples(index=False):
        lines.append(f"| {r.feature} | {fmt(r.median_all)} | {fmt(r.median_positive_120m)} | {fmt(r.median_nonpositive_120m)} | {fmt(r.delta_pos_minus_nonpos)} |")

    # Add compact best/worst quartile diagnostics per feature.
    lines += ["", "## Quartile continuation map (E4)", ""]
    if not fq.empty:
        for f in fq.feature.unique():
            z = fq[fq.feature == f].sort_values("quartile")
            vals = "; ".join(
                f"Q{int(r.quartile)} n={int(r.n)}: +60={r.positive_60m:.1%}, mean60={r.mean_60m_pct:.3f}%, +120={r.positive_120m:.1%}, mean120={r.mean_120m_pct:.3f}%"
                for r in z.itertuples(index=False)
            )
            lines.append(f"- **{f}** — {vals}")

    e4mfe = pd.to_numeric(ev["E4_mfe_120m_pct"], errors="coerce")
    e4mae = pd.to_numeric(ev["E4_mae_120m_pct"], errors="coerce")
    lines += [
        "",
        "## E4 path diagnostic",
        "",
        f"- Median 120m MFE: **{e4mfe.median():.3f}%**",
        f"- Median 120m MAE: **{e4mae.median():.3f}%**",
        "",
        "## Boundary",
        "",
        "This is a Development-only characterization. The result can nominate an entry character or execution coordinate, but cannot create a new live gate. Any threshold derived from these distributions requires a separately preregistered test.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("COMPLETE_DEVELOPMENT_ENTRY_STRUCTURE_CHARACTERIZATION\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
