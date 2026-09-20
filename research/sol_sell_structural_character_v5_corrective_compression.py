#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import math
import time
import numpy as np
import pandas as pd

import sol_reset_winner_first_v1 as wf1
import sol_sell_structural_character_v2_adaptive as v2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SELL_STRUCTURAL_CHARACTER_V5_CORRECTIVE_COMPRESSION"

DEV_YEARS = (2020, 2021, 2022)
CONF_YEARS = (2023, 2024)

FEATURES = (
    "ascent_bars",
    "up_path_efficiency",
    "median_adjacent_overlap",
    "overlap_gt50_share",
    "range_contraction_ratio",
    "body_contraction_ratio",
    "largest_bull_body_share",
    "sign_flip_rate",
    "higher_low_share",
    "rise_per_bar_range_units",
    "max_bull_body_range_units",
    "pre_return_drawup_fraction",
)
QUANTILES = (0.25, 0.50, 0.75)
MIN_DEV_N = 35
MIN_DEV_LIFT = 0.10


def load5_with_retry(symbol: str):
    base = wf1.v3.v1.base
    original = wf1.v3.v1.fetch_one_with_volume

    def retry_fetch(*args, **kwargs):
        last = None
        for attempt in range(4):
            try:
                return original(*args, **kwargs)
            except Exception as e:
                last = e
                if attempt < 3:
                    time.sleep(2.0 * (attempt + 1))
        raise last

    base.fetch_one = retry_fetch
    return base.load5(symbol)


def wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = successes / n
    den = 1.0 + z*z/n
    center = p + z*z/(2*n)
    adj = z * math.sqrt((p*(1-p) + z*z/(4*n))/n)
    return (center - adj) / den


def resolved_rate(df: pd.DataFrame) -> float:
    if df.empty:
        return np.nan
    return float((df.outcome == "CONTINUATION").mean())


def structural_dedup(stage_d: pd.DataFrame) -> pd.DataFrame:
    x = stage_d.copy()
    x["return_year"] = pd.to_datetime(x.first_return_time, utc=True).dt.year.astype(int)
    x = x.sort_values(
        ["bos_i_h1", "origin_i_h1", "first_return_i_5m", "raid_i_h1", "structure_id"],
        ascending=[True, True, True, True, True],
    )
    return x.drop_duplicates(
        subset=["bos_i_h1", "origin_i_h1", "first_return_i_5m"],
        keep="first",
    ).reset_index(drop=True)


def overlap_ratio(ph, pl, ch, cl):
    pr = ph - pl
    cr = ch - cl
    den = min(pr, cr)
    if not np.isfinite(den) or den <= 0:
        return np.nan
    ov = max(0.0, min(ph, ch) - max(pl, cl))
    return float(np.clip(ov / den, 0.0, 1.0))


def extract_path_features(dedup: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    rows = []

    for _, r in dedup.iterrows():
        start = int(idx.searchsorted(pd.Timestamp(r.bos_close_time)))
        touch = int(r.first_return_i_5m)

        out = r.to_dict()
        out["path_status"] = "USABLE"

        if touch <= start:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        pre = lo[start:touch]
        if len(pre) == 0 or not np.isfinite(pre).any():
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        min_low = float(np.nanmin(pre))
        rel_candidates = np.where(np.isclose(pre, min_low, rtol=0.0, atol=max(1e-12, abs(min_low)*1e-12)))[0]
        if len(rel_candidates) == 0:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        anchor = start + int(rel_candidates[-1])
        n = touch - anchor + 1

        out["path_anchor_i_5m"] = anchor
        out["path_anchor_time"] = idx[anchor]
        out["path_anchor_low"] = float(lo[anchor])
        out["ascent_bars"] = int(n)

        if n < 4:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        pop = op[anchor:touch+1]
        phi = hi[anchor:touch+1]
        plo = lo[anchor:touch+1]
        pcl = cl[anchor:touch+1]

        ranges = phi - plo
        bodies = np.abs(pcl - pop)
        med_range = float(np.nanmedian(ranges))
        net = float(pcl[-1] - pcl[0])
        diffs = np.diff(pcl)
        path = float(np.nansum(np.abs(diffs)))
        efficiency = net / path if path > 0 else np.nan

        ovs = []
        for j in range(1, n):
            ovs.append(overlap_ratio(phi[j-1], plo[j-1], phi[j], plo[j]))
        ovs = np.array(ovs, dtype=float)
        valid_ovs = ovs[np.isfinite(ovs)]

        third = max(1, n // 3)
        first_ranges = ranges[:third]
        last_ranges = ranges[-third:]
        first_bodies = bodies[:third]
        last_bodies = bodies[-third:]

        first_r = float(np.nanmedian(first_ranges))
        last_r = float(np.nanmedian(last_ranges))
        first_b = float(np.nanmedian(first_bodies))
        last_b = float(np.nanmedian(last_bodies))

        bull_bodies = np.maximum(pcl - pop, 0.0)
        bull_sum = float(np.nansum(bull_bodies))
        max_bull = float(np.nanmax(bull_bodies)) if len(bull_bodies) else np.nan

        nz = diffs[np.abs(diffs) > 1e-12]
        if len(nz) >= 2:
            flips = np.sign(nz[1:]) != np.sign(nz[:-1])
            sign_flip = float(np.mean(flips))
        else:
            sign_flip = np.nan

        higher_low_share = float(np.mean(plo[1:] > plo[:-1])) if n >= 2 else np.nan

        denom_drawup = float(r.zone_low) - float(lo[anchor])
        drawup = (
            (float(hi[touch]) - float(lo[anchor])) / denom_drawup
            if denom_drawup > 0 else np.nan
        )

        out.update({
            "up_path_efficiency": float(efficiency) if np.isfinite(efficiency) else np.nan,
            "median_adjacent_overlap": float(np.nanmedian(valid_ovs)) if len(valid_ovs) else np.nan,
            "overlap_gt50_share": float(np.mean(valid_ovs >= 0.50)) if len(valid_ovs) else np.nan,
            "range_contraction_ratio": float(last_r / first_r) if first_r > 0 else np.nan,
            "body_contraction_ratio": float(last_b / first_b) if first_b > 0 else np.nan,
            "largest_bull_body_share": float(max_bull / bull_sum) if bull_sum > 0 else np.nan,
            "sign_flip_rate": sign_flip,
            "higher_low_share": higher_low_share,
            "rise_per_bar_range_units": float(net / ((n - 1) * med_range)) if n > 1 and med_range > 0 else np.nan,
            "max_bull_body_range_units": float(max_bull / med_range) if med_range > 0 else np.nan,
            "pre_return_drawup_fraction": float(drawup) if np.isfinite(drawup) else np.nan,
        })
        rows.append(out)

    return pd.DataFrame(rows)


def feature_summary(usable: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for outcome, g in usable.groupby("outcome"):
        row = {"outcome": outcome, "n": int(len(g))}
        for f in FEATURES:
            s = pd.to_numeric(g[f], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            row[f+"_median"] = float(s.median()) if len(s) else np.nan
            row[f+"_p25"] = float(s.quantile(.25)) if len(s) else np.nan
            row[f+"_p75"] = float(s.quantile(.75)) if len(s) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def atomic_specs(dev: pd.DataFrame):
    specs = []
    qrows = []
    for f in FEATURES:
        s = pd.to_numeric(dev[f], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) < MIN_DEV_N:
            continue
        for q in QUANTILES:
            thr = float(s.quantile(q))
            qrows.append({"feature": f, "quantile": q, "threshold": thr})
            for opx in ("<=", ">="):
                specs.append({
                    "feature": f,
                    "op": opx,
                    "threshold": thr,
                    "text": f"{f} {opx} {thr:.12g}",
                })
    return specs, pd.DataFrame(qrows)


def atom_mask(df: pd.DataFrame, a) -> pd.Series:
    s = pd.to_numeric(df[a["feature"]], errors="coerce")
    if a["op"] == "<=":
        return s <= float(a["threshold"])
    return s >= float(a["threshold"])


def candidate_row(dev: pd.DataFrame, atoms, baseline: float):
    m = pd.Series(True, index=dev.index)
    for a in atoms:
        m &= atom_mask(dev, a)
    g = dev[m].copy()
    n = len(g)
    if n < MIN_DEV_N:
        return None
    succ = int((g.outcome == "CONTINUATION").sum())
    r = succ / n
    lift = r - baseline
    if lift < MIN_DEV_LIFT:
        return None
    out = {
        "rule": " AND ".join(a["text"] for a in atoms),
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
        "atom2_feature": "",
        "atom2_op": "",
        "atom2_threshold": np.nan,
    }
    if len(atoms) == 2:
        out.update({
            "atom2_feature": atoms[1]["feature"],
            "atom2_op": atoms[1]["op"],
            "atom2_threshold": float(atoms[1]["threshold"]),
        })
    return out


def apply_rule(df: pd.DataFrame, row) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    a1 = {
        "feature": row["atom1_feature"],
        "op": row["atom1_op"],
        "threshold": float(row["atom1_threshold"]),
    }
    m &= atom_mask(df, a1)
    if int(row["conditions"]) == 2:
        a2 = {
            "feature": row["atom2_feature"],
            "op": row["atom2_op"],
            "threshold": float(row["atom2_threshold"]),
        }
        m &= atom_mask(df, a2)
    return df[m].copy()


def yearly_confirmation(confirm: pd.DataFrame, selected) -> pd.DataFrame:
    rows = []
    for y in CONF_YEARS:
        base = confirm[confirm.return_year == y].copy()
        sel = apply_rule(base, selected)
        br = resolved_rate(base)
        sr = resolved_rate(sel)
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
    x5, coverage = load5_with_retry("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    _, _, stage_b = v2.detect_h1_family(x5)
    _, stage_d = v2.resolve_return_and_response(stage_b, x5)

    dedup = structural_dedup(stage_d)
    features = extract_path_features(dedup, x5)

    binary = features[features.outcome.isin(["CONTINUATION", "INVALIDATED"])].copy()
    usable = binary[features.loc[binary.index, "path_status"] == "USABLE"].copy()

    # Require complete values only when a rule references them; baseline includes all usable paths.
    dev = usable[usable.return_year.isin(DEV_YEARS)].copy()
    confirm = usable[usable.return_year.isin(CONF_YEARS)].copy()

    if len(dev) < 80 or len(confirm) < 60:
        raise RuntimeError(
            f"insufficient usable temporal samples: dev={len(dev)} confirm={len(confirm)}"
        )

    dev_base = resolved_rate(dev)
    conf_base = resolved_rate(confirm)

    atoms, thresholds = atomic_specs(dev)
    candidates = []

    for a in atoms:
        z = candidate_row(dev, [a], dev_base)
        if z is not None:
            candidates.append(z)

    for a, b in itertools.combinations(atoms, 2):
        if a["feature"] == b["feature"]:
            continue
        z = candidate_row(dev, [a, b], dev_base)
        if z is not None:
            candidates.append(z)

    cand = pd.DataFrame(candidates)
    feat_sum = feature_summary(usable)

    # Persist common outputs before verdict handling.
    dedup.to_csv(ROOT / f"{PFX}_DedupResponses.csv", index=False)
    features.to_csv(ROOT / f"{PFX}_PathFeatures.csv", index=False)
    features[features.path_status != "USABLE"].to_csv(
        ROOT / f"{PFX}_TooShortPaths.csv", index=False
    )
    feat_sum.to_csv(ROOT / f"{PFX}_FeatureSummary.csv", index=False)
    thresholds.to_csv(ROOT / f"{PFX}_Thresholds.csv", index=False)

    def pct(v):
        return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

    if cand.empty:
        pd.DataFrame().to_csv(ROOT / f"{PFX}_EligibleCandidates.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_SelectedDerivationCases.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_SelectedConfirmationCases.csv", index=False)
        pd.DataFrame().to_csv(ROOT / f"{PFX}_ConfirmationYearSummary.csv", index=False)

        verdict = "NO_ELIGIBLE_DERIVATION_RULE"
        summary = pd.DataFrame([{
            "coverage": coverage,
            "raw_v2_responses": len(stage_d),
            "dedup_responses": len(dedup),
            "usable_binary_paths": len(usable),
            "development_n": len(dev),
            "development_baseline_rate": dev_base,
            "confirmation_n": len(confirm),
            "confirmation_baseline_rate": conf_base,
            "eligible_candidates": 0,
            "verdict": verdict,
        }])
        summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

        lines = [
            "# SOL SELL Structural Character V5 — Corrective Compression Result",
            "",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Raw V2 response rows: **{len(stage_d)}**",
            f"- Deduplicated structural paths: **{len(dedup)}**",
            f"- Usable resolved retracement paths: **{len(usable)}**",
            "- 2020-2022 derivation; 2023-2024 frozen confirmation; 2025+ CLOSED.",
            "- No entry, TP, SL, session, indicator, or execution optimization.",
            "",
            "## Derivation",
            "",
            f"- N={len(dev)}",
            f"- Baseline continuation={pct(dev_base)}",
            "- No one- or two-feature quantile rule met the preregistered minimum N and +10pp lift requirement.",
            "",
            f"**VERDICT: {verdict}**",
            "",
            "This means the frozen corrective/compression feature family did not produce an eligible structural subtype on derivation data. No confirmation rule was selected and no threshold was rescued.",
            "",
            "2025_PLUS=CLOSED",
        ]
    else:
        cand = cand.sort_values(
            ["wilson_lower", "n", "conditions", "rule"],
            ascending=[False, False, True, True],
        ).reset_index(drop=True)
        cand.to_csv(ROOT / f"{PFX}_EligibleCandidates.csv", index=False)

        selected = cand.iloc[0].to_dict()
        dev_sel = apply_rule(dev, selected)
        conf_sel = apply_rule(confirm, selected)
        year = yearly_confirmation(confirm, selected)

        dev_rate = resolved_rate(dev_sel)
        conf_rate = resolved_rate(conf_sel)
        conf_lift = conf_rate - conf_base if np.isfinite(conf_rate) else np.nan

        y23 = year[year.year == 2023].iloc[0]
        y24 = year[year.year == 2024].iloc[0]

        gates = {
            "confirmation_n_ge_30": len(conf_sel) >= 30,
            "confirmation_rate_ge_45pct": bool(np.isfinite(conf_rate) and conf_rate >= .45),
            "confirmation_lift_ge_10pp": bool(np.isfinite(conf_lift) and conf_lift >= .10),
            "year_2023_above_baseline": bool(
                np.isfinite(y23.selected_rate) and y23.selected_rate > y23.baseline_rate
            ),
            "year_2024_above_baseline": bool(
                np.isfinite(y24.selected_rate) and y24.selected_rate > y24.baseline_rate
            ),
        }
        verdict = (
            "CORRECTIVE_COMPRESSION_CHARACTER"
            if all(gates.values())
            else "REJECTED_AS_DEFINED"
        )

        dev_sel.to_csv(ROOT / f"{PFX}_SelectedDerivationCases.csv", index=False)
        conf_sel.to_csv(ROOT / f"{PFX}_SelectedConfirmationCases.csv", index=False)
        year.to_csv(ROOT / f"{PFX}_ConfirmationYearSummary.csv", index=False)

        summary = pd.DataFrame([{
            "coverage": coverage,
            "raw_v2_responses": len(stage_d),
            "dedup_responses": len(dedup),
            "usable_binary_paths": len(usable),
            "development_n": len(dev),
            "development_baseline_rate": dev_base,
            "development_selected_n": len(dev_sel),
            "development_selected_rate": dev_rate,
            "development_lift": dev_rate - dev_base,
            "development_wilson_lower": float(selected["wilson_lower"]),
            "confirmation_n": len(confirm),
            "confirmation_baseline_rate": conf_base,
            "confirmation_selected_n": len(conf_sel),
            "confirmation_selected_rate": conf_rate,
            "confirmation_lift": conf_lift,
            "eligible_candidates": len(cand),
            **{f"gate_{k}": v for k, v in gates.items()},
            "selected_rule": selected["rule"],
            "verdict": verdict,
        }])
        summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

        lines = [
            "# SOL SELL Structural Character V5 — Corrective Compression Result",
            "",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Raw V2 response rows: **{len(stage_d)}**",
            f"- Deduplicated structural paths: **{len(dedup)}**",
            f"- Usable resolved retracement paths: **{len(usable)}**",
            "- 2020-2022 derivation; 2023-2024 frozen confirmation; 2025+ CLOSED.",
            "- No entry, TP, SL, session, indicator, or execution optimization.",
            "",
            "## Selected corrective/compression rule",
            "",
            f"**{selected['rule']}**",
            "",
            "## Derivation — 2020-2022",
            "",
            f"- Baseline: N={len(dev)}, continuation={pct(dev_base)}",
            f"- Selected: N={len(dev_sel)}, continuation={pct(dev_rate)}",
            f"- Lift: **{(dev_rate-dev_base)*100:.2f} pp**",
            f"- Wilson 95% lower bound: **{pct(float(selected['wilson_lower']))}**",
            "",
            "## Frozen confirmation — 2023-2024",
            "",
            f"- Baseline: N={len(confirm)}, continuation={pct(conf_base)}",
            f"- Selected: N={len(conf_sel)}, continuation={pct(conf_rate)}",
            f"- Lift: **{conf_lift*100:.2f} pp**" if np.isfinite(conf_lift) else "- Lift: n/a",
            "",
            "| Year | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        for _, y in year.iterrows():
            lift = f"{y.lift*100:.2f} pp" if np.isfinite(y.lift) else "n/a"
            lines.append(
                f"| {int(y.year)} | {int(y.baseline_n)} | {pct(y.baseline_rate)} | "
                f"{int(y.selected_n)} | {pct(y.selected_rate)} | {lift} |"
            )

        lines += ["", "## Frozen gate audit", ""]
        for k, v in gates.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        lines += [
            "",
            f"**VERDICT: {verdict}**",
            "",
            "This result concerns only the anatomy of the retracement path into the bearish block. It does not define entry, stop-loss, take-profit, or trade horizon.",
            "",
            "2025_PLUS=CLOSED",
        ]

    result_text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(result_text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        f"VERDICT={verdict}\n2025_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(result_text)


if __name__ == "__main__":
    main()
