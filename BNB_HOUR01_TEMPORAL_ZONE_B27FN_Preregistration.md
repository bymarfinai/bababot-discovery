# BNB 01:00 WIB Temporal-Zone Refinement — B27FN Preregistration

## Purpose

B27FN tests whether the 01:00 WIB structural leader found by the frozen 24-hour B27FA–B27FK sweep and retained after B27FL normalization is a robust temporal zone or a brittle exact-hour boundary.

This milestone is structural-only. It does not define an entry, stop, target, PnL, fee, leverage, weekday filter, or holdout test.

## Frozen data and universe

- Symbol: BNBUSDT
- Raw 5m loader: unchanged inherited repository loader
- Development partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC exclusive
- Normalized common local-date universe from B27FL: 2022-01-02 through 2024-12-31 inclusive
- Expected complete sessions per anchor: 1095
- Timezone: Asia/Jakarta (WIB, UTC+7)
- All seven weekdays included
- No external, reference-validation, August, or holdout data may be used

## Frozen geometry

For each tested anchor A:

- Reference window: A through A+4 hours
- Execution window: A+4 through A+8 hours
- Reference H = maximum 5m high in the 4h reference window
- Reference L = minimum 5m low in the 4h reference window
- R = H - L

The structural state machine is unchanged from B27EM/B27FA–B27FM.

## Frozen anchor grid

All nine anchors are preregistered before any B27FN result is observed:

- 23:00 WIB
- 23:30 WIB
- 00:00 WIB
- 00:30 WIB
- 01:00 WIB
- 01:30 WIB
- 02:00 WIB
- 02:30 WIB
- 03:00 WIB

This is a symmetric 30-minute neighborhood around the frozen 01:00 center, extending two hours on each side. No anchor may be added, removed, or shifted after seeing partial results.

## Mandatory reproduction gates

The already-known whole-hour anchors must reproduce their normalized B27FL values exactly before the half-hour results are interpreted:

| Anchor | Sessions | Causal leaves | H2 |
|---|---:|---:|---:|
| 23:00 | 1095 | 145 | 109 |
| 00:00 | 1095 | 137 | 105 |
| 01:00 | 1095 | 162 | 132 |
| 02:00 | 1095 | 162 | 126 |
| 03:00 | 1095 | 142 | 96 |

Any mismatch aborts B27FN.

## Frozen structural outputs

For each anchor report:

- complete sessions
- K1 qualified count/rate
- causal leaves
- H2 arrivals
- opposite break before H2
- ambiguous H2 vs opposite break
- no H2 by end
- H2/causal-leave rate
- resolved H2 share
- median minutes leave→H2

H2/leave is a structural outcome rate, not trading win rate.

## Temporal-zone diagnostics

### A. Local sensitivity curve

Report the nine anchors sorted chronologically and by H2/leave rate.

### B. 30-minute neighbors around the frozen center

Report 00:30, 01:00, and 01:30 together, including:

- individual H2/leave rates
- pooled leaves and H2 across the three anchors
- simple unweighted mean of the three anchor rates
- maximum minus minimum rate spread

### C. Frozen robustness classification

Classify only after all nine results are complete:

**ROBUST_TEMPORAL_ZONE** if all are true:
1. 00:30 and 01:30 each have at least 100 causal leaves;
2. both 00:30 and 01:30 have H2/leave >= 75%;
3. unweighted mean of 00:30, 01:00, 01:30 is >= 78%;
4. neither adjacent half-hour rate is more than 7.5 percentage points below the 01:00 center.

**BOUNDARY_SENSITIVE** if either 00:30 or 01:30 is below 70% H2/leave or more than 10 percentage points below 01:00.

Otherwise classify **MIXED_TEMPORAL_ZONE**.

These thresholds are frozen before seeing half-hour results and are prioritization diagnostics only, not trading rules.

### D. High-strength contiguous region

For descriptive purposes, identify the longest contiguous sequence on the nine-point 30-minute grid where every anchor has:

- at least 100 causal leaves; and
- H2/leave >= 75%.

This does not select a trading time. It only describes the width of the temporal habitat.

## Interpretation boundary

B27FN may support or weaken the hypothesis that the 01:00 WIB result belongs to a wider temporal zone. It must not:

- define a trading entry
- reuse the B27FM 92% exploratory executable candidate as a trading rule
- define stop/target
- compute PnL, PF, expectancy, fees, slippage, leverage, or sizing
- select weekdays
- use holdout data
- optimize reference-window length

## Stop rule

Persist all B27FN outputs and STOP. Any test of alternative reference-window length, exact entry, or economics requires a new preregistered milestone.
