# BNB B38-S12 — E2 Structural Target Selection

**Scientific identity:** `BNB_B38_S12_E2_TARGET_SELECTION_V1`

## Purpose

Hold detector, E2 entry and structural risk geometry constant and test whether target selection can improve payoff without sacrificing the >=70% E2 hit-rate character.

## Frozen entry / SL

Exact B38-S10 E2:
`touch -> reclaim -> one completed hold -> break above max(reclaim_high, hold_high) -> entry at completed 15m close`.

SL:
- lowest 15m low from first touch through E2 entry;
- exact 5m intrabar touch invalidation.

No close-based stop is used in S12.

## Structural objectives known at entry

Use exact B38-S3 causal objective construction:
- confirmed 15m pivot highs;
- frozen pre-retest expansion_high;
- confirmed H1 pivot highs.

No future pivot may be used.

## Full-exit target candidates

### T1 FULL_TP1
Nearest known structural objective.

### T2 FULL_TP2_FALLBACK_TP1
Second known objective if available, otherwise TP1.

### T3 FULL_TP3_FALLBACK_HIGHEST
Third known objective if available; otherwise highest available among TP1/TP2.

### T4 FULL_EXPANSION_FALLBACK_TP1
Frozen pre-retest expansion_high if above entry; otherwise TP1.

### T5 FULL_H1_NEAREST_FALLBACK_TP1
Nearest already-confirmed H1 pivot high above entry; otherwise TP1.

### T6 FULL_MAJOR_NEAREST_FALLBACK_TP1
Nearest price above entry among:
- frozen expansion_high; and
- already-confirmed H1 pivot highs.
Fallback TP1 if no such major objective exists.

## Runner candidates

These preserve the first structural realization while allowing additional structural payoff.

### R1 HALF_TP1_HALF_TP2_BE
- 50% position exits at TP1.
- Remaining 50% targets TP2.
- If TP2 unavailable: full position exits at TP1.
- After TP1 is touched, runner stop becomes entry price **starting from the next completed 5m bar**, avoiding same-bar ordering assumptions.
- runner target before BE -> second half wins TP2 R;
- BE before runner target -> second half exits at 0R.

### R2 HALF_TP1_HALF_MAJOR_BE
- 50% exits TP1.
- Remaining 50% targets the nearest major objective from T6, only if that major objective is strictly above TP1.
- otherwise full exit TP1.
- runner BE activation same as R1.

The 50/50 split is frozen before scoring and is not scanned.

## Scoring

Full exits:
- target touch before SL = WIN;
- SL before target = LOSS;
- same 5m = AMBIGUOUS.

Runner:
- full SL before TP1 = LOSS (-1R);
- TP1 first establishes a positive partial realization;
- runner then resolves from the next 5m bar to major/TP2 or BE;
- trade is classified WIN if final realized R > 0;
- same-bar runner target and BE = AMBIGUOUS_RUNNER.

Report:
- W/L/WR;
- median winning R;
- expectancy R;
- total R;
- PF;
- max loss streak;
- max DD;
- baseline TP1 WIN retention;
- baseline TP1 LOSS -> WIN conversions;
- target-source usage;
- yearly stability.

## Interpretation

S12 is historical development/reference characterization, not clean validation.

The objective is not maximum WR. A useful target policy must retain:
- >=70% WR approximately;
- positive expectancy;
- PF >1;
- stable behavior in DEV and REF.

## Stop rule

Do not:
- alter E2;
- alter SL;
- scan RR thresholds;
- filter trades;
- tune partial fractions;
- add sessions/indicators/derivatives;
- choose targets using future information.
