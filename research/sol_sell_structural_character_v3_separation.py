#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import math
import numpy as np
import pandas as pd

import sol_reset_winner_first_v1 as wf1
import sol_sell_structural_character_v2_adaptive as v2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SELL_STRUCTURAL_CHARACTER_V3_SEPARATION"

DERIV_YEARS = (2020, 2021, 2022)
CONF_YEARS = (2023, 2024)
FEATURES = (
    "raid_depth_pct",
    "reclaim_delay_h1_bars",
    "bars_reclaim_to_bos",
    "displacement_range_units",
    "bear_path_efficiency",
    "bos_extension_range_units",
    "zone_width_range_units",
    "bos_to_return_min",
    "return_penetration_zone_width",
    "retrace_fraction_of_raid_leg",
    "origin_distance_from_pre_return_low_fraction",
)
QUANTILES = (0.25, 0.50, 0.75)
MIN_DERIV_N = 35
MIN_DERIV_LIFT = 0.08


def wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = successes / n
    den = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    adj = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (center - adj) / den


def rate(g: pd.DataFrame) -> float:
    if g.empty:
        return np.nan
    return float((g.outcome == "CONTINUATION").mean())


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    denom = x.raid_extreme.astype(float) - x.pre_return_structural_low.astype(float)
    valid = denom > 0
    x["retrace_fraction_of_raid_leg"] = np.where(
        valid,
        (x.return_high.astype(float) - x.pre_return_structural_low.astype(float)) / denom,
        np.nan,
    )
    x["origin_distance_from_pre_return_low_fraction"] = np.where(
        valid,
        (x.zone_low.astype(float) - x.pre_return_structural_low.astype(float)) / denom,
        np.nan,
    )
    return x


def atomic_specs(deriv: pd.DataFrame):
    specs = []
    qrows = []
    for f in FEATURES:
        vals = pd.to_numeric(deriv[f], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(vals) < MIN_DERIV_N:
            continue
        for q in QUANTILES:
            thr = float(vals.quantile(q))
            qrows.append({"feature": f, "quantile": q, "threshold": thr})
            for op in ("<=", ">="):
                text = f"{f} {op} {thr:.12g}"
                specs.append({"feature": f, "op": op, "threshold": thr, "text": text})
    return specs, pd.DataFrame(qrows)


def mask_for(df: pd.DataFrame, atom) -> pd.Series:
    x = pd.to_numeric(df[atom["feature"]], errors="coerce")
    if atom["op"] == "<=":
        return x <= float(atom["threshold"])
    return x >= float(atom["threshold"])


def candidate_row(deriv, atoms, baseline):
    mask = pd.Series(True, index=deriv.index)
    for a in atoms:
        mask &= mask_for(deriv, a)
    g = deriv[mask].copy()
    n = len(g)
    if n < MIN_DERIV_N:
        return None
    succ = int((g.outcome == "CONTINUATION").sum())
    r = succ / n
    lift = r - baseline
    if lift < MIN_DERIV_LIFT:
        return None
    rule = " AND ".join(a["text"] for a in atoms)
    return {
        "rule": rule,
        "conditions": len(atoms),
        "n": n,
        "continuation": succ,
        "invalidated": int(n - succ),
        "rate": r,
        "lift": lift,
        "wilson_lower": wilson_lower(succ, n),
        "atom1_feature": atoms[0]["feature"],
        "atom1_op": atoms[0]["op"],
        "atom1_threshold": float(atoms[0]["threshold"]),
        "atom2_feature": atoms[1]["feature"] if len(atoms) == 2 else "",
        "atom2_op": atoms[1]["op"] if len(atoms) == 2 else "",
        "atom2_threshold": float(atoms[1]["threshold"]) if len(atoms) == 2 else np.nan,
    }


def apply_rule(df: pd.DataFrame, row) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    atom1 = {
        "feature": row["atom1_feature"],
        "op": row["atom1_op"],
        "threshold": float(row["atom1_threshold"]),
    }
    m &= mask_for(df, atom1)
    if int(row["conditions"]) == 2:
        atom2 = {
            "feature": row["atom2_feature"],
            "op": row["atom2_op"],
            "threshold": float(row["atom2_threshold"]),
        }
        m &= mask_for(df, atom2)
    return df[m].copy()


def year_stats(df: pd.DataFrame, selected_row):
    rows = []
    for y in CONF_YEARS:
        base = df[df.year == y].copy()
        sel = apply_rule(base, selected_row)
        br = rate(base)
        sr = rate(sel)
        rows.append({
            "year": y,
            "baseline_n": len(base),
            "baseline_rate": br,
            "selected_n": len(sel),
            "selected_rate": sr,
            "lift": sr - br if np.isfinite(sr) and np.isfinite(br) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    _, stage_a, stage_b = v2.detect_h1_family(x5)
    _, stage_d = v2.resolve_return_and_response(stage_b, x5)
    stage_d = derive_features(stage_d)

    resolved = stage_d[stage_d.outcome.isin(["CONTINUATION", "INVALIDATED"])].copy()
    deriv = resolved[resolved.year.isin(DERIV_YEARS)].copy()
    confirm = resolved[resolved.year.isin(CONF_YEARS)].copy()
    if len(deriv) < 80 or len(confirm) < 60:
        raise RuntimeError("insufficient resolved sample for frozen temporal split")

    deriv_baseline = rate(deriv)
    conf_baseline = rate(confirm)

    atoms, thresholds = atomic_specs(deriv)
    candidates = []

    for a in atoms:
        row = candidate_row(deriv, [a], deriv_baseline)
        if row:
            candidates.append(row)

    for a, b in itertools.combinations(atoms, 2):
        if a["feature"] == b["feature"]:
            continue
        row = candidate_row(deriv, [a, b], deriv_baseline)
        if row:
            candidates.append(row)

    cand = pd.DataFrame(candidates)
    if cand.empty:
        raise RuntimeError("no eligible derivation candidate under preregistered support/lift rules")

    cand = cand.sort_values(
        ["wilson_lower", "n", "conditions", "rule"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    selected = cand.iloc[0].to_dict()

    deriv_sel = apply_rule(deriv, selected)
    conf_sel = apply_rule(confirm, selected)
    year = year_stats(confirm, selected)

    conf_rate = rate(conf_sel)
    conf_lift = conf_rate - conf_baseline if np.isfinite(conf_rate) else np.nan

    gates = {
        "confirmation_n_ge_30": len(conf_sel) >= 30,
        "confirmation_rate_ge_45pct": bool(np.isfinite(conf_rate) and conf_rate >= .45),
        "confirmation_lift_ge_8pp": bool(np.isfinite(conf_lift) and conf_lift >= .08),
        "year_2023_above_baseline": bool(
            len(year[year.year == 2023]) and
            np.isfinite(year.loc[year.year == 2023, "selected_rate"].iloc[0]) and
            year.loc[year.year == 2023, "selected_rate"].iloc[0] >
            year.loc[year.year == 2023, "baseline_rate"].iloc[0]
        ),
        "year_2024_above_baseline": bool(
            len(year[year.year == 2024]) and
            np.isfinite(year.loc[year.year == 2024, "selected_rate"].iloc[0]) and
            year.loc[year.year == 2024, "selected_rate"].iloc[0] >
            year.loc[year.year == 2024, "baseline_rate"].iloc[0]
        ),
    }
    verdict = "STRUCTURAL_CHARACTER_CANDIDATE" if all(gates.values()) else "REJECTED_AS_DEFINED"

    selected_summary = pd.DataFrame([{
        "selected_rule": selected["rule"],
        "conditions": int(selected["conditions"]),
        "derivation_baseline_n": len(deriv),
        "derivation_baseline_rate": deriv_baseline,
        "derivation_selected_n": len(deriv_sel),
        "derivation_selected_rate": rate(deriv_sel),
        "derivation_lift": rate(deriv_sel) - deriv_baseline,
        "derivation_wilson_lower": float(selected["wilson_lower"]),
        "confirmation_baseline_n": len(confirm),
        "confirmation_baseline_rate": conf_baseline,
        "confirmation_selected_n": len(conf_sel),
        "confirmation_selected_rate": conf_rate,
        "confirmation_lift": conf_lift,
        **{f"gate_{k}": v for k, v in gates.items()},
        "verdict": verdict,
    }])

    thresholds.to_csv(ROOT / f"{PFX}_Thresholds.csv", index=False)
    cand.to_csv(ROOT / f"{PFX}_EligibleCandidates.csv", index=False)
    deriv_sel.to_csv(ROOT / f"{PFX}_SelectedDerivationCases.csv", index=False)
    conf_sel.to_csv(ROOT / f"{PFX}_SelectedConfirmationCases.csv", index=False)
    year.to_csv(ROOT / f"{PFX}_ConfirmationYearSummary.csv", index=False)
    selected_summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

    def pct(v):
        return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

    lines = [
        "# SOL SELL Structural Character V3 — Winner/Failure Separation Result",
        "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        "- Rule selection: **2020-2022 only**.",
        "- Frozen confirmation: **2023-2024 only**.",
        "- 2025+ remained CLOSED.",
        "- No entry, TP, SL, hour, indicator, or regime filter was used.",
        "",
        "## Selected structural rule",
        "",
        f"**{selected['rule']}**",
        "",
        "## Derivation",
        "",
        f"- Baseline: N={len(deriv)}, continuation={pct(deriv_baseline)}",
        f"- Selected: N={len(deriv_sel)}, continuation={pct(rate(deriv_sel))}",
        f"- Lift: **{(rate(deriv_sel)-deriv_baseline)*100:.2f} pp**",
        f"- Wilson 95% lower bound: **{pct(float(selected['wilson_lower']))}**",
        "",
        "## Frozen confirmation",
        "",
        f"- Baseline: N={len(confirm)}, continuation={pct(conf_baseline)}",
        f"- Selected: N={len(conf_sel)}, continuation={pct(conf_rate)}",
        f"- Lift: **{conf_lift*100:.2f} pp**" if np.isfinite(conf_lift) else "- Lift: n/a",
        "",
        "| Year | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, y in year.iterrows():
        lift = f"{y.lift*100:.2f} pp" if np.isfinite(y.lift) else "n/a"
        lines.append(
            f"| {int(y.year)} | {int(y.baseline_n)} | {pct(y.baseline_rate)} | {int(y.selected_n)} | {pct(y.selected_rate)} | {lift} |"
        )

    lines += ["", "## Frozen gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines += [
        "",
        f"**VERDICT: {verdict}**",
        "",
        "## Interpretation",
        "",
        "This rule describes a structural subtype inside the broader bearish family. It is not an entry rule and it does not specify stop-loss or take-profit placement.",
        "If promoted, the next phase may study adaptive activation/entry only inside this frozen structural cohort. SL and TP remain separate later phases.",
        "",
        "2025_PLUS=CLOSED",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        f"VERDICT={verdict}\nSELECTED_RULE={selected['rule']}\nCONFIRMATION_N={len(conf_sel)}\n2025_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
