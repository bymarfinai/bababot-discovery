#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile
import pandas as pd

import sol_r4b_stageB_2023_component_screen as stageb

ROOT = Path(__file__).resolve().parent.parent
SURVIVOR_PATH = ROOT / "SOL_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
STAGEB_CELLS_PATH = ROOT / "SOL_R4B_STAGEB_2023_CELL_RESULTS.csv"

OUT_CELLS = ROOT / "SOL_R4B_STAGEC_2024_CELL_RESULTS.csv"
OUT_VERDICTS = ROOT / "SOL_R4B_STAGEC_2024_COMPONENT_VERDICTS.csv"
OUT_SURVIVORS = ROOT / "SOL_R4B_STAGEC_2024_STABLE_PLATEAUS.csv"
OUT_RESULT = ROOT / "SOL_R4B_STAGEC_2024_COMPONENT_SCREEN.md"
OUT_STATUS = ROOT / "SOL_R4B_STAGEC_2024_Status.txt"
OUT_PROVENANCE = ROOT / "SOL_R4B_STAGEC_PROVENANCE.md"

EXPECTED_SURVIVORS = {
    (3, 1, "DRIVE_UP__STR_B60_80", "LB360/H240;LB360/H360"),
    (4, 1, "EFF_MID__RANGE_MID", "LB120/H360;LB120/H480"),
    (5, 1, "DRIVE_DOWN__STR_B80_100", "LB180/H120;LB180/H240;LB240/H120;LB360/H120"),
    (6, 3, "DRIVE_DOWN__STR_B80_100", "LB180/H120;LB240/H120;LB360/H120"),
    (10, 1, "RV_MID__RANGE_LOW", "LB240/H360;LB360/H360"),
    (14, 2, "DRIVE_UP__STR_B80_100", "LB120/H360;LB180/H360;LB240/H360"),
    (14, 3, "EFF_LOW__RV_HIGH", "LB120/H240;LB180/H240"),
    (15, 1, "RV_HIGH__RANGE_MID", "LB180/H120;LB180/H240;LB180/H360"),
}


def main() -> None:
    if not SURVIVOR_PATH.exists():
        raise FileNotFoundError(SURVIVOR_PATH)
    if not STAGEB_CELLS_PATH.exists():
        raise FileNotFoundError(STAGEB_CELLS_PATH)

    survivors = pd.read_csv(SURVIVOR_PATH)
    b_cells = pd.read_csv(STAGEB_CELLS_PATH)
    if len(survivors) != 8:
        raise AssertionError(f"Stage C must receive exactly 8 Stage-B survivor plateaus, got {len(survivors)}")

    actual = {
        (int(r.hour_wib), int(r.component_rank), str(r.character_rule), str(r.component_cells))
        for r in survivors.itertuples(index=False)
    }
    if actual != EXPECTED_SURVIVORS:
        raise AssertionError("Stage-B survivor registry changed; refusing Stage-C reselection")

    parsed_cells = sum(len(stageb.parse_cells(str(r.component_cells))) for r in survivors.itertuples(index=False))
    if parsed_cells != 21:
        raise AssertionError(f"Stage C frozen membership must be exactly 21 cells, got {parsed_cells}")

    # Rebuild the component metadata shape expected by the frozen Stage-B engine.
    # Development summaries are taken from the actual 2023 Stage-B cell results;
    # they are reporting metadata only. The engine independently recomputes every
    # 2023 baseline cell and every 2024 test cell before applying identical gates.
    rows = []
    for r in survivors.itertuples(index=False):
        g = b_cells[
            (b_cells.hour_wib == int(r.hour_wib)) &
            (b_cells.component_rank == int(r.component_rank))
        ].copy()
        expected_n = len(stageb.parse_cells(str(r.component_cells)))
        if len(g) != expected_n:
            raise AssertionError(
                f"Stage-B cell registry mismatch H{int(r.hour_wib):02d}/R{int(r.component_rank)}: "
                f"expected {expected_n}, got {len(g)}"
            )
        rows.append({
            "hour_wib": int(r.hour_wib),
            "component_rank": int(r.component_rank),
            "character_rule": str(r.character_rule),
            "component_size": expected_n,
            "component_cells": str(r.component_cells),
            "wr_min": float(g.test_wr.min()),
            "wr_mean": float(g.test_wr.mean()),
            "exp_floor": float(g.test_exp.min()),
            "exp_mean": float(g.test_exp.mean()),
        })
    normalized = pd.DataFrame(rows)

    with tempfile.TemporaryDirectory(prefix="sol-r4b-stagec-") as td:
        frozen = Path(td) / "SOL_R4B_STAGEC_FROZEN_COMPONENTS.csv"
        normalized.to_csv(frozen, index=False)

        # Reuse the audited Stage-B engine verbatim. Only the frozen cohort,
        # calendar windows and output paths change. This preserves all viability,
        # retention, drawdown and plateau-survival gates without tuning on 2024.
        stageb.COMP_PATH = frozen
        stageb.OUT_CELLS = OUT_CELLS
        stageb.OUT_VERDICTS = OUT_VERDICTS
        stageb.OUT_SURVIVORS = OUT_SURVIVORS
        stageb.OUT_RESULT = OUT_RESULT
        stageb.OUT_STATUS = OUT_STATUS
        stageb.DEV_START = pd.Timestamp("2023-01-01", tz="UTC")
        stageb.DEV_END = pd.Timestamp("2024-01-01", tz="UTC")
        stageb.TEST_START = pd.Timestamp("2024-01-01", tz="UTC")
        stageb.TEST_END = pd.Timestamp("2025-01-01", tz="UTC")
        stageb.main()

    # Correct Stage-B-only prose emitted by the reused engine; calculations above
    # are untouched. Keep a deterministic report and explicit provenance trail.
    report = OUT_RESULT.read_text()
    report = report.replace(
        "# SOL R4b — Stage B 2023 Connected-Component Screen",
        "# SOL R4b — Stage C 2024 Connected-Component Screen",
    )
    report = report.replace(
        "**COMPONENT MEMBERSHIP WAS FROZEN FROM 2022. EACH CELL IS TESTED AT THE SAME COORDINATE IN 2023. 2024-2026 CLOSED.**",
        "**COMPONENT MEMBERSHIP IS FROZEN FROM THE 8 STAGE-B 2023 SURVIVOR PLATEAUS. EACH OF THE 21 CELLS IS TESTED AT THE SAME COORDINATE IN 2024. NO RESELECTION, REPLACEMENT, OR NEW SEARCH.**",
    )
    report = report.replace("2023 viable", "2024 viable")
    report = report.replace("## Stable plateaus frozen for Stage C", "## Stable plateaus surviving Stage C")
    report = report.replace("2023 viable/stable", "2024 viable/stable")
    report = report.replace(
        "No component or cell may be modified after observing these 2023 results.",
        "No component or cell may be modified or replaced after observing these 2024 results.",
    )
    OUT_RESULT.write_text(report)
    OUT_STATUS.write_text("SOL_R4B_STAGEC_COMPLETE\n")

    provenance = [
        "# SOL R4b Stage C 2024 — Provenance",
        "",
        "- Source registry: `SOL_R4B_STAGEB_2023_STABLE_PLATEAUS.csv`",
        "- Baseline cell metrics: `SOL_R4B_STAGEB_2023_CELL_RESULTS.csv`",
        "- Frozen survivor plateaus: **8**",
        "- Frozen member cells: **21**",
        "- Baseline window: **2023-01-01 UTC <= t < 2024-01-01 UTC**",
        "- Test window: **2024-01-01 UTC <= t < 2025-01-01 UTC**",
        "- Evaluation engine: Stage-B engine reused without gate modification.",
        "- Policy: **no reselection, no replacement, no new search, no post-2024 tuning**.",
        "",
        "Frozen survivor IDs:",
    ]
    for r in survivors.itertuples(index=False):
        provenance.append(
            f"- H{int(r.hour_wib):02d}/R{int(r.component_rank)} `{r.character_rule}` — {r.component_cells}"
        )
    OUT_PROVENANCE.write_text("\n".join(provenance) + "\n")


if __name__ == "__main__":
    main()
