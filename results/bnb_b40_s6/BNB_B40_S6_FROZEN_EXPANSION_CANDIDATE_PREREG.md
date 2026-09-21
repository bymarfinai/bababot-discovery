# BNB B40-S6 — Frozen Expansion Candidate Validation Preregistration

## Objective
Validate one frozen B40 expansion-state candidate without searching new thresholds or combinations.

S6 asks:
"Once a B40 demand zone has already proven survival by reaching +0.50 event-R, does FAST survival proof identify zones that are materially more likely to continue toward >=1R, >=1.5R, and >=2R?"

## Frozen parent
Use only true B40-S1 SURVIVE zones:
- DEV = 500
- REF = 309

Frozen outcomes:
- GE1R
- GE1_5R
- GE2R

Expected parent parity:
- DEV: 361 / 266 / 205
- REF: 231 / 168 / 134

## Frozen primary candidate
### XP1_FAST_PROOF60
PASS iff:
`time_to_0_5r_min <= 60`

Interpretation:
the demand zone proves that it can deliver +0.50 event-R within 60 minutes of first retest.

The 60-minute cutoff is frozen from B40-S5 before S6 validation.
No alternate proof-speed cutoff is searched.

## Frozen comparison benchmarks
Reported for context only. They cannot replace XP1 in S6.

### B1_NARROW_SOURCE_Q1
PASS iff:
`base_width_pct <= 0.006155789474971198`

This is the frozen DEV Q25 source-width cut from B40-S5.

### B2_STRONG_P5_RANGE_Q4
Among the frozen +5m GE1R-unresolved cohort only:
PASS iff:
`p5_range_r > 0.4509029031810024`

This is the frozen DEV Q75 cut from B40-S5 GE1R analysis.

B2 is not directly comparable to whole-survivor retention because cases that already reached +1R before +5m are outside its cohort.

## Required validation metrics
For XP1 and B1, for DEV, REF, and each year:
- PASS count / rate
- >=1R precision
- >=1.5R precision
- >=2R precision
- uplift over parent survivor base rate
- expander retention for each target
- local-only false-positive count/rate for GE1R
- Wilson 95% interval for GE1R precision
- median survival-proof time within PASS

For B2:
- +5m eligible count
- PASS count/rate
- residual GE1R precision
- uplift over +5m residual GE1R base
- residual GE1R retention
- yearly stability

## Strict no-combination rule
S6 does NOT test:
- fast proof + narrow source
- fast proof + p5 range
- source + reaction scores
- weighted models
- alternate threshold lengths

Those belong only to a later stage if XP1 itself validates.

## Advance rule
XP1 may advance as a frozen Expansion State candidate only if:
1. GE1R precision is materially above the whole-survivor base rate in DEV and REF;
2. >=1.5R and >=2R also improve in the same direction;
3. expander retention remains operationally useful;
4. yearly results do not depend on one isolated year;
5. REF does not collapse relative to DEV.

S6 validates expansion probability only.
It does not define final entry, stop, or take-profit geometry.
