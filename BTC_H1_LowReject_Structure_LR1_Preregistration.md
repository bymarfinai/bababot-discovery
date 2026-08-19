# BTC H1 LOW_REJECT Structure LR1 — Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. Timeframe 1H only.**

## Objective
Test whether the four strongest fixed H1 LOW_REJECT reaction times found by H1-MAP can be upgraded from ~60-62% directional follow-through toward 70-80% by using only the internal structure of the rejecting 1H candle, without shifting times or using lower timeframes.

## Frozen event hours
Exact UTC event hours, inherited from H1-MAP and not re-selected here:
- 04:00 UTC = 11:00 WIB (`LONDON_OPEN -3h`)
- 08:00 UTC = 15:00 WIB (`ASIA_CLOSE 0h` / `LONDON_OPEN +1h`)
- 18:00 UTC = 01:00 WIB next day (`LONDON_CLOSE +2h`)
- 19:00 UTC = 02:00 WIB next day (`LONDON_CLOSE +3h`)

Each event 1H candle is compared with the completed prior-3H range. A qualifying core event is exactly:
- event low < prior3 LOW;
- event high does not exceed prior3 HIGH;
- event close >= prior3 LOW;
=> `LOW_REJECT`, mapped LONG.

Entry diagnostics start at the next 1H open after the LOW_REJECT candle is complete.

## Frozen structural features
Only information inside the completed event candle and completed prior3H range is allowed:
1. `sweep_depth_range` = (prior3_low - event_low) / (prior3_high - prior3_low)
2. `lower_wick_ratio` = (min(event_open,event_close) - event_low) / event_range
3. `close_position` = (event_close - event_low) / event_range
4. `body_ratio` = abs(event_close-event_open) / event_range
5. `range_expansion` = event_range / median(range of the three prior 1H candles)
6. `reclaim_depth_range` = (event_close - prior3_low) / (prior3_high - prior3_low)

No EMA, volume, taker flow, OI, funding, premium, weekday, lower timeframe, or future feature.

## Selection model
One shallow deterministic `DecisionTreeClassifier` is fit on the pooled four-hour development events only:
- criterion=`gini`
- max_depth=2
- max_leaf_nodes=4
- min_samples_leaf=25
- random_state=20260819
- features exactly the six above.

Label = whether LONG direction is positive after the next 3 completed 1H candles from the causal next-1H entry open.

After fitting, select exactly one terminal leaf among leaves with development N>=25 by:
1. highest development 3H positive rate;
2. then highest N;
3. then lower node id.

The exact tree path defining that leaf is frozen before any validation/external result is inspected.

## Evidence partitions
Because the four clock cells themselves were discovered using 2022-2026 H1-MAP, the independent historical check must be earlier data:
- **External untouched**: 2020-01-01 <= event < 2022-01-01.
- **Reference**: 2022-01-01 <= event < 2026-07-30.
  - first 70% of reference events chronologically = development;
  - last 30% = reference validation.
- **Post-cutoff August**: 2026-08-01 onward through completed official archives available at runtime.

Official Binance USD-M BTCUSDT 1H archives are used directly. Missing archives are not fabricated.

## Directional diagnostics
For selected leaf and unfiltered LOW_REJECT control, report:
- N;
- next1H LONG-positive rate;
- next3H LONG-positive rate;
- average/median next3H return;
- four chronological blocks in external data;
- per-hour results for 04/08/18/19 UTC.

## Executable 1:1 diagnostic
Without changing the selected leaf:
- LONG entry = next 1H open;
- structural SL = LOW of the completed LOW_REJECT event candle;
- fee = 0.15% round trip;
- TP raw distance = structural risk + 0.30%, so modeled net reward magnitude equals modeled net loss magnitude (net RR 1:1);
- max hold 6 completed 1H candles;
- same-1H TP/SL ambiguity = adverse/SL first.

This executable layer is diagnostic; the tree is selected only from next3H direction, not PnL.

## Gates
`LR1_STRUCTURE_SUPPORTED` requires the frozen selected leaf:
- reference validation N>=20 and next3H positive rate >=70%;
- external N>=20 and next3H positive rate >=70%;
- at least 3/4 external chronological blocks with N>=5 have next3H positive rate >=60%.

`LR1_80_CANDIDATE` requires:
- reference validation N>=20 and >=80%;
- external N>=20 and >=80%;
- at least 3/4 external blocks N>=5 and >=70%.

Executable net-1:1 results are reported separately and cannot rescue a failed directional gate.

## Guardrails
- 1H only;
- exact four event hours only;
- prior range fixed at 3H;
- no deeper tree, alternative min leaf, or feature additions after result;
- no post-hoc single-hour carveout;
- no TP/SL/RR sweep;
- no live code changes.
