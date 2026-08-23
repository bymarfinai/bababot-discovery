# B27BY — BTC 24H Adaptive F15 Pre-Second-Low SHORT — Preregistration

## Purpose
Test whether the causal pre-second-touch entry architecture that produced LONG F85 in B27W and SHORT F15 in B27AK transfers to the full-24H B27BE 4H-block SHORT atlas.

This is a direct transfer test, not a new fraction search. The only entry fraction tested is the exact SHORT mirror **F15**.

Research only. No live BBC change.

## Frozen source cohort
Use exactly the persisted `BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv` cohort.

Primary reporting universe: `external`, `development`, `reference_validation`.

Mandatory B27BE K1+OPP0 identity in the three major partitions:
- pooled major: 2,767;
- external: 862;
- development: 1,264;
- reference_validation: 641;
- BULL pooled major: 1,146 = 400 / 500 / 246;
- BEAR pooled major: 1,122 = 203 / 630 / 289;
- SIDEWAYS pooled major: 499 = 259 / 134 / 106.

The B27BE observation design remains frozen:
- BTCUSDT raw 5m;
- all seven calendar days;
- six sequential UTC 4H observation blocks: 00-04, 04-08, 08-12, 12-16, 16-20, 20-00;
- each observation block uses the immediately previous completed 4H high `H` and low `L` as frozen liquidity boundaries;
- no Asia/London/New-York session filter.

## Frozen SHORT chronology
For each B27BE row with `k1_opp0 == True`:

1. `Low Touch #1 / K1` is the first distinct raw-5m visit to `L` under B27BE semantics: `low <= L` and `close >= L`, with zero prior High visits.
2. Consecutive qualifying Low-touch bars belong to the same K1 touch episode.
3. The K1 episode ends only after a completed raw-5m bar that is not a Low touch.
4. If strict `close < L` or strict `close > H` occurs before a causal leave is established, there is no eligible pullback window.
5. Entry search begins only from the next raw-5m bar after the completed leave bar.
6. `L2_ARRIVAL` is the first later raw-5m bar with `low <= L`, including a bar that closes below L.
7. Opposite invalidation is first later completed raw-5m `close > H`.
8. The 4H observation-block end is the time boundary if neither terminal event occurs.
9. The L2/opposite-break terminal bar is never entry-eligible.

## Frozen adaptive F15 entry
Normalize each frozen previous-4H range as Low=0 and High=1.

Only one candidate is permitted:

`F15 = L + 0.15 * (H - L)`

This is adaptive in price because the absolute entry level changes with each immediately previous completed 4H range.

A SHORT limit fill is counted only when an eligible raw-5m bar strictly before the terminal bar spans F15 (`low <= F15 <= high`).

No EMA, ATR, volume, session, weekday, regime, candle-body, distance, or additional price fraction may alter the entry.

## Structural outcome
After a valid F15 fill, structural success is `L2_ARRIVAL` before opposite High close-break or the 4H block end.

L2 is a structural milestone only, not a trading TP. No stop, target, RR, fee, PF, WR economics, leverage, or PnL is tested in B27BY.

## Required reporting
Report:
- K1+OPP0 count;
- clean causal-leave windows;
- F15 fills;
- fill / clean-window rate;
- L2 hits after fill;
- L2 / fill rate;
- median minutes fill -> L2 for successes.

Report these for:
- external, development, reference_validation;
- pooled OOS = external + reference_validation;
- pooled major;
- each causal 4H regime BULL / BEAR / SIDEWAYS pooled-major;
- each of the six UTC 4H clock blocks pooled-major.

Persist one-row-per-B27BE-K1 event with K1, leave, eligibility, fill, L2/opposite-break and terminal timestamps.

## Frozen gates
### Transfer gate
`F15_TRANSFER_PASS` only if ALL hold:
1. exact B27BE K1+OPP0 identities reproduce;
2. every fill is strictly after causal leave and strictly before the terminal bar;
3. external, development, and reference_validation each have >=30 F15 fills;
4. external, development, and reference_validation each have L2/fill >=70%.

### Full-24H adaptive gate
`FULL24H_ADAPTIVE_PASS` only if `F15_TRANSFER_PASS` and additionally:
5. each of the six pooled-major UTC clock blocks has >=30 F15 fills and L2/fill >=65%;
6. each pooled-major regime BULL / BEAR / SIDEWAYS has >=30 F15 fills and L2/fill >=65%.

No clock or regime may be selected post hoc if the universal gate fails.

## Verdicts
- If both gates pass: `B27BY_F15_FULL24H_ADAPTIVE_SUPPORTED`.
- If transfer passes but universal gate fails: `B27BY_F15_TRANSFER_SUPPORTED_NOT_UNIVERSAL`.
- Otherwise: `B27BY_F15_NOT_SUPPORTED`.

A structural pass only permits a separately preregistered economic test. It does not authorize live deployment.
