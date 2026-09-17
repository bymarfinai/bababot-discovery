# BNB B30-S1 — Pure Structure Detector Library Result

**Status: BNB_B30_S1_STRUCTURE_LIBRARY_READY**

S1 is a structural census only. No entry, future WIN/LOSS, return, MFE/MAE, TP/SL or PnL is evaluated here.

## Immutable source integrity
- SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa` — PASS
- Rows: **229,267**
- Bounds: **2020-02-10 14:15:00+00:00 → 2026-08-26 00:00:00+00:00**
- Exact predecessor clauses never cross missing 15m timestamps.

## Structure census
| ID | Structure | Side | N | 2022 | 2023 | 2024 | 2025 | 2026* | /year | Median gap | Eras >=15 | Max era | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| S01 | SWEEP_LOW_RECLAIM | LONG | 8092 | 1777 | 1671 | 1797 | 1732 | 1115 | 1739.4 | 3.8h | 5 | 22.2% | STRUCTURALLY_VIABLE |
| S02 | HL_CONTINUATION | LONG | 797 | 154 | 164 | 181 | 177 | 121 | 171.3 | 36.6h | 5 | 22.7% | STRUCTURALLY_VIABLE |
| S03 | BREAK_HIGH_HOLD | LONG | 1577 | 261 | 362 | 428 | 374 | 152 | 339.0 | 17.0h | 5 | 27.1% | STRUCTURALLY_VIABLE |
| S04 | FAILED_BREAKDOWN_RECLAIM | LONG | 5109 | 1036 | 1142 | 1136 | 1122 | 673 | 1098.2 | 5.8h | 5 | 22.4% | STRUCTURALLY_VIABLE |
| S05 | SWEEP_HIGH_REJECT | SHORT | 8542 | 1883 | 1784 | 1875 | 1829 | 1171 | 1836.2 | 3.5h | 5 | 22.0% | STRUCTURALLY_VIABLE |
| S06 | LH_CONTINUATION | SHORT | 637 | 140 | 140 | 148 | 123 | 86 | 136.9 | 43.8h | 5 | 23.2% | STRUCTURALLY_VIABLE |
| S07 | BREAK_LOW_HOLD | SHORT | 1207 | 228 | 244 | 273 | 296 | 166 | 259.5 | 23.0h | 5 | 24.5% | STRUCTURALLY_VIABLE |
| S08 | FAILED_BREAKOUT_REJECT | SHORT | 5553 | 1090 | 1232 | 1294 | 1236 | 701 | 1193.7 | 5.5h | 5 | 23.3% | STRUCTURALLY_VIABLE |

`2026*` ends at the immutable A1 cutoff 2026-08-26.

## Cross-family same-timestamp overlap
Only non-zero off-diagonal overlaps are listed; overlap is descriptive and does not suppress either detector.

| A | B | Same timestamp | Jaccard |
|---|---|---:|---:|
| S05 SWEEP_HIGH_REJECT | S08 FAILED_BREAKOUT_REJECT | 847 | 6.39% |
| S01 SWEEP_LOW_RECLAIM | S04 FAILED_BREAKDOWN_RECLAIM | 735 | 5.90% |
| S02 HL_CONTINUATION | S05 SWEEP_HIGH_REJECT | 121 | 1.31% |
| S01 SWEEP_LOW_RECLAIM | S06 LH_CONTINUATION | 87 | 1.01% |
| S04 FAILED_BREAKDOWN_RECLAIM | S05 SWEEP_HIGH_REJECT | 39 | 0.29% |
| S01 SWEEP_LOW_RECLAIM | S08 FAILED_BREAKOUT_REJECT | 39 | 0.29% |
| S02 HL_CONTINUATION | S04 FAILED_BREAKDOWN_RECLAIM | 32 | 0.54% |
| S01 SWEEP_LOW_RECLAIM | S05 SWEEP_HIGH_REJECT | 17 | 0.10% |
| S06 LH_CONTINUATION | S08 FAILED_BREAKOUT_REJECT | 17 | 0.28% |
| S01 SWEEP_LOW_RECLAIM | S02 HL_CONTINUATION | 3 | 0.03% |
| S05 SWEEP_HIGH_REJECT | S06 LH_CONTINUATION | 2 | 0.02% |
| S01 SWEEP_LOW_RECLAIM | S03 BREAK_HIGH_HOLD | 1 | 0.01% |

## Decision
**BNB_B30_S1_STRUCTURE_LIBRARY_READY**

Structurally viable detectors: **8/8**.
Every viable detector advances independently to B30-S2 entry discovery. S2 may search structure-specific entry mechanisms but may not change these S1 definitions. Economics remains forbidden until an entry mechanism is frozen.

No live orders were placed.
