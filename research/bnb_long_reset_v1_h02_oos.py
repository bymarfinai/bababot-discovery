#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "research" / "bnb_long_reset_v1_h00_primary.py"
PFX = "BNB_LONG_RESET_V1_H02_OOS"

OUT_EVENTS = ROOT / f"{PFX}_Events.csv"
OUT_SIGNALS = ROOT / f"{PFX}_Signals.csv"
OUT_BLOCKS = ROOT / f"{PFX}_Blocks.csv"
OUT_HORIZONS = ROOT / f"{PFX}_Horizons.csv"
OUT_ANCHORS = ROOT / f"{PFX}_Anchors.csv"
OUT_QUARTERS = ROOT / f"{PFX}_Quarters.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATE = ROOT / f"{PFX}_State.json"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

spec = importlib.util.spec_from_file_location("bnb_reset_h00_base", BASE_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load frozen base runner: {BASE_RUNNER}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

# Frozen OOS protocol. Development history remains available only so causal
# rolling percentiles at the first OOS observations have the same information
# a live process would have had. Evaluation itself is OOS only.
TARGET_LOCAL_HOUR = 2
OOS_START_LOCAL = pd.Timestamp("2025-01-01T00:00:00Z")
OOS_END_LOCAL_EXCL = pd.Timestamp("2026-07-31T00:00:00Z")
HIGH_CUTOFF = 2.0 / 3.0
PRIMARY_PCT = "rv_ratio_60_240_pct"
SECONDARY_PCT = "efficiency_60m_pct"
REFERENCE_NOTIONAL = 500.0

# Need 5m data through the end of July 2026. H02 +240m exits for Jul-30
# remain inside Jul-30 local, so this end is sufficient.
base.DATA_END = pd.Timestamp("2026-07-31T00:00:00Z")


def build_h02_history(x: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for i, ts in enumerate(x.index):
        local = ts + pd.Timedelta(hours=7)
        if local.year < 2022 or local.year > 2026:
            continue
        if local.hour != TARGET_LOCAL_HOUR or local.minute not in base.ANCHOR_MINUTES:
            continue
        row = base.feature_row(x, i, ts)
        if row is not None and all(np.isfinite(row[f"r{h}"]) for h in base.HORIZONS):
            rows.append(row)
    E = pd.DataFrame(rows).sort_values("entry_ts_utc").reset_index(drop=True)
    if len(E) < 6000:
        raise RuntimeError(f"unexpectedly low H02 history count: {len(E)}")
    E["consensus_return"] = E[[f"r{h}" for h in base.HORIZONS]].mean(axis=1)
    E["consensus_win"] = E.consensus_return > 0
    return E


def max_drawdown_additive(x: np.ndarray) -> float:
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return np.nan
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(np.max(dd)) if len(dd) else 0.0


def expanded_stats(x: np.ndarray) -> dict:
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {
            "n": 0, "wr": np.nan, "mean": np.nan, "median": np.nan,
            "pf": np.nan, "gross_pos": np.nan, "gross_neg": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "max_dd": np.nan,
            "loss_streak": 0,
        }
    pos = a[a > 0]
    neg = a[a < 0]
    gross_pos = float(pos.sum())
    gross_neg = float(neg.sum())
    return {
        "n": int(len(a)),
        "wr": float(np.mean(a > 0)),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "pf": float(base.pf(a)),
        "gross_pos": gross_pos,
        "gross_neg": gross_neg,
        "avg_win": float(np.mean(pos)) if len(pos) else np.nan,
        "avg_loss": float(np.mean(neg)) if len(neg) else np.nan,
        "max_dd": max_drawdown_additive(a),
        "loss_streak": int(base.max_loss_streak(a)),
    }


def metric_row(label: str, q: pd.DataFrame, col: str = "consensus_return") -> dict:
    s = expanded_stats(q[col].to_numpy(float))
    return {"label": label, **s}


def pct(v: float) -> str:
    return "nan" if not np.isfinite(v) else f"{100.0 * float(v):.2f}%"


def num(v: float, d: int = 3) -> str:
    return "nan" if not np.isfinite(v) else f"{float(v):.{d}f}"


def money_from_return(v: float) -> str:
    if not np.isfinite(v):
        return "nan"
    return f"${REFERENCE_NOTIONAL * float(v):+,.2f}"


def stats_markdown(s: dict) -> list[str]:
    total = REFERENCE_NOTIONAL * s["mean"] * s["n"] if s["n"] else np.nan
    return [
        f"- N: **{s['n']:,}**",
        f"- WR: **{pct(s['wr'])}**",
        f"- Mean: **{pct(s['mean'])}**",
        f"- Median: **{pct(s['median'])}**",
        f"- PF: **{num(s['pf'])}**",
        f"- Raw $/signal @ $500: **{money_from_return(s['mean'])}**",
        f"- Raw cumulative equivalent: **${total:+,.2f}**" if np.isfinite(total) else "- Raw cumulative equivalent: nan",
        f"- Avg win @ $500: **{money_from_return(s['avg_win'])}**",
        f"- Avg loss @ $500: **{money_from_return(s['avg_loss'])}**",
        f"- Raw max DD @ $500: **${-REFERENCE_NOTIONAL * s['max_dd']:,.2f}**",
        f"- Max loss streak: **{s['loss_streak']}**",
    ]


def main() -> None:
    x, coverage = base.load5()
    E = build_h02_history(x)
    E = base.add_causal_percentiles(E)

    oos = E[(E.local_wib >= OOS_START_LOCAL) & (E.local_wib < OOS_END_LOCAL_EXCL)].copy()
    if len(oos) < 1500:
        raise RuntimeError(f"unexpectedly low OOS H02 event count: {len(oos)}")

    oos["primary_high"] = oos[PRIMARY_PCT] >= HIGH_CUTOFF
    oos["secondary_high"] = oos[SECONDARY_PCT] >= HIGH_CUTOFF
    sig = oos[oos.primary_high & oos.secondary_high].copy().sort_values("entry_ts_utc")

    oos.to_csv(OUT_EVENTS, index=False)
    sig.to_csv(OUT_SIGNALS, index=False)

    pooled = expanded_stats(sig.consensus_return.to_numpy(float))
    pooled_gate = bool(
        pooled["n"] >= 120
        and pooled["wr"] > 0.55
        and pooled["mean"] > 0
        and pooled["pf"] >= 1.20
    )

    # Calendar blocks.
    block_rows = []
    block_defs = [
        ("2025", pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2026-01-01T00:00:00Z")),
        ("2026_to_Jul30", pd.Timestamp("2026-01-01T00:00:00Z"), OOS_END_LOCAL_EXCL),
    ]
    for label, a, b in block_defs:
        q = sig[(sig.local_wib >= a) & (sig.local_wib < b)]
        r = metric_row(label, q)
        r["supportive"] = bool(r["n"] >= 40 and r["wr"] >= 0.52 and r["mean"] > 0 and r["pf"] >= 1.05)
        block_rows.append(r)
    blocks = pd.DataFrame(block_rows)
    blocks.to_csv(OUT_BLOCKS, index=False)
    block_gate = bool(blocks.supportive.all())

    # Diagnostic horizons.
    horizon_rows = []
    for h in base.HORIZONS:
        r = metric_row(f"{h}m", sig, f"r{h}")
        r["supportive"] = bool(r["n"] >= 120 and r["wr"] >= 0.53 and r["mean"] > 0 and r["pf"] >= 1.10)
        horizon_rows.append(r)
    horizons = pd.DataFrame(horizon_rows)
    horizons.to_csv(OUT_HORIZONS, index=False)
    horizon_gate = bool(int(horizons.supportive.sum()) >= 2)

    # Quarter-hour anchors.
    anchor_rows = []
    for a in base.ANCHOR_MINUTES:
        q = sig[sig.anchor_minute == a]
        r = metric_row(f"02:{a:02d}", q)
        r["supportive"] = bool(r["n"] >= 20 and r["wr"] >= 0.52 and r["mean"] > 0 and r["pf"] >= 1.05)
        anchor_rows.append(r)
    anchors = pd.DataFrame(anchor_rows)
    anchors.to_csv(OUT_ANCHORS, index=False)
    anchor_gate = bool(int(anchors.supportive.sum()) >= 3)

    # Calendar quarters, diagnostic guardrail only.
    tmp = sig.copy()
    # local_wib is stored as shifted UTC wall-time; strip tz for Period conversion.
    local_naive = pd.to_datetime(tmp.local_wib).dt.tz_localize(None)
    tmp["quarter"] = local_naive.dt.to_period("Q").astype(str)
    q_rows = []
    for qtr in sorted(tmp.quarter.unique()):
        r = metric_row(qtr, tmp[tmp.quarter == qtr])
        r["positive_mean"] = bool(r["mean"] > 0)
        q_rows.append(r)
    quarters = pd.DataFrame(q_rows)
    quarters.to_csv(OUT_QUARTERS, index=False)
    positive_quarters = int(quarters.positive_mean.sum()) if len(quarters) else 0
    quarter_warning = bool(positive_quarters < 4)

    mandatory_pass = bool(pooled_gate and block_gate and horizon_gate and anchor_gate)
    status = "OOS_PASS" if mandatory_pass else "OOS_FAIL"
    OUT_STATUS.write_text(status + "\n")

    span_days = (OOS_END_LOCAL_EXCL - OOS_START_LOCAL).total_seconds() / 86400.0
    signals_per_week = pooled["n"] / (span_days / 7.0)
    unique_days = int(pd.to_datetime(sig.local_wib).dt.date.nunique()) if len(sig) else 0

    state = {
        "status": status,
        "symbol": "BNBUSDT",
        "side": "LONG",
        "habitat_wib": "02:00-03:00",
        "primary": "rv_ratio_60_240__HIGH",
        "secondary": "efficiency_60m__HIGH",
        "oos_period_wib": "2025-01-01 through 2026-07-30",
        "coverage": float(coverage),
        "oos_h02_events": int(len(oos)),
        "selected_signals": int(len(sig)),
        "unique_signal_days": unique_days,
        "signals_per_week": float(signals_per_week),
        "gates": {
            "pooled": pooled_gate,
            "calendar_blocks": block_gate,
            "horizons": horizon_gate,
            "anchors": anchor_gate,
            "positive_quarters": positive_quarters,
            "quarter_warning": quarter_warning,
        },
        "pooled": pooled,
        "next_action": "TRADE_CONSTRUCTION" if status == "OOS_PASS" else "REJECT_H02_NO_RETUNE",
    }
    OUT_STATE.write_text(json.dumps(state, indent=2) + "\n")

    lines = [
        "# BNB LONG Reset V1 — H02 Untouched OOS Result",
        "",
        f"**Verdict: {status}**",
        "",
        "Frozen character: `rv_ratio_60_240__HIGH` + `efficiency_60m__HIGH`",
        "Habitat: 02:00–03:00 WIB",
        "OOS: 2025-01-01 through 2026-07-30 WIB",
        "No retuning was performed after OOS exposure.",
        "",
        f"Data coverage (support history + OOS): **{coverage:.4%}**",
        f"All H02 OOS events: **{len(oos):,}**",
        f"Selected frozen-character signals: **{len(sig):,}**",
        f"Unique signal days: **{unique_days:,}**",
        f"Approx signals/week over full OOS span: **{signals_per_week:.2f}**",
        "",
        "## Pooled OOS economics",
        "",
        *stats_markdown(pooled),
        "",
        f"Pooled gate: **{'PASS' if pooled_gate else 'FAIL'}**",
        "",
        "## Calendar blocks",
        "",
        "| Block | N | WR | Mean | PF | Raw $/signal | Raw total | DD @ $500 | LS | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in blocks.iterrows():
        lines.append(
            f"| {r.label} | {int(r.n)} | {pct(r.wr)} | {pct(r['mean'])} | {num(r.pf)} | "
            f"{money_from_return(r['mean'])} | ${REFERENCE_NOTIONAL*r['mean']*r.n:+,.2f} | "
            f"${-REFERENCE_NOTIONAL*r.max_dd:,.2f} | {int(r.loss_streak)} | {'PASS' if r.supportive else 'FAIL'} |"
        )
    lines += ["", f"Calendar-block gate: **{'PASS' if block_gate else 'FAIL'}**", "", "## Diagnostic horizons", "",
              "| Horizon | N | WR | Mean | PF | Raw $/signal | Raw total | DD @ $500 | Gate |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in horizons.iterrows():
        lines.append(
            f"| {r.label} | {int(r.n)} | {pct(r.wr)} | {pct(r['mean'])} | {num(r.pf)} | "
            f"{money_from_return(r['mean'])} | ${REFERENCE_NOTIONAL*r['mean']*r.n:+,.2f} | "
            f"${-REFERENCE_NOTIONAL*r.max_dd:,.2f} | {'PASS' if r.supportive else 'FAIL'} |"
        )
    lines += ["", f"Horizon gate: **{'PASS' if horizon_gate else 'FAIL'}** ({int(horizons.supportive.sum())}/3 supportive)",
              "", "## Quarter-hour anchors", "",
              "| Anchor WIB | N | WR | Mean | PF | Raw $/signal | Raw total | DD @ $500 | LS | Gate |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in anchors.iterrows():
        lines.append(
            f"| {r.label} | {int(r.n)} | {pct(r.wr)} | {pct(r['mean'])} | {num(r.pf)} | "
            f"{money_from_return(r['mean'])} | ${REFERENCE_NOTIONAL*r['mean']*r.n:+,.2f} | "
            f"${-REFERENCE_NOTIONAL*r.max_dd:,.2f} | {int(r.loss_streak)} | {'PASS' if r.supportive else 'FAIL'} |"
        )
    lines += ["", f"Anchor gate: **{'PASS' if anchor_gate else 'FAIL'}** ({int(anchors.supportive.sum())}/4 supportive)",
              "", "## OOS calendar quarters (diagnostic)", "",
              "| Quarter | N | WR | Mean | PF | Raw $/signal | Raw total | Positive mean |",
              "|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in quarters.iterrows():
        lines.append(
            f"| {r.label} | {int(r.n)} | {pct(r.wr)} | {pct(r['mean'])} | {num(r.pf)} | "
            f"{money_from_return(r['mean'])} | ${REFERENCE_NOTIONAL*r['mean']*r.n:+,.2f} | {'YES' if r.positive_mean else 'NO'} |"
        )
    lines += [
        "",
        f"Positive-mean quarters: **{positive_quarters}/{len(quarters)}**",
        f"Quarter diagnostic: **{'WARNING' if quarter_warning else 'CLEAN'}**",
        "",
        "## Locked interpretation",
        "",
        "OOS validation evaluates the frozen character exactly as promoted from Development. It does not choose a final holding period and does not apply TP/SL, fees, slippage, leverage mechanics, or overlap execution rules.",
        "",
        "If OOS_PASS, next stage is trade construction. If OOS_FAIL, this H02 character is rejected without OOS retuning/rescue.",
        "",
        "Research/shadow only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(status)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
