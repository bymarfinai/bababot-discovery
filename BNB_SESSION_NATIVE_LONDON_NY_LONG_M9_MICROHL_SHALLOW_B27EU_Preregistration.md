# BNB Session-Native LONG M9 MICRO_HL Shallow Guardrail — B27EU Preregistration

## Purpose
Test one simple causal hypothesis from B27ET loss anatomy on a previously unused MICRO_HL economics holdout: losses are more common when the MICRO_HL entry itself occurs too deep below H.

## Frozen setup
- Pair: BNBUSDT
- Structure: B27EM London 08:00 local → New York 09:30 local reference, NY execution 09:30–16:00 local
- Entry: B27EO `E5_MICRO_HL_BULL` unchanged
- TP: `H + 0.30R`
- SL: `entry - 0.30R`
- Round-trip fee: 0.10%
- Slippage: 0.05%
- Total cost: 0.15% per trade
- Intrabar: TP and SL active from entry bar; if both hit same 5m bar, SL wins; unresolved exits at NY close

## Single frozen guardrail
`SHALLOW_MICRO_HL = entry_depth_R <= 0.32452830188679327`

The threshold is the P75 `entry_depth_R` of the 25 development net winners observed in B27ET. It is determined mechanically from development winners and is frozen before any external MICRO_HL economics are evaluated.

No additional feature, time filter, body filter, path-depth filter, or threshold will be tested in B27EU.

## Holdout
Only B27EM `external` partition: 2020-01-01 to 2022-01-01.

Reference-validation, August, and development are not used to select or modify the B27EU rule.

## Comparison
Report both on the same external population:
1. `RAW_MICRO_HL_EXTERNAL`: every frozen E5 eligible entry.
2. `SHALLOW_MICRO_HL_EXTERNAL`: subset satisfying the frozen entry-depth guardrail.

For each cohort report N, TP/SL/session-close counts, same-bar collisions, net WR, average net return/trade, total PnL at $500 illustrative notional, profit factor, max drawdown, median gross RR, and retention.

Also report the share of net losses that hit SL before H, using the same strict-before-exit convention as B27ET, as a descriptive diagnostic only.

## Preregistered support contract
The shallow hypothesis is `SUPPORTED` only if all are true:
- shallow N >= 10;
- retention >= 50% of raw external E5 entries;
- shallow average net return > 0;
- shallow profit factor > 1.0;
- shallow average net return improves by at least +0.0005 absolute (+0.05 percentage points) versus raw external.

`STRONG_SUPPORT` additionally requires shallow profit factor >= 1.20.

If any primary support condition fails, verdict is `NOT_SUPPORTED`.

## Research integrity
- No external result may be inspected before this preregistration is committed.
- No alternate percentile or second feature may be introduced after seeing external results.
- This milestone tests only the frozen shallow-entry hypothesis; it does not promote live trading.
- Main remains untouched.

STOP after B27EU result. No TP/SL retuning, no reference-validation reveal, no August, no SHORT, no live integration.
