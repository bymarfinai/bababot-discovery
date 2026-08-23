# B27CD — BTC 24H Clock-Adaptive R4-Risk SHORT Economics — Preregistration

## Purpose
B27CA supported clock-adaptive pre-break SHORT entries. B27CB showed LOCAL_R = entry - previous-4H Low produces stops that are far too tight. B27CC showed structural winners commonly require adverse excursion around 21–30% of the previous completed 4H range depending on clock.

B27CD tests one frozen, anatomy-derived economic rule. No stop/target sweep is permitted.

Research only. Live BBC unchanged.

## Frozen entry cohort
Reuse exact B27CA/B27CC adaptive filled entries only:
- 00-04 UTC: F05
- 04-08 UTC: F05
- 08-12 UTC: F10
- 12-16 UTC: F05
- 16-20 UTC: F05
- 20-00 UTC: F05

Exact identity must reproduce external 250 / development 380 / reference_validation 177 / pooled major 807 / pooled OOS 427.

## Development-only stop derivation
For each UTC clock independently:
1. use only DEVELOPMENT rows labeled B27CC `structural_winner == True`;
2. use only valid causal `mae_r4` values;
3. calculate P75 of causal MAE as a fraction of previous completed 4H range R4;
4. round UP to the nearest 0.05 R4 increment;
5. the resulting fraction is frozen for that clock and then applied unchanged to external and reference_validation.

No external or validation outcome may affect the stop fraction.

## Economic geometry
For each filled SHORT:
- entry = exact B27CA adaptive fill price;
- R4 = H - L of the immediately previous completed 4H range;
- stop distance = frozen clock stop fraction × R4;
- target distance = exactly the same distance;
- nominal RR = exactly 1:1.

Thus:
- stop = entry + stop_distance;
- target = entry - stop_distance.

No EMA/ATR/volume/regime/weekday filter, trailing stop, break-even, runner, or post-hoc clock removal.

## Causality and ambiguity
Use BTCUSDT raw 5m.

The entry is the persisted B27CA limit fill. On the fill bar, if the high reaches the stop, count STOP. Do not credit a TP on the fill bar because intrabar ordering is unknown.

From the next 5m bar onward:
- if STOP and TP occur in the same bar, STOP wins;
- otherwise first hit wins;
- if neither is hit by the end of the same 4H observation block, exit at the final 5m close (`TIME`).

## Economics
Illustrative notional: $500 per trade.
Round-trip fee: $0.40 per trade.
No additional slippage.

SHORT net PnL = ((entry - exit_price) / entry) × 500 - 0.40.

## Required reporting
Report N, WR, PF, expectancy/trade, total net PnL, TP/STOP/TIME counts for:
- external;
- development;
- reference_validation;
- pooled OOS;
- pooled major;
- every clock on pooled OOS and pooled major.

Also persist the exact development P75 and rounded frozen R4 stop fraction for every clock.

## Frozen gate
`B27CD_R4_RISK_ECON_SUPPORTED` only if:
- N: external >=100, development >=150, validation >=60;
- every major partition expectancy > 0;
- every major partition PF >= 1.20;
- every major partition WR >= 50%;
- pooled OOS expectancy > 0 and PF >= 1.20.

`HIGH_QUALITY_70` is PASS only if the supported rule also has WR >=70% in all three major partitions.

Otherwise verdict is `B27CD_R4_RISK_ECON_NOT_SUPPORTED`.

No failed clock may be removed post hoc inside B27CD.