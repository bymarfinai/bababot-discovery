# BTC Temporal Saturday T-Method S5.7F — Frozen Recovery Candidates × Management Counterfactual

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — PROMISING FULL-COVERAGE ACTION CANDIDATES FOUND; PREDECLARED PROMOTION GATE NOT YET PASSED  
**Research only:** live BBC untouched

## Frozen design
Three S5.7E recovery candidates were tested separately, without definition changes or combinations:

1. `NO_HIGHER_LOW_30`: on exact `REJECTED_HINGE`, if still unresolved at +30m and `higher_low_recent` is absent, exit at the +30m actual open.
2. `NO_BULL_TOP_Q_30`: on exact `REJECTED_HINGE`, if still unresolved at +30m and the latest completed 5m candle is NOT bullish with close in the top quartile, exit at the +30m actual open.
3. `NO_POS_TAKER_60`: on exact `REJECTED_HINGE`, if still unresolved at +60m and recent completed 15m taker imbalance is NOT positive, exit at the +60m actual open.

Otherwise frozen A7.19 is preserved exactly.

No signal combination, no threshold tuning, no alternate snapshot, no exit-price sweep.

## Parity
- Static parent all 139: **+$87.200**
- A7.19 all 139: **+$103.383**
- Exact rejected cohort: **16** = 7 post-signal expanders / 9 stalled

## Candidate results
### `NO_HIGHER_LOW_30`
- actions **4** = D3 / V1
- full PnL **+$106.594**
- delta vs A7.19 **+$3.211**
- D delta **+$1.431**
- V delta **+$1.780**
- WR **52.52%**
- PF **1.482**
- DD **31.705**
- LS **5**
- stalled: 3 actions, **+$4.421** delta
- expander: 1 action, **-$1.210** delta
- expander positive→nonpositive: **0**
- predeclared gate: **FAIL** (validation action support only N1; expander aggregate damaged)

### `NO_BULL_TOP_Q_30` — strongest same-sample candidate
- actions **9** = D6 / V3
- full PnL **+$111.240**
- delta vs A7.19 **+$7.857**
- D delta **+$4.790**
- V delta **+$3.067**
- WR **54.68%**
- PF **1.510**
- DD **28.346**
- LS **5**
- stalled: 7 actions, **+$10.196** delta
  - D **+$5.999**
  - V **+$4.197**
- expanders: 2 actions, **-$2.340** delta
  - D **-$1.210**
  - V **-$1.130**
- expander positive→nonpositive: **0**
- predeclared gate: **FAIL** only because expander-safety component required nonnegative expander delta.

Per-action note: both eventual expanders cut by this rule remained profitable; the rule reduced their realized profit rather than flipping them to losses. One stalled trade that was already profitable was also clipped, but aggregate stalled economics improved strongly.

### `NO_POS_TAKER_60` — second strong same-sample candidate
- actions **5** = D2 / V3
- full PnL **+$110.238**
- delta vs A7.19 **+$6.855**
- D delta **+$4.825**
- V delta **+$2.031**
- WR **53.24%**
- PF **1.501**
- DD **28.311**
- LS **5**
- stalled: 4 actions, **+$8.667** delta
  - D **+$4.825**
  - V **+$3.843**
- expander: 1 action, **-$1.812** delta, validation only
- expander positive→nonpositive: **0**
- predeclared gate: **FAIL** because expander aggregate was clipped.

## Important interpretation
The S5.7E recovery-state idea has now shown **economic value**, not just classification value.

Both `NO_BULL_TOP_Q_30` and `NO_POS_TAKER_60` improve A7.19 in BOTH discovery and validation, and most of their benefit comes from rescuing the frozen 9-trade stalled cohort.

However, the current sample also shows the unavoidable tradeoff:
> absence of recovery can identify many stalled trades, but it can still occur before a minority of eventual expanders later recover.

Crucially, no eventual expander was flipped from positive to nonpositive by either strong candidate. The predeclared promotion gate was intentionally stricter and therefore rejected them because any aggregate expander clipping failed `expander_safe`.

## Benchmark position
- A7.19 official frozen full-coverage champion before S5.7F: **+$103.383**
- A7.26 preserved selective candidate: **+$109.587** on 123/139 trades
- S5.7F `NO_BULL_TOP_Q_30`: **+$111.240 on 139/139 trades** — highest same-sample Saturday PnL seen among these frozen management variants, but **NOT promoted official yet** because the predeclared gate failed.
- S5.7F `NO_POS_TAKER_60`: **+$110.238 on 139/139 trades** — also above A7.26 same-sample PnL while retaining full entry coverage, but not promoted yet.

## Research decision
**Do not discard this branch.** The action hypothesis has meaningful D/V economic support.

But do not relax the failed gate post hoc merely because headline PnL improved.

The clean next milestone, if continuing, is a robustness study on the two frozen strong candidates (`NO_BULL_TOP_Q_30`, `NO_POS_TAKER_60`) using chronological folds / action-level stability and no new signal definitions. The goal is to determine whether limited expander clipping is a stable cost of rescuing stalled trades or a same-sample accident.

A7.19 remains official until that robustness question is answered. A7.26 remains preserved.

## Execution
Successful workflow run: **32030048279**.
