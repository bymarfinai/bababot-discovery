# SOL H23 06:45 WIB Anchor-Local Forward Shadow — Preregistration

## Research status

**NEW OOS-DERIVED HYPOTHESIS. NOT YET FORWARD-CONFIRMED.**

This experiment follows the formal SOL frozen-winner OOS validation in which 0/4 pooled hourly winners replicated. Post-validation anatomy showed that one quarter-hour anchor inside H23 remained positive across Development, External, and Reference Validation. Because that anchor was isolated after OOS inspection, all data through 2026-07-29 are now hypothesis-generation evidence only for this lineage.

Research/shadow only. No live promotion or profit guarantee.

## Frozen candidate

Exactly one candidate is permitted:

- Symbol: SOLUSDT Binance USD-M Futures.
- Direction: LONG only.
- Clock: **23:45 UTC / 06:45 WIB only**.
- Character: **DRIVE_DOWN__STR_B80_100**.
- Lookback: **15 minutes**.
- Hold: **120 minutes**.
- Entry: exact 23:45 UTC 5m open when the frozen character is true.
- Exit: exact 5m open 120 minutes later.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Causal feature construction and normalization unchanged from the SOL economic-first engine.
- Rolling percentile history: 60 observations, minimum 40 prior observations.
- Weekdays only, unchanged from discovery.

No alternative clock, neighboring anchor, rule, lookback, hold, entry, exit, fee, or threshold may be substituted after forward data are inspected.

## Historical provenance — descriptive only

The exact frozen candidate produced:

| Partition | N | WR | Net | Exp | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| External 2020–2021 | 33 | 63.64% | +$204.34 | +$6.19 | 2.589 | $97.53 |
| Development 2022–2024 | 78 | 53.85% | +$132.64 | +$1.70 | 1.594 | $86.16 |
| Reference Validation 2025–2026-07-29 | 35 | 62.86% | +$37.39 | +$1.07 | 1.752 | $22.47 |

Combined historical provenance: 146 trades, approximately 58.22% WR, +$374.37 net, and +$2.56/trade. These figures are **not** a clean OOS validation because External and Reference Validation were inspected when the anchor-local hypothesis was generated.

## Fresh forward window

The first untouched forward/shadow window is frozen as:

- Start: **2026-08-01 00:00 UTC**.
- End: **2026-09-12 00:00 UTC** (exclusive).

The experiment may download raw Binance 5m data through the frozen end timestamp. Data before the forward start may be loaded only to construct causal rolling state; no pre-August outcome is part of the forward score.

## Readout

Report every qualifying forward trade and the aggregate:

- N
- WR
- net PnL
- expectancy/trade
- PF
- max DD
- max loss streak
- max win streak
- entry timestamp
- exit timestamp
- entry price
- exit price
- net PnL per trade

## Evaluation rule

The original single-anchor supportive economics are retained without relaxation:

- N >= 40
- WR >= 52%
- net PnL > $0
- expectancy > $0/trade
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

If forward N < 40, the only permitted formal status is **FORWARD_INSUFFICIENT_SAMPLE**, regardless of observed WR or PnL. Positive small-N results must not be called confirmation, and negative small-N results must not be used to tune or replace the candidate.

If N >= 40, report **FORWARD_SUPPORT_PASS** or **FORWARD_SUPPORT_FAIL** strictly from the frozen thresholds above.

## Stop rule

After this run, preserve the candidate unchanged. Do not use the forward outcomes to choose a neighboring quarter-hour, alternate lookback/hold, or another Development passer. Any such change requires a separately named new hypothesis and a new untouched future window.
