# SOL LONG Full Character V1 — Trap-Reclaim Deep Anatomy

**Status: CHARACTER_EDGE_FOUND_BUT_NOT_2026_VALIDATED**

## Frozen lineage
- Source universe: `SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1_Trades.csv`
- Total frozen trades: 279
- LONG definition: `SELL_SIDE` liquidity event -> downside sweep/reclaim -> LONG
- Total frozen LONG: 147
- Derivatives-covered LONG: 98
- DEV: <=2024
- REF: 2025-2026

## Stage 1 — OI/taker trap gate
DEV-derived trap gate:
`oi_trap_interaction_1h >= 0.0000605498`

Interpretation: the 1h OI change and direction-normalized taker pressure form a short-trap-like state around a downside liquidity event.

Selected:
- 21 trades
- 17 winners / 4 losers
- WR 80.95%
- Total R +15.42R
- Wilson 95% interval approximately 60.0%-92.3%

No 2026 LONG satisfies this frozen trap threshold.

## Stage 2 — Complete deep anatomy of all 21 trap cases
All 21/21 cases were re-fetched causally from Binance USD-M historical klines:
- SOL 1m: 90m pre-entry
- SOL 5m: 24h pre-entry
- BTC 5m: 4h pre-entry
- ETH 5m: 4h pre-entry

Feature families:
- 30/60/120/240m return
- range
- trend efficiency
- down-bar fraction
- sign flips
- taker-buy share
- candle body / wick / close location
- time since local low
- rebound from local low
- local-low volume/taker anatomy
- BTC/ETH contemporaneous returns
- derivatives OI/crowd/taker features

## Strongest stable discriminator
### Four-hour pre-entry price extension
`m5_ret240`:
- winner median (all trap cases): +0.015%
- loser median: +1.249%
- AUC winner-oriented: 0.191
- DEV AUC: 0.250
- REF AUC: 0.071

Lower 4h pre-entry extension is strongly associated with trap winners.

DEV-only q75 cutoff:
`m5_ret240 <= 0.006314016` (<= +0.6314% over ~4h)

Results:
- DEV: 8W / 1L = 88.89%, +9.80R
- REF 2025: 5W / 0L = 100%, +7.25R
- Combined: 13W / 1L = 92.86%, +17.05R
- Wilson 95% interval for combined WR: approximately 68.5%-98.7%

Sensitivity is not a single-point spike:
- DEV q70 cap ~+0.514% -> 11W/1L overall = 91.67%
- DEV q75 cap ~+0.631% -> 13W/1L = 92.86%
- DEV q80 cap ~+0.714% -> 13W/1L = 92.86%
- DEV q85 cap ~+1.073% -> 15W/2L = 88.24%

This supports an **anti-late-extension guard**, not an exact magic threshold.

## Failure anatomy
Four trap losses split into two repeatable failure modes.

### Failure A — weak local reclaim
2023-08-15:
- 60m SOL return: +0.358%
- 60m rebound from local low: +0.476%
- 240m return: -0.068%
- 4h OI change: +0.643%
- crowd ratio: 1.353

This loss is not late/overextended. It is a **weak-reclaim / insufficient local displacement** failure.

### Failure B — late / overextended trap
Three losses had large positive 4h price extension before entry:
- 2024-08-28: +1.791%, OI4h +2.281%
- 2025-07-30: +1.026%, OI4h +1.918%
- 2025-10-13: +1.472%, OI4h +1.154%

These look like a trap signal arriving **after the move is already extended**, rather than at a fresh directional turning point.

## Stronger exploratory Grade-A variants
These are promising but samples are too small for promotion.

### Local reclaim floor + 4h extension cap
DEV-derived:
- `m5_ret60 >= +0.4213%`
- `m5_ret240 <= +0.6314%`

Results:
- DEV: 6/6 wins
- REF 2025: 4/4 wins
- Combined: 10/10 wins, +9.96R
- Wilson lower 95% bound only ~72.2% because N=10

### OI4h cap
DEV q60:
`oi_change_4h <= +0.3869%`

Within trap cohort:
- DEV: 7/7 wins
- REF 2025: 4/4 wins
- Combined: 11/11 wins, +15.83R
- Wilson lower 95% bound ~74.1%

This may represent a distinction between a **fresh short trap** and a broader multi-hour position build/trend. It is not promoted because N is small and there is no 2026 qualifying trap cohort.

## 2026 regime check
Derivatives-covered 2026 LONG:
- 21 trades
- 13W / 8L = 61.90%
- +4.77R

Exact trap gate `>=0.0000605498`:
- 0 qualifying trades.

Highest 2026 trap value:
- 2026-07-30: +0.00001514
- outcome: LOSS

Most 2026 near-misses have taker ratio >1 (buy-dominant), i.e. the historical OI-up / aggressive-sell short-trap microstructure is largely absent.

Therefore the historical 80-93% trap-reclaim character has **not been validated in the 2026 regime**. The correct live behavior under the frozen gate is inactivity, not lowering the threshold to force trades.

## Cross-market context
BTC/ETH pre-entry returns were included in the deep anatomy. They did not emerge as a stable primary separator of the four losses from the winners and are not promoted.

## Final structural archetype
The strongest evidence currently supports:

1. downside liquidity sweep / SELL_SIDE event;
2. short-trap-like OI/taker condition;
3. reclaim / bullish response;
4. **not already extended materially over the previous ~4h**;
5. stronger candidate quality when local ~60m rebound/displacement is already visible.

Conceptually:

`DOWNSIDE LIQUIDITY -> NEW SHORT/TRAP PRESSURE -> RECLAIM -> FRESH (NOT LATE) -> LONG`

The failure alternatives are:

`TRAP + WEAK RECLAIM -> FAILURE RISK`

or

`TRAP + LATE 4H EXTENSION -> FAILURE RISK`

## Decision
- A real historical LONG character edge is present.
- The original 80.95% trap cohort improves to 92.86% with a simple DEV-derived anti-extension guard.
- 100% variants exist retrospectively but are too small to claim as a robust 100% setup.
- No 2026 exact-gate observations exist, so this is **not yet a current-regime ready-to-trade 80% claim**.
- Do not loosen the trap threshold solely to manufacture 2026 trades.
