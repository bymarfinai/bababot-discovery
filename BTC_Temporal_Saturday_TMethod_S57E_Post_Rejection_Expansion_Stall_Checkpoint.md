# BTC Temporal Saturday T-Method S5.7E — Post-Rejection Expansion vs Stall Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; FIXED CONFIRMATION CANDIDATES FOUND, NO MANAGEMENT ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen causal design
- Cohort: exact 16 S5.7C/S5.7D `REJECTED_HINGE` trades.
- `REJECTED_HINGE`: upper wick of the first completed +0.50% hinge candle is >=50% of full candle range.
- Overall outcome landmark: post-signal +0.80% expansion, inherited from the existing Saturday deep-runner geometry.
- Exact outcome parity: **7 post-signal expanders / 9 stalled**.
- Predictor snapshots: **+15m / +30m / +60m** after rejected morphology becomes knowable.
- At each snapshot, only trades still alive and not already at +0.80% are evaluated. The target is future +0.80% after the snapshot.
- No feature threshold sweep, no new exit, no TP/partial TP, no sizing change, no A7.19 override.

## Frozen parity
- Static parent all 139: **+$87.200**
- A7.19 all 139: **+$103.383**
- Rejected cohort: **16**
- Post-signal expanders: **7**
- Stalled: **9**

Outcome labels are hindsight only, but they confirm why the branch matters economically:
- 7 expanders produce A7.19 aggregate **+$39.174**
- 9 stalled produce A7.19 aggregate **-$2.228**
- expander median post-signal MFE **+1.450%**
- stalled median post-signal MFE **+0.510%**

This does **not** itself define a causal rule; it establishes that correctly separating expansion from stall would matter.

## Snapshot support
| Snapshot | Period | N | Alive | Already +0.8 | Unresolved | Future expand N/rate |
|---:|---|---:|---:|---:|---:|---:|
| 15m | full | 16 | 15 | 0 | 15 | 7 / 46.7% |
| 15m | discovery | 10 | 10 | 0 | 10 | 4 / 40.0% |
| 15m | validation | 6 | 5 | 0 | 5 | 3 / 60.0% |
| 30m | full | 16 | 15 | 2 | 13 | 5 / 38.5% |
| 30m | discovery | 10 | 10 | 1 | 9 | 3 / 33.3% |
| 30m | validation | 6 | 5 | 1 | 4 | 2 / 50.0% |
| 60m | full | 16 | 14 | 3 | 12 | 4 / 33.3% |
| 60m | discovery | 10 | 9 | 2 | 8 | 2 / 25.0% |
| 60m | validation | 6 | 5 | 1 | 4 | 2 / 50.0% |

The unresolved validation support is therefore very small at 30m/60m. Any 100% rate from a single positive validation observation must not be treated as a finished trading rule.

## Fixed confirmation events that pass the predeclared gate
The gate required signal and non-signal support in both discovery and validation, the declared expansion direction in both halves, and >=20 percentage-point full-sample effect.

### 1) +30m `higher_low_recent`
- Full: signal expansion **50.0%** vs no-signal **20.0%** → **+30.0pp**
- Discovery: **40.0% vs 25.0%** → +15.0pp
- Validation: **66.7% vs 0.0%** → +66.7pp
- Support D yes/no: **5 / 4**
- Support V yes/no: **3 / 1**

Direction transfers, but the validation no-signal comparator is only N1.

### 2) +30m `last_bull_top_q`
Definition: latest completed 5m candle is bullish and closes in the top quartile of its range.
- Full: **66.7% vs 30.0%** → **+36.7pp**
- Discovery: **50.0% vs 28.6%** → +21.4pp
- Validation: **100% vs 33.3%** → +66.7pp
- Support D yes/no: **2 / 7**
- Support V yes/no: **1 / 3**

Direction transfers, but validation signal-positive is only N1.

### 3) +60m `recent_taker_pos`
Definition: mean taker imbalance over the most recent completed 15m is positive.
- Full: **50.0% vs 16.7%** → **+33.3pp**
- Discovery: **40.0% vs 0.0%** → +40.0pp
- Validation: **100% vs 33.3%** → +66.7pp
- Support D yes/no: **5 / 3**
- Support V yes/no: **1 / 3**

This is the cleanest flow-mechanism clue, but again validation signal-positive is N1.

## Continuous path evidence
No cutoff is promoted; these are rank/median clues only.

### +15m — early renewed excursion already matters
- `max_high_progress`: D AUC **0.792**, V **1.000**, EXPAND_HIGH
  - full median expander **+0.512%** vs stalled **+0.458%**
- `max_close_progress`: D **0.667**, V **1.000**, EXPAND_HIGH
  - full median **+0.485% vs +0.359%**
- `ema20_dist`: D **0.625**, V **1.000**, EXPAND_HIGH
  - full median **+0.198% vs +0.127%** above EMA20

Interpretation: within 15m, expanders tend to re-establish higher price acceptance rather than merely print another named candlestick pattern.

### +30m — price acceptance is the strongest separation
- `decision_progress`: D AUC **0.889**, V **1.000**
  - full median expander **+0.482%** vs stalled **+0.283%**
- `close_vs_hinge_high`: D **0.833**, V **1.000**
  - full median **-0.044% vs -0.279%** below the rejected hinge high
- `last_body_ratio`: D **0.833**, V **1.000**
  - full median **0.604 vs 0.388**

Interpretation: expanders are typically much closer to repairing the rejected high and have a more committed latest candle body by 30m.

### +60m — retained floor + flow confirmation become important
- `recent15_taker`: D AUC **0.833**, V **1.000**
  - full median expander **+0.013** vs stalled **-0.086**
- `min_close_progress`: D **0.833**, V **0.750**
  - full median expander **+0.341%** vs stalled **+0.178%**
- `min_low_progress`: D **0.833**, V **0.750**

Interpretation: rejected trades that still expand tend to preserve a higher floor and later regain buying flow; stalled trades show weaker retained structure and more negative recent taker flow.

## Important non-promotion
A post-hoc observation is that at +30m the conjunction `higher_low_recent AND last_bull_top_q` occurs in only **2 trades**, one discovery and one validation, and both later expand. This is **not promoted** because that conjunction was not predeclared and N=2 is far too small.

Likewise, no continuous cutoff is selected from the observed medians/AUCs.

## S5.7E verdict
**FORENSIC PASS.** There is causal evidence that rejected hinges can be separated into renewed-expansion vs stall states after the rejection:

> **early renewed price acceptance → higher-low / stronger close structure → later positive taker recovery**

is the emerging expansion mechanism.

However, **NO management action is promoted yet** because:
1. the parent rejected cohort is only 16 trades;
2. unresolved validation support is 5 trades at 15m and only 4 at 30m/60m;
3. two of the three eligible binary candidates have validation signal-positive N1;
4. picking a conjunction or continuous cutoff now would be post-hoc overfit.

## Research decision
- Preserve the three fixed confirmation candidates exactly as discovered; do not tune their definitions.
- Do not turn `REJECTED_HINGE` itself into a cut/TP rule.
- Do not combine the candidates post hoc on this sample.
- If continuing, the clean next milestone is a **candidate robustness / management counterfactual study** using these frozen events, with particular attention to whether a no-recovery/stall state can improve realized economics without damaging the 7 expanders.
- A7.19 remains the official full-coverage Saturday champion.
- A7.26 remains the preserved selective benchmark.

## Execution note
The first workflow attempt failed solely from a pandas object-boolean inversion bug in the reporting function. A dtype-safe runner fixed that implementation issue without changing cohort, labels, features, thresholds, snapshots, or promotion gate. The successful research run is **32029476095**.
