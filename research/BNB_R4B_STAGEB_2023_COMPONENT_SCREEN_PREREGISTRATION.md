# BNB R4b — Stage B 2023 Frozen-Component Screen Preregistration

## Information firewall

- Stage A 2022 frozen files are immutable inputs.
- Open **2023 only**.
- 2024, 2025, and 2026 remain **closed**.
- Every Stage-A frozen cell is replayed at exactly the same WIB hour, character rule, lookback, and hold.
- No cell may be added, removed, re-centered, rescued, or substituted after 2023 is inspected.
- B27/B28 results remain excluded from ranking and survival decisions.

## 2023 per-cell economic viability

A frozen cell is economically viable in 2023 when:

- N `>= 50`
- WR `>= 52%`
- Net `> 0`
- expectancy `> 0`
- PF `>= 1.15`
- max DD `<= min($160, 1.50 × 2022 DD + $20)`

Loss streak is not a hard kill-switch. It is flagged as risk clustering when:

`2023 LS > max(12, 2022 LS + 4)`.

## Performance-retention diagnostic

A viable cell is marked performance-stable versus 2022 when all are true:

- WR deterioration no worse than `-5 percentage points`;
- expectancy retention `>= 60%` of 2022;
- PF retention `>= 70%` of 2022.

This stricter flag is a component-level retention diagnostic, not a requirement that every member cell retain identical performance.

## Component verdicts

For each frozen component:

- `STABLE_PLATEAU_FROZEN` when component size `>=2`, at least `2` cells are economically viable, at least `1` cell is performance-stable, and viable fraction `>=50%`;
- `PARTIAL_PLATEAU_PERSISTENCE` when at least `2` cells are viable but the stable-plateau rule is not met;
- `NARROW_STABLE_POINT` only for a one-cell component whose cell is performance-stable;
- otherwise `PLATEAU_DEGRADATION_FAIL`.

Only `STABLE_PLATEAU_FROZEN` components may advance as formal plateau survivors. Narrow points remain diagnostic and do not become robust plateaus.

## Outputs

Persist:

- all 2023 frozen-cell results;
- all component verdicts;
- stable plateau survivor table;
- scientific result and status.

No 2024 data may be opened unless and until Stage B outputs have been persisted.

Research/shadow only.