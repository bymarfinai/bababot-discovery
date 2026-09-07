# SOL LONG 15UTC L2 Fast-Fail Anatomy — A50 Preregistration

## Objective

Freeze the supported A20 `R360/15 / E0_RESTING_H -> E40` parent and study only the largest 15UTC loss class: `L2_BREAK_FAST_FAIL_5M`.

The question is **not** whether L2 is recoverable in hindsight. A26 already established that. A50 asks whether the roughly 50/50 split between latent-recoverable L2 and true-failure L2 can be separated using information available no later than the completed 5m failure candle.

## Frozen cohort

Source: `SOL_LONG_15UTC_LOSS_CONVERSION_A26_LOSSES.csv`.

Central 15UTC only:
- Development expected L2 N = 115
- External expected L2 N = 51
- Reference Validation expected L2 N = 68
- Total expected L2 N = 234

Outcome label:
- `LATENT_RECOVERABLE`: post-exit E40 is eventually reached inside the frozen A26 recovery window.
- `TRUE_FAILURE_PROXY`: post-exit E40 is not reached inside that frozen window.

These are future-defined **labels only**. They may never be used as live features.

## Causal observation cutoff

A50 features may use:
1. bars completed before the first H breakout candle,
2. the completed breakout candle,
3. the completed failure candle that defines L2 (`break_to_fail_min = 5`),
4. path information from entry through that completed failure candle.

No bar after the failure candle is permitted in any feature.

## Frozen feature families

### PRE_BREAK_APPROACH
- prebreak last-close distance to H / R
- last 15m / 30m / 60m return / R
- last 30m / 60m range / R
- upper-range occupancy before breakout

### BREAK_CANDLE
- breakout close excess above H / R
- breakout high excess / R
- breakout body / R
- breakout full range / R
- breakout upper/lower wick / R
- breakout close location inside candle

### FAILURE_CANDLE
- failure close relative to H / R
- failure low relative to H / R
- failure depth below H / R
- failure body / R
- failure full range / R
- failure upper/lower wick / R
- failure close location inside candle

### BREAK_TO_FAIL
- breakout-close to failure-close drop / R
- breakout-high to failure-low excursion / R
- maximum excess above H before failure / R
- maximum depth below H by failure / R

### TIMING
- entry-to-break minutes
- entry-to-failure minutes

## Discovery and replication gates

For each feature compare median latent-recoverable vs true-failure L2.

A feature is `directionally replicated` only if:
- Development median gap is non-zero,
- External gap has the same sign,
- Reference Validation gap has the same sign,
- at least 4 adequately populated Development half-year blocks have the same sign as pooled Development.

A feature is `strong replicated` only if additionally:
- Development effect (absolute median gap / pooled IQR) >= 0.30,
- External effect >= 0.10,
- Reference Validation effect >= 0.10.

No threshold grid is allowed in A50.

## Next-step rule

- If zero directionally replicated features: stop this microstructure branch.
- If one or more directionally replicated features exist: A50B may test one minimal causal decision rule at the L2 failure decision point.
- A50B thresholds must be frozen from Development only; External and Reference Validation remain untouched until the rule is frozen.

Research only. Live Baba Bot remains unchanged.