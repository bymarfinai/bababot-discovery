#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_CENTERS = ROOT / "ETH_R4_STAGEA_2022_PLATEAU_CENTERS.csv"
OUT_COHORT = ROOT / "ETH_R4_STAGEA_2022_FROZEN_COHORT.csv"
OUT_RESULT = ROOT / "ETH_R4_STAGEA_2022_COHORT_FREEZE.md"
OUT_STATUS = ROOT / "ETH_R4_STAGEA_2022_Status.txt"

LOOKBACKS = [60, 120, 180, 240, 360]
HOLDS = [120, 240, 360, 480]


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def finite_col(d: pd.DataFrame, col: str) -> pd.Series:
    return np.isfinite(pd.to_numeric(d[col], errors="coerce"))


def rank_frame(d: pd.DataFrame) -> pd.DataFrame:
    return d.sort_values(
        [
            "strict_support_count", "economic_support_count", "economic_support_ratio",
            "support_floor_exp", "min_half_exp", "exp", "pf", "dd", "ls", "trades",
            "hold_min", "lookback_min", "character_rule",
        ],
        ascending=[False, False, False, False, False, False, False, True, True, False, True, True, True],
        kind="mergesort",
    )


def main():
    li = {v: i for i, v in enumerate(LOOKBACKS)}
    hi = {v: i for i, v in enumerate(HOLDS)}
    all_centers = []
    frozen = []

    for hour in range(24):
        p = ROOT / f"ETH_R3_H{hour:02d}_STAGEA_2022_DevGrid.csv"
        if not p.exists():
            raise FileNotFoundError(f"missing R3 Development grid for H{hour:02d}: {p}")
        D = pd.read_csv(p)
        if len(D) != 1800:
            raise AssertionError(f"H{hour:02d}: expected 1800 R3 Development cells, got {len(D)}")

        D["dev_eligible"] = as_bool(D["dev_eligible"])
        numeric = [
            "lookback_min", "hold_min", "trades", "wr", "net", "exp", "pf", "dd", "ls",
            "H1_exp", "H1_pf", "H2_exp", "H2_pf", "min_half_exp", "positive_anchors",
        ]
        for c in numeric:
            D[c] = pd.to_numeric(D[c], errors="coerce")

        economic_support = (
            (D.trades >= 50) & finite_col(D, "wr") & (D.wr >= .52) &
            (D.net > 0) & finite_col(D, "exp") & (D.exp > 0) &
            finite_col(D, "pf") & (D.pf >= 1.15) & finite_col(D, "dd") & (D.dd <= 160) &
            finite_col(D, "H1_exp") & (D.H1_exp > 0) & finite_col(D, "H1_pf") & (D.H1_pf > 1) &
            finite_col(D, "H2_exp") & (D.H2_exp > 0) & finite_col(D, "H2_pf") & (D.H2_pf > 1) &
            (D.positive_anchors >= 2)
        )
        D["economic_support"] = economic_support

        E = D[D.dev_eligible].copy()
        if E.empty:
            raise AssertionError(f"H{hour:02d}: no R3 Development-eligible cells; R4 cohort cannot be formed")

        rows = []
        for r in E.itertuples(index=False):
            lb = int(r.lookback_min); hold = int(r.hold_min); rule = str(r.character_rule)
            if lb not in li or hold not in hi:
                raise AssertionError(f"unexpected timing H{hour:02d}: LB{lb}/H{hold}")
            same = D[D.character_rule.astype(str) == rule].copy()
            dist = same.apply(
                lambda z: abs(li[int(z.lookback_min)] - li[lb]) + abs(hi[int(z.hold_min)] - hi[hold]), axis=1
            )
            local = same[dist <= 1].copy()
            strict_count = int(local.dev_eligible.sum())
            econ = local[local.economic_support].copy()
            econ_count = int(len(econ))
            local_count = int(len(local))
            floor_exp = float(econ.exp.min()) if econ_count else -np.inf
            mean_exp = float(econ.exp.mean()) if econ_count else -np.inf
            rows.append({
                "hour_wib": hour,
                "character_rule": rule,
                "lookback_min": lb,
                "hold_min": hold,
                "trades": int(r.trades),
                "wr": float(r.wr),
                "net": float(r.net),
                "exp": float(r.exp),
                "pf": float(r.pf),
                "dd": float(r.dd),
                "ls": int(r.ls),
                "H1_exp": float(r.H1_exp),
                "H1_pf": float(r.H1_pf),
                "H2_exp": float(r.H2_exp),
                "H2_pf": float(r.H2_pf),
                "min_half_exp": float(r.min_half_exp),
                "positive_anchors": int(r.positive_anchors),
                "local_cell_count": local_count,
                "strict_support_count": strict_count,
                "economic_support_count": econ_count,
                "economic_support_ratio": (econ_count / local_count) if local_count else 0.0,
                "support_floor_exp": floor_exp,
                "support_mean_exp": mean_exp,
            })

        C = pd.DataFrame(rows)
        all_centers.append(C)

        # Exactly one best plateau center per exact character rule.
        per_rule = []
        for _, g in C.groupby("character_rule", sort=True):
            per_rule.append(rank_frame(g).iloc[0])
        R = pd.DataFrame(per_rule)
        R = rank_frame(R).reset_index(drop=True)
        K = R.head(3).copy()
        K.insert(1, "candidate_rank", np.arange(1, len(K) + 1, dtype=int))
        frozen.append(K)

    CENTERS = pd.concat(all_centers, ignore_index=True)
    COHORT = pd.concat(frozen, ignore_index=True)
    CENTERS.to_csv(OUT_CENTERS, index=False)
    COHORT.to_csv(OUT_COHORT, index=False)

    counts = COHORT.groupby("hour_wib").size()
    if len(counts) != 24 or int(counts.min()) < 1 or int(counts.max()) > 3:
        raise AssertionError(f"invalid frozen cohort hour counts: {counts.to_dict()}")

    lines = [
        "# ETH R4 — Stage A 2022 Full-24 Cohort Freeze", "",
        "**2022-ONLY COHORT CONSTRUCTION. R4 2023 HAS NOT BEEN OPENED. 2024 CLOSED. 2025-2026 CLOSED.**", "",
        f"Frozen candidates: **{len(COHORT)}** across **24/24 WIB hours**.",
        "At most three candidates are frozen per hour, with one representative per exact character rule.",
        "Ranking prioritizes strict/economic local plateau breadth before peak center performance.", "",
        "| WIB hour | Rank | Frozen character | Timing | N | WR | Exp | PF | DD | Strict support | Econ support | Support ratio | Floor Exp |", 
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in COHORT.sort_values(["hour_wib", "candidate_rank"]).itertuples(index=False):
        lines.append(
            f"| {int(r.hour_wib):02d}:00-{(int(r.hour_wib)+1)%24:02d}:00 | {int(r.candidate_rank)} | {r.character_rule} | "
            f"LB{int(r.lookback_min)}/H{int(r.hold_min)} | {int(r.trades)} | {100*float(r.wr):.2f}% | "
            f"${float(r.exp):+.2f} | {float(r.pf):.3f} | ${float(r.dd):.2f} | {int(r.strict_support_count)}/{int(r.local_cell_count)} | "
            f"{int(r.economic_support_count)}/{int(r.local_cell_count)} | {100*float(r.economic_support_ratio):.1f}% | ${float(r.support_floor_exp):+.2f} |"
        )

    lines += [
        "", "## Freeze rule", "",
        "This cohort is now immutable for R4 Stage B. No candidate may be added, removed, or replaced after viewing R4 2023 results.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("ETH_R4_2022_COHORT_FROZEN\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
