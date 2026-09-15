#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_v5_batch2f_structural_grammar as b2f

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2G_GRAMMAR_REGIME_ANALOG"
TEST_YEARS = b2f.TEST_YEARS
ROUNDTRIP_COST_PCT = b2f.ROUNDTRIP_COST_PCT
NOTIONAL = b2f.NOTIONAL
K_NEIGHBORS = 30
MIN_GRAMMAR_SUPPORT = 30

CONTEXT_COLS = [
    "ret_60_sigma",
    "eff_60",
    "compression_range_30_120",
    "compression_rv_30_120",
    "close_pos_120",
    "state_margin",
]


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    return math.inf if neg <= 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def econ(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n": 0, "wr": np.nan, "exp": np.nan, "pf": np.nan, "pnl": 0.0,
                "dd": np.nan, "ls": 0, "up": np.nan}
    r = g.net60_pct.astype(float)
    pnl = g.pnl60_usd.astype(float)
    return {
        "n": int(len(g)),
        "wr": float((r > 0).mean()),
        "exp": float(r.mean()),
        "pf": float(profit_factor(pnl)),
        "pnl": float(pnl.sum()),
        "dd": float(max_drawdown(pnl)),
        "ls": int(max_loss_streak(pnl)),
        "up": float(g.target_up_first.astype(float).mean()),
    }


def fmt(v, d=3) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def add_context(ep: pd.DataFrame) -> pd.DataFrame:
    q = ep.copy()
    sigma = q.sigma60_pct.astype(float)
    q["ret_60_sigma"] = q.ret_60.astype(float) / sigma
    miss = [c for c in CONTEXT_COLS if c not in q.columns]
    if miss:
        raise RuntimeError(f"missing context columns: {miss}")
    vals = q[CONTEXT_COLS].astype(float).to_numpy()
    if not np.isfinite(vals).all():
        raise RuntimeError("non-finite Batch 2G context")
    return q


def robust_params(tr: pd.DataFrame):
    a = tr[CONTEXT_COLS].astype(float)
    med = a.median(axis=0).to_numpy(dtype=float)
    q25 = a.quantile(.25, axis=0).to_numpy(dtype=float)
    q75 = a.quantile(.75, axis=0).to_numpy(dtype=float)
    scale = q75 - q25
    scale[~np.isfinite(scale) | (np.abs(scale) < 1e-12)] = 1.0
    return med, scale


def walk_forward(ep: pd.DataFrame):
    assigns = []
    dictionaries = []
    neighbor_rows = []

    for y in TEST_YEARS:
        train_years = b2f.b2d.b2.train_years_for(y)
        tr = ep[ep.test_year.isin(train_years)].copy().reset_index(drop=True)
        te = ep[ep.test_year == y].copy().reset_index(drop=True)
        if tr.empty or te.empty:
            raise RuntimeError(f"bad split {y}")

        stats = b2f.train_motif_stats(tr, y).reset_index(drop=True)
        dictionaries.append(stats)
        stat_map = stats.set_index("grammar")
        eligible = set(stats.loc[stats.eligible, "grammar"].astype(str))

        med, scale = robust_params(tr)
        xtr = (tr[CONTEXT_COLS].astype(float).to_numpy() - med) / scale
        xte = (te[CONTEXT_COLS].astype(float).to_numpy() - med) / scale
        tr_grammar = tr.grammar.astype(str).to_numpy()

        te["grammar_eligible"] = te.grammar.astype(str).isin(eligible)
        te["analog_available"] = False
        te["analog_k"] = 0
        te["analog_edge_pct"] = np.nan
        te["analog_up_first"] = np.nan
        te["analog_pf60"] = np.nan
        te["analog_mean_distance"] = np.nan
        te["analog_median_distance"] = np.nan
        te["train_grammar_n"] = 0
        te["train_grammar_edge_pct"] = np.nan
        te["train_grammar_up_first"] = np.nan
        te["selected_long"] = False

        for i in range(len(te)):
            gr = str(te.at[i, "grammar"])
            if gr not in eligible or gr not in stat_map.index:
                continue
            pool = np.flatnonzero(tr_grammar == gr)
            if len(pool) < MIN_GRAMMAR_SUPPORT:
                continue

            st = stat_map.loc[gr]
            # One exact row per grammar in a fold; defensive handling if pandas returns a frame.
            if isinstance(st, pd.DataFrame):
                st = st.iloc[0]
            grammar_n = int(st.train_n)
            grammar_edge = float(st.train_edge_pct)
            grammar_up = float(st.train_up_first)

            d = np.linalg.norm(xtr[pool] - xte[i], axis=1)
            k = min(K_NEIGHBORS, len(pool))
            order = np.argsort(d, kind="stable")[:k]
            nbr_idx = pool[order]
            nbr = tr.iloc[nbr_idx]
            local_edge = float(nbr.net60_pct.astype(float).mean())
            local_up = float(nbr.target_up_first.astype(float).mean())
            local_pf = float(profit_factor(nbr.pnl60_usd.astype(float)))
            md = float(np.mean(d[order]))
            med_d = float(np.median(d[order]))
            selected = bool(local_edge > 0.0 and local_up > grammar_up)

            te.at[i, "analog_available"] = True
            te.at[i, "analog_k"] = k
            te.at[i, "analog_edge_pct"] = local_edge
            te.at[i, "analog_up_first"] = local_up
            te.at[i, "analog_pf60"] = local_pf
            te.at[i, "analog_mean_distance"] = md
            te.at[i, "analog_median_distance"] = med_d
            te.at[i, "train_grammar_n"] = grammar_n
            te.at[i, "train_grammar_edge_pct"] = grammar_edge
            te.at[i, "train_grammar_up_first"] = grammar_up
            te.at[i, "selected_long"] = selected

            neighbor_rows.append({
                "test_year": y,
                "entry_time": te.at[i, "entry_time"],
                "grammar": gr,
                "selected_long": selected,
                "train_grammar_n": grammar_n,
                "train_grammar_edge_pct": grammar_edge,
                "train_grammar_up_first": grammar_up,
                "analog_k": k,
                "analog_edge_pct": local_edge,
                "analog_up_first": local_up,
                "analog_pf60": local_pf,
                "analog_mean_distance": md,
                "analog_median_distance": med_d,
            })

        assigns.append(te)

    return (
        pd.concat(assigns, ignore_index=True).sort_values("entry_time").reset_index(drop=True),
        pd.concat(dictionaries, ignore_index=True),
        pd.DataFrame(neighbor_rows),
    )


def comparison_rows(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [
        ("ALL_HIGH_STATE", pred),
        ("GRAMMAR_ONLY", pred[pred.grammar_eligible]),
        ("GRAMMAR_REGIME", pred[pred.selected_long]),
    ]
    for scope, g in scopes:
        e = econ(g)
        rows.append({"scope": scope, **e})
    return pd.DataFrame(rows)


def yearly_rows(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        base = pred[pred.test_year == y]
        grammar = base[base.grammar_eligible]
        regime = base[base.selected_long]
        be, ge, re = econ(base), econ(grammar), econ(regime)
        rows.append({
            "test_year": y,
            "all_n": be["n"], "all_up": be["up"], "all_exp": be["exp"], "all_pf": be["pf"],
            "grammar_n": ge["n"], "grammar_up": ge["up"], "grammar_exp": ge["exp"], "grammar_pf": ge["pf"], "grammar_pnl": ge["pnl"],
            "regime_n": re["n"], "regime_up": re["up"], "regime_lift_vs_all": (re["up"] / be["up"] if re["n"] and be["up"] > 0 else np.nan),
            "regime_wr": re["wr"], "regime_exp": re["exp"], "regime_pf": re["pf"], "regime_pnl": re["pnl"],
            "regime_dd": re["dd"], "regime_ls": re["ls"],
        })
    return pd.DataFrame(rows)


def grammar_transfer(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (y, gr), g in pred.groupby(["test_year", "grammar"]):
        go = g[g.grammar_eligible]
        rg = g[g.selected_long]
        if go.empty and rg.empty:
            continue
        ge, re = econ(go), econ(rg)
        rows.append({
            "test_year": int(y), "grammar": str(gr),
            "test_n": int(len(g)), "grammar_eligible": bool(g.grammar_eligible.any()),
            "grammar_only_n": ge["n"], "grammar_only_up": ge["up"], "grammar_only_exp": ge["exp"], "grammar_only_pf": ge["pf"],
            "regime_n": re["n"], "regime_up": re["up"], "regime_exp": re["exp"], "regime_pf": re["pf"], "regime_pnl": re["pnl"],
            "mean_analog_edge_pct": float(rg.analog_edge_pct.mean()) if len(rg) else np.nan,
            "mean_analog_up_first": float(rg.analog_up_first.mean()) if len(rg) else np.nan,
            "mean_analog_distance": float(rg.analog_mean_distance.mean()) if len(rg) else np.nan,
        })
    return pd.DataFrame(rows).sort_values(["test_year", "regime_n"], ascending=[True, False])


def main():
    b2f.b2d.b2.b1.v4.v3.v1.base.fetch_one = b2f.b2d.b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2f.b2d.b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ep = add_context(b2f.build_episodes(x5))
    pred, dictionary, neighbors = walk_forward(ep)
    comp = comparison_rows(pred)
    yr = yearly_rows(pred)
    transfer = grammar_transfer(pred)
    selected = pred[pred.selected_long].copy().sort_values("entry_time").reset_index(drop=True)

    all_e = econ(pred)
    grammar_e = econ(pred[pred.grammar_eligible])
    regime_e = econ(selected)
    lift = regime_e["up"] / all_e["up"] if regime_e["n"] and all_e["up"] > 0 else np.nan
    positive_years = int((yr.regime_pnl > 0).sum())
    y2024 = yr[yr.test_year == 2024].iloc[0]

    gates = {
        "regime_selected_n_ge_100": regime_e["n"] >= 100,
        "regime_up_first_lift_ge_1_20x": bool(np.isfinite(lift) and lift >= 1.20),
        "regime_expectancy_positive": bool(np.isfinite(regime_e["exp"]) and regime_e["exp"] > 0),
        "regime_pf_ge_1_10": bool(np.isfinite(regime_e["pf"]) and regime_e["pf"] >= 1.10),
        "positive_regime_pnl_years_ge_2_of_3": positive_years >= 2,
        "regime_expectancy_beats_grammar_only": bool(np.isfinite(regime_e["exp"]) and np.isfinite(grammar_e["exp"]) and regime_e["exp"] > grammar_e["exp"]),
        "year_2024_regime_n_ge_30_and_expectancy_positive": bool(int(y2024.regime_n) >= 30 and np.isfinite(y2024.regime_exp) and float(y2024.regime_exp) > 0),
    }
    verdict = "READY_FOR_BATCH3_RISK_ENVELOPE" if all(gates.values()) else "GRAMMAR_REGIME_ANALOG_NOT_READY"

    pred.to_csv(ROOT / f"{PFX}_Assignments.csv", index=False)
    dictionary.to_csv(ROOT / f"{PFX}_TrainingGrammarDictionary.csv", index=False)
    neighbors.to_csv(ROOT / f"{PFX}_AnalogAudit.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedTrades.csv", index=False)
    comp.to_csv(ROOT / f"{PFX}_PooledComparison.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    transfer.to_csv(ROOT / f"{PFX}_GrammarTransfer.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 2G — Grammar-Conditioned Causal Regime Analog Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- OOS HIGH_STATE episodes 2022-2024: **{len(pred)}**",
        f"- Batch-2F grammar-only trades: **{int(pred.grammar_eligible.sum())}**",
        f"- Regime-filtered LONG trades: **{regime_e['n']}**",
        f"- Same-grammar analog K: **{K_NEIGHBORS}**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Pooled comparison", "",
        "| Scope | N | UP_FIRST | WR60 | Exp60 | PF60 | PnL | Max DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in comp.iterrows():
        lines.append(
            f"| {r.scope} | {int(r.n)} | {float(r.up)*100:.2f}% | {float(r.wr)*100:.2f}% | {fmt(r.exp,4)}% | {fmt(r.pf)} | ${float(r.pnl):.2f} | ${fmt(r.dd,2)} | {int(r.ls)} |"
            if int(r.n) > 0 else f"| {r.scope} | 0 | n/a | n/a | n/a | n/a | $0.00 | n/a | 0 |"
        )
    lines += ["", f"- Regime UP_FIRST lift vs ALL HIGH_STATE: **{fmt(lift)}x**", "", "## Year stability", "",
              "| Year | All N | Grammar N | Grammar Exp | Regime N | Regime UP | Lift | Regime WR | Regime Exp | PF | PnL |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.all_n)} | {int(r.grammar_n)} | {fmt(r.grammar_exp,4)}% | {int(r.regime_n)} | {float(r.regime_up)*100:.2f}% | {fmt(r.regime_lift_vs_all)}x | {float(r.regime_wr)*100:.2f}% | {fmt(r.regime_exp,4)}% | {fmt(r.regime_pf)} | ${float(r.regime_pnl):.2f} |"
            if int(r.regime_n) > 0 else f"| {int(r.test_year)} | {int(r.all_n)} | {int(r.grammar_n)} | {fmt(r.grammar_exp,4)}% | 0 | n/a | n/a | n/a | n/a | n/a | $0.00 |"
        )

    lines += ["", "## Grammar transfer after regime filter", ""]
    for _, r in transfer.iterrows():
        if int(r.regime_n) <= 0:
            continue
        lines.append(
            f"- {int(r.test_year)} `{r.grammar}` — grammar-only N{int(r.grammar_only_n)} exp {fmt(r.grammar_only_exp,4)}% PF {fmt(r.grammar_only_pf)} → regime N{int(r.regime_n)} exp {fmt(r.regime_exp,4)}% UP {float(r.regime_up)*100:.2f}% PF {fmt(r.regime_pf)}"
        )

    u = transfer[transfer.grammar == "U-U-U-U"]
    lines += ["", "## `U-U-U-U` focus", ""]
    if u.empty:
        lines.append("- No eligible OOS `U-U-U-U` rows.")
    else:
        for _, r in u.iterrows():
            lines.append(
                f"- {int(r.test_year)}: grammar-only N{int(r.grammar_only_n)} exp {fmt(r.grammar_only_exp,4)}% → regime N{int(r.regime_n)} exp {fmt(r.regime_exp,4)}% PF {fmt(r.regime_pf)}"
            )

    lines += ["", "## Batch 2G gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", f"# BATCH 2G VERDICT: {verdict}", "",
              "READY_FOR_BATCH3_RISK_ENVELOPE means causal within-grammar regime analogs repair the grammar instability with positive pre-exit-optimization OOS economics, including 2024.",
              "GRAMMAR_REGIME_ANALOG_NOT_READY means do not rescue this architecture by sweeping K, context features, distance metric, scaling, grammar definitions, hours, horizon, TP, or SL on 2022-2024."]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
