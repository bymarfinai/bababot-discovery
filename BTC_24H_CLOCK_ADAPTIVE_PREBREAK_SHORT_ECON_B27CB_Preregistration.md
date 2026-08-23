# B27CB — BTC 24H Clock-Adaptive Pre-Break SHORT Economic Backtest — Preregistration

## Purpose
Convert the exact supported B27CA clock-adaptive pre-break SHORT structure into a real economic trade without changing the entry selection.

Frozen B27CA clock entry fractions:
- 00-04 UTC -> F05
- 04-08 UTC -> F05
- 08-12 UTC -> F10
- 12-16 UTC -> F05
- 16-20 UTC -> F05
- 20-00 UTC -> F05

The B27CA entry occurs after Low Touch #1 / K1 has causally ended, during the pre-return window, and strictly before the first later genuine Low #2 / Low close-break / opposite High close-break terminal bar.

This experiment tests economics only. It may not alter the B27CA clock fractions, K1/OPP0 identity, causal leave semantics, fill timestamp, or session/block structure.

Research only. Live BBC unchanged.

## Frozen source identity
Use exactly the persisted B27CA candidate and selection outputs:
- `BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Candidates.csv`
- `BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Selection.csv`

Primary partitions:
- external
- development
- reference_validation

B27CA exact selected-clock fills must reproduce before economics are evaluated.

No regime filter, weekday filter, session relabeling, EMA, ATR, volume, candle-body, or future information may alter the cohort.

## Entry
For each selected B27CA candidate row with `filled == True`:
- `L` = frozen previous completed 4H Low
- `H` = frozen previous completed 4H High
- `R4 = H-L`
- selected fraction `f` is frozen by clock from B27CA
- entry = `L + f*R4`
- entry timestamp = exact B27CA fill bar start

The position is considered filled at the exact limit price when the raw 5m fill bar spans the entry.

## Adaptive risk unit
Define one local risk unit from the already-frozen entry geometry:

`LOCAL_R = entry - L = f * R4`

Thus:
- F05 clocks use `LOCAL_R = 0.05*R4`
- F10 clock uses `LOCAL_R = 0.10*R4`

Require `LOCAL_R > 0`.

## Frozen stop/target grid
Six variants only; every nominal reward:risk is >=1:1.

| Variant | Stop distance | Target distance | Nominal RR |
|---|---:|---:|---:|
| S1_T1 | 1.0 LOCAL_R | 1.0 LOCAL_R | 1.00 |
| S1_T1_5 | 1.0 LOCAL_R | 1.5 LOCAL_R | 1.50 |
| S1_T2 | 1.0 LOCAL_R | 2.0 LOCAL_R | 2.00 |
| S1_5_T1_5 | 1.5 LOCAL_R | 1.5 LOCAL_R | 1.00 |
| S1_5_T2 | 1.5 LOCAL_R | 2.0 LOCAL_R | 1.33 |
| S2_T2 | 2.0 LOCAL_R | 2.0 LOCAL_R | 1.00 |

For a SHORT:
- stop = `entry + stop_multiple*LOCAL_R`
- target = `entry - target_multiple*LOCAL_R`

No extra variants may be added after results are observed.

## Chronological execution
Raw event clock is repository BTCUSDT 5m.

For each exact B27CA fill and each frozen variant:
1. Entry is the exact B27CA limit fill price on the B27CA fill bar.
2. On the fill bar, a same-bar wick to/through the stop is counted as STOP conservatively because intrabar ordering relative to the entry is unknowable.
3. Same-fill-bar target touches are NOT credited; the target may only win from the next raw 5m bar onward.
4. From the next raw 5m bar through the end of the same frozen 4H observation block:
   - STOP if `high >= stop`;
   - TP if `low <= target`;
   - if both are touched on the same bar, STOP wins conservatively.
5. STOP exits at the exact frozen stop price; TP exits at the exact frozen target price.
6. If neither occurs by observation-block end, time-exit at the final raw 5m close of that block.
7. No bar at or after the next 4H block may affect the trade.
8. One B27CA setup creates at most one trade per variant; observation blocks are sequential so no cross-block overlap exists.

No slippage assumption is added; this is explicitly reported as a limitation.

## Economics
To remain comparable with the existing London->NY economic lineage:
- illustrative notional: $500 per trade
- round-trip fee: $0.40
- SHORT gross return = `(entry - exit_price) / entry`
- net PnL = `gross_return * 500 - 0.40`
- trading win iff `net_pnl_usd > 0`

Report real trading WR, PF, expectancy/trade, total net PnL, TP/STOP/TIME counts, median hold minutes, median winner and loser PnL.

## Required reporting
For every variant report separately for:
- external
- development
- reference_validation
- pooled OOS = external + reference_validation
- pooled major

Also report every variant by each of the six UTC clock blocks for pooled major and pooled OOS, so weak/strong hours are never hidden inside a 24H aggregate.

Persist one row per trade per variant with:
- partition / regime / clock
- entry fraction and entry timestamp/price
- LOCAL_R and R4
- stop/target multipliers and exact prices
- exit timestamp/price/reason
- gross return
- net PnL
- hold minutes

## Frozen robust gate
A variant is `ROBUST_PASS` only if ALL hold:
1. exact B27CA selected fraction map and fill identities reproduce;
2. every trade has `stop > entry > target` and exact frozen geometry;
3. external >=100 trades, development >=150 trades, reference_validation >=60 trades;
4. net expectancy >0 in external, development, and reference_validation separately;
5. PF >=1.20 in external, development, and reference_validation separately;
6. trading WR >=50% in external, development, and reference_validation separately;
7. pooled OOS expectancy >0 and PF >=1.20;
8. no clock/regime/weekday post-hoc exclusion is used to rescue the variant.

`HIGH_QUALITY_70` additionally requires trading WR >=70% in all three major partitions for the exact same variant.

If multiple variants pass, select one by:
1. highest minimum PF across external/development/reference_validation;
2. then highest pooled-OOS expectancy/trade;
3. then higher nominal RR;
4. then tighter stop multiple.

If none pass, verdict is `B27CB_CLOCK_ADAPTIVE_ECON_NOT_SUPPORTED` and no stop/target geometry may be rescued inside B27CB.
If at least one passes, verdict is `B27CB_CLOCK_ADAPTIVE_ECON_SUPPORTED` and the frozen tie-break identifies the candidate.

Research only. Live BBC unchanged.
