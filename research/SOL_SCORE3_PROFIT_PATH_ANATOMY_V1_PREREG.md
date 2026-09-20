# SOL Score-3 Profit-Path Anatomy V1 — Preregistration

## Objective

Characterize the post-entry profit path of **anatomy score = 3** SOL trades under the already-frozen upstream stack.

This is NOT a TP optimization experiment.

The questions are:

1. how much favorable excursion is typically available after entry;
2. when the favorable peak occurs;
3. how much of that excursion is given back before the frozen structural horizon;
4. whether simple causal giveback signatures appear before profit erosion;
5. whether those signatures are stable enough to justify a later adaptive-exit experiment.

## Frozen upstream stack

Detector:
- actionable structural-liquidity detector;
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

Entry:
- score 3 -> FIVE_MIN_REVERSAL_BREAK.

Initial SL:
- static RECLAIM_EXTREME.
- no post-entry tightening.

No TP is active in V1 anatomy.

Only filled score-3 entries are analyzed.

## Evidence split

- 2020-2024 = anatomy discovery.
- 2025 = retrospective consistency check only.
- 2026+ CLOSED for V1.

2025 has already been observed in prior TP experiments, so it is not an untouched holdout.

No adaptive-exit rule is promoted in this experiment.

## Trade path horizon

From entry until first of:
1. static RECLAIM_EXTREME SL hit; or
2. frozen structural-outcome-known time.

If SL is hit, path ends at SL.

If SL is not hit, terminal value is measured at the OPEN of the first 5m bar at or after structural-outcome-known time.

Conservative same-bar convention:
- if entry and SL can both be reached in the same 5m bar, SL is counted.

## R definition

`1R = abs(entry - RECLAIM_EXTREME SL)`

Directional favorable excursion:

SHORT:
`(entry - subsequent_low) / R`

LONG:
`(subsequent_high - entry) / R`

Directional adverse excursion:

SHORT:
`(subsequent_high - entry) / R`

LONG:
`(entry - subsequent_low) / R`

## Core anatomy features

For every score-3 filled trade:

1. `mfe_r`
2. `mae_r`
3. `time_to_mfe_min`
4. `horizon_or_stop_r`
5. `giveback_r = mfe_r - horizon_or_stop_r`
6. `retained_fraction = horizon_or_stop_r / mfe_r` when MFE > 0
7. first-touch times for:
   - +0.25R
   - +0.50R
   - +0.75R
   - +1.00R
   - +1.50R
8. whether static SL was hit before the structural horizon.

Report separately for:
- positive structural events;
- negative structural events;
- BUY_SIDE;
- SELL_SIDE;
- each year.

## Profit-path cohorts

For positive structural events only:

### NEVER_REACHED_050R
MFE < 0.50R.

### RETAINED
MFE >= 0.50R and giveback at terminal < 0.25R.

### MODERATE_GIVEBACK
MFE >= 0.50R and terminal giveback is >= 0.25R but < 0.50R.

### LARGE_GIVEBACK
MFE >= 0.50R and terminal giveback >= 0.50R.

These cohorts are descriptive labels only.

## Frozen causal giveback signatures

Evaluate the following signatures only after running MFE has reached at least +0.50R.

### ABS_DD_025R
First completed 5m CLOSE whose directional drawdown from the running favorable best is >= 0.25R.

### ABS_DD_050R
First completed 5m CLOSE whose directional drawdown from the running favorable best is >= 0.50R.

### FRAC_DD_25PCT
First completed 5m CLOSE that gives back >=25% of the running MFE.

Requires running MFE >=0.50R.

### FRAC_DD_50PCT
First completed 5m CLOSE that gives back >=50% of the running MFE.

Requires running MFE >=0.50R.

### TWO_OPPOSITE_CLOSES
After reaching +0.50R:
- SHORT: first occurrence of two consecutive bullish 5m closes;
- LONG: first occurrence of two consecutive bearish 5m closes.

### MICRO_BREAK_3BAR
After reaching +0.50R:
- SHORT: first completed 5m CLOSE above the highest HIGH of the prior 3 completed 5m bars;
- LONG: first completed 5m CLOSE below the lowest LOW of the prior 3 completed 5m bars.

All signatures are evaluated causally with no future bars.

## Signature diagnostics

For each signature report:

1. trigger rate among positive structural events that reached +0.50R;
2. trigger rate among negative structural events that reached +0.50R;
3. median MFE at trigger;
4. median realized R if hypothetically exited at trigger CLOSE;
5. median final/horizon R without exit;
6. median `saved_r = trigger_close_r - final_r`;
7. recovery rate:
   - after trigger, price later exceeds the pre-trigger running favorable best before path end;
8. new-peak-after-trigger median increment R;
9. time from trigger to path end;
10. same statistics by 2020-2024 aggregate and retrospective 2025.

A signature is called a:

`PROFIT_GIVEBACK_SIGNATURE_CANDIDATE`

only if in 2020-2024 positive structural events:

1. eligible positive trades reaching +0.50R >= 80;
2. signature trigger N >= 40;
3. median saved_r >= +0.20R;
4. recovery rate <= 35%;
5. median trigger-close R > 0;
6. median saved_r > 0 separately in at least 4 of 5 years.

Retrospective 2025 consistency requires:
- eligible positive trades reaching +0.50R >= 15;
- trigger N >= 8;
- median saved_r > 0;
- recovery rate <= 45%;
- median trigger-close R > 0.

No signature threshold may be changed after results.

## Interpretation

This experiment does not create a TP.

A successful signature means:

> after a score-3 trade has already developed profit, a causal path-degradation event repeatedly appears before a substantial terminal giveback and does not usually recover to a new favorable peak.

Only such a signature may be promoted into a separate adaptive-exit validation experiment.

2026_PLUS=CLOSED
