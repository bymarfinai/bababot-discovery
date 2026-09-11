#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_e13c_e12_native_hold_sequential as e13c
import eth_economic_first_e12a_long_13_14wib_character as e12a
import eth_economic_first_e11_market_state_character as e11

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E14A_24H_DAILY_CAMPAIGN"
OUT_SIGNALS = ROOT / f"{PFX}_Signals.csv"
OUT_GRID = ROOT / f"{PFX}_ArchitectureGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_Leaderboard.csv"
OUT_CAMPAIGNS = ROOT / f"{PFX}_SelectedCampaigns.csv"
OUT_TRANCHES = ROOT / f"{PFX}_SelectedTranches.csv"
OUT_HOURS = ROOT / f"{PFX}_SelectedHourContribution.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

YEARS = (2022, 2023, 2024)
MAX_NOTIONAL = 500.0
FEE_RATE = 0.75 / 500.0
POLICIES = ("SEQUENTIAL_ANY", "PRICE_IMPROVEMENT", "DISTINCT_HOUR_CONFIRM")
MAX_ENTRIES = (1, 2, 3, 4)
BOUNDARY_UTC_HOUR = 16  # 23:00 WIB


def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def campaign_bounds(ts: pd.DatetimeIndex):
    shifted = ts - pd.Timedelta(hours=BOUNDARY_UTC_HOUR)
    starts = shifted.floor("D") + pd.Timedelta(hours=BOUNDARY_UTC_HOUR)
    closes = starts + pd.Timedelta(days=1)
    return starts, closes


def build_signals(x5: pd.DataFrame) -> pd.DataFrame:
    pa, pz = e13c.base.PARTS["development"]
    rows = []
    for hour in range(24):
        exp, formal, rule, lb, native_hold = e13c.MAP[hour]
        for q in (0, 15, 30, 45):
            clock = (e13c.utc_base(hour) + q) % 1440
            S = e11.state_frame(x5, clock, lb)
            ent = pd.DatetimeIndex(S.entry_ts)
            pre = pd.DatetimeIndex(S.pre_ts)
            masks = e12a.masks_for_frame(S)
            starts, closes = campaign_bounds(ent)
            close_px = x5["open"].reindex(closes).to_numpy(float)
            ep = S.entry_price.to_numpy(float)
            m = (
                (pre >= pa) & (ent >= pa) & (starts >= pa) & (closes < pz) &
                np.isfinite(ep) & np.isfinite(close_px) & masks[rule]
            )
            idx = np.flatnonzero(m)
            for i in idx:
                rows.append({
                    "experiment": exp,
                    "formal_status": formal,
                    "source_hour_wib": hour,
                    "anchor_wib": f"{hour:02d}:{q:02d}",
                    "clock_utc_min": clock,
                    "rule": rule,
                    "lookback_min": lb,
                    "native_hold_min_reference": native_hold,
                    "entry_ts": ent[i],
                    "entry_price": float(ep[i]),
                    "campaign_start": starts[i],
                    "campaign_close": closes[i],
                    "campaign_exit_price": float(close_px[i]),
                })
    T = pd.DataFrame(rows)
    if len(T) == 0:
        return T
    return T.sort_values(["campaign_start", "entry_ts", "source_hour_wib", "clock_utc_min"]).reset_index(drop=True)


def avg_cost(entries):
    if not entries:
        return np.nan
    total_notional = sum(x["notional"] for x in entries)
    total_units = sum(x["notional"] / x["entry_price"] for x in entries)
    return total_notional / total_units if total_units > 0 else np.nan


def accept_campaign(G: pd.DataFrame, policy: str, k: int):
    tranche_notional = MAX_NOTIONAL / k
    accepted = []
    used_hours = set()
    for r in G.sort_values(["entry_ts", "source_hour_wib", "clock_utc_min"]).itertuples(index=False):
        if len(accepted) >= k:
            break
        ok = False
        if len(accepted) == 0:
            ok = True
        elif policy == "SEQUENTIAL_ANY":
            ok = True
        elif policy == "PRICE_IMPROVEMENT":
            ok = float(r.entry_price) < avg_cost(accepted)
        elif policy == "DISTINCT_HOUR_CONFIRM":
            ok = int(r.source_hour_wib) not in used_hours
        else:
            raise ValueError(policy)
        if not ok:
            continue
        d = r._asdict()
        d["notional"] = tranche_notional
        accepted.append(d)
        used_hours.add(int(r.source_hour_wib))
    return accepted


def run_architecture(T: pd.DataFrame, policy: str, k: int):
    camps, tranche_rows = [], []
    for start, G in T.groupby("campaign_start", sort=True):
        A = accept_campaign(G, policy, k)
        if not A:
            continue
        exit_price = float(A[0]["campaign_exit_price"])
        close_ts = A[0]["campaign_close"]
        first_price = float(A[0]["entry_price"])
        total_gross = 0.0
        total_net = 0.0
        for j, a in enumerate(A, start=1):
            notional = float(a["notional"])
            gross = notional * (exit_price / float(a["entry_price"]) - 1.0)
            fee = FEE_RATE * notional
            net = gross - fee
            total_gross += gross
            total_net += net
            tr = dict(a)
            tr.update({
                "policy": policy, "max_entries": k, "tranche_no": j,
                "gross_pnl": gross, "fee": fee, "net_pnl": net,
            })
            tranche_rows.append(tr)
        cost = avg_cost(A)
        deployed = sum(float(a["notional"]) for a in A)
        camps.append({
            "policy": policy,
            "max_entries": k,
            "architecture": f"{policy}_K{k}",
            "campaign_start": start,
            "campaign_close": close_ts,
            "first_entry_ts": A[0]["entry_ts"],
            "last_entry_ts": A[-1]["entry_ts"],
            "entries": len(A),
            "deployed_notional": deployed,
            "capital_utilization": deployed / MAX_NOTIONAL,
            "first_entry_price": first_price,
            "weighted_avg_entry": cost,
            "entry_improvement_vs_first": (first_price - cost) / first_price if np.isfinite(cost) else np.nan,
            "exit_price": exit_price,
            "hours_to_close_from_first": (pd.Timestamp(close_ts) - pd.Timestamp(A[0]["entry_ts"])) / pd.Timedelta(hours=1),
            "gross_pnl": total_gross,
            "net_pnl": total_net,
            "win": total_net > 0,
            "source_hours": "+".join(str(int(a["source_hour_wib"])) for a in A),
        })
    C = pd.DataFrame(camps).sort_values("campaign_start").reset_index(drop=True) if camps else pd.DataFrame()
    X = pd.DataFrame(tranche_rows).sort_values(["campaign_start", "entry_ts", "tranche_no"]).reset_index(drop=True) if tranche_rows else pd.DataFrame()
    return C, X


def summarize(C: pd.DataFrame):
    if C is None or len(C) == 0:
        return e12a.summarize(np.array([]), np.array([]))
    return e12a.summarize(C.net_pnl.to_numpy(float), C.gross_pnl.to_numpy(float))


def architecture_row(C: pd.DataFrame, policy: str, k: int):
    ss = summarize(C)
    row = {
        "architecture": f"{policy}_K{k}", "policy": policy, "max_entries": k,
        "campaign_n": len(C), "win_rate": ss.get("win_rate", np.nan), "net_pnl": ss.get("net_pnl", np.nan),
        "expectancy": ss.get("expectancy", np.nan), "pf": ss.get("pf", np.nan), "max_dd": ss.get("max_dd", np.nan),
        "max_loss_streak": ss.get("max_loss_streak", 0), "max_win_streak": ss.get("max_win_streak", 0),
        "avg_entries": C.entries.mean() if len(C) else np.nan,
        "median_entries": C.entries.median() if len(C) else np.nan,
        "avg_deployed_notional": C.deployed_notional.mean() if len(C) else np.nan,
        "avg_capital_utilization": C.capital_utilization.mean() if len(C) else np.nan,
        "avg_entry_improvement_vs_first": C.entry_improvement_vs_first.mean() if len(C) else np.nan,
        "avg_hours_to_close_from_first": C.hours_to_close_from_first.mean() if len(C) else np.nan,
    }
    for n in (1,2,3,4):
        row[f"campaigns_{n}_entries"] = int((C.entries == n).sum()) if len(C) else 0
    min_exp = np.inf
    years55 = 0
    era_ok = True
    for y in YEARS:
        Y = C[pd.DatetimeIndex(C.campaign_start).year == y] if len(C) else C
        ys = summarize(Y)
        n = len(Y); wr = ys.get("win_rate", np.nan); net = ys.get("net_pnl", np.nan); exp = ys.get("expectancy", np.nan); pf = ys.get("pf", np.nan)
        row.update({f"y{y}_n": n, f"y{y}_wr": wr, f"y{y}_net": net, f"y{y}_exp": exp, f"y{y}_pf": pf})
        era_ok &= bool(n >= 150 and np.isfinite(wr) and wr >= .52 and net > 0 and np.isfinite(exp) and exp > 0 and np.isfinite(pf) and pf >= 1.05)
        years55 += int(np.isfinite(wr) and wr >= .55)
        min_exp = min(min_exp, exp if np.isfinite(exp) else -np.inf)
    row["min_year_exp"] = float(min_exp)
    row["years_wr55"] = years55
    pooled_ok = bool(
        row["campaign_n"] >= 500 and np.isfinite(row["win_rate"]) and row["win_rate"] >= .55 and
        row["net_pnl"] > 0 and np.isfinite(row["expectancy"]) and row["expectancy"] > 0 and
        np.isfinite(row["pf"]) and row["pf"] >= 1.20 and row["max_loss_streak"] <= 10
    )
    row["pooled_gate"] = pooled_ok
    row["era_gate"] = bool(era_ok and years55 >= 2)
    row["robust"] = bool(row["pooled_gate"] and row["era_gate"])
    return row


def decorate_vs_baseline(D: pd.DataFrame):
    B = D[(D.policy == "SEQUENTIAL_ANY") & (D.max_entries == 1)]
    if len(B) != 1:
        raise AssertionError("missing unique E14A k=1 baseline")
    b = B.iloc[0]
    wr_pres, pareto = [], []
    for _, r in D.iterrows():
        wp = bool(np.isfinite(r.win_rate) and r.win_rate >= b.win_rate - 1e-12)
        wr_pres.append(wp)
        floor = bool(
            r.robust and wp and r.net_pnl >= b.net_pnl - 1e-9 and r.expectancy >= b.expectancy - 1e-12 and
            r.pf >= b.pf - 1e-12 and r.max_dd <= b.max_dd + 1e-9 and r.max_loss_streak <= b.max_loss_streak
        )
        improved = bool(
            r.win_rate > b.win_rate + 5e-5 or r.net_pnl > b.net_pnl + .005 or r.expectancy > b.expectancy + .005 or
            r.pf > b.pf + .0005 or r.max_dd < b.max_dd - .005 or r.max_loss_streak < b.max_loss_streak
        )
        pareto.append(bool(floor and improved))
    D = D.copy()
    D["wr_preserving"] = wr_pres
    D["strict_pareto_improver"] = pareto
    return D, b


def rank_candidates(D: pd.DataFrame):
    R = D[D.robust & D.wr_preserving].copy()
    R = R.sort_values(
        ["min_year_exp", "years_wr55", "expectancy", "pf", "win_rate", "max_dd", "max_loss_streak", "net_pnl", "max_entries", "policy"],
        ascending=[False, False, False, False, False, True, True, False, True, True]
    ).reset_index(drop=True)
    R["rank"] = np.arange(1, len(R)+1)
    return R


def main():
    e13c.base.synthetic_tests()
    x5, coverage = e13c.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    T = build_signals(x5)
    if len(T) == 0:
        raise RuntimeError("no E14A source signals")
    T.to_csv(OUT_SIGNALS, index=False)

    rows = []
    ledgers = {}
    tranches = {}
    for k in MAX_ENTRIES:
        for policy in POLICIES:
            C, X = run_architecture(T, policy, k)
            rows.append(architecture_row(C, policy, k))
            ledgers[(policy,k)] = C
            tranches[(policy,k)] = X

    D = pd.DataFrame(rows)
    if len(D) != 12:
        raise AssertionError(f"expected 12 architecture cells, got {len(D)}")
    # k=1 controls must be identical across policies.
    C1 = D[D.max_entries == 1]
    for col in ("campaign_n","win_rate","net_pnl","expectancy","pf","max_dd","max_loss_streak"):
        vals = C1[col].to_numpy(float)
        if np.nanmax(vals) - np.nanmin(vals) > 1e-9:
            raise AssertionError(f"k=1 controls diverged on {col}: {vals}")

    D, B = decorate_vs_baseline(D)
    R = rank_candidates(D)
    D.to_csv(OUT_GRID, index=False)
    R.to_csv(OUT_LEADER, index=False)

    selected = R.iloc[0] if len(R) else None
    if selected is not None:
        key = (selected.policy, int(selected.max_entries))
        ledgers[key].to_csv(OUT_CAMPAIGNS, index=False)
        tranches[key].to_csv(OUT_TRANCHES, index=False)
        X = tranches[key]
        hrs=[]
        for h in range(24):
            H = X[X.source_hour_wib == h] if len(X) else X
            hrs.append({
                "hour_wib":h, "experiment":e13c.MAP[h][0], "formal_status":e13c.MAP[h][1], "rule":e13c.MAP[h][2],
                "accepted_tranches":len(H), "accepted_notional":H.notional.sum() if len(H) else 0.0,
                "net_contribution":H.net_pnl.sum() if len(H) else 0.0,
                "win_tranche_rate":float((H.net_pnl>0).mean()) if len(H) else np.nan,
            })
        pd.DataFrame(hrs).to_csv(OUT_HOURS, index=False)

    lines = [
        "# ETH E14A — 24H Daily Campaign Aggregation Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "All 24 E12 hourly representative LONG characters were temporarily eligible as signal sources. This does not promote E12 FAIL hours.",
        "Campaign window: 23:00 WIB to next 23:00 WIB; maximum total notional $500; fixed daily flat at campaign close.", "",
        "## 12 preregistered architecture cells", "",
        "| Architecture | N | WR | Net | Exp | PF | DD | LS | Avg entries | Util | Entry impr | 2022 WR/Exp | 2023 | 2024 | Robust | WR-preserve | Pareto |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in D.sort_values(["robust","wr_preserving","min_year_exp","expectancy"], ascending=[False,False,False,False]).itertuples(index=False):
        lines.append(
            f"| {r.architecture} | {int(r.campaign_n)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{r.avg_entries:.2f} | {pct(r.avg_capital_utilization)} | {pct(r.avg_entry_improvement_vs_first)} | {pct(r.y2022_wr)}/{money(r.y2022_exp)} | "
            f"{pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | {'YES' if r.robust else 'NO'} | {'YES' if r.wr_preserving else 'NO'} | {'YES' if r.strict_pareto_improver else 'NO'} |"
        )

    lines += ["", "## E14A single-entry daily baseline", "",
              f"**SEQUENTIAL_ANY_K1**: N **{int(B.campaign_n)}**, WR **{pct(B.win_rate)}**, net **{money(B.net_pnl)}**, exp **{money(B.expectancy)}**, PF **{float(B.pf):.3f}**, DD **{money(B.max_dd)}**, LS **{int(B.max_loss_streak)}**.", ""]

    pareto = D[D.strict_pareto_improver].copy()
    lines += ["## Strict Pareto readout", ""]
    if len(pareto):
        for r in pareto.sort_values(["min_year_exp","expectancy","pf"], ascending=[False,False,False]).itertuples(index=False):
            lines.append(f"- **{r.architecture}** — WR {pct(r.win_rate)}, net {money(r.net_pnl)}, exp {money(r.expectancy)}, PF {r.pf:.3f}, DD {money(r.max_dd)}, LS {int(r.max_loss_streak)}, min-year exp {money(r.min_year_exp)}")
    else:
        lines.append("- No multi-entry architecture achieved strict Pareto improvement versus the k=1 daily baseline under the frozen gates.")

    if selected is None:
        status = "ETH_E14A_NO_ROBUST_WR_PRESERVING_ARCHITECTURE"
        lines += ["", "## Verdict", "", f"**{status}**", "", "No architecture passed the frozen ROBUST + WR-preservation selection rules."]
    else:
        s = selected
        status = "ETH_E14A_ROBUST_WR_PRESERVING_ARCHITECTURE_FOUND"
        lines += ["", "## Robustness-ranked WR-preserving winner", "", f"**{s.architecture}**", "",
                  f"N **{int(s.campaign_n)}**, WR **{pct(s.win_rate)}**, net **{money(s.net_pnl)}**, exp **{money(s.expectancy)}**, PF **{float(s.pf):.3f}**, DD **{money(s.max_dd)}**, LS **{int(s.max_loss_streak)}**.",
                  f"Average entries/campaign **{s.avg_entries:.2f}**, average capital utilization **{pct(s.avg_capital_utilization)}**, average entry improvement vs first **{pct(s.avg_entry_improvement_vs_first)}**.",
                  f"Minimum yearly expectancy **{money(s.min_year_exp)}**; years WR>=55% **{int(s.years_wr55)}/3**; strict Pareto vs k=1 baseline: **{'YES' if bool(s.strict_pareto_improver) else 'NO'}**.", "",
                  "### Cross-era", ""]
        for y in YEARS:
            lines.append(f"- {y}: N **{int(s[f'y{y}_n'])}**, WR **{pct(s[f'y{y}_wr'])}**, net **{money(s[f'y{y}_net'])}**, exp **{money(s[f'y{y}_exp'])}**, PF **{float(s[f'y{y}_pf']):.3f}**")
        lines += ["", "### Entries-per-campaign distribution", ""]
        for n in (1,2,3,4):
            lines.append(f"- {n} entries: **{int(s[f'campaigns_{n}_entries'])}** campaigns")
        lines += ["", "### Selected architecture source-hour contribution", "", "| WIB | E12 | Formal | Accepted | Notional | Net contribution | Tranche WR |", "|---:|---|---|---:|---:|---:|---:|"]
        H = pd.read_csv(OUT_HOURS)
        for r in H.itertuples(index=False):
            lines.append(f"| {int(r.hour_wib):02d} | {r.experiment} | {r.formal_status} | {int(r.accepted_tranches)} | {money(r.accepted_notional)} | {money(r.net_contribution)} | {pct(r.win_tranche_rate)} |")
        lines += ["", "## Verdict", "", f"**{status}**"]

    lines += ["", "Research/shadow only. E14A changes the unit to a daily campaign and therefore must not overwrite E12/E13 native-hold conclusions. No OOS exposure and no live authorization."]
    OUT_STATUS.write_text(status + "\n")
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
