# B27BU — BTC 24H BEAR-Origin Failed-Reclaim LONG Economics — Preregistration

## Purpose

B27BT found a causal BEAR-origin SIDEWAYS failed-reclaim path with pooled-OOS transition rate 78.6% (external 83.3%, reference_validation 75.0%). B27BU tests whether that structural transition edge can be converted into a causal LONG with positive economics without using the eventual regime label or the containing 4H final close at entry time.

This is a research economic screen only. No live BBC change is allowed.

## Frozen source cohort

Use exactly the persisted B27BT episode artifact and select only:
- `origin_state == BEAR`;
- `path_class == FAILED_RECLAIM`;
- major partitions external / development / reference_validation.

Mandatory signal identity:
- external: 6;
- development: 20;
- reference_validation: 8;
- pooled major: 34;
- pooled OOS external + reference_validation: 14.

B27BT chronology is frozen: first 5m close above the prior BEAR swing high -> later completed 5m reclaim close at/below the frozen boundary -> first later completed 5m re-break close above the boundary. The re-break completion is the signal confirmation. No 4H final-close condition is allowed.

## Frozen LONG entry

For each signal:
- confirmation completes at `confirmation_complete_ts`;
- entry is exactly the OPEN of the raw 5m bar at `eligible_open_ts`, i.e. the next 5m bar after the completed re-break confirmation;
- no limit-entry optimization, delay, EMA, ATR, session, candle-body, volume, distance, or other filter is allowed.

## Frozen structural stop

Use one stop only.

For the frozen 48x5m age-2 source interval, let:
- `RCL` = first reclaim bar identified by B27BT;
- `RB` = first re-break bar identified by B27BT.

`LOCAL_LOW = min(raw 5m low from RCL through RB inclusive)`.

LONG stop = exact `LOCAL_LOW` as a resting stop.

Require `LOCAL_LOW < actual next-open entry`. If not, mark the signal invalid and do not silently alter the stop.

No ATR buffer, percentage buffer, tick offset, previous swing low, or alternative stop is tested in B27BU.

## Frozen target grid

Risk `R = entry - LOCAL_LOW`.

Test exactly three resting profit targets:
- `R1_0`: entry + 1.00R;
- `R1_5`: entry + 1.50R;
- `R2_0`: entry + 2.00R.

No sub-1R target is allowed. No other target may be added after results are observed.

## Frozen trade resolution

Starting from the entry 5m bar:
1. stop touch: `low <= LOCAL_LOW`;
2. target touch: `high >= target`;
3. if stop and target are both touched in the same 5m bar, score STOP conservatively;
4. if neither resolves first, time-exit at the earlier of:
   - B27BT `exit_effective_ts`, when the completed 4H detector causally leaves SIDEWAYS; or
   - entry + 24 hours;
5. time-exit price is the first raw 5m OPEN at/after that deadline.

The eventual RESUME/TRANSITION outcome may be stored for diagnostics only and cannot alter entry, stop, target, or exit ordering.

## Economics

Use the same illustrative convention as the recent B27 economic lineage:
- notional: $500 per trade;
- round-trip fee: $0.40;
- no leverage assumption required;
- no extra slippage model.

LONG net PnL = `(exit_px / entry_px - 1) * 500 - 0.40`.

Trading win = `net_pnl_usd > 0`.

## Required outputs

For external, development, reference_validation, pooled OOS, pooled major and each target:
- signals;
- executed trades / invalid geometry count;
- TP / SL / regime-exit / 24h-exit counts;
- WR;
- PF;
- mean net expectancy/trade;
- total net PnL;
- median risk distance as % of entry;
- nominal RR;
- median holding time;
- transition-vs-resume diagnostic split.

Persist one row per signal per frozen target with full confirmation, entry, stop, target, exit, and PnL values.

## Frozen support gate

A target is `ROBUST_PASS` only if ALL hold:
1. exact B27BT BEAR FAILED_RECLAIM identity reproduces: 6 external / 20 development / 8 reference_validation;
2. entry is exactly the next raw 5m open after causal re-break confirmation;
3. all executed trades satisfy stop < entry < target;
4. each of external / development / reference_validation has >=5 executed trades;
5. each of external / development / reference_validation has positive mean net expectancy/trade;
6. each of external / development / reference_validation has PF >=1.20;
7. each of external / development / reference_validation has WR >=50%;
8. no eventual regime outcome or 4H final close is used for entry or risk geometry.

`HIGH_QUALITY_70` additionally requires WR >=70% in external, development, and reference_validation for the same exact target.

If multiple targets are ROBUST_PASS, predeclared selection is highest minimum PF across the three major partitions; tie-breaker is higher pooled-major expectancy. If none pass, verdict is `B27BU_BEAR_FAILED_RECLAIM_LONG_NOT_SUPPORTED`.

Reference_validation has already been inspected in the lineage, so this remains historical discovery evidence rather than pristine live promotion.

Research only. Live BBC unchanged.
