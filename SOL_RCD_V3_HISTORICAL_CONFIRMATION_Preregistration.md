# SOL RCD v3 — Secondary Historical Confirmation Preregistration

## Frozen-before-confirmation evidence

The five finalists were frozen in repository commit `f69ed1733bba133d745447ef6d9c76eae5b6c49b` before this confirmation engine is created.

No finalist may be replaced, retuned, or reordered based on historical-confirmation performance.

## Scientific status

This is **secondary historical confirmation**, not pristine untouched OOS, because External / Reference Validation eras have been exposed in earlier SOL research. It tests whether the Development-only RCD-v3 construction generalizes to those eras without changing any definition.

## Frozen items

For each finalist, keep unchanged:

- structural shape rule
- local scale state and Development-only q33/q67 boundaries
- broader regime and Development-only 24h/72h/7d boundaries
- lookback
- hold
- all 15-minute clocks
- LONG side
- exact 5m open entry and exact-open exit
- $500 notional
- $0.75 round-trip fee

## Confirmation partitions

- External: 2020-01-01 through 2021-12-31
- Reference Validation: 2025-01-01 through 2026-07-29
- August 2026: shadow only; never a confirmation gate

## Per-partition gate

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max loss streak <= 10

## Combined External + Reference gate

- N >= 180
- net PnL > 0
- expectancy > 0
- PF >= 1.20
- max loss streak <= 10

## Labels

- `HISTORICAL_CONFIRMATION_STRONG`: External PASS + Reference PASS + Combined PASS
- `HISTORICAL_CONFIRMATION_PARTIAL`: Combined PASS and exactly one partition PASS
- `HISTORICAL_CONFIRMATION_FAIL`: otherwise

## Required reporting

For every finalist report:

- Development frozen metrics
- External metrics
- Reference Validation metrics
- Combined metrics
- 2020, 2021, 2025, 2026 annual economics
- minute-anchor economics
- hour-of-day economics
- August shadow metrics

## Stop rule

No threshold, broad regime, local scale, lookback, hold, clock, TP/SL, Fibonacci, or candidate substitution may be changed after this run.

Even a STRONG result remains secondary evidence. True confirmation requires fresh forward data after the currently available dataset.