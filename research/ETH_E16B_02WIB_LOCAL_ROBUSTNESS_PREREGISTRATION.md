# ETH E16B — 02:00–03:00 WIB Local Robustness / Overfit Diagnostic

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen question

Does the E16A 02:00–03:00 WIB LONG edge form a stable local parameter basin, or is it mainly a single-point optimization artifact?

E16B is **not** allowed to search for a new character. It only evaluates local neighborhoods around the two E16A formal passers already selected before this test.

## Frozen E16A centers

1. Primary: `RV_HIGH__RANGE_MID / LB150 / H300`
2. Secondary: `DRIVE_DOWN__STR_B60_80 / LB120 / H330`

No rule substitution is permitted.

## Frozen local neighborhoods

### Primary neighborhood

- Rule: `RV_HIGH__RANGE_MID`
- Lookbacks: `120, 150, 180`
- Holds: `270, 300, 330`
- Total: 9 cells
- Axial neighbors of center: `(120,300)`, `(180,300)`, `(150,270)`, `(150,330)`

### Secondary neighborhood

- Rule: `DRIVE_DOWN__STR_B60_80`
- Lookbacks: `90, 120, 150`
- Holds: `300, 330, 360`
- Total: 9 cells
- Axial neighbors of center: `(90,330)`, `(150,330)`, `(120,300)`, `(120,360)`

All cells must come directly from the persisted E16A 8,100-candidate Development grid. No OOS data may be read.

## Economic-support definition

A neighborhood cell is `economically_supportive` only if all of the following hold:

- pooled N >= 160
- pooled WR >= 55%
- pooled net > 0
- pooled expectancy >= +$0.50/trade
- pooled PF >= 1.20
- pooled max DD <= $150
- pooled max loss streak <= 10
- 2022 expectancy > 0 and PF > 1.00
- 2023 expectancy > 0 and PF > 1.00
- 2024 expectancy > 0 and PF > 1.00

This is a local-robustness diagnostic, not a replacement for the original E12 formal gate. `candidate_gate` remains reported separately and unchanged.

## Plateau criteria

A center has `PLATEAU_PASS` if:

1. the center itself remains a full E12 `candidate_gate` PASS;
2. at least 5 of the 9 neighborhood cells are economically supportive;
3. at least 3 of the 4 axial neighbors are economically supportive;
4. neighborhood median WR >= 55%;
5. neighborhood median expectancy >= +$0.50/trade;
6. neighborhood median PF >= 1.20.

A center has `SPIKE_RISK` if either:

- <=3 of 9 cells are economically supportive; or
- <=1 of 4 axial neighbors are economically supportive.

Otherwise its plateau status is `MIXED`.

## Leave-one-year-out local selection test

For each held-out Development year (2022, 2023, 2024), selection is restricted to the same 9-cell neighborhood and same frozen rule.

A cell is eligible using the other two training years only if **both training years** have:

- WR >= 52%
- expectancy > 0
- PF > 1.00

Among eligible cells, select deterministically by:

1. highest minimum training-year expectancy;
2. highest mean training-year expectancy;
3. highest minimum training-year PF;
4. highest mean training-year WR;
5. smallest Manhattan distance from the frozen E16A center;
6. lower hold, then lower lookback as final deterministic tie-breakers.

The held-out year passes if the selected cell has:

- N >= 40
- WR >= 52%
- expectancy > 0
- PF > 1.00

No re-selection after viewing the held-out year is allowed.

## Interpretation

For the primary E16A center:

- `ROBUST_STRONG`: PLATEAU_PASS and 3/3 held-out years pass.
- `ROBUST_MODERATE`: PLATEAU_PASS and 2/3 held-out years pass.
- `OVERFIT_RISK_HIGH`: SPIKE_RISK or <=1/3 held-out years pass.
- otherwise `ROBUSTNESS_MIXED`.

The secondary center is diagnostic corroboration and is scored using the same rules.

OOS remains closed regardless of E16B outcome. E16B can reduce or increase overfit concern, but it does not provide true OOS validation.