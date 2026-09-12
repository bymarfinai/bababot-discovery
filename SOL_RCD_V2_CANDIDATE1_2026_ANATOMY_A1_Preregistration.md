# SOL RCD v2 Candidate #1 — 2026 Anatomy A1 Preregistration

## Status and scientific scope

This experiment is **diagnostic / secondary mechanism analysis only**. It is not untouched OOS and it cannot promote a live filter. Candidate #1 and its 2026 weakness are already exposed from prior historical confirmation.

The frozen candidate is unchanged:

- LONG only
- shape: `DRIVE_UP__STR_B0_20`
- scale: `RAW_RANGE_LB_HIGH`
- lookback: 30 minutes
- hold: 960 minutes
- all 15-minute anchors across the 24-hour clock
- exact 5-minute open entry and exact-open exit
- $500 notional and $0.75 round-trip fee
- original Development-derived Phase 1A RAW_RANGE_LB boundaries

No shape, scale state, lookback, hold, anchor, entry, exit, fee, or notional may be changed in A1.

## Question

Why did the frozen candidate retain positive economic expectancy from 2020 through 2025 but become negative in 2026?

The objective is to identify a **missing broader pre-entry context dimension**, not to rescue the candidate.

## Pre-entry broader-context feature universe

Only the following causal features are allowed. Every value is measured using information available strictly before the entry open:

1. `ret_24h` — entry open / open 24h earlier - 1
2. `ret_72h` — entry open / open 72h earlier - 1
3. `ret_7d` — entry open / open 7d earlier - 1
4. `range_24h` — trailing 24h high-low range / start open
5. `range_72h` — trailing 72h high-low range / start open
6. `range_7d` — trailing 7d high-low range / start open
7. `loc_24h` — entry position inside the trailing 24h high-low range
8. `loc_72h` — entry position inside the trailing 72h high-low range
9. `loc_7d` — entry position inside the trailing 7d high-low range
10. `range_ratio_24_72` — trailing 24h range divided by trailing 72h range

No additional feature may be added after seeing the results.

## Frozen binning rule

For each feature, q33 and q67 are fitted **only on the frozen candidate's Development 2022–2024 trades**. These cutoffs are then frozen and mapped unchanged to 2020, 2021, 2025, and 2026.

Bands are `LOW`, `MID`, `HIGH`.

No threshold grid search is allowed.

## Required diagnostics

For every feature and cohort/year report:

- N
- median, q25, q75
- Development q33/q67
- PSI versus Development
- LOW/MID/HIGH composition

For every feature band and year/partition report candidate economics:

- N
- WR
- net PnL
- expectancy
- PF
- max drawdown
- max loss streak

Also report the frozen candidate's post-entry path by year:

- median MFE
- median MAE
- median giveback

This path analysis is descriptive only and cannot justify changing hold/exit in A1.

## Diagnostic ranking

Features are ranked by their 2026 distribution shift versus Development using PSI, with absolute median displacement in Development-IQR units as a secondary descriptor.

Interpretation of PSI is preregistered:

- `< 0.10`: weak shift
- `0.10–0.25`: moderate shift
- `>= 0.25`: strong shift

A feature can be called a **primary 2026 context discriminator** only if all are true:

1. PSI versus Development is >= 0.25 in 2026;
2. 2026 has a materially concentrated band (`LOW`, `MID`, or `HIGH`) with at least 55% of candidate trades;
3. that band's Development expectancy is meaningfully different from at least one other band and the ordering is directionally consistent with 2026 degradation;
4. the same interpretation is not contradicted by 2025 economics.

These rules classify evidence only; they do not create a trading gate.

## Allowed verdict labels

- `BROADER_VOLATILITY_CONTEXT_DOMINANT`
- `BROADER_DIRECTION_LOCATION_CONTEXT_DOMINANT`
- `MIXED_BROADER_CONTEXT_SHIFT`
- `NO_CLEAR_BROADER_CONTEXT_MECHANISM`

Volatility context is represented by `range_24h`, `range_72h`, `range_7d`, `range_ratio_24_72`.

Direction/location context is represented by `ret_24h`, `ret_72h`, `ret_7d`, `loc_24h`, `loc_72h`, `loc_7d`.

## Stop rule

A1 must stop after diagnosis. Specifically:

- no new filter can be promoted;
- no 2026-derived threshold can be used;
- no candidate replacement is allowed;
- no hold, lookback, anchor, entry, exit, TP, SL, or Fibonacci calibration is allowed;
- no statement of restored robustness is allowed.

If a missing context dimension is identified, any future RCD-v3 definition must be preregistered separately and must derive its thresholds without optimizing on 2026.
