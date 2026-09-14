#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_RUNNER = ROOT / "research" / "bnb_long_reset_v1_h00_primary.py"
PFX = "BNB_LONG_RESET_V1_H02_TRADE_CONSTRUCTION"

OUT_SIGNALS = ROOT / f"{PFX}_DevelopmentSignals.csv"
OUT_LEADER = ROOT / f"{PFX}_Leaderboard.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_YEARS = ROOT / f"{PFX}_SelectedYears.csv"
OUT_QUARTERS = ROOT / f"{PFX}_SelectedQuarters.csv"
OUT_ANCHORS = ROOT / f"{PFX}_SelectedAnchors.csv"
OUT_EXITS = ROOT / f"{PFX}_SelectedExits.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATE = ROOT / f"{PFX}_State.json"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

spec = importlib.util.spec_from_file_location("bnb_reset_h00_base", BASE_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"unable to load frozen base runner: {BASE_RUNNER}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

TARGET_LOCAL_HOUR = 2
HIGH_CUTOFF = 2.0 / 3.0
PRIMARY_PCT = "rv_ratio_60_240_pct"
SECONDARY_PCT = "efficiency_60m_pct"
REFERENCE_NOTIONAL = 500.0
ROUNDTRIP_COST = 0.0012
DEV_START_LOCAL = pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END_LOCAL_EXCL = pd.Timestamp("2025-01-01T00:00:00Z")
DEV_WEEKS = (DEV_END_LOCAL_EXCL - DEV_START_LOCAL).total_seconds() / 86400.0 / 7.0

TIME_HOLDS = (60, 120, 180, 240, 360)
TP_LEVELS = (0.006, 0.009, 0.012, 0.015)
SL_LEVELS = (0.006, 0.009, 0.012)
MAX_HOLDS = (240, 360)


def max_drawdown_additive(x: np.ndarray) -> float:
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return np.nan
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(np.max(dd)) if len(dd) else 0.0


def stats(x: np.ndarray) -> dict:
    a = np.asarray(x, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {
            "n": 0, "wr": np.nan, "mean": np.nan, "median": np.nan,
            "pf": np.nan, "loss_streak": 0, "max_dd": np.nan,
        }
    return {
        "n": int(len(a)),
        "wr": float(np.mean(a > 0)),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "pf": float(base.pf(a)),
        "loss_streak": int(base.max_loss_streak(a)),
        "max_dd": max_drawdown_additive(a),
    }


def build_h02_development(x: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for i, ts in enumerate(x.index):
        local = ts + pd.Timedelta(hours=7)
        if local.year not in base.DEV_YEARS:
            continue
        if local.hour != TARGET_LOCAL_HOUR or local.minute not in base.ANCHOR_MINUTES:
            continue
        row = base.feature_row(x, i, ts)
        if row is not None and all(np.isfinite(row[f"r{h}"]) for h in base.HORIZONS):
            rows.append(row)
    E = pd.DataFrame(rows).sort_values("entry_ts_utc").reset_index(drop=True)
    if len(E) < 4000:
        raise RuntimeError(f"unexpectedly low H02 development event count: {len(E)}")
    E = base.add_causal_percentiles(E)
    E["primary_high"] = E[PRIMARY_PCT] >= HIGH_CUTOFF
    E["secondary_high"] = E[SECONDARY_PCT] >= HIGH_CUTOFF
    return E


def candidates() -> list[dict]:
    out: list[dict] = []
    for hold in TIME_HOLDS:
        out.append({
            "name": f"TIME_{hold:03d}m",
            "kind": "TIME",
            "hold": hold,
            "tp": None,
            "sl": None,
            "complexity": 0,
        })
    for tp in TP_LEVELS:
        for sl in SL_LEVELS:
            for hold in MAX_HOLDS:
                out.append({
                    "name": f"TPSL_TP{int(round(tp*10000)):03d}_SL{int(round(sl*10000)):03d}_H{hold:03d}",
                    "kind": "TPSL",
                    "hold": hold,
                    "tp": tp,
                    "sl": sl,
                    "complexity": 1,
                })
    if len(out) != 29:
        raise RuntimeError(f"candidate count changed: {len(out)}")
    return out


def price_at_open(x: pd.DataFrame, ts: pd.Timestamp) -> float:
    if ts not in x.index:
        raise RuntimeError(f"missing exact 5m exit bar: {ts}")
    return float(x.loc[ts, "open"])


def resolve_trade(x: pd.DataFrame, s: pd.Series, c: dict) -> dict:
    entry_ts = pd.Timestamp(s.entry_ts_utc)
    entry = float(s.entry_price)
    deadline = entry_ts + pd.Timedelta(minutes=int(c["hold"]))

    if c["kind"] == "TIME":
        exit_px = price_at_open(x, deadline)
        return {
            "exit_ts_utc": deadline,
            "occupied_until_utc": deadline,
            "exit_price": exit_px,
            "exit_reason": f"TIME_{c['hold']}m",
            "gross_return": exit_px / entry - 1.0,
        }

    tp_px = entry * (1.0 + float(c["tp"]))
    sl_px = entry * (1.0 - float(c["sl"]))
    bars = x[(x.index >= entry_ts) & (x.index < deadline)]
    expected_bars = int(c["hold"]) // 5
    if len(bars) != expected_bars:
        raise RuntimeError(
            f"incomplete intratrade 5m path for {entry_ts}: got {len(bars)}, expected {expected_bars}"
        )

    for ts, b in bars.iterrows():
        hit_sl = float(b.low) <= sl_px
        hit_tp = float(b.high) >= tp_px
        if hit_sl:
            # Frozen conservative same-bar convention: if both touch, SL wins.
            return {
                "exit_ts_utc": ts,
                "occupied_until_utc": ts + pd.Timedelta(minutes=5),
                "exit_price": sl_px,
                "exit_reason": "SL" if not hit_tp else "SL_SAME_BAR_ADVERSE_FIRST",
                "gross_return": -float(c["sl"]),
            }
        if hit_tp:
            return {
                "exit_ts_utc": ts,
                "occupied_until_utc": ts + pd.Timedelta(minutes=5),
                "exit_price": tp_px,
                "exit_reason": "TP",
                "gross_return": float(c["tp"]),
            }

    exit_px = price_at_open(x, deadline)
    return {
        "exit_ts_utc": deadline,
        "occupied_until_utc": deadline,
        "exit_price": exit_px,
        "exit_reason": f"TIME_STOP_{c['hold']}m",
        "gross_return": exit_px / entry - 1.0,
    }


def simulate(x: pd.DataFrame, sig: pd.DataFrame, c: dict) -> tuple[pd.DataFrame, int]:
    trades: list[dict] = []
    occupied_until: pd.Timestamp | None = None
    skipped = 0

    for _, s in sig.iterrows():
        ts = pd.Timestamp(s.entry_ts_utc)
        if occupied_until is not None and ts < occupied_until:
            skipped += 1
            continue

        r = resolve_trade(x, s, c)
        gross = float(r["gross_return"])
        net = gross - ROUNDTRIP_COST
        local = pd.Timestamp(s.local_wib)
        trade = {
            "rule": c["name"],
            "entry_ts_utc": ts,
            "entry_wib": local,
            "year": int(local.year),
            "quarter": pd.Timestamp(local).tz_localize(None).to_period("Q").strftime("%YQ%q"),
            "anchor_minute": int(s.anchor_minute),
            "entry_price": float(s.entry_price),
            "exit_ts_utc": r["exit_ts_utc"],
            "exit_price": float(r["exit_price"]),
            "exit_reason": r["exit_reason"],
            "gross_return": gross,
            "net_return": net,
            "gross_pnl_500": REFERENCE_NOTIONAL * gross,
            "net_pnl_500": REFERENCE_NOTIONAL * net,
        }
        trades.append(trade)
        occupied_until = pd.Timestamp(r["occupied_until_utc"])

    T = pd.DataFrame(trades)
    return T, skipped


def candidate_row(T: pd.DataFrame, skipped: int, c: dict, structural_n: int) -> dict:
    gross = stats(T.gross_return.to_numpy(float))
    net = stats(T.net_return.to_numpy(float))
    row = {
        "rule": c["name"],
        "kind": c["kind"],
        "hold_minutes": int(c["hold"]),
        "tp": c["tp"],
        "sl": c["sl"],
        "complexity": int(c["complexity"]),
        "structural_signals": int(structural_n),
        "executed_trades": int(net["n"]),
        "skipped_overlap": int(skipped),
        "trades_per_week": float(net["n"] / DEV_WEEKS),
        "gross_wr": gross["wr"],
        "gross_mean": gross["mean"],
        "gross_pf": gross["pf"],
        "net_wr": net["wr"],
        "net_mean": net["mean"],
        "net_pf": net["pf"],
        "net_median": net["median"],
        "net_loss_streak": int(net["loss_streak"]),
        "net_max_dd_return": net["max_dd"],
        "net_max_dd_500": REFERENCE_NOTIONAL * net["max_dd"] if np.isfinite(net["max_dd"]) else np.nan,
        "net_total_500": REFERENCE_NOTIONAL * float(T.net_return.sum()),
    }

    pooled_checks = [
        net["n"] >= 180,
        row["trades_per_week"] >= 1.0,
        net["mean"] > 0,
        net["pf"] >= 1.15,
        net["loss_streak"] <= 12,
    ]

    year_gate = True
    min_year_mean = np.inf
    min_year_pf = np.inf
    for y in base.DEV_YEARS:
        q = T[T.year == y]
        ys = stats(q.net_return.to_numpy(float))
        ok = bool(ys["n"] >= 50 and ys["mean"] > 0 and ys["pf"] >= 1.02)
        year_gate &= ok
        min_year_mean = min(min_year_mean, ys["mean"] if np.isfinite(ys["mean"]) else -np.inf)
        min_year_pf = min(min_year_pf, ys["pf"] if np.isfinite(ys["pf"]) else -np.inf)
        row.update({
            f"y{y}_n": ys["n"],
            f"y{y}_wr": ys["wr"],
            f"y{y}_mean": ys["mean"],
            f"y{y}_pf": ys["pf"],
            f"y{y}_pass": ok,
        })

    positive_quarters = 0
    per_year_positive: dict[int, int] = {}
    quarter_means: dict[str, float] = {}
    for y in base.DEV_YEARS:
        per_year_positive[y] = 0
        for qn in range(1, 5):
            label = f"{y}Q{qn}"
            q = T[T.quarter == label]
            qm = float(q.net_return.mean()) if len(q) else np.nan
            quarter_means[label] = qm
            if np.isfinite(qm) and qm > 0:
                positive_quarters += 1
                per_year_positive[y] += 1

    quarter_gate = bool(
        positive_quarters >= 8
        and all(per_year_positive[y] >= 2 for y in base.DEV_YEARS)
    )
    pooled_gate = bool(all(pooled_checks))
    full_gate = bool(pooled_gate and year_gate and quarter_gate)

    row.update({
        "pooled_gate": pooled_gate,
        "year_gate": bool(year_gate),
        "positive_quarters": int(positive_quarters),
        "y2022_positive_quarters": int(per_year_positive[2022]),
        "y2023_positive_quarters": int(per_year_positive[2023]),
        "y2024_positive_quarters": int(per_year_positive[2024]),
        "quarter_gate": quarter_gate,
        "full_gate": full_gate,
        "min_year_net_mean": float(min_year_mean),
        "min_year_net_pf": float(min_year_pf),
        "gate_score": int(sum(bool(x) for x in pooled_checks))
            + int(sum(bool(row[f"y{y}_pass"]) for y in base.DEV_YEARS))
            + int(positive_quarters >= 8)
            + int(all(per_year_positive[y] >= 2 for y in base.DEV_YEARS)),
    })
    for label, qm in quarter_means.items():
        row[f"{label}_mean"] = qm
    return row


def select_passer(L: pd.DataFrame) -> pd.Series | None:
    P = L[L.full_gate.astype(bool)].copy()
    if not len(P):
        return None
    P = P.sort_values(
        by=[
            "min_year_net_mean", "min_year_net_pf", "positive_quarters",
            "net_pf", "net_mean", "net_max_dd_return", "complexity", "rule",
        ],
        ascending=[False, False, False, False, False, True, True, True],
        kind="mergesort",
    )
    return P.iloc[0]


def fmt_pct(v: float) -> str:
    return "nan" if not np.isfinite(v) else f"{100.0*float(v):.3f}%"


def fmt_num(v: float, d: int = 3) -> str:
    if not np.isfinite(v):
        return "inf" if v == np.inf else "nan"
    return f"{float(v):.{d}f}"


def breakdown(T: pd.DataFrame):
    years = []
    for y in base.DEV_YEARS:
        q = T[T.year == y]
        s = stats(q.net_return.to_numpy(float))
        years.append({"year": y, **s, "net_total_500": REFERENCE_NOTIONAL * float(q.net_return.sum())})

    quarters = []
    for y in base.DEV_YEARS:
        for qn in range(1, 5):
            label = f"{y}Q{qn}"
            q = T[T.quarter == label]
            s = stats(q.net_return.to_numpy(float))
            quarters.append({"quarter": label, **s, "net_total_500": REFERENCE_NOTIONAL * float(q.net_return.sum()), "positive": bool(s["n"] and s["mean"] > 0)})

    anchors = []
    for a in base.ANCHOR_MINUTES:
        q = T[T.anchor_minute == a]
        s = stats(q.net_return.to_numpy(float))
        anchors.append({"anchor_wib": f"02:{a:02d}", **s, "net_total_500": REFERENCE_NOTIONAL * float(q.net_return.sum())})

    exits = []
    for reason, q in T.groupby("exit_reason", sort=True):
        s = stats(q.net_return.to_numpy(float))
        exits.append({"exit_reason": reason, **s, "net_total_500": REFERENCE_NOTIONAL * float(q.net_return.sum())})

    return pd.DataFrame(years), pd.DataFrame(quarters), pd.DataFrame(anchors), pd.DataFrame(exits)


def main() -> None:
    x, coverage = base.load5()
    E = build_h02_development(x)
    sig = E[E.primary_high & E.secondary_high].copy().sort_values("entry_ts_utc")
    sig.to_csv(OUT_SIGNALS, index=False)
    if len(sig) < 400:
        raise RuntimeError(f"unexpectedly low frozen-character Development signals: {len(sig)}")

    rows: list[dict] = []
    trade_cache: dict[str, pd.DataFrame] = {}
    skipped_cache: dict[str, int] = {}
    for c in candidates():
        T, skipped = simulate(x, sig, c)
        rows.append(candidate_row(T, skipped, c, len(sig)))
        trade_cache[c["name"]] = T
        skipped_cache[c["name"]] = skipped

    L = pd.DataFrame(rows)
    # Display order is deterministic and keeps full-gate passers first.
    L = L.sort_values(
        by=["full_gate", "gate_score", "min_year_net_mean", "net_pf", "net_mean", "rule"],
        ascending=[False, False, False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    L.to_csv(OUT_LEADER, index=False)

    selected = select_passer(L)
    status = "CONSTRUCTION_PASS" if selected is not None else "CONSTRUCTION_FAIL"
    OUT_STATUS.write_text(status + "\n")

    selected_rule = None
    selected_payload = None
    if selected is not None:
        selected_rule = str(selected.rule)
        T = trade_cache[selected_rule].copy()
        T.to_csv(OUT_TRADES, index=False)
        Y, Q, A, X = breakdown(T)
        Y.to_csv(OUT_YEARS, index=False)
        Q.to_csv(OUT_QUARTERS, index=False)
        A.to_csv(OUT_ANCHORS, index=False)
        X.to_csv(OUT_EXITS, index=False)
        selected_payload = {k: (bool(v) if isinstance(v, (np.bool_, bool)) else int(v) if isinstance(v, (np.integer,)) else float(v) if isinstance(v, (np.floating,)) else v) for k, v in selected.to_dict().items()}
    else:
        # Keep schemas available even on failure.
        pd.DataFrame().to_csv(OUT_TRADES, index=False)
        pd.DataFrame().to_csv(OUT_YEARS, index=False)
        pd.DataFrame().to_csv(OUT_QUARTERS, index=False)
        pd.DataFrame().to_csv(OUT_ANCHORS, index=False)
        pd.DataFrame().to_csv(OUT_EXITS, index=False)

    state = {
        "status": status,
        "symbol": "BNBUSDT",
        "side": "LONG",
        "habitat_wib": "02:00-03:00",
        "primary": "rv_ratio_60_240__HIGH",
        "secondary": "efficiency_60m__HIGH",
        "development_period": "2022-01-01 through 2024-12-31 WIB",
        "construction_selection_uses_oos": False,
        "data_coverage": float(coverage),
        "h02_development_events": int(len(E)),
        "frozen_structural_signals": int(len(sig)),
        "candidate_count": int(len(L)),
        "full_gate_passers": int(L.full_gate.astype(bool).sum()),
        "roundtrip_cost": ROUNDTRIP_COST,
        "reference_notional": REFERENCE_NOTIONAL,
        "overlap_rule": "ONE_POSITION_NO_STACKING",
        "selected_rule": selected_rule,
        "selected": selected_payload,
        "next_action": "FREEZE_SELECTED_AND_PREREG_EXECUTABLE_OOS" if status == "CONSTRUCTION_PASS" else "STOP_NO_RETUNE",
    }
    OUT_STATE.write_text(json.dumps(state, indent=2, allow_nan=True) + "\n")

    lines = [
        "# BNB LONG Reset V1 — H02 Trade Construction Development Result",
        "",
        f"**Verdict: {status}**",
        "",
        "Frozen structural character: `rv_ratio_60_240__HIGH` + `efficiency_60m__HIGH`",
        "Habitat: 02:00–03:00 WIB, LONG, all four anchors retained.",
        "Construction selection period: 2022–2024 Development only.",
        "OOS is not used by this runner for candidate selection or ranking.",
        "",
        f"Data coverage: **{coverage:.4%}**",
        f"H02 Development events: **{len(E):,}**",
        f"Frozen-character structural signals: **{len(sig):,}**",
        f"Frozen construction candidates: **{len(L)}**",
        f"Full-gate passers: **{int(L.full_gate.astype(bool).sum())}**",
        "",
        "Execution assumptions: ONE_POSITION/no stacking; 5m anchor-open entry; adverse-first same-bar TP/SL; 0.12% modeled round-trip cost; $500 fixed reference notional.",
        "",
        "## Leaderboard",
        "",
        "| Rank | Rule | Trades | Skip | /wk | Net WR | Net mean | Net PF | Net total $500 | Max DD $500 | LS | +Q | Gate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in L.head(15).iterrows():
        lines.append(
            f"| {i+1} | {r.rule} | {int(r.executed_trades)} | {int(r.skipped_overlap)} | {r.trades_per_week:.2f} | "
            f"{fmt_pct(r.net_wr)} | {fmt_pct(r.net_mean)} | {fmt_num(r.net_pf)} | ${r.net_total_500:+,.2f} | "
            f"-${r.net_max_dd_500:,.2f} | {int(r.net_loss_streak)} | {int(r.positive_quarters)}/12 | {'PASS' if bool(r.full_gate) else 'FAIL'} |"
        )

    if selected is not None:
        T = trade_cache[selected_rule]
        Y, Q, A, X = breakdown(T)
        lines += [
            "",
            "## Selected construction",
            "",
            f"**{selected_rule}**",
            "",
            f"Executed trades: **{int(selected.executed_trades)}** from **{len(sig)}** structural signals; skipped overlap **{int(selected.skipped_overlap)}**.",
            f"Frequency: **{selected.trades_per_week:.2f}/week**.",
            f"Gross: WR **{fmt_pct(selected.gross_wr)}**, mean **{fmt_pct(selected.gross_mean)}**, PF **{fmt_num(selected.gross_pf)}**.",
            f"Net after 0.12% RT cost: WR **{fmt_pct(selected.net_wr)}**, mean **{fmt_pct(selected.net_mean)}**, PF **{fmt_num(selected.net_pf)}**.",
            f"Net equivalent @ $500: **${selected.net_total_500:+,.2f}**, max DD **-${selected.net_max_dd_500:,.2f}**, max loss streak **{int(selected.net_loss_streak)}**.",
            "",
            "### Calendar years",
            "",
            "| Year | N | Net WR | Net mean | Net PF | Net total $500 |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        for _, r in Y.iterrows():
            lines.append(f"| {int(r.year)} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_pct(r['mean'])} | {fmt_num(r.pf)} | ${r.net_total_500:+,.2f} |")
        lines += [
            "",
            "### Quarter consistency",
            "",
            "| Quarter | N | Net WR | Net mean | Net PF | Net total $500 | Positive |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for _, r in Q.iterrows():
            lines.append(f"| {r.quarter} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_pct(r['mean'])} | {fmt_num(r.pf)} | ${r.net_total_500:+,.2f} | {'YES' if bool(r.positive) else 'NO'} |")
        lines += [
            "",
            "### Executed anchor distribution",
            "",
            "| Anchor | N | Net WR | Net mean | Net PF | Net total $500 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for _, r in A.iterrows():
            lines.append(f"| {r.anchor_wib} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_pct(r['mean'])} | {fmt_num(r.pf)} | ${r.net_total_500:+,.2f} |")
        lines += [
            "",
            "### Exit reasons",
            "",
            "| Exit reason | N | Net WR | Net mean | Net PF | Net total $500 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for _, r in X.iterrows():
            lines.append(f"| {r.exit_reason} | {int(r.n)} | {fmt_pct(r.wr)} | {fmt_pct(r['mean'])} | {fmt_num(r.pf)} | ${r.net_total_500:+,.2f} |")
        lines += [
            "",
            "**Next action:** freeze this exact selected construction and preregister executable OOS validation. No parameter may change from OOS feedback.",
        ]
    else:
        lines += [
            "",
            "No frozen candidate satisfied all pooled, yearly, and quarter gates after modeled trading friction.",
            "",
            "**Next action: STOP_NO_RETUNE.** Do not loosen gates or use known OOS to rescue construction.",
        ]

    lines += ["", "Research/shadow only."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")

    print(json.dumps({
        "status": status,
        "events": len(E),
        "signals": len(sig),
        "candidates": len(L),
        "passers": int(L.full_gate.astype(bool).sum()),
        "selected": selected_rule,
    }, indent=2))


if __name__ == "__main__":
    main()
