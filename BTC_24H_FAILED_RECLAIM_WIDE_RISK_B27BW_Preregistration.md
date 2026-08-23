# B27BW — BTC 24H BEAR-Origin Failed-Reclaim Widened-Risk Economics — Preregistration

## Purpose

B27BV showed that the B27BU `LOCAL_LOW` stop is routinely breached even on eventual TRANSITION paths: pooled-major TRANSITION median MAE was 2.02 local-R and P75 was 2.81 local-R, while median MFE was 3.47 local-R. B27BW therefore tests only whether two preregistered widened risk envelopes can convert the same causal BEAR-origin FAILED_RECLAIM signal into robust LONG economics.

This is a research economic screen only. No live BBC change is allowed.

## Frozen source cohort and entry

Reuse exactly the persisted B27BT BEAR-origin `FAILED_RECLAIM` signals:
- external: 6;
- development: 20;
- reference_validation: 8;
- pooled major: 34;
- pooled OOS: 14.

Entry remains exactly the OPEN of the raw 5m bar at `eligible_open_ts`, immediately after the completed causal re-break confirmation. No delay, limit entry, session, EMA, ATR, candle, volume, distance, eventual regime outcome, or containing-4H final-close filter is allowed.

## Frozen local risk coordinate

Recompute the unchanged B27BU local risk coordinate:
- `LOCAL_LOW = min(raw 5m low from the first reclaim bar through the first re-break bar inclusive)`;
- `LOCAL_R = entry - LOCAL_LOW`;
- require `LOCAL_R > 0`.

`LOCAL_LOW` itself is not the B27BW stop. It is only the already-audited risk unit inherited from B27BU/B27BV.

## Frozen widened stops

Test exactly two resting stops, derived from the B27BV excursion envelope before B27BW results are inspected:
- `S2`: `stop = entry - 2.0 * LOCAL_R`;
- `S3`: `stop = entry - 3.0 * LOCAL_R`.

No 2.5R, 3.5R, ATR buffer, percentage buffer, swing-low substitution, or other stop is allowed in B27BW.

## Frozen target grid

For each widened stop define `WIDE_R = entry - stop` and test exactly:
- `T1_0`: target = `entry + 1.0 * WIDE_R`;
- `T1_5`: target = `entry + 1.5 * WIDE_R`;
- `T2_0`: target = `entry + 2.0 * WIDE_R`.

This produces six fixed variants: `S2_T1_0`, `S2_T1_5`, `S2_T2_0`, `S3_T1_0`, `S3_T1_5`, `S3_T2_0`.

No target below 1:1 against actual widened risk and no other target are allowed.

## Frozen trade resolution

Starting from the entry 5m bar:
1. stop hit if `low <= stop`;
2. target hit if `high >= target`;
3. if both occur in the same raw 5m bar, score STOP conservatively;
4. if unresolved, time-exit at the earlier of the B27BT detector `exit_effective_ts` or entry + 24 hours;
5. time-exit price is the first raw 5m OPEN at/after that deadline.

The eventual RESUME/TRANSITION label is diagnostic only and cannot affect execution.

## Economics

Use the frozen recent-lineage convention:
- notional: $500 per trade;
- round-trip fee: $0.40;
- no leverage assumption;
- no extra slippage model.

LONG net PnL = `(exit_px / entry_px - 1) * 500 - 0.40`.
Trading win = `net_pnl_usd > 0`.

## Required outputs

For each of the six variants and external / development / reference_validation / pooled OOS / pooled major report:
- signals and executed trades;
- TP / SL / detector-exit / 24h-exit counts;
- WR;
- PF;
- mean net expectancy/trade;
- total net PnL;
- median actual widened risk as % of entry;
- median hold time;
- diagnostic TRANSITION vs RESUME economics.

Persist one row per signal per variant with entry, LOCAL_R, stop, target, exit, and PnL.

## Frozen support and selection gate

A variant is `ROBUST_PASS` only if ALL hold:
1. exact B27BT signal identity reproduces: 6 external / 20 development / 8 reference_validation;
2. entry is exactly the next raw 5m open after re-break confirmation;
3. every executed trade satisfies stop < entry < target and exact S2/S3/T geometry;
4. external / development / reference_validation each have >=5 executed trades;
5. external / development / reference_validation each have positive mean net expectancy/trade;
6. external / development / reference_validation each have PF >=1.20;
7. external / development / reference_validation each have WR >=50%;
8. no eventual regime label or containing 4H final close is used in execution.

`HIGH_QUALITY_70` additionally requires WR >=70% in all three major partitions for the same exact variant.

If multiple variants ROBUST_PASS, select the one with the highest minimum PF across external/development/reference_validation; tie-breaker is higher pooled-major expectancy; second tie-breaker is smaller stop multiplier.

If none passes, verdict is `B27BW_FAILED_RECLAIM_WIDE_RISK_NOT_SUPPORTED`.

Reference_validation has already been inspected in this lineage, so this remains historical discovery evidence rather than pristine live promotion.

Research only. Live BBC unchanged.
