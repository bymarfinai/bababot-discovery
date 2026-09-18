# BNB B31-S1 — Causal Swing-Structure Detector Library Preregistration

## Scientific identity
`BNB_B31_S1_SWING_STRUCTURE_LIBRARY_V1`

B31 replaces B30's rolling-state proxies with price-action structures built from causally confirmed swing highs/lows. B30 remains frozen; this is a new identity, not a rescue.

## Stage separation
S1 is **structure only**. It may not evaluate entry, forward direction, WIN/LOSS, MFE/MAE, TP/SL, PnL, PF, DD, fees, leverage, or economics.

Pipeline:
`S1 swing structure -> S2 structure-specific entry -> S3 economics -> OOS/shadow`.

## Data
- BNBUSDT USD-M perpetual 5m Binance Vision OHLC.
- Raw load begins 2021-11-01 UTC to provide structural warmup.
- Census: 2022-01-01 through accepted A1 cutoff 2026-08-26 00:00 UTC.
- Accepted B29-A1 artifact id `10336102957`, SHA256 `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`.
- Raw identity must match A1 at overlapping decision timestamps for ret_15 and 5m close_location within 5e-8.
- 15m structure bars are reconstructed causally from three exact consecutive 5m bars ending on :00/:15/:30/:45.

## Causal swing definition
On 15m bars, a pivot at bar `p` is confirmed only at `p+2 bars`.
- Swing high: high[p] strictly exceeds highs of p-2, p-1, p+1, p+2.
- Swing low: low[p] strictly undercuts lows of p-2, p-1, p+1, p+2.
- Until the confirmation bar closes, the pivot does not exist for the detector.
- Sweep/break levels on a bar may use only pivots confirmed **before** that bar.

## Frozen detector library

### Long
S01 `SWING_LOW_SWEEP_RECLAIM`
- current 15m low < latest previously confirmed swing-low price;
- current 15m close >= that swing-low price.

S02 `HH_HL_SETUP`
- a new swing low is confirmed now;
- latest two confirmed swing lows are rising;
- latest two confirmed swing highs are rising;
- the latest confirmed swing high pivot lies chronologically between the previous swing low and the newly confirmed swing low.
Completion is the confirmation timestamp of the higher low.

S03 `BREAK_RETEST_HOLD`
- a 15m close newly breaks above the latest previously confirmed swing high;
- within the next 1-4 completed 15m bars, price trades to/below the broken level and closes above it.
Completion is the retest-hold close.

S04 `FAILED_BREAKDOWN_RECLAIM`
- a 15m close newly breaks below the latest previously confirmed swing low;
- within the next 1-4 completed 15m bars, a close returns to/above that level.
Completion is the reclaim close.

### Short
S05 `SWING_HIGH_SWEEP_REJECT`
- current high > latest previously confirmed swing-high price;
- current close <= that level.

S06 `LL_LH_SETUP`
- a new swing high is confirmed now;
- latest two confirmed swing highs are falling;
- latest two confirmed swing lows are falling;
- latest confirmed swing low pivot lies between previous swing high and newly confirmed swing high.
Completion is the confirmation timestamp of the lower high.

S07 `BREAK_RETEST_REJECT`
- close newly breaks below latest confirmed swing low;
- within next 1-4 bars price trades to/above broken level and closes below it.

S08 `FAILED_BREAKOUT_REJECT`
- close newly breaks above latest confirmed swing high;
- within next 1-4 bars a close returns to/below the broken level.

## De-duplication
Each detector has its own frozen 60-minute cooldown, retaining the first causal completion. Cross-family overlap is measured, not suppressed.

## S1 viability
A detector is `STRUCTURALLY_VIABLE` iff:
1. pooled N >= 120;
2. at least 4/5 eras (2022-2026*) have >=15 detections;
3. max era share <=35%;
4. source/integrity/causality checks pass.

No outcome metric participates in viability.

## S2
Each viable detector advances independently. Its definition is immutable. Entry mechanisms may use only information known at/after the structure completion timestamp.

## Anti-rescue
- no threshold edits after counts are seen;
- no outcome-driven structure filtering;
- no clock/session filters;
- no merging weak structures;
- no economics before a structure+entry pair is frozen.
