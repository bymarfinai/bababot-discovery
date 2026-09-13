#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import pandas as pd

import sol_r4b_stageA_2022_component_freeze as stagea
import sol_r4b_stageB_2023_component_screen as stageb

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_R4C_H00_H120"
HOUR_WIB = 0
HOLD_MIN = 120
LOOKBACKS = (60, 120, 180, 240, 360)

DEV_GRID = ROOT / f"{PFX}_2022_DEV_GRID.csv"
DEV_COMPONENTS = ROOT / f"{PFX}_2022_ALL_COMPONENTS.csv"
DEV_FROZEN = ROOT / f"{PFX}_2022_FROZEN_COMPONENTS.csv"

V23_CELLS = ROOT / f"{PFX}_2023_CELL_RESULTS.csv"
V23_VERDICTS = ROOT / f"{PFX}_2023_COMPONENT_VERDICTS.csv"
V23_SURVIVORS = ROOT / f"{PFX}_2023_STABLE_PLATEAUS.csv"
V23_REPORT = ROOT / f"{PFX}_2023_VALIDATION.md"
V23_STATUS = ROOT / f"{PFX}_2023_Status.txt"

V24_INPUT = ROOT / f"{PFX}_2024_FROZEN_INPUT.csv"
V24_CELLS = ROOT / f"{PFX}_2024_CELL_RESULTS.csv"
V24_VERDICTS = ROOT / f"{PFX}_2024_COMPONENT_VERDICTS.csv"
V24_SURVIVORS = ROOT / f"{PFX}_2024_STABLE_PLATEAUS.csv"
V24_REPORT = ROOT / f"{PFX}_2024_VALIDATION.md"
V24_STATUS = ROOT / f"{PFX}_2024_Status.txt"

OUT_RESULT = ROOT / f"{PFX}_RESULT.md"
OUT_PROVENANCE = ROOT / f"{PFX}_PROVENANCE.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"


def safe_read(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def run_2022_discovery() -> tuple[pd.DataFrame, pd.DataFrame, float]:
    # Pre-registered R4c H00 screen: hour and hold are fixed before evaluation.
    # We reuse the audited R4b character definitions and Stage-A gates verbatim.
    stagea.LOOKBACKS = LOOKBACKS
    stagea.HOLDS = (HOLD_MIN,)
    stagea.HOURS_WIB = (HOUR_WIB,)
    stagea.START = pd.Timestamp("2022-01-01", tz="UTC")
    stagea.MID = pd.Timestamp("2022-07-01", tz="UTC")
    stagea.END = pd.Timestamp("2023-01-01", tz="UTC")
    stagea.MIN_COMPONENT_SIZE = 2
    stagea.MAX_COMPONENTS_PER_HOUR = 3

    stagea.legacy.base.synthetic_tests()
    x5, coverage = stagea.legacy.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x22 = x5[(idx >= stagea.START) & (idx < stagea.END)].copy()

    cache = stagea.prepare_hour(x22, HOUR_WIB)
    rows = []
    for rule in stagea.legacy.RULES:
        for lb in LOOKBACKS:
            rows.append(stagea.eval_cell(cache, HOUR_WIB, int(lb), HOLD_MIN, str(rule)))
    D = pd.DataFrame(rows)
    expected = len(stagea.legacy.RULES) * len(LOOKBACKS)
    if len(D) != expected:
        raise AssertionError(f"expected {expected} H00/H120 cells, got {len(D)}")
    D.to_csv(DEV_GRID, index=False)

    C = stagea.build_components(D)
    C.to_csv(DEV_COMPONENTS, index=False)
    F = stagea.freeze_top_components(C)
    F.to_csv(DEV_FROZEN, index=False)
    return D, F, float(coverage)


def run_validation(comp_path: Path, dev_start: str, dev_end: str, test_start: str, test_end: str,
                   out_cells: Path, out_verdicts: Path, out_survivors: Path,
                   out_report: Path, out_status: Path) -> None:
    stageb.COMP_PATH = comp_path
    stageb.OUT_CELLS = out_cells
    stageb.OUT_VERDICTS = out_verdicts
    stageb.OUT_SURVIVORS = out_survivors
    stageb.OUT_RESULT = out_report
    stageb.OUT_STATUS = out_status
    stageb.DEV_START = pd.Timestamp(dev_start, tz="UTC")
    stageb.DEV_END = pd.Timestamp(dev_end, tz="UTC")
    stageb.TEST_START = pd.Timestamp(test_start, tz="UTC")
    stageb.TEST_END = pd.Timestamp(test_end, tz="UTC")
    stageb.main()


def normalize_for_next_stage(survivors: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in survivors.itertuples(index=False):
        g = cells[
            (cells.hour_wib == int(r.hour_wib)) &
            (cells.component_rank == int(r.component_rank))
        ].copy()
        if len(g) != int(r.component_size):
            raise AssertionError(
                f"Frozen membership mismatch H{int(r.hour_wib):02d}/R{int(r.component_rank)}: "
                f"expected {int(r.component_size)}, got {len(g)}"
            )
        rows.append({
            "hour_wib": int(r.hour_wib),
            "component_rank": int(r.component_rank),
            "character_rule": str(r.character_rule),
            "component_size": int(r.component_size),
            "component_cells": str(r.component_cells),
            "wr_min": float(g.test_wr.min()),
            "wr_mean": float(g.test_wr.mean()),
            "exp_floor": float(g.test_exp.min()),
            "exp_mean": float(g.test_exp.mean()),
        })
    return pd.DataFrame(rows)


def fmt_component_rows(df: pd.DataFrame, period: str) -> list[str]:
    if df.empty:
        return [f"- {period}: **no stable plateau**."]
    lines = []
    for r in df.itertuples(index=False):
        lines.append(
            f"- {period}: H{int(r.hour_wib):02d} R{int(r.component_rank)} `{r.character_rule}` — "
            f"{r.component_cells}; viable {int(r.test_viable_cells)}/{int(r.component_size)}, "
            f"median WR {100*float(r.test_median_wr):.2f}%, median exp ${float(r.test_median_exp):+.2f}, "
            f"median PF {float(r.test_median_pf):.3f}, max DD ${float(r.test_max_dd):.2f}."
        )
    return lines


def main() -> None:
    D, F, coverage = run_2022_discovery()

    lines = [
        "# SOL R4c — H00 Fixed-Hold Character Scan", "",
        "**Purpose:** start the 24-hour sequential SOL character discovery at H00 (00:00–01:00 WIB) while postponing hold optimization.", "",
        f"- Hour: **H00 / 00:00–01:00 WIB**",
        f"- Screening hold: **{HOLD_MIN} minutes, frozen**",
        f"- Lookbacks tested: **{', '.join(str(x) for x in LOOKBACKS)} minutes**",
        f"- Character rules: **{len(stagea.legacy.RULES)}**, inherited unchanged from R4b",
        f"- 2022 development cells: **{len(D)}**",
        f"- Raw SOLUSDT 5m coverage: **{coverage:.4%}**", "",
        "The hold is a fixed screening anchor, not a selected optimum. Character and lookback structure are allowed to differ from H05.", "",
    ]

    eligible = D[D.dev_eligible.astype(bool)].copy()
    lines += [f"2022 strict-eligible cells: **{len(eligible)}**."]

    if F.empty:
        lines += [
            "Frozen 2022 connected plateaus: **0**.", "",
            "## Verdict", "",
            "**H00_REJECTED_AT_DEVELOPMENT** — no connected lookback plateau of size >=2 exists at fixed H120 under the unchanged R4b Stage-A gates.",
            "No 2023/2024 validation was run because there is no frozen H00 cohort to validate.",
        ]
        OUT_STATUS.write_text("SOL_R4C_H00_REJECTED_AT_DEVELOPMENT\n")
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        OUT_PROVENANCE.write_text(
            "# SOL R4c H00 H120 — Provenance\n\n"
            "- Parent checkpoint: R4b Stage C 2024 completed state.\n"
            "- Discovery window: 2022 only.\n"
            "- Fixed hour: H00 WIB.\n"
            "- Fixed screening hold: 120 minutes.\n"
            "- Search dimensions: 90 inherited character rules × 5 lookbacks.\n"
            "- Hold was not optimized.\n"
            "- 2023 and 2024 remain unused by this R4c H00 run because development produced no plateau.\n"
        )
        return

    lines += [f"Frozen 2022 connected plateaus: **{len(F)}**.", ""]
    for r in F.sort_values("component_rank").itertuples(index=False):
        lines.append(
            f"- 2022 R{int(r.component_rank)} `{r.character_rule}` — {r.component_cells}; "
            f"WR min/mean {100*float(r.wr_min):.2f}%/{100*float(r.wr_mean):.2f}%, "
            f"exp floor/mean ${float(r.exp_floor):+.2f}/${float(r.exp_mean):+.2f}."
        )

    # Validate the exact 2022 frozen components in 2023. No reselection/replacement.
    run_validation(
        DEV_FROZEN, "2022-01-01", "2023-01-01", "2023-01-01", "2024-01-01",
        V23_CELLS, V23_VERDICTS, V23_SURVIVORS, V23_REPORT, V23_STATUS,
    )
    S23 = safe_read(V23_SURVIVORS)
    V23 = safe_read(V23_VERDICTS)
    lines += ["", "## 2023 frozen validation", ""]
    lines += fmt_component_rows(S23, "2023")

    if S23.empty:
        lines += ["", "## Verdict", "", "**H00_REJECTED_IN_2023** — the fixed-H120 H00 development plateau did not persist. No component was replaced or reselected after validation."]
        OUT_STATUS.write_text("SOL_R4C_H00_REJECTED_IN_2023\n")
    else:
        # Preserve complete component membership from the 2022 freeze; only survivor plateaus advance.
        C23 = safe_read(V23_CELLS)
        N24 = normalize_for_next_stage(S23, C23)
        N24.to_csv(V24_INPUT, index=False)
        run_validation(
            V24_INPUT, "2023-01-01", "2024-01-01", "2024-01-01", "2025-01-01",
            V24_CELLS, V24_VERDICTS, V24_SURVIVORS, V24_REPORT, V24_STATUS,
        )
        S24 = safe_read(V24_SURVIVORS)
        lines += ["", "## 2024 frozen validation", ""]
        lines += fmt_component_rows(S24, "2024")
        if S24.empty:
            lines += ["", "## Verdict", "", "**H00_REJECTED_IN_2024** — a 2023 survivor failed to retain a stable plateau in 2024. No reselection or replacement was permitted."]
            OUT_STATUS.write_text("SOL_R4C_H00_REJECTED_IN_2024\n")
        else:
            lines += ["", "## Verdict", "", "**H00_CHARACTER_SURVIVES_2024** — at least one fixed-H120 connected character/lookback plateau persisted through 2022 discovery → 2023 frozen validation → 2024 frozen validation."]
            OUT_STATUS.write_text("SOL_R4C_H00_CHARACTER_SURVIVES_2024\n")

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_PROVENANCE.write_text(
        "# SOL R4c H00 H120 — Provenance\n\n"
        "- Parent branch checkpoint: `sol-r4b-cohort-plateau-screen` at `128747de04df3c7f69a259a3980ab800c0708d47`.\n"
        "- New branch: `sol-r4c-hourly-character-scan`.\n"
        "- Fixed hour: H00 = 00:00–01:00 WIB.\n"
        "- Fixed screening hold: 120 minutes. Hold optimization is explicitly deferred.\n"
        "- Character universe: the same 90 causal R4b character rules.\n"
        "- Lookbacks: 60, 120, 180, 240, 360 minutes.\n"
        "- Development: 2022 only.\n"
        "- First validation: exact frozen membership in 2023.\n"
        "- Second validation: exact surviving membership in 2024, only if 2023 passes.\n"
        "- No component replacement, no post-validation reselection, no gate loosening.\n"
        "- Important: 2023/2024 have appeared in prior R4b research, so this R4c run is a structured reanalysis, not a claim of globally untouched historical data.\n"
    )


if __name__ == "__main__":
    main()
