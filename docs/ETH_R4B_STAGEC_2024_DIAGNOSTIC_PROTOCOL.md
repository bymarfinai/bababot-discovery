# ETH R4b — Stage C 2024 Component Diagnostic Protocol

## Scope

R4b Stage B produced one `STABLE_PLATEAU_FROZEN`: H04 rank 1, `DRIVE_DOWN__STR_B80_100`, a five-cell 2022 timing component. Only this frozen plateau is eligible for Stage C.

H01, H02 and H05 showed partial persistence but did not satisfy the preregistered R4b stable-plateau gate; they remain closed in this stage.

Historical caveat: parts of H04 2024 were already examined in earlier R3 work. Therefore Stage C is a **component-level persistence diagnostic**, not a claim of pristine 2024 OOS.

## Data handling

- 2024 period: 2024-01-01 UTC through 2025-01-01 UTC.
- Full earlier history may be loaded for indicator warmup, but only events with entry >= 2024-01-01 and exit < 2025-01-01 count.
- Use explicit period extraction; do not use the legacy helper that hard-codes a 2024-01-01 end date.
- Every event frame must include `gross` and `net` columns.
- Character rule and each LB/Hold coordinate remain exactly frozen from the R4b 2022 component.
- No 2024 timing reselection is allowed.

## Cell diagnostics

Each frozen component cell is evaluated at the same coordinate in 2024 and compared with its own 2022 Development metrics.

Economic viability remains:

- N >= 50
- WR >= 52%
- Net > 0
- Exp > 0
- PF >= 1.15
- DD <= min(160, 1.50 * that cell's 2022 DD + 20)

For reference, strict performance stability is also reported using the existing Stage-B retention gates:

- economically viable
- WR change >= -5 percentage points versus 2022
- Exp retention >= 60%
- PF retention >= 70%

Loss streak remains diagnostic only.

## Component interpretation

Because this is a later-regime persistence diagnostic rather than a new parameter search:

- `ECONOMIC_PLATEAU_PERSISTS` if at least 50% of the frozen component cells are economically viable in 2024, component median Exp > 0, and component median PF >= 1.15.
- `PARTIAL_ECONOMIC_PERSISTENCE` if at least two cells are economically viable, or if component median Exp > 0 with median PF > 1.
- `COMPONENT_COLLAPSE` otherwise.

Strict-stable-cell count is reported separately and does not by itself override the economic-persistence interpretation.

2025 and 2026 remain closed after this diagnostic.
