#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

import sol_v5_batch2_activation_entry as b2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2C_EARLY_ENTRY_MANAGEMENT"
TEST_YEARS = b2.TEST_YEARS
CHECKPOINTS = b2.CHECKPOINTS
ROUNDTRIP_COST_PCT = b2.ROUNDTRIP_COST_PCT
NOTIONAL = b2.NOTIONAL
MODEL_END = b2.MODEL_END


def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except Exception:
        return False


def _pfmt(v) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def _next_open(x5: pd.DataFrame, p: int, cp_min: int) -> tuple[pd.Timestamp, float] | None:
    j = p + cp_min // 5
    if j >= len(x5):
        return None
    return x5.index[j], float(x5.open.iloc[j])


def simulate_policy(x5: pd.DataFrame, episodes: pd.DataFrame, pred_cp: pd.DataFrame) -> pd.DataFrame:
    eps = episodes[episodes.test_year.isin(TEST_YEARS)].copy().sort_values("entry_time").reset_index(drop=True)
    if eps.empty:
        raise RuntimeError("no test HIGH_STATE episodes")

    cp_lookup = {
        (str(r.episode_id), int(r.checkpoint_min)): r
        for _, r in pred_cp.iterrows()
    }

    pos = x5.index.get_indexer(pd.DatetimeIndex(pd.to_datetime(eps.entry_time, utc=True)))
    op = x5.open.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    rows = []
    for (_, e), p in zip(eps.iterrows(), pos):
        if p < 0 or p + 11 >= len(x5):
            continue
        state_ts = pd.Timestamp(e.entry_time)
        if x5.index[p + 11] != state_ts + pd.Timedelta(minutes=55):
            continue
        if state_ts + pd.Timedelta(minutes=60) > MODEL_END:
            continue

        entry_price = float(op[p])
        baseline_exit_price = float(cl[p + 11])
        baseline_gross = (baseline_exit_price / entry_price - 1.0) * 100.0
        baseline_net = baseline_gross - ROUNDTRIP_COST_PCT

        first_barrier = str(e.first_barrier)
        up_t = float(e.time_to_up_impulse_min) if _finite(e.time_to_up_impulse_min) else np.nan
        dn_t = float(e.time_to_down_impulse_min) if _finite(e.time_to_down_impulse_min) else np.nan

        exit_reason = None
        exit_time = None
        exit_price = None
        management_cp = None
        last_direction_score = np.nan
        last_direction_cutoff = np.nan
        score_checks = 0
        held_high_conf_checks = 0

        for cp in CHECKPOINTS:
            # Barrier state has priority because it is causally known by checkpoint close.
            if first_barrier == "UP_FIRST" and _finite(up_t) and up_t <= cp:
                exit_reason = "UP_CONFIRMED_HOLD60"
                exit_time = state_ts + pd.Timedelta(minutes=60)
                exit_price = baseline_exit_price
                management_cp = cp
                break

            if first_barrier == "DOWN_FIRST" and _finite(dn_t) and dn_t <= cp:
                nxt = _next_open(x5, p, cp)
                if nxt is None:
                    break
                exit_time, exit_price = nxt
                exit_reason = "DOWN_FIRST_EXIT"
                management_cp = cp
                break

            if first_barrier == "BOTH_SAME_BAR":
                t_same = up_t if _finite(up_t) else dn_t
                if _finite(t_same) and t_same <= cp:
                    nxt = _next_open(x5, p, cp)
                    if nxt is None:
                        break
                    exit_time, exit_price = nxt
                    exit_reason = "BOTH_SAME_BAR_EXIT"
                    management_cp = cp
                    break

            key = (str(e.episode_id), int(cp))
            r = cp_lookup.get(key)
            if r is None:
                nxt = _next_open(x5, p, cp)
                if nxt is None:
                    break
                exit_time, exit_price = nxt
                exit_reason = "MISSING_SCORE_EXIT"
                management_cp = cp
                break

            score = float(r.activation_score)
            cutoff = float(r.activation_cutoff)
            last_direction_score = score
            last_direction_cutoff = cutoff
            score_checks += 1

            if score >= cutoff:
                held_high_conf_checks += 1
                continue

            nxt = _next_open(x5, p, cp)
            if nxt is None:
                break
            exit_time, exit_price = nxt
            exit_reason = "LOW_DIRECTION_EXIT"
            management_cp = cp
            break

        if exit_reason is None:
            exit_reason = "SURVIVED_30_HOLD60"
            exit_time = state_ts + pd.Timedelta(minutes=60)
            exit_price = baseline_exit_price
            management_cp = 30

        gross = (float(exit_price) / entry_price - 1.0) * 100.0
        net = gross - ROUNDTRIP_COST_PCT
        duration_min = float((pd.Timestamp(exit_time) - state_ts) / pd.Timedelta(minutes=1))

        rows.append({
            "episode_id": str(e.episode_id),
            "state_entry_time": state_ts,
            "test_year": int(e.test_year),
            "entry_price": entry_price,
            "state_score": float(e.pred_impulse),
            "first_barrier": first_barrier,
            "time_to_up_impulse_min": up_t,
            "time_to_down_impulse_min": dn_t,
            "exit_reason": exit_reason,
            "management_checkpoint_min": int(management_cp),
            "exit_time": pd.Timestamp(exit_time),
            "exit_price": float(exit_price),
            "duration_min": duration_min,
            "last_direction_score": last_direction_score,
            "last_direction_cutoff": last_direction_cutoff,
            "score_checks": int(score_checks),
            "high_conf_hold_checks": int(held_high_conf_checks),
            "policy_gross_pct": gross,
            "policy_net_pct": net,
            "policy_pnl_usd": net / 100.0 * NOTIONAL,
            "baseline_net60_pct": baseline_net,
            "baseline_pnl60_usd": baseline_net / 100.0 * NOTIONAL,
        })

    out = pd.DataFrame(rows).sort_values("state_entry_time").reset_index(drop=True)
    if out.empty:
        raise RuntimeError("no evaluable policy trades")
    return out


def yearly_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        g = trades[trades.test_year == y].copy()
        pe = b2.econ_returns(g.policy_net_pct)
        be = b2.econ_returns(g.baseline_net60_pct)
        rows.append({
            "test_year": y,
            "n": int(len(g)),
            "policy_wr": pe["wr"],
            "policy_expectancy_pct": pe["expectancy_pct"],
            "policy_pf": pe["pf"],
            "policy_pnl_usd": pe["net_pnl_usd"],
            "policy_max_dd_usd": pe["max_dd_usd"],
            "policy_max_ls": pe["max_ls"],
            "baseline_wr": be["wr"],
            "baseline_expectancy_pct": be["expectancy_pct"],
            "baseline_pf": be["pf"],
            "baseline_pnl_usd": be["net_pnl_usd"],
            "baseline_max_dd_usd": be["max_dd_usd"],
            "expectancy_delta_pp": pe["expectancy_pct"] - be["expectancy_pct"],
            "median_duration_min": float(g.duration_min.median()) if len(g) else np.nan,
            "up_confirmed_rate": float((g.exit_reason == "UP_CONFIRMED_HOLD60").mean()) if len(g) else np.nan,
            "low_direction_exit_rate": float((g.exit_reason == "LOW_DIRECTION_EXIT").mean()) if len(g) else np.nan,
        })
    return pd.DataFrame(rows)


def reason_summary(trades: pd.DataFrame) -> pd.DataFrame:
    q = trades.groupby("exit_reason", as_index=False).agg(
        n=("episode_id", "size"),
        mean_policy_net_pct=("policy_net_pct", "mean"),
        median_policy_net_pct=("policy_net_pct", "median"),
        mean_duration_min=("duration_min", "mean"),
        win_rate=("policy_net_pct", lambda s: float((s > 0).mean())),
    )
    q["rate"] = q.n / len(trades)
    return q.sort_values("n", ascending=False).reset_index(drop=True)


def checkpoint_exit_summary(trades: pd.DataFrame) -> pd.DataFrame:
    q = trades.groupby(["management_checkpoint_min", "exit_reason"], as_index=False).agg(
        n=("episode_id", "size"),
        mean_policy_net_pct=("policy_net_pct", "mean"),
        win_rate=("policy_net_pct", lambda s: float((s > 0).mean())),
    )
    q["rate"] = q.n / len(trades)
    return q.sort_values(["management_checkpoint_min", "n"], ascending=[True, False]).reset_index(drop=True)


def main():
    # Rebuild frozen state and Batch 2 OOS direction predictions exactly.
    b2.b1.v4.v3.v1.base.fetch_one = b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = b2.b1.v4.build_opportunities(x5)
    pred_state = b2.b1.causal_scores(ev)
    mapped = b2.b1.map_future_paths(x5, pred_state)
    episodes = b2.episode_starts(mapped)
    checkpoints = b2.build_checkpoints(x5, episodes)
    pred_cp, _ = b2.walk_forward(checkpoints)

    trades = simulate_policy(x5, episodes, pred_cp)
    yr = yearly_summary(trades)
    reasons = reason_summary(trades)
    cps = checkpoint_exit_summary(trades)

    policy_e = b2.econ_returns(trades.policy_net_pct)
    base_e = b2.econ_returns(trades.baseline_net60_pct)
    delta = float(policy_e["expectancy_pct"] - base_e["expectancy_pct"])
    pos_years = int((yr.policy_pnl_usd > 0).sum())

    gates = {
        "policy_n_ge_1500": int(len(trades)) >= 1500,
        "policy_expectancy_positive": bool(np.isfinite(policy_e["expectancy_pct"]) and policy_e["expectancy_pct"] > 0),
        "policy_pf_ge_1_10": bool(np.isfinite(policy_e["pf"]) and policy_e["pf"] >= 1.10),
        "paired_expectancy_improvement_positive": bool(np.isfinite(delta) and delta > 0),
        "policy_max_dd_not_worse_than_baseline": bool(np.isfinite(policy_e["max_dd_usd"]) and np.isfinite(base_e["max_dd_usd"]) and policy_e["max_dd_usd"] <= base_e["max_dd_usd"]),
        "positive_pnl_years_ge_2_of_3": pos_years >= 2,
    }
    passed = bool(all(gates.values()))
    verdict = "READY_FOR_BATCH3_RISK_ENVELOPE" if passed else "EARLY_ENTRY_MANAGEMENT_NOT_READY"

    trades.to_csv(ROOT / f"{PFX}_Trades.csv", index=False)
    pred_cp.to_csv(ROOT / f"{PFX}_DirectionPredictions.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    reasons.to_csv(ROOT / f"{PFX}_ExitReasonSummary.csv", index=False)
    cps.to_csv(ROOT / f"{PFX}_CheckpointExitSummary.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 2C — Early Entry + Directional Management Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- Evaluable HIGH_STATE trades 2022-2024: **{len(trades)}**",
        f"- Median policy duration: **{float(trades.duration_min.median()):.1f} min**",
        f"- UP_CONFIRMED hold rate: **{float((trades.exit_reason == 'UP_CONFIRMED_HOLD60').mean())*100:.2f}%**",
        f"- LOW_DIRECTION early-exit rate: **{float((trades.exit_reason == 'LOW_DIRECTION_EXIT').mean())*100:.2f}%**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Pooled economics", "",
        f"- Policy WR: **{policy_e['wr']*100:.2f}%**",
        f"- Policy expectancy: **{policy_e['expectancy_pct']:.4f}%**",
        f"- Policy PF: **{_pfmt(policy_e['pf'])}**",
        f"- Policy net PnL: **${policy_e['net_pnl_usd']:.2f}**",
        f"- Policy max DD: **${policy_e['max_dd_usd']:.2f}**",
        f"- Policy max loss streak: **{policy_e['max_ls']}**", "",
        f"- Baseline +60m WR: **{base_e['wr']*100:.2f}%**",
        f"- Baseline +60m expectancy: **{base_e['expectancy_pct']:.4f}%**",
        f"- Baseline +60m PF: **{_pfmt(base_e['pf'])}**",
        f"- Baseline +60m net PnL: **${base_e['net_pnl_usd']:.2f}**",
        f"- Baseline +60m max DD: **${base_e['max_dd_usd']:.2f}**",
        f"- Paired expectancy delta: **{delta:+.4f} pp**", "",
        "## Year stability", "",
        "| Year | N | Policy WR | Policy Exp | PF | Policy PnL | Baseline Exp | Δ Exp | Policy DD | Baseline DD | Median dur |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.n)} | {float(r.policy_wr)*100:.2f}% | {float(r.policy_expectancy_pct):.4f}% | {_pfmt(r.policy_pf)} | ${float(r.policy_pnl_usd):.2f} | {float(r.baseline_expectancy_pct):.4f}% | {float(r.expectancy_delta_pp):+.4f} | ${float(r.policy_max_dd_usd):.2f} | ${float(r.baseline_max_dd_usd):.2f} | {float(r.median_duration_min):.1f}m |"
        )

    lines += ["", "## Exit reasons", "", "| Reason | N | Rate | WR | Mean net | Mean duration |", "|---|---:|---:|---:|---:|---:|"]
    for _, r in reasons.iterrows():
        lines.append(
            f"| {r.exit_reason} | {int(r.n)} | {float(r.rate)*100:.2f}% | {float(r.win_rate)*100:.2f}% | {float(r.mean_policy_net_pct):.4f}% | {float(r.mean_duration_min):.1f}m |"
        )

    lines += ["", "## Batch 2C decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# BATCH 2C VERDICT: {verdict}", "",
        "READY_FOR_BATCH3_RISK_ENVELOPE means early entry plus frozen causal direction management is economically better than unconditional HIGH_STATE +60m holding and is stable enough to begin adaptive risk-envelope work.",
        "EARLY_ENTRY_MANAGEMENT_NOT_READY means do not rescue the policy by sweeping direction cutoffs, checkpoint timing, TP, SL, or holding horizon on the same 2022-2024 research sample.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
