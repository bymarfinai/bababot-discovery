#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A53_PATH = Path(__file__).resolve().parent / "sol_long_15utc_executable_guard_a53.py"
spec = importlib.util.spec_from_file_location("a53", A53_PATH)
a53 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a53)
a2 = a53.a2

OUT_TRADES = ROOT / "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_TRADES.csv"
OUT_METRICS = ROOT / "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_METRICS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_BLOCKS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_Status.txt"

PARTS = ("development", "external", "reference_validation")
EXPECTED_N = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_WIN = {"development": 244, "external": 115, "reference_validation": 150}
VARIANT = "A59_H05_HALF_RESTORE_H10"
NOTIONAL = 500.0
CUT_FRAC = 0.50
RESTORE_NOTIONAL = NOTIONAL * CUT_FRAC
STRESS = 0.0005
BAR = pd.Timedelta(minutes=5)
HORIZON = pd.Timedelta(minutes=720)
TARGET_R = 0.40
EPS = 1e-12


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"

def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum()); gl = float(-x[x <= 0].sum())
    if gl == 0: return np.inf if gp > 0 else np.nan
    return gp / gl

def max_dd(vals):
    x = pd.to_numeric(vals, errors="coerce").fillna(0.0).to_numpy(float)
    eq = np.concatenate([[0.0], np.cumsum(x)])
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq))

def max_loss_streak(vals):
    best = 0; cur = 0
    for v in pd.to_numeric(vals, errors="coerce").fillna(0.0):
        if float(v) <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return best

def positive_week_rate(q, col):
    if q.empty: return np.nan
    z = q.copy()
    ts = pd.to_datetime(z.entry_ts, utc=True).dt.tz_convert(None)
    z["week"] = ts.dt.to_period("W-SUN")
    w = pd.to_numeric(z[col], errors="coerce").groupby(z["week"]).sum()
    return float((w > 0).mean()) if len(w) else np.nan

def bar_pos(idx, ts):
    i = int(idx.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(idx) or idx[i] != pd.Timestamp(ts):
        raise RuntimeError(f"timestamp parity failure {ts}")
    return i


def live_h05(confirmed, close_i, H, R):
    return bool(confirmed and close_i > H + EPS and close_i <= H + 0.05 * R + EPS)

def live_restore_h10(close_i, H, R):
    return bool(close_i > H + 0.10 * R + EPS)


def hybrid_simulate(m, r):
    idx, op, hi, cl = m["idx"], m["open"], m["high"], m["close"]
    ei = bar_pos(idx, r.entry_ts)
    end_ts = pd.Timestamp(r.execution_start) + HORIZON
    endpos = int(idx.searchsorted(end_ts, "left"))
    if endpos <= ei or endpos > len(idx): raise RuntimeError("bad horizon")
    final_i = endpos - 1
    if idx[final_i] != end_ts - BAR: raise RuntimeError("horizon parity")
    bi = bar_pos(idx, r.h1_break_ts) if pd.notna(r.h1_break_ts) else -1

    H, L, R = float(r.H), float(r.L), float(r.R)
    entry_price = float(r.entry_price)
    target = H + TARGET_R * R
    confirmed = bool(bi == ei)

    cut_done = False
    restore_done = False
    cut_signal_i = -1
    cut_exec_i = -1
    restore_signal_i = -1
    restore_exec_i = -1
    cut_price = np.nan
    restore_price = np.nan
    realized = 0.0
    initial_frac_active = 1.0
    restored_active = False
    pending_cut = False
    pending_restore = False

    exit_i = final_i
    exit_price = float(cl[final_i])
    exit_reason = "TIME"

    # Entry candle itself is not evaluated for target/invalidation under frozen A2,
    # but its completed close may causally schedule the first H05 partial cut.
    if live_h05(confirmed, float(cl[ei]), H, R):
        pending_cut = True
        cut_signal_i = ei

    for i in range(ei + 1, endpos):
        # Management signals from the previous completed candle execute at this open.
        if pending_cut and not cut_done:
            cut_done = True
            pending_cut = False
            cut_exec_i = i
            cut_price = float(op[i])
            realized += NOTIONAL * CUT_FRAC * (cut_price / entry_price - 1.0)
            initial_frac_active = 1.0 - CUT_FRAC

        if pending_restore and cut_done and not restore_done:
            restore_done = True
            pending_restore = False
            restore_exec_i = i
            restore_price = float(op[i])
            restored_active = True

        if not confirmed and bi >= 0 and i >= bi:
            confirmed = True

        # Frozen A2 target precedence.
        if float(hi[i]) >= target:
            exit_i = i
            exit_price = target
            exit_reason = "TARGET"
            break

        # Frozen structural terminal event.
        bad = (float(cl[i]) <= H + EPS) if confirmed else (float(cl[i]) < L - EPS)
        if bad:
            ni = i + 1
            if ni < endpos:
                exit_i = ni
                exit_price = float(op[ni])
                exit_reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            else:
                exit_i = i
                exit_price = float(cl[i])
                exit_reason = "TIME_AFTER_FINAL_INVALIDATION"
            break

        # Only still-live trades can generate management signals.
        if (not cut_done) and (not pending_cut) and live_h05(confirmed, float(cl[i]), H, R):
            pending_cut = True
            cut_signal_i = i
        elif cut_done and (not restore_done) and (not pending_restore) and live_restore_h10(float(cl[i]), H, R):
            pending_restore = True
            restore_signal_i = i

    # Close active legs at the frozen parent terminal/target price.
    raw = realized
    raw += NOTIONAL * initial_frac_active * (exit_price / entry_price - 1.0)
    if restored_active:
        raw += RESTORE_NOTIONAL * (exit_price / float(restore_price) - 1.0)

    # Frozen parent 5bps stress on original notional; one additional 5bps
    # round-trip charge only when the removed half was actually restored.
    stress_cost = STRESS * NOTIONAL + (STRESS * RESTORE_NOTIONAL if restore_done else 0.0)
    pnl5 = raw - stress_cost

    return {
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_exit_reason": r.exit_reason,
        "parent_pnl": float(r.pnl),
        "parent_pnl_5bps": float(r.pnl_5bps),
        "parent_won": bool(float(r.pnl) > 0),
        "parent_loss_class": r.loss_class,
        "exit_ts": idx[exit_i],
        "exit_reason": exit_reason,
        "exit_price": exit_price,
        "pnl": raw,
        "pnl_5bps": pnl5,
        "won": bool(raw > 0),
        "won_5bps": bool(pnl5 > 0),
        "cut_done": cut_done,
        "cut_signal_ts": idx[cut_signal_i] if cut_signal_i >= 0 else pd.NaT,
        "cut_known_ts": idx[cut_signal_i] + BAR if cut_signal_i >= 0 else pd.NaT,
        "cut_exec_ts": idx[cut_exec_i] if cut_exec_i >= 0 else pd.NaT,
        "cut_price": cut_price,
        "restore_done": restore_done,
        "restore_signal_ts": idx[restore_signal_i] if restore_signal_i >= 0 else pd.NaT,
        "restore_known_ts": idx[restore_signal_i] + BAR if restore_signal_i >= 0 else pd.NaT,
        "restore_exec_ts": idx[restore_exec_i] if restore_exec_i >= 0 else pd.NaT,
        "restore_price": restore_price,
        "stress_cost": stress_cost,
        "delta_pnl": raw - float(r.pnl),
        "delta_pnl_5bps": pnl5 - float(r.pnl_5bps),
    }


def build_trades(m):
    rows = []
    errors = []
    for part in PARTS:
        q = a53.parent(m, part)
        if len(q) != EXPECTED_N[part]: errors.append(f"{part} N={len(q)}")
        wins = int((pd.to_numeric(q.pnl, errors="coerce") > 0).sum())
        if wins != EXPECTED_WIN[part]: errors.append(f"{part} winner count {wins}")
        for _, r in q.iterrows():
            # Independent frozen baseline replay parity first.
            b = a53.simulate(m, r, "BASELINE")
            if abs(float(b["pnl"]) - float(r.pnl)) > 1e-7:
                errors.append(f"raw baseline parity {part} {r.entry_ts}")
            if abs(float(b["pnl_5bps"]) - float(r.pnl_5bps)) > 1e-7:
                errors.append(f"stress baseline parity {part} {r.entry_ts}")
            h = hybrid_simulate(m, r)
            # Hybrid must not alter the frozen structural destination itself.
            if str(h["exit_reason"]) != str(b["exit_reason"]) or pd.Timestamp(h["exit_ts"]) != pd.Timestamp(b["exit_ts"]):
                errors.append(f"structural path mismatch {part} {r.entry_ts}: {h['exit_reason']} {h['exit_ts']} vs {b['exit_reason']} {b['exit_ts']}")
            rows.append(h)
    if errors:
        raise RuntimeError("; ".join(errors[:30]))
    t = pd.DataFrame(rows).sort_values(["partition", "entry_ts"]).reset_index(drop=True)
    if len(t) != 1219: raise RuntimeError(f"row count {len(t)}")
    return t


def one_metrics(q, hybrid):
    q = q.sort_values("entry_ts")
    if hybrid:
        p = pd.to_numeric(q.pnl, errors="coerce")
        p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    else:
        p = pd.to_numeric(q.parent_pnl, errors="coerce")
        p5 = pd.to_numeric(q.parent_pnl_5bps, errors="coerce")
    parent_win = q.parent_won.astype(bool)
    cut = q.cut_done.astype(bool) if hybrid else pd.Series(False, index=q.index)
    restore = q.restore_done.astype(bool) if hybrid else pd.Series(False, index=q.index)
    out = {
        "n": len(q),
        "wr": float((p > 0).mean()), "pf": pf(p), "expectancy": float(p.mean()), "net": float(p.sum()),
        "max_dd": max_dd(p), "max_loss_streak": max_loss_streak(p),
        "positive_week_rate": positive_week_rate(q.assign(_x=p.values), "_x"),
        "wr_5bps": float((p5 > 0).mean()), "pf_5bps": pf(p5), "expectancy_5bps": float(p5.mean()), "net_5bps": float(p5.sum()),
        "max_dd_5bps": max_dd(p5), "max_loss_streak_5bps": max_loss_streak(p5),
        "positive_week_rate_5bps": positive_week_rate(q.assign(_x=p5.values), "_x"),
        "cuts": int(cut.sum()), "restores": int(restore.sum()),
        "restore_rate_of_cuts": float(restore.sum()/cut.sum()) if cut.sum() else np.nan,
        "parent_winners_cut": int((cut & parent_win).sum()),
        "parent_winners_restored": int((restore & parent_win).sum()),
        "parent_losses_cut": int((cut & ~parent_win).sum()),
        "parent_losses_restored": int((restore & ~parent_win).sum()),
        "winner_pnl_delta": float(pd.to_numeric(q.loc[parent_win, "delta_pnl"], errors="coerce").sum()) if hybrid else 0.0,
        "loss_pnl_delta": float(pd.to_numeric(q.loc[~parent_win, "delta_pnl"], errors="coerce").sum()) if hybrid else 0.0,
        "delta_net": float(pd.to_numeric(q.delta_pnl, errors="coerce").sum()) if hybrid else 0.0,
        "delta_net_5bps": float(pd.to_numeric(q.delta_pnl_5bps, errors="coerce").sum()) if hybrid else 0.0,
    }
    return out


def build_metrics(t):
    rows = []
    for part in PARTS:
        q = t[t.partition == part].copy()
        rows.append({"partition": part, "variant": "BASELINE", **one_metrics(q, False)})
        rows.append({"partition": part, "variant": VARIANT, **one_metrics(q, True)})
    return pd.DataFrame(rows)


def build_blocks(t):
    rows = []
    q = t[t.partition == "development"].copy()
    for bi in range(6):
        b = q[pd.to_numeric(q.dev_block, errors="coerce") == bi].copy()
        rows.append({
            "dev_block": bi,
            "n": len(b),
            "baseline_net": float(pd.to_numeric(b.parent_pnl, errors="coerce").sum()),
            "hybrid_net": float(pd.to_numeric(b.pnl, errors="coerce").sum()),
            "delta_net": float(pd.to_numeric(b.delta_pnl, errors="coerce").sum()),
            "baseline_net_5bps": float(pd.to_numeric(b.parent_pnl_5bps, errors="coerce").sum()),
            "hybrid_net_5bps": float(pd.to_numeric(b.pnl_5bps, errors="coerce").sum()),
            "delta_net_5bps": float(pd.to_numeric(b.delta_pnl_5bps, errors="coerce").sum()),
            "cuts": int(b.cut_done.sum()),
            "restores": int(b.restore_done.sum()),
        })
    return pd.DataFrame(rows)


def partition_pass(metrics, part, include_blocks=None):
    b = metrics[(metrics.partition == part) & (metrics.variant == "BASELINE")].iloc[0]
    h = metrics[(metrics.partition == part) & (metrics.variant == VARIANT)].iloc[0]
    checks = {
        "raw_net": bool(h.net > b.net + EPS),
        "stress_net": bool(h.net_5bps > b.net_5bps + EPS),
        "raw_pf": bool(h.pf > b.pf + EPS),
        "stress_pf": bool(h.pf_5bps > b.pf_5bps + EPS),
        "stress_wr": bool(h.wr_5bps + EPS >= b.wr_5bps),
        "raw_dd": bool(h.max_dd <= b.max_dd + EPS),
    }
    if include_blocks is not None:
        checks["raw_blocks"] = bool((include_blocks.delta_net > 0).sum() >= 4)
        checks["stress_blocks"] = bool((include_blocks.delta_net_5bps > 0).sum() >= 4)
    return all(checks.values()), checks


def write_result(metrics, blocks, coverage):
    dev_pass, dev_checks = partition_pass(metrics, "development", blocks)
    ext_pass, ext_checks = partition_pass(metrics, "external")
    ref_pass, ref_checks = partition_pass(metrics, "reference_validation")
    fully = bool(dev_pass and ext_pass and ref_pass)
    if fully:
        status = "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_SUPPORTED"
    elif dev_pass:
        status = "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_DEVELOPMENT_ONLY"
    else:
        status = "SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_REJECTED"

    lines = [
        "# SOL LONG 15:00 UTC H05 Partial De-risk + H10 Restore — A59 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "A59 tests exactly one preregistered executable hybrid: first POST_H05 completed warning -> cut 50% at next 5m open -> if the still-live trade later closes above H+0.10R, restore the removed 50% at the next 5m open. No ratio or threshold sweep is used.", "",
        "## Reconciliation", "",
        "Frozen parent counts and winner counts reconcile at 601/281/337 and 244/115/150. BASELINE replay is exact trade-by-trade within tolerance, and A59 management does not alter the parent structural terminal/target timestamp or reason.", "",
        "## Economics", "",
        "| Partition | Variant | WR | PF | Exp | Net | DD | Loss streak | Week+ | 5bps WR | 5bps PF | 5bps Exp | 5bps Net | 5bps DD | 5bps streak | 5bps Week+ | Cuts | Restores | Restore/cut | Winner cut/restored | Loss cut/restored | Winner Δ | Loss Δ | Total Δ | 5bps Δ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for part in PARTS:
        for variant in ("BASELINE", VARIANT):
            r = metrics[(metrics.partition == part) & (metrics.variant == variant)].iloc[0]
            lines.append(
                f"| {part} | {variant} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.expectancy)} | ${fmt(r.net)} | ${fmt(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.positive_week_rate)} | "
                f"{pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.expectancy_5bps)} | ${fmt(r.net_5bps)} | ${fmt(r.max_dd_5bps)} | {int(r.max_loss_streak_5bps)} | {pct(r.positive_week_rate_5bps)} | "
                f"{int(r.cuts)} | {int(r.restores)} | {pct(r.restore_rate_of_cuts)} | {int(r.parent_winners_cut)}/{int(r.parent_winners_restored)} | {int(r.parent_losses_cut)}/{int(r.parent_losses_restored)} | "
                f"${fmt(r.winner_pnl_delta)} | ${fmt(r.loss_pnl_delta)} | ${fmt(r.delta_net)} | ${fmt(r.delta_net_5bps)} |"
            )

    lines += ["", "## Development six-block deltas", "", "| Block | N | Raw ΔNet | 5bps ΔNet | Cuts | Restores |", "|---:|---:|---:|---:|---:|---:|"]
    for _, r in blocks.sort_values("dev_block").iterrows():
        lines.append(f"| {int(r.dev_block)+1} | {int(r.n)} | ${fmt(r.delta_net)} | ${fmt(r.delta_net_5bps)} | {int(r.cuts)} | {int(r.restores)} |")
    lines += ["", f"Positive Development blocks: **{int((blocks.delta_net>0).sum())}/6 raw**, **{int((blocks.delta_net_5bps>0).sum())}/6 stress**.", ""]

    lines += ["## Frozen gate decision", "", "| Partition | Gate | Details |", "|---|---:|---|"]
    def detail(c): return ", ".join(f"{k}={'PASS' if v else 'fail'}" for k,v in c.items())
    lines.append(f"| Development | {'PASS' if dev_pass else 'fail'} | {detail(dev_checks)} |")
    lines.append(f"| External | {'PASS' if ext_pass else 'fail'} | {detail(ext_checks)} |")
    lines.append(f"| Reference Validation | {'PASS' if ref_pass else 'fail'} | {detail(ref_checks)} |")
    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if status.endswith("SUPPORTED"):
        lines.append("The fixed H05 half-cut/H10 restore hybrid improves the complete preregistered economics gate in Development and both OOS partitions.")
    elif status.endswith("DEVELOPMENT_ONLY"):
        lines.append("The hybrid passes Development but fails at least one OOS confirmation gate; it is not authorized for live promotion.")
    else:
        lines.append("The hybrid fails the frozen Development gate; OOS metrics are diagnostic only and no live promotion is authorized.")
    lines += ["", "Research only. Live Baba Bot remains unchanged."]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    return status


def main():
    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)
    t = build_trades(m)
    metrics = build_metrics(t)
    blocks = build_blocks(t)
    t.to_csv(OUT_TRADES, index=False)
    metrics.to_csv(OUT_METRICS, index=False)
    blocks.to_csv(OUT_BLOCKS, index=False)
    status = write_result(metrics, blocks, coverage)
    print(status)

if __name__ == "__main__":
    main()
