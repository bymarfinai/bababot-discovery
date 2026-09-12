# SOL Robust Character Discovery v2 — Historical Confirmation Preregistration

Status: PREREGISTERED AFTER FINALIST FREEZE AND BEFORE RCD-v2 HISTORICAL CONFIRMATION EXECUTION

Frozen finalist source commit: `c8530d05aeca8f64e20c8c0e0fb78904e8433af6`.

The four Phase 1A finalists are fixed and may not be substituted, retuned, filtered, or rescued during this experiment.

## Scientific status

External and Reference Validation eras have been viewed in earlier SOL research. Therefore this experiment is explicitly **secondary historical confirmation**, not pristine untouched OOS.

The purpose is to ask whether characters that were discovered by the new robustness-by-construction method retain economic edge across older and newer eras without any post-freeze modification.

## Frozen finalists

1. `DRIVE_UP__STR_B0_20 | RAW_RANGE_LB_HIGH | LB30 | Hold960m`
2. `EFF_HIGH__EXT_LOW | RANGE_72H_HIGH | LB120 | Hold240m`
3. `EFF_HIGH__EXT_LOW | RAW_RANGE_LB_LOW | LB240 | Hold720m`
4. `EFF_HIGH__EXT_LOW | RANGE_24H_MID | LB120 | Hold360m`

All Development-fitted q33/q67 scale boundaries are read from the persisted `SOL_RCD_V2_PHASE1A_ScaleBoundaries.csv` and frozen exactly.

## Trading mechanics

Exactly as Phase 1A:

- SOLUSDT LONG only
- raw 5m source data
- weekdays only
- all quarter-hour decision clocks (00/15/30/45 every UTC hour)
- exact-open entry at decision timestamp
- exact-open time exit after frozen hold
- USD 500 notional
- USD 0.75 round-trip fee
- no TP/SL
- no Fibonacci adjustment
- no entry retuning
- no clock filtering
- no candidate-specific rescue

## Historical partitions

### External

`2020-01-01 <= decision time < 2022-01-01`

### Reference Validation

`2025-01-01 <= decision time < 2026-07-30`

### August 2026

`2026-08-01 <= decision time < 2026-08-26`

August is **SHADOW_ONLY** and is never used for pass/fail classification.

## Required metrics

For each frozen finalist and each partition:

- N trades
- win rate
- net PnL
- expectancy/trade
- PF
- max drawdown
- max loss streak
- max win streak

Also report:

- External + Reference Validation combined historical economics
- calendar-year economics for 2020, 2021, 2025, 2026
- minute-anchor economics
- UTC-hour economics
- retention ratio versus Development trade count and expectancy

## Confirmation gates

The confirmation philosophy mirrors RCD-v2 discovery: economic expectancy and PF are primary; WR is descriptive, not a hard gate.

### Per-partition gate

External and Reference Validation must EACH satisfy:

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max loss streak <= 10

No DD hard threshold and no WR hard threshold are introduced post-freeze because neither was a Phase 1A discovery hard gate.

### Combined historical gate

External + Reference Validation pooled must satisfy:

- N >= 180
- net PnL > 0
- expectancy > 0
- PF >= 1.20
- max loss streak <= 10

### Labels

`HISTORICAL_CONFIRMATION_STRONG`

- External partition passes
- Reference Validation partition passes
- combined historical gate passes

`HISTORICAL_CONFIRMATION_PARTIAL`

- combined historical gate passes
- exactly one of External / Reference Validation passes

`HISTORICAL_CONFIRMATION_FAIL`

- combined historical gate fails, OR
- neither External nor Reference Validation passes

The label is mechanical. No qualitative override.

## Anti-rescue stop rule

After historical results are exposed:

- no scale band may be changed
- no lookback may be changed
- no hold may be changed
- no hour or minute anchor may be removed
- no finalist may be replaced by the next Development candidate
- no threshold may be recalibrated using External or Reference Validation

If all finalists fail, the result is accepted as evidence that RCD-v2 Phase 1A methodology is still insufficient.

If one or more finalists pass, they remain research candidates only. True confirmation requires fresh forward data after the current dataset endpoint.

## Required outputs

Prefix: `SOL_RCD_V2_HISTCONF_`

- CandidateSummary.csv
- PartitionEconomics.csv
- YearEconomics.csv
- AnchorEconomics.csv
- HourEconomics.csv
- AugustShadow.csv
- Result.md
- Status.txt
- Run.log
