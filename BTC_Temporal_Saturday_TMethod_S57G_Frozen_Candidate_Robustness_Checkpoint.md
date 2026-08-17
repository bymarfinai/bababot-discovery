# BTC Temporal Saturday T-Method S5.7G — Frozen Candidate Robustness

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — BOTH FROZEN CANDIDATES ROBUST-TRADEOFF PASS; NO LIVE BBC MODIFICATION  
**Research only:** live BBC untouched

## Frozen benchmarks
- Static parent: **+$87.200**
- A7.19 official pre-S5.7G full-coverage benchmark: **+$103.383**
- A7.26 preserved selective benchmark: **+$109.587 on 123/139**
- Candidates are unchanged from S5.7F: `NO_BULL_TOP_Q_30` and `NO_POS_TAKER_60`.

## Predeclared S5.7G robust-tradeoff gate
This milestone does not rewrite S5.7F's stricter zero-expander-clipping gate. It separately tests whether limited expander clipping is a stable economic cost.

A candidate passes only if:
1. Discovery and validation delta are both positive.
2. Delta is positive in >=3/4 chronological folds; if a fold has no actions, all action-bearing folds must be positive and at least 3 folds must contain actions.
3. Leave-one-action-out total delta remains >0 after removing any single action.
4. No eventual expander winner is flipped from positive A7.19 PnL to nonpositive.
5. Aggregate stalled rescue is larger than the absolute aggregate expander clipping.

No signal combinations, threshold tuning, alternate snapshots, or exit-price sweep.

## Candidate 1 — NO_BULL_TOP_Q_30
Frozen action:
> On `REJECTED_HINGE`, if still unresolved at +30m and the latest completed 5m candle is NOT bullish with its close in the top quartile of its range, exit at the +30m actual open; otherwise preserve A7.19.

Results:
- Full coverage: **139/139**
- Actions: **9**
- Full PnL: **+$111.240**
- Delta vs A7.19: **+$7.857**
- Discovery delta: **+$4.790**
- Validation delta: **+$3.067**
- WR: **54.68%**
- PF: **1.510**
- Max DD: **28.346**
- Loss streak: **5**

Tradeoff:
- Stalled actions: **7**, rescue **+$10.196**
- Expander actions: **2**, clipping **-$2.340**
- Expander positive -> nonpositive: **0**
- Rescue/clipping economic balance is strongly positive.

Chronological folds:
- Fold 1: actions 0, delta **+$0.000**
- Fold 2: actions 5, delta **+$1.705** = stalled **+$2.915** + expander **-$1.210**
- Fold 3: actions 1, delta **+$3.085** = stalled **+$3.085**, no expander action
- Fold 4: actions 3, delta **+$3.067** = stalled **+$4.197** + expander **-$1.130**

Fold gate: **PASS — 3/3 action-bearing folds positive**.

Action-level jackknife:
- Worst leave-one-action-out total delta: **+$4.772**
- Therefore the candidate remains additive even after its single best action is removed.
- Jackknife gate: **PASS**.

**S5.7G ROBUST TRADEOFF: PASS.**

## Candidate 2 — NO_POS_TAKER_60
Frozen action:
> On `REJECTED_HINGE`, if still unresolved at +60m and mean taker imbalance over the most recent completed 15m is NOT positive, exit at the +60m actual open; otherwise preserve A7.19.

Results:
- Full coverage: **139/139**
- Actions: **5**
- Full PnL: **+$110.238**
- Delta vs A7.19: **+$6.855**
- Discovery delta: **+$4.825**
- Validation delta: **+$2.031**
- WR: **53.24%**
- PF: **1.501**
- Max DD: **28.311**
- Loss streak: **5**

Tradeoff:
- Stalled actions: **4**, rescue **+$8.667**
- Expander actions: **1**, clipping **-$1.812**
- Expander positive -> nonpositive: **0**

Chronological folds:
- Fold 1: actions 0, delta **+$0.000**
- Fold 2: actions 1, delta **+$0.871**
- Fold 3: actions 1, delta **+$3.954**
- Fold 4: actions 3, delta **+$2.031** = stalled **+$3.843** + expander **-$1.812**

Fold gate: **PASS — 3/3 action-bearing folds positive**.

Action-level jackknife:
- Worst leave-one-action-out total delta: **+$2.901**
- Jackknife gate: **PASS**.

**S5.7G ROBUST TRADEOFF: PASS.**

## Interpretation
S5.7F's economic uplift is not explained by one jackpot trade and is not confined to only discovery or validation. Both frozen candidates are additive in every chronological fold in which they actually trigger, survive removal of their best individual action, rescue more stalled PnL than they clip from eventual expanders, and never convert an expander winner into a nonpositive result.

This supports the adaptive mechanism:
> `REJECTED_HINGE` is not itself an exit state; it creates a lower-confidence state that is given a fixed recovery window. Absence of a frozen recovery confirmation can justify earlier monetization while keeping all Saturday entries.

## Champion status after S5.7G
For same-sample Saturday management:
1. **NO_BULL_TOP_Q_30: +$111.240 on 139/139 — highest full-coverage PnL and S5.7G robust-tradeoff PASS.**
2. NO_POS_TAKER_60: **+$110.238 on 139/139 — robust-tradeoff PASS.**
3. A7.26 selective: **+$109.587 on 123/139.**
4. A7.19 frozen prior full-coverage benchmark: **+$103.383 on 139/139.**

`NO_BULL_TOP_Q_30` is therefore the **provisional same-sample full-coverage Saturday champion after robustness**, but it is still based on the same 971-day research sample. It should not be called true OOS-confirmed until tested on genuinely unseen data / forward OOS.

No live BBC modification is made in S5.7G.

## Execution
- Successful workflow run: **32030430056**
- Artifact: `s57g-output`, ID **9288686810**
