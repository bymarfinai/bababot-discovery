# BNB B30-S1 — Pure Structure Detector Library Preregistration

## Scientific identity
`BNB_B30_S1_STRUCTURE_LIBRARY_V1`

This is a methodology reset after B29. The accepted B29-A1 immutable structure fingerprint remains the data foundation, but B30 separates **structure**, **entry**, and **economics** into different scientific stages.

## Core rule
S1 detects market structures only. It MUST NOT evaluate or contain:
- entry prices or entry triggers;
- future-return direction or WIN/LOSS labels;
- TP/SL, MFE/MAE, RR, PnL, expectancy, profit factor, fees or leverage;
- outcome-driven thresholds;
- clock/session filters.

A structure can advance to S2 only because it is objectively detectable, sufficiently frequent, non-duplicative, and represented across eras. Profitability is not an S1 criterion.

## Immutable source
Use only accepted B29-A1 artifact:
- artifact id: `10336102957`
- file: `BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz`
- SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- rows: `229267`
- first decision: `2020-02-10T14:15:00Z`
- last decision: `2026-08-26T00:00:00Z`

Primary structural census: calendar years 2022, 2023, 2024, 2025, and 2026 through the immutable cutoff.

All predecessor clauses require exact timestamp adjacency. Known A1 gaps may not be crossed.

## Event de-duplication
Each detector is de-duplicated independently with a frozen 60-minute same-detector cooldown. The first causal completion timestamp is retained. Different detector families may fire at the same timestamp; cross-family overlap is measured rather than suppressed.

## Frozen detector library

### Long-side structures

#### S01 `SWEEP_LOW_RECLAIM`
Completion at `t` when:
- `sweep_low_60(t) == 1`.

Interpretation: current bar trades below the previous completed 60-minute low and closes back at/above that prior low.

#### S02 `HL_CONTINUATION`
Completion at `t` when all are true:
- exact `t-15m path_state == PULLBACK_FROM_UP`;
- `path_state(t) == CONT_UP`;
- `structure_state(t) == HH_HL`.

Interpretation: an established upward 6h path undergoes a 60m pullback, then resumes upward while the rolling 60m structure is higher-high/higher-low versus the preceding 60m window.

#### S03 `BREAK_HIGH_HOLD`
Completion at `t` when:
- exact `t-15m break_high_60 == 1`;
- `break_high_60(t) == 1`.

Interpretation: close remains above the previous rolling 60m high for two consecutive 15m decisions.

#### S04 `FAILED_BREAKDOWN_RECLAIM`
Completion at `t` when:
- exact `t-15m break_low_60 == 1`;
- `break_low_60(t) == 0`;
- `close_location(t) > 0`.

Interpretation: a prior downside close-break is no longer present and the current candle closes in its upper half, forming a causal reclaim structure.

### Short-side structures

#### S05 `SWEEP_HIGH_REJECT`
Completion at `t` when:
- `sweep_high_60(t) == 1`.

#### S06 `LH_CONTINUATION`
Completion at `t` when all are true:
- exact `t-15m path_state == PULLBACK_FROM_DOWN`;
- `path_state(t) == CONT_DOWN`;
- `structure_state(t) == LH_LL`.

#### S07 `BREAK_LOW_HOLD`
Completion at `t` when:
- exact `t-15m break_low_60 == 1`;
- `break_low_60(t) == 1`.

#### S08 `FAILED_BREAKOUT_REJECT`
Completion at `t` when:
- exact `t-15m break_high_60 == 1`;
- `break_high_60(t) == 0`;
- `close_location(t) < 0`.

## S1 outputs
For each detector report only structural diagnostics:
- pooled distinct detections;
- detections in each year 2022–2026;
- detections per 365 days of observed data;
- median and 10th percentile inter-event gap;
- maximum single-era share;
- number of eras with at least 15 detections;
- overlap with every other detector at the same completion timestamp;
- structural viability status.

No forward outcome columns are permitted in any S1 artifact.

## Frozen structural viability gate
A detector is `STRUCTURALLY_VIABLE` iff:
1. pooled distinct detections >= 120;
2. at least 4 of 5 eras have >=15 detections;
3. no single era contributes >35% of pooled detections;
4. median inter-event gap >=60 minutes after cooldown by construction;
5. source integrity and exact-adjacency checks pass.

Failure of viability does NOT mean the structure loses money. It means only that this dataset does not provide enough repeated structural observations for the planned independent entry-discovery stage.

## S2 rule
Every S1-viable structure advances independently to a new preregistered **entry-discovery** identity. S2 may define structure-specific entry mechanisms, but may not alter the S1 detector definition.

## S3 rule
Only after one entry mechanism for a structure is frozen may economics be studied. S3 is where TP/SL, excursions, fees, expectancy, PF, DD and PnL first become legal.

## Stop / anti-rescue rules
- Do not add structure clauses after seeing counts to make a detector more frequent.
- Do not merge two weak detectors because their combination looks attractive later.
- Do not use outcomes to redefine an S1 detector.
- Do not use time-of-day filters in S1.
- Do not call any S1 result a trade setup.
