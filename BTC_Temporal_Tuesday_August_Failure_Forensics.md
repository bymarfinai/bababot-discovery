# Tuesday August Failure-to-Develop Forensics

**Status: COMPLETE — forensic only; frozen A5.11 unchanged; live BBC untouched.**

## Reproduction gate
- Historical A5.11 parity: **PASS**; 89/139 wins, PnL **$+130.33**.

## Headline
- Historical +0.50% development rate: **69.1%** (96/139).
- August development rate: **0.0%** (0/3).
- August frozen PnL: **$-5.68**.

## August pre-entry state

| Date | MFE | PnL | 6h ret | Overnight | EMA spread | vs EMA20 | EMA20 1h slope | 24h loc | 24h range | Taker1h | Robust bad-state hits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-04 | 0.468% | $-4.75 | -0.243% | -0.243% | -0.054% | +0.009% | -0.204% | 0.737 | 2.876% | -0.066 | 0 |
| 2026-08-11 | 0.193% | $-0.82 | +0.249% | +0.249% | -0.029% | -0.001% | -0.071% | 0.126 | 2.486% | -0.173 | 0 |
| 2026-08-18 | 0.416% | $-0.10 | +0.337% | +0.337% | -0.030% | -0.040% | -0.060% | 0.823 | 2.992% | -0.038 | 0 |

## Natural binary states that were bad in BOTH chronology slices

A state is listed only when its skipped subgroup had negative PnL and lower +0.50% development rate in both D and V.

- **None.** No predeclared natural binary state met the strict cross-slice bad-state rule.

## Discovery-quartile states that were bad in BOTH chronology slices

Thresholds are Q25/Q75 from the first 83 Tuesdays only; no August tuning.

- **None.** No discovery-quartile tail met the strict cross-slice rule.

## August historical percentiles

These percentiles are descriptive only; they are useful for seeing whether August was structurally unusual.

### 2026-08-04
- Most extreme pre-entry features: taker4h 4th pct, ema20_slope1h 13th pct, range6 19th pct, range24 19th pct, ret3h 24th pct, taker1h 24th pct.
- Strict robust bad-state gate hits: **0**.
### 2026-08-11
- Most extreme pre-entry features: range6 1th pct, loc24 4th pct, taker1h 6th pct, range24 13th pct, ret12h 14th pct, mon_ret 15th pct.
- Strict robust bad-state gate hits: **0**.
### 2026-08-18
- Most extreme pre-entry features: range6 16th pct, range24 21th pct, loc24 78th pct, ret24h 73th pct, ema20_slope1h 29th pct, ret1h 32th pct.
- Strict robust bad-state gate hits: **0**.

## Execution interpretation

- A deployable WAIT guard must be based only on pre-entry information and should first survive D/V chronology without using August to choose its numeric threshold.
- If a robust historical gate also catches August, it becomes a **candidate shadow guard**, not an immediately deployable live rule.
- If no strict gate exists, the correct action is to keep Tuesday frozen and treat August as a regime warning rather than manufacture a filter from three losses.

## Guardrail
Robust labels require negative skipped PnL and lower develop-rate in both D and V. V is same-sample report-only, not untouched OOS. August is not used to define feature signs or quartile thresholds. Do not deploy a new gate solely because it catches N=3 August losses; freeze any candidate and forward-test it first.
