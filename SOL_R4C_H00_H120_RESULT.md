# SOL R4c — H00 Fixed-Hold Character Scan

**Purpose:** start the 24-hour sequential SOL character discovery at H00 (00:00–01:00 WIB) while postponing hold optimization.

- Hour: **H00 / 00:00–01:00 WIB**
- Screening hold: **120 minutes, frozen**
- Lookbacks tested: **60, 120, 180, 240, 360 minutes**
- Character rules: **90**, inherited unchanged from R4b
- 2022 development cells: **450**
- Raw SOLUSDT 5m coverage: **99.7698%**

The hold is a fixed screening anchor, not a selected optimum. Character and lookback structure are allowed to differ from H05.

2022 strict-eligible cells: **0**.
Frozen 2022 connected plateaus: **0**.

## Verdict

**H00_REJECTED_AT_DEVELOPMENT** — no connected lookback plateau of size >=2 exists at fixed H120 under the unchanged R4b Stage-A gates.
No 2023/2024 validation was run because there is no frozen H00 cohort to validate.
