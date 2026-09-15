#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

import bnb_b29_b1j_journey_sweep_character as b1j

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B2_ENTRY_DISCOVERY"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_POLICIES = ROOT / f"{PFX}_PolicyMetrics.csv"
OUT_SELECTED = ROOT / f"{PFX}_SelectedPolicies.csv"
OUT_REF = ROOT / f"{PFX}_ReferenceValidation.csv"
OUT_FILLS = ROOT / f"{PFX}_Fills.csv.gz"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

STEP = pd.Timedelta(minutes=15)
DEV_YEARS = [2022, 2023, 2024]
REF_YEARS = [2025, 2026]
ALL_YEARS = DEV_YEARS + REF_YEARS

POLICIES = [
    "E0_EVENT_CLOSE",
    "E15_ANY",
    "E15_UP",
    "E15_PULLBACK",
    "E15_HOLD",
    "E15_UP_HOLD",
    "E15_PULLBACK_HOLD",
    "E30_TWO_UP",
    "E30_PULLBACK_RECOVER",
    "E30_HOLD",
]
ENTRY_DELAY = {
    "E0_EVENT_CLOSE": 0,
    "E15_ANY": 15,
    "E15_UP": 15,
    "E15_PULLBACK": 15,
    "E15_HOLD": 15,
    "E15_UP_HOLD": 15,
    "E15_PULLBACK_HOLD": 15,
    "E30_TWO_UP": 30,
    "E30_PULLBACK_RECOVER": 30,
    "E30_HOLD": 30,
}


def compound_return(fp: pd.DataFrame, event_index: pd.DatetimeIndex, start_min: int, end_min: int) -> pd.Series:
    """Return from close at event+start_min to close at event+end_min, exact-grid only."""
    if end_min <= start_min or start_min % 15 or end_min % 15:
        raise ValueError("invalid compound window")
    r = pd.to_numeric(fp["ret_15"], errors="coerce").astype(float)
    growth = pd.Series(1.0, index=event_index, dtype=float)
    valid = pd.Series(True, index=event_index, dtype=bool)
    for m in range(start_min + 15, end_min + 1, 15):
        z = r.reindex(event_index + pd.Timedelta(minutes=m))
        z.index = event_index
        valid &= z.notna()
        growth *= 1.0 + z.fillna(0.0)
    return (growth - 1.0).where(valid)


def frozen_character_events(fp: pd.DataFrame) -> pd.DataFrame:
    beh = b1j.build_forward(fp)
    E = b1j.build_events(fp, beh)
    E = E[
        E["pre_path_state"].eq("CONT_DOWN") &
        E["reclaim_strength"].eq("HIGH") &
        E["reclaim_body"].eq("LOW")
    ].copy()
    E = E[E["year"].isin(ALL_YEARS)].sort_index()
    return E


def future_rows(fp: pd.DataFrame, idx: pd.DatetimeIndex, minutes: int) -> pd.DataFrame:
    z = fp.reindex(idx + pd.Timedelta(minutes=minutes)).copy()
    z.index = idx
    return z


def policy_masks(fp: pd.DataFrame, events: pd.DataFrame) -> dict[str, pd.Series]:
    idx = pd.DatetimeIndex(events.index)
    t15 = future_rows(fp, idx, 15)
    t30 = future_rows(fp, idx, 30)

    r15a = pd.to_numeric(t15["ret_15"], errors="coerce")
    r15b = pd.to_numeric(t30["ret_15"], errors="coerce")
    b15 = pd.to_numeric(t15["break_low_60"], errors="coerce")
    b30 = pd.to_numeric(t30["break_low_60"], errors="coerce")

    avail15 = r15a.notna() & b15.notna()
    avail30 = avail15 & r15b.notna() & b30.notna()

    masks = {
        "E0_EVENT_CLOSE": pd.Series(True, index=idx),
        "E15_ANY": avail15,
        "E15_UP": avail15 & r15a.gt(0.0),
        "E15_PULLBACK": avail15 & r15a.le(0.0),
        "E15_HOLD": avail15 & b15.eq(0.0),
        "E15_UP_HOLD": avail15 & r15a.gt(0.0) & b15.eq(0.0),
        "E15_PULLBACK_HOLD": avail15 & r15a.le(0.0) & b15.eq(0.0),
        "E30_TWO_UP": avail30 & r15a.gt(0.0) & r15b.gt(0.0),
        "E30_PULLBACK_RECOVER": avail30 & r15a.le(0.0) & r15b.gt(0.0),
        "E30_HOLD": avail30 & b15.eq(0.0) & b30.eq(0.0),
    }
    return {k: v.astype(bool) for k, v in masks.items()}


def build_fills(fp: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    idx = pd.DatetimeIndex(events.index)
    masks = policy_masks(fp, events)
    rows = []
    for policy in POLICIES:
        d = ENTRY_DELAY[policy]
        primary = compound_return(fp, idx, d, 60)
        anchor120 = compound_return(fp, idx, d, 120)
        entry60 = compound_return(fp, idx, d, d + 60)
        valid = masks[policy] & primary.notna() & anchor120.notna() & entry60.notna()
        for ts in idx[valid.to_numpy()]:
            rows.append({
                "event_ts": ts,
                "year": int(ts.year),
                "policy": policy,
                "entry_delay_min": d,
                "primary_ret": float(primary.loc[ts]),
                "primary_hit": bool(primary.loc[ts] > 0.0),
                "anchor120_ret": float(anchor120.loc[ts]),
                "anchor120_hit": bool(anchor120.loc[ts] > 0.0),
                "entry60_ret": float(entry60.loc[ts]),
                "entry60_hit": bool(entry60.loc[ts] > 0.0),
            })
    return pd.DataFrame(rows).sort_values(["policy", "event_ts"]).reset_index(drop=True)


def bh_adjust(pvals: np.ndarray) -> np.ndarray:
    m = len(pvals)
    order = np.argsort(pvals)
    ps = pvals[order]
    adj_sorted = np.minimum.accumulate((ps * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m, dtype=float)
    out[order] = np.minimum(adj_sorted, 1.0)
    return out


def dev_metrics(events: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    dev_events = events[events["year"].isin(DEV_YEARS)]
    denom = {y: int((dev_events["year"] == y).sum()) for y in DEV_YEARS}
    denom_total = len(dev_events)
    rows = []
    for policy in POLICIES:
        g = fills[(fills.policy == policy) & fills.year.isin(DEV_YEARS)].copy()
        ns = {y: int((g.year == y).sum()) for y in DEV_YEARS}
        hits = int(g.primary_hit.sum())
        n = len(g)
        year_hits = {y: (float(g.loc[g.year == y, "primary_hit"].mean()) if ns[y] else np.nan) for y in DEV_YEARS}
        rows.append({
            "policy": policy,
            "entry_delay_min": ENTRY_DELAY[policy],
            "n_dev": n,
            "participation_dev": n / denom_total if denom_total else np.nan,
            "n_2022": ns[2022], "n_2023": ns[2023], "n_2024": ns[2024],
            "hit_dev": hits / n if n else np.nan,
            "hit_2022": year_hits[2022], "hit_2023": year_hits[2023], "hit_2024": year_hits[2024],
            "worst_dev_hit": min(year_hits.values()) if all(np.isfinite(list(year_hits.values()))) else np.nan,
            "wilson_dev": b1j.wilson_lcb(hits, n) if n else np.nan,
            "median_primary_dev": float(g.primary_ret.median()) if n else np.nan,
            "hit_anchor120_dev": float(g.anchor120_hit.mean()) if n else np.nan,
            "hit_entry60_dev": float(g.entry60_hit.mean()) if n else np.nan,
            "max_dev_share": max(ns.values()) / n if n else np.nan,
            "pval_one_sided": float(binomtest(hits, n, 0.5, alternative="greater").pvalue) if n else 1.0,
        })
    M = pd.DataFrame(rows)
    M["qval_bh"] = bh_adjust(M["pval_one_sided"].to_numpy(float))
    M["fdr_sig"] = M.qval_bh <= 0.05
    M["dev_gate"] = (
        (M.n_dev >= 120) &
        (M.n_2022 >= 30) & (M.n_2023 >= 30) & (M.n_2024 >= 30) &
        (M.participation_dev >= 0.35) &
        (M.hit_dev >= 0.60) &
        (M.hit_2022 >= 0.55) & (M.hit_2023 >= 0.55) & (M.hit_2024 >= 0.55) &
        (M.wilson_dev > 0.54) &
        (M.median_primary_dev > 0.0) &
        (M.hit_anchor120_dev >= 0.57) &
        (M.hit_entry60_dev >= 0.57) &
        (M.max_dev_share <= 0.45) &
        M.fdr_sig
    )
    return M


def select_policies(metrics: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    eligible = metrics[metrics.dev_gate].copy().sort_values(
        ["worst_dev_hit", "wilson_dev", "hit_dev", "median_primary_dev", "n_dev", "policy"],
        ascending=[False, False, False, False, False, True],
    )
    dev_sets = {
        p: set(pd.to_datetime(fills[(fills.policy == p) & fills.year.isin(DEV_YEARS)].event_ts, utc=True))
        for p in eligible.policy
    }
    chosen = []
    chosen_sets = []
    for _, row in eligible.iterrows():
        s = dev_sets[row.policy]
        duplicate = False
        for cs in chosen_sets:
            union = len(s | cs)
            jac = len(s & cs) / union if union else 0.0
            if jac > 0.90:
                duplicate = True
                break
        if duplicate:
            continue
        chosen.append(row)
        chosen_sets.append(s)
        if len(chosen) == 3:
            break
    if not chosen:
        return eligible.head(0).copy()
    S = pd.DataFrame(chosen).reset_index(drop=True)
    S.insert(0, "candidate_rank", np.arange(1, len(S) + 1))
    return S


def reference_metrics(selected: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, s in selected.iterrows():
        policy = str(s.policy)
        g = fills[fills.policy == policy].copy()
        gref = g[g.year.isin(REF_YEARS)]
        n25 = int((g.year == 2025).sum()); n26 = int((g.year == 2026).sum())
        h25 = float(g.loc[g.year == 2025, "primary_hit"].mean()) if n25 else np.nan
        h26 = float(g.loc[g.year == 2026, "primary_hit"].mean()) if n26 else np.nan
        nref = len(gref)
        href = float(gref.primary_hit.mean()) if nref else np.nan
        pooled_n = len(g)
        pooled_hits = int(g.primary_hit.sum())
        era_hits = {y: float(g.loc[g.year == y, "primary_hit"].mean()) if (g.year == y).any() else np.nan for y in ALL_YEARS}
        era_ns = {y: int((g.year == y).sum()) for y in ALL_YEARS}
        pass_gate = all([
            n25 >= 25,
            np.isfinite(h25) and h25 >= 0.55,
            n26 >= 20,
            np.isfinite(h26) and h26 >= 0.55,
            np.isfinite(href) and href >= 0.57,
            nref > 0 and float(gref.primary_ret.median()) > 0.0,
            nref > 0 and float(gref.anchor120_hit.mean()) >= 0.55,
            nref > 0 and float(gref.entry60_hit.mean()) >= 0.55,
            pooled_n > 0 and pooled_hits / pooled_n >= 0.59,
            pooled_n > 0 and b1j.wilson_lcb(pooled_hits, pooled_n) > 0.55,
            all(np.isfinite(era_hits[y]) and era_hits[y] > 0.50 for y in ALL_YEARS),
            pooled_n > 0 and max(era_ns.values()) / pooled_n <= 0.35,
        ])
        rows.append({
            "candidate_rank": int(s.candidate_rank),
            "policy": policy,
            "entry_delay_min": int(s.entry_delay_min),
            "n_2025": n25, "hit_2025": h25,
            "n_2026": n26, "hit_2026": h26,
            "n_ref": nref, "hit_ref": href,
            "median_primary_ref": float(gref.primary_ret.median()) if nref else np.nan,
            "hit_anchor120_ref": float(gref.anchor120_hit.mean()) if nref else np.nan,
            "hit_entry60_ref": float(gref.entry60_hit.mean()) if nref else np.nan,
            "n_pooled": pooled_n,
            "hit_pooled": pooled_hits / pooled_n if pooled_n else np.nan,
            "wilson_pooled": b1j.wilson_lcb(pooled_hits, pooled_n) if pooled_n else np.nan,
            **{f"hit_{y}": era_hits[y] for y in ALL_YEARS},
            "max_era_share": max(era_ns.values()) / pooled_n if pooled_n else np.nan,
            "gate": "PASS" if pass_gate else "REJECT",
        })
    return pd.DataFrame(rows)


def pct(v):
    return "nan" if pd.isna(v) else f"{100*float(v):.2f}%"


def main():
    fp, diag = b1j.load_frozen_a1()
    events = frozen_character_events(fp)
    expected_eras = {2022: 97, 2023: 82, 2024: 114, 2025: 93, 2026: 65}
    era_counts = {y: int((events.year == y).sum()) for y in ALL_YEARS}
    character_ok = len(events) == 451 and era_counts == expected_eras

    fills = build_fills(fp, events)
    finite_ok = bool(len(fills) and np.isfinite(fills[["primary_ret", "anchor120_ret", "entry60_ret"]].to_numpy(float)).all())
    policies_ok = set(fills.policy.unique()) == set(POLICIES)
    integrity_ok = bool(diag["sha_ok"] and diag["rows_ok"] and diag["boundary_ok"] and diag["quarter_grid_ok"] and diag["unique_ok"] and character_ok and finite_ok and policies_ok)

    M = dev_metrics(events, fills)
    S = select_policies(M, fills)
    R = reference_metrics(S, fills)

    if not integrity_ok:
        status = "BNB_B29_B2_DATA_TOOLING_FAILURE"
    elif len(R) and (R.gate == "PASS").any():
        status = "BNB_B29_B2_ENTRY_DISCOVERY_PASS"
    else:
        status = "BNB_B29_B2_ENTRY_DISCOVERY_REJECT"

    fills.to_csv(OUT_FILLS, index=False, compression="gzip")
    M.to_csv(OUT_POLICIES, index=False)
    S.to_csv(OUT_SELECTED, index=False)
    R.to_csv(OUT_REF, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29-B2 — Frozen Character Entry Discovery Result", "",
        f"**Status: {status}**", "",
        "B2 tests only preregistered causal entry timing/mechanisms on the frozen B1J LONG character. No TP, SL, leverage, fees, PnL dollars or live orders are tested.", "",
        "## Integrity", "",
        f"- Accepted A1 SHA256: `{diag['sha256']}`",
        f"- Exact immutable A1 identity: **{'PASS' if diag['sha_ok'] else 'FAIL'}**",
        f"- Frozen B1J character event set: **{'PASS' if character_ok else 'FAIL'}** ({len(events)} events)",
        f"- Era counts: {era_counts}",
        f"- Gap-safe finite entry outcomes: **{'PASS' if finite_ok else 'FAIL'}**", "",
        "## Development policy screen (2022-2024)", "",
        "| Policy | N | Part. | Primary hit | Wilson | Worst era | 2022 | 2023 | 2024 | t+120 hit | Entry+60 hit | BH q | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in M.sort_values(["dev_gate", "worst_dev_hit", "wilson_dev"], ascending=[False, False, False]).iterrows():
        lines.append(
            f"| {r.policy} | {int(r.n_dev)} | {pct(r.participation_dev)} | {pct(r.hit_dev)} | {pct(r.wilson_dev)} | {pct(r.worst_dev_hit)} | "
            f"{pct(r.hit_2022)} | {pct(r.hit_2023)} | {pct(r.hit_2024)} | {pct(r.hit_anchor120_dev)} | {pct(r.hit_entry60_dev)} | {r.qval_bh:.6g} | {'PASS' if r.dev_gate else 'REJECT'} |"
        )

    lines.extend(["", "## Frozen shortlist", ""])
    if len(S):
        lines += ["| Rank | Policy | N dev | Hit dev | Worst dev | Wilson |", "|---:|---|---:|---:|---:|---:|"]
        for _, r in S.iterrows():
            lines.append(f"| {int(r.candidate_rank)} | {r.policy} | {int(r.n_dev)} | {pct(r.hit_dev)} | {pct(r.worst_dev_hit)} | {pct(r.wilson_dev)} |")
    else:
        lines.append("No entry policy passed every frozen development gate.")

    lines.extend(["", "## Reference validation (2025-2026)", ""])
    if len(R):
        lines += [
            "| Rank | Policy | 2025 N/hit | 2026 N/hit | Ref hit | Ref t+120 | Ref entry+60 | Pooled hit | Pooled Wilson | Gate |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for _, r in R.iterrows():
            lines.append(
                f"| {int(r.candidate_rank)} | {r.policy} | {int(r.n_2025)} / {pct(r.hit_2025)} | {int(r.n_2026)} / {pct(r.hit_2026)} | "
                f"{pct(r.hit_ref)} | {pct(r.hit_anchor120_ref)} | {pct(r.hit_entry60_ref)} | {pct(r.hit_pooled)} | {pct(r.wilson_pooled)} | {r.gate} |"
            )
        lines += ["", "## Five-era primary-hit detail", "", "| Rank | Policy | 2022 | 2023 | 2024 | 2025 | 2026 |", "|---:|---|---:|---:|---:|---:|---:|"]
        for _, r in R.iterrows():
            lines.append(f"| {int(r.candidate_rank)} | {r.policy} | {pct(r.hit_2022)} | {pct(r.hit_2023)} | {pct(r.hit_2024)} | {pct(r.hit_2025)} | {pct(r.hit_2026)} |")

    lines.extend(["", "## Decision", "", f"**{status}**", ""])
    if status.endswith("PASS"):
        winners = R[R.gate == "PASS"].policy.tolist()
        lines.append(f"Passing frozen entry policy/policies: {', '.join(winners)}. Entry-level promotion only; TP/SL/risk discovery remains separate.")
    elif status.endswith("REJECT"):
        lines.append("No preregistered entry policy passed every development and reference gate. Do not proceed to TP/SL from B2-v1.")
    else:
        lines.append("Integrity/tooling failure; no scientific interpretation is allowed.")
    lines += ["", "No live orders were placed."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
