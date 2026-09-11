#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_e13c_e12_native_hold_sequential as e13c

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E14B_24H_OPPORTUNITY_SCHEDULER"
OUT_PRIORS = ROOT / f"{PFX}_HourPriors.csv"
OUT_VALUES = ROOT / f"{PFX}_SlotValues.csv"
OUT_GRID = ROOT / f"{PFX}_PolicyGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_Leaderboard.csv"
OUT_HOURS = ROOT / f"{PFX}_HourContribution.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_DECISIONS = ROOT / f"{PFX}_SelectedDecisions.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

YEARS = (2022, 2023, 2024)
MARGINS = (0.00, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00)
REPEAT_DAYS = 60
EXTRACT_DAY = 30
SLOTS_PER_DAY = 96

# Frozen benchmark from E13D strict-Pareto candidate.
KLO = dict(wr=0.556430, net=647.28, exp=1.6989, pf=1.4695, dd=96.03, ls=6)


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def summarize(T: pd.DataFrame):
    return e13c.summarize_df(T)


def development_days():
    pa, pz = e13c.base.PARTS["development"]
    # Calendar days with entry timestamps in Development. The final few anchor slots
    # may be ineligible for long native holds; this denominator is deliberately a
    # simple periodic arrival-rate prior, as preregistered.
    a = pd.Timestamp(pa).floor("D")
    z = pd.Timestamp(pz).floor("D")
    return max(1, int((z - a) / pd.Timedelta(days=1)))


def build_priors(T: pd.DataFrame) -> pd.DataFrame:
    denom = development_days() * 4.0
    rows = []
    for h in range(24):
        X = T[T.source_hour_wib == h].copy()
        year_exps = {}
        for y in YEARS:
            Y = X[pd.DatetimeIndex(X.entry_ts).year == y]
            ss = summarize(Y)
            year_exps[y] = float(ss.get("expectancy", np.nan))
        finite = [v for v in year_exps.values() if np.isfinite(v)]
        conservative = min(finite) if len(finite) == len(YEARS) else -np.inf
        q = max(0.0, conservative) if np.isfinite(conservative) else 0.0
        pooled = summarize(X)
        exp, formal, rule, lb, hold = e13c.MAP[h]
        rows.append({
            "hour_wib": h,
            "experiment": exp,
            "formal_status": formal,
            "rule": rule,
            "lookback_min": lb,
            "native_hold_min": hold,
            "opportunities": len(X),
            "scheduled_anchor_slots_prior": denom,
            "signal_probability": min(1.0, len(X) / denom),
            "pooled_wr": pooled.get("win_rate", np.nan),
            "pooled_net": pooled.get("net_pnl", np.nan),
            "pooled_exp": pooled.get("expectancy", np.nan),
            "pooled_pf": pooled.get("pf", np.nan),
            "y2022_exp": year_exps[2022],
            "y2023_exp": year_exps[2023],
            "y2024_exp": year_exps[2024],
            "conservative_edge": conservative,
            "continuation_q": q,
        })
    return pd.DataFrame(rows).sort_values("hour_wib").reset_index(drop=True)


def solve_slot_values(P: pd.DataFrame):
    by_h = P.set_index("hour_wib")
    pattern = []
    for slot in range(SLOTS_PER_DAY):
        h = slot // 4
        r = by_h.loc[h]
        pattern.append((float(r.signal_probability), float(r.continuation_q), int(r.native_hold_min // 15), h))

    max_d = max(x[2] for x in pattern)
    n = REPEAT_DAYS * SLOTS_PER_DAY + max_d + 2
    V = np.zeros(n + 1, dtype=float)
    for t in range(REPEAT_DAYS * SLOTS_PER_DAY - 1, -1, -1):
        p, q, d, _ = pattern[t % SLOTS_PER_DAY]
        wait = V[t + 1]
        take = q + V[min(t + d, n)]
        V[t] = (1.0 - p) * wait + p * max(take, wait)

    base = EXTRACT_DAY * SLOTS_PER_DAY
    rows = []
    adv = np.zeros(SLOTS_PER_DAY, dtype=float)
    for s in range(SLOTS_PER_DAY):
        t = base + s
        p, q, d, h = pattern[s]
        wait = V[t + 1]
        take = q + V[t + d]
        a = take - wait
        adv[s] = a
        rows.append({
            "slot_wib": s,
            "hour_wib": h,
            "minute_wib": (s % 4) * 15,
            "signal_probability": p,
            "continuation_q": q,
            "native_hold_slots": d,
            "native_hold_min": d * 15,
            "take_value": take,
            "wait_value": wait,
            "advantage": a,
        })
    return pd.DataFrame(rows), adv


def slot_of_entry(ts) -> int:
    wib = pd.Timestamp(ts) + pd.Timedelta(hours=7)
    return int(wib.hour * 4 + wib.minute // 15)


def replay(T: pd.DataFrame, policy: str, margin: float | None, advantages: np.ndarray):
    U = T.sort_values(["entry_ts", "source_hour_wib", "clock_utc_min"]).reset_index(drop=True)
    taken, decisions = [], []
    busy_until = None
    for r in U.itertuples(index=False):
        d = r._asdict()
        slot = slot_of_entry(r.entry_ts)
        a = float(advantages[slot])
        d.update({"policy": policy, "margin": margin, "slot_wib": slot, "advantage": a})
        if busy_until is not None and r.entry_ts < busy_until:
            d["decision"] = "SKIPPED_BUSY"
            decisions.append(d)
            continue
        take = policy == "FIRST_VALID_ALL24" or a + 1e-12 >= float(margin)
        if take:
            d["decision"] = "TAKE"
            taken.append(d)
            decisions.append(d)
            busy_until = r.exit_ts
        else:
            d["decision"] = "SKIPPED_WAIT_VALUE"
            decisions.append(d)
    return pd.DataFrame(taken), pd.DataFrame(decisions)


def pareto(row, b):
    floor = (
        row["win_rate"] >= b["wr"] - 1e-12 and
        row["net_pnl"] >= b["net"] - 1e-9 and
        row["expectancy"] >= b["exp"] - 1e-12 and
        row["pf"] >= b["pf"] - 1e-12 and
        row["max_dd"] <= b["dd"] + 1e-9 and
        row["max_loss_streak"] <= b["ls"]
    )
    improved = (
        row["win_rate"] > b["wr"] + 5e-5 or row["net_pnl"] > b["net"] + .005 or
        row["expectancy"] > b["exp"] + .005 or row["pf"] > b["pf"] + .0005 or
        row["max_dd"] < b["dd"] - .005 or row["max_loss_streak"] < b["ls"]
    )
    return bool(floor and improved)


def policy_row(E: pd.DataFrame, D: pd.DataFrame, policy: str, margin: float | None):
    ss = summarize(E)
    total = len(D)
    row = {
        "policy": policy,
        "margin": np.nan if margin is None else margin,
        "executed_trades": len(E),
        "skipped_busy": int((D.decision == "SKIPPED_BUSY").sum()) if len(D) else 0,
        "skipped_wait_value": int((D.decision == "SKIPPED_WAIT_VALUE").sum()) if len(D) else 0,
        "execution_rate": len(E) / total if total else np.nan,
        "win_rate": ss.get("win_rate", np.nan),
        "net_pnl": ss.get("net_pnl", np.nan),
        "expectancy": ss.get("expectancy", np.nan),
        "pf": ss.get("pf", np.nan),
        "max_dd": ss.get("max_dd", np.nan),
        "max_loss_streak": ss.get("max_loss_streak", 0),
        "max_win_streak": ss.get("max_win_streak", 0),
        "avg_hold_h": E.hold_min.mean() / 60.0 if len(E) else np.nan,
        "median_hold_h": E.hold_min.median() / 60.0 if len(E) else np.nan,
    }
    min_exp = np.inf
    years55 = 0
    era_ok = True
    for y in YEARS:
        Y = E[pd.DatetimeIndex(E.entry_ts).year == y] if len(E) else E
        ys = summarize(Y)
        n = len(Y); wr = ys.get("win_rate", np.nan); net = ys.get("net_pnl", np.nan); ex = ys.get("expectancy", np.nan); pf = ys.get("pf", np.nan)
        row.update({f"y{y}_n": n, f"y{y}_wr": wr, f"y{y}_net": net, f"y{y}_exp": ex, f"y{y}_pf": pf})
        ok = bool(n >= 40 and np.isfinite(wr) and wr >= .52 and net > 0 and np.isfinite(ex) and ex > 0 and np.isfinite(pf) and pf >= 1.05)
        era_ok &= ok
        years55 += int(np.isfinite(wr) and wr >= .55)
        min_exp = min(min_exp, ex if np.isfinite(ex) else -np.inf)
    row["min_year_exp"] = float(min_exp)
    row["years_wr55"] = years55
    pooled_ok = bool(
        row["executed_trades"] >= 160 and np.isfinite(row["win_rate"]) and row["win_rate"] >= .55 and
        row["net_pnl"] > 0 and np.isfinite(row["expectancy"]) and row["expectancy"] >= .50 and
        np.isfinite(row["pf"]) and row["pf"] >= 1.20 and np.isfinite(row["max_dd"]) and row["max_dd"] <= 131.02 and
        row["max_loss_streak"] <= 8
    )
    row["pooled_gate"] = pooled_ok
    row["era_gate"] = bool(era_ok and years55 >= 2)
    row["robust"] = bool(row["pooled_gate"] and row["era_gate"])
    return row


def hour_contrib(policy, E: pd.DataFrame, D: pd.DataFrame):
    rows = []
    for h in range(24):
        X = E[E.source_hour_wib == h] if len(E) else E
        Q = D[D.source_hour_wib == h] if len(D) else D
        ss = summarize(X)
        rows.append({
            "policy": policy,
            "hour_wib": h,
            "experiment": e13c.MAP[h][0],
            "formal_status": e13c.MAP[h][1],
            "native_hold_min": e13c.MAP[h][4],
            "signals": len(Q),
            "executed": len(X),
            "skipped_busy": int((Q.decision == "SKIPPED_BUSY").sum()) if len(Q) else 0,
            "skipped_wait_value": int((Q.decision == "SKIPPED_WAIT_VALUE").sum()) if len(Q) else 0,
            "wr": ss.get("win_rate", np.nan),
            "net": ss.get("net_pnl", np.nan),
            "exp": ss.get("expectancy", np.nan),
            "pf": ss.get("pf", np.nan),
        })
    return rows


def main():
    e13c.base.synthetic_tests()
    x5, coverage = e13c.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    T = e13c.build_opportunities(x5)
    if len(T) == 0:
        raise RuntimeError("no E12-native opportunities")

    P = build_priors(T)
    S, adv = solve_slot_values(P)
    P.to_csv(OUT_PRIORS, index=False)
    S.to_csv(OUT_VALUES, index=False)

    specs = [("FIRST_VALID_ALL24", None)] + [(f"OC_M{int(m*100):03d}", m) for m in MARGINS]
    rows, hour_rows = [], []
    ledgers, decisions = {}, {}
    for name, margin in specs:
        E, D = replay(T, name, margin, adv)
        rows.append(policy_row(E, D, name, margin))
        hour_rows += hour_contrib(name, E, D)
        ledgers[name] = E
        decisions[name] = D

    G = pd.DataFrame(rows)
    ref = G[G.policy == "FIRST_VALID_ALL24"]
    if len(ref) != 1:
        raise AssertionError("missing FIRST_VALID_ALL24")
    b = ref.iloc[0]
    # Reproduction guard for E13C all-24 sequential semantics.
    if int(b.executed_trades) != 1149:
        raise AssertionError(f"expected E13C all24 N=1149, got {int(b.executed_trades)}")

    base_actual = dict(wr=float(b.win_rate), net=float(b.net_pnl), exp=float(b.expectancy), pf=float(b.pf), dd=float(b.max_dd), ls=int(b.max_loss_streak))
    G["pareto_vs_all24"] = [bool(r.robust and pareto(r._asdict(), base_actual)) for r in G.itertuples(index=False)]
    G["pareto_vs_klo"] = [bool(r.robust and pareto(r._asdict(), KLO)) for r in G.itertuples(index=False)]

    R = G[(G.policy != "FIRST_VALID_ALL24") & G.robust].copy().sort_values(
        ["min_year_exp","years_wr55","expectancy","pf","win_rate","max_dd","max_loss_streak","net_pnl","executed_trades","margin"],
        ascending=[False,False,False,False,False,True,True,False,False,True]
    ).reset_index(drop=True)
    if len(R):
        R["rank"] = np.arange(1, len(R)+1)

    G.to_csv(OUT_GRID, index=False)
    R.to_csv(OUT_LEADER, index=False)
    H = pd.DataFrame(hour_rows)
    H.to_csv(OUT_HOURS, index=False)

    selected = R.iloc[0] if len(R) else None
    if selected is not None:
        name = str(selected.policy)
        ledgers[name].to_csv(OUT_TRADES, index=False)
        decisions[name].to_csv(OUT_DECISIONS, index=False)

    lines = [
        "# ETH E14B — 24H Causal Opportunity-Cost Scheduler Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "All 24 frozen hourly representatives were eligible signal sources; E12 FAIL labels were not promoted.",
        "Native E12 fixed holds were preserved; one active position max; no TP/SL/DCA/daily forced flat.", "",
        "## Hour-level continuation priors", "",
        "| WIB | E12 | Formal | Hold | Opps | Signal p | Exp22 | Exp23 | Exp24 | Conservative q |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in P.itertuples(index=False):
        lines.append(f"| {int(r.hour_wib):02d} | {r.experiment} | {r.formal_status} | {int(r.native_hold_min)}m | {int(r.opportunities)} | {pct(r.signal_probability)} | {money(r.y2022_exp)} | {money(r.y2023_exp)} | {money(r.y2024_exp)} | {money(r.continuation_q)} |")

    lines += ["", "## Policy grid", "",
              "| Policy | N | WR | Net | Exp | PF | DD | LS | Busy skip | Wait skip | Avg hold | Min-year exp | Y>=55 | Robust | Pareto all24 | Pareto KLO |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    for r in G.itertuples(index=False):
        lines.append(f"| {r.policy} | {int(r.executed_trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.skipped_busy)} | {int(r.skipped_wait_value)} | {float(r.avg_hold_h):.2f}h | {money(r.min_year_exp)} | {int(r.years_wr55)}/3 | {'YES' if r.robust else 'NO'} | {'YES' if r.pareto_vs_all24 else 'NO'} | {'YES' if r.pareto_vs_klo else 'NO'} |")

    lines += ["", "## Reference reproduction", "",
              f"FIRST_VALID_ALL24: N **{int(b.executed_trades)}**, WR **{pct(b.win_rate)}**, net **{money(b.net_pnl)}**, exp **{money(b.expectancy)}**, PF **{float(b.pf):.3f}**, DD **{money(b.max_dd)}**, LS **{int(b.max_loss_streak)}**.", ""]

    if selected is None:
        status = "ETH_E14B_NO_ROBUST_SCHEDULER"
        lines += ["## Verdict", "", f"**{status}**", "",
                  "No preregistered Bellman reservation-margin scheduler passed the frozen pooled + cross-era robustness gate."]
    else:
        s = selected
        name = str(s.policy)
        status = "ETH_E14B_ROBUST_SCHEDULER_FOUND"
        lines += ["## Development-selected scheduler", "", f"**{name}**", "",
                  f"N **{int(s.executed_trades)}**, WR **{pct(s.win_rate)}**, net **{money(s.net_pnl)}**, exp **{money(s.expectancy)}**, PF **{float(s.pf):.3f}**, DD **{money(s.max_dd)}**, LS **{int(s.max_loss_streak)}**.",
                  f"Min-year expectancy **{money(s.min_year_exp)}**; years WR>=55% **{int(s.years_wr55)}/3**; Pareto vs all24 **{'YES' if bool(s.pareto_vs_all24) else 'NO'}**; Pareto vs K+L+O **{'YES' if bool(s.pareto_vs_klo) else 'NO'}**.", "", "### Cross-era", ""]
        for y in YEARS:
            lines.append(f"- {y}: N **{int(s[f'y{y}_n'])}**, WR **{pct(s[f'y{y}_wr'])}**, net **{money(s[f'y{y}_net'])}**, exp **{money(s[f'y{y}_exp'])}**, PF **{float(s[f'y{y}_pf']):.3f}**")
        lines += ["", "### Selected scheduler hour contribution", "", "| WIB | E12 | Hold | Signals | Exec | Busy | Wait | WR | Net | Exp | PF |", "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in H[H.policy == name].itertuples(index=False):
            lines.append(f"| {int(r.hour_wib):02d} | {r.experiment} | {int(r.native_hold_min)}m | {int(r.signals)} | {int(r.executed)} | {int(r.skipped_busy)} | {int(r.skipped_wait_value)} | {pct(r.wr)} | {money(r.net)} | {money(r.exp)} | {float(r.pf):.3f} |")
        lines += ["", "## Verdict", "", f"**{status}**"]

    lines += ["", "The Bellman prior is a Development-selected approximation that assumes independent future signal arrivals. Research/shadow only; no OOS exposure and no live authorization."]
    OUT_STATUS.write_text(status + "\n")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
