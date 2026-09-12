# SOL Robust Character Discovery v3 — Preregistration

## Objective

Find SOL LONG characters that are robust by construction, not repaired after historical failure.

RCD-v3 searches the Development 2022–2024 partition only. The search representation is:

`structural shape × local absolute scale × broader-volatility regime × lookback × hold`

The broader-volatility dimension is included because the frozen RCD-v2 candidate #1 anatomy identified broader absolute volatility as the dominant missing context. RCD-v3 does **not** use 2026 to fit any threshold or select any candidate.

## Data isolation

Discovery/fitting partition: **Development 2022-01-01 through 2024-12-31 only**.

External 2020–2021, Reference Validation 2025 through 2026-07-29, and August 2026 are forbidden during candidate generation, ranking, rejection, plateau analysis, and finalist freezing.

Historical confirmation after freeze is explicitly secondary because these eras have been exposed in prior research. No result from those eras may alter a frozen finalist.

## Frozen execution assumptions

- SOLUSDT LONG only
- Binance Futures 5m raw engine already used by SOL discovery
- exact 5m open entry
- exact-open exit
- notional: $500
- round-trip fee: $0.75
- lookbacks: 15, 30, 60, 120, 240, 360 minutes
- holds: 60, 120, 240, 360, 720, 960 minutes
- clocks: all 15-minute anchors over 24h

No TP, SL, Fibonacci, or intrabar rescue is permitted in RCD-v3 discovery.

## Structural-shape universe

Reuse the already frozen 90 causal character rules from RCD-v2:

- drive direction / drive strength
- efficiency percentile
- realized-volatility percentile
- relative range percentile
- terminal extension percentile
- preregistered pair combinations

No additional shape rule may be added after results are seen.

## Local absolute-scale universe

Reuse RCD-v2 Development-fitted local scale states:

- `NONE`
- `RAW_RANGE_LB_LOW/MID/HIGH`
- `RANGE_24H_LOW/MID/HIGH`
- `RANGE_72H_LOW/MID/HIGH`
- `RANGE_RATIO_24_72_LOW/MID/HIGH`

All q33/q67 boundaries are fit separately for each lookback using Development only.

## Broader-volatility regime

Broader context uses three pre-entry absolute ranges:

- trailing 24h range
- trailing 72h range
- trailing 7d range

For each feature, q33/q67 are fit on Development only and mapped to LOW/MID/HIGH.

The three horizon bands are collapsed by a preregistered majority rule:

- `BROAD_QUIET`: at least two of 24h/72h/7d are LOW
- `BROAD_ACTIVE`: at least two of 24h/72h/7d are HIGH
- `BROAD_NORMAL`: all remaining combinations
- `BROAD_NONE`: no broader-regime restriction; control state

No 2026-derived threshold is used. No alternative broad-regime definition may be substituted after the run.

## Candidate universe

Expected points:

90 structural rules × 13 local-scale states × 4 broad states × 6 lookbacks × 6 holds = **168,480 candidate points**.

Every point is retained in the output, including rejected points.

## Hard robustness gates

### Pooled Development gate

- N >= 180
- net PnL > 0
- expectancy > 0
- PF >= 1.20
- max loss streak <= 10

### Calendar gate

For **each** of 2022, 2023, 2024:

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >= 1.05

### Concentration gate

- no single Development year may contribute >65% of positive net PnL
- no single 15-minute anchor may contribute >60% of positive net PnL unless at least one adjacent anchor also has positive expectancy and PF >=1.05

### Parameter plateau gate

Within the same structural rule, local-scale state, and broad-regime state, use the 3×3 lookback/hold neighborhood around the center point. The center passes only if:

- at least 3 neighboring/center points have positive expectancy
- at least 2 have PF >=1.10
- median neighborhood expectancy >0
- center contributes <=55% of positive net across the neighborhood

No gate may be loosened after results are observed.

## Robustness score

Only candidates passing all hard gates and plateau enter scoring.

Score components are preregistered:

- calendar consistency: 25 points
- parameter plateau: 20 points
- pooled economics: 15 points
- clock/hour stability: 15 points
- local-scale neighborhood support: 10 points
- broader-regime neighborhood support: 5 points
- sample/concentration quality: 10 points

Total: 100 points.

Broader-regime support is descriptive robustness, not a hard requirement: `BROAD_NONE` receives full support only when economics are positive in all three broad regimes; a conditional broad state receives more support when an adjacent broader state is also positive.

## Finalist freeze

Freeze at most 5 structurally distinct finalists before any historical confirmation.

Structural family key:

`shape_rule + principal_local_scale_variable + broad_regime`

Within a family, only the highest robustness-score candidate can be frozen.

Tie-break order:

1. robustness score
2. minimum yearly expectancy
3. PF

The frozen file and commit must exist before historical confirmation is run.

## Historical confirmation after freeze

Frozen finalists only. No runner-up substitution and no retuning.

Partitions:

- External 2020–2021
- Reference Validation 2025 through 2026-07-29
- August 2026 shadow only

Per partition gate:

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >=1.05
- max loss streak <=10

Combined External + Reference gate:

- N >=180
- net PnL >0
- expectancy >0
- PF >=1.20
- max loss streak <=10

Labels:

- `HISTORICAL_CONFIRMATION_STRONG`: both partitions + combined pass
- `HISTORICAL_CONFIRMATION_PARTIAL`: combined passes and exactly one partition passes
- `HISTORICAL_CONFIRMATION_FAIL`: otherwise

Because historical eras are already exposed, even STRONG is secondary evidence, not pristine untouched OOS.

## Stop rule

If zero finalists survive Development robustness, stop. Do not loosen gates.

If finalists fail historical confirmation, stop. Do not rescue by changing broad regime, local scale, threshold, lookback, hold, clock, TP/SL, Fibonacci, or entry.

True confirmation of any surviving RCD-v3 character requires fresh forward data after the currently available dataset.