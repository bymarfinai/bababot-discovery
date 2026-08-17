# BTC Temporal Saturday S6.0 — Dynamic Direction Oracle Opportunity

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — ORACLE CAPACITY PASS FOR DYNAMIC-DIRECTION RESEARCH; NOT A CAUSAL RULE  
**Research only:** live BBC untouched

## Frozen question
For the exact 50 frozen Saturday BUY trades that never reach +0.50% favorable excursion, what happens if direction is mirrored to SHORT from the exact same Saturday 18:00 WIB entry using the same TP2.6%, SL1.2%, max-hold18h geometry?

`NO +0.50` is a hindsight label and cannot be used live. This milestone measures whether there is enough opposite-direction capacity to justify learning a causal pre-entry BUY-vs-SELL selector.

## Frozen mirrored SHORT mechanics
- exact same 18:00 WIB / 11:00 UTC entry open;
- TP 2.60%, SL 1.20%, max hold 18h;
- adverse-first on same-5m ambiguity;
- fixed $500 notional, $0.75 round-trip fee;
- funding sign reversed correctly for SHORT;
- no alternate entry, threshold sweep, classifier, or management tuning.

## Parity
- Saturday entries: **139**
- frozen static BUY parent: **65W/74L = 46.76% WR**, **+$87.200**
- reached +0.50%: **89**
- never reached +0.50%: **50**

## Exact 50 NO+0.50 cohort
Original BUY:
- **2/50 wins = 4.00% WR**
- **-$162.439**

Mirrored SHORT from the same entry:
- **30/50 wins = 60.00% WR**
- **+$82.933**
- PF **6.407**
- max DD **2.564**
- loss streak **2**

Directional recoverability:
- BUY loss -> SHORT win: **30**
- SHORT better than BUY: **43/50**
- both directions lose: **18**
- both directions win: **0**

This is a large and economically meaningful opposite-direction opportunity.

## Chronology split — exact NO+0.50 cohort
### Discovery
- N **29**
- BUY: **1/29 = 3.45% WR**, **-$107.127**
- SHORT: **18/29 = 62.07% WR**, **+$61.182**
- BUY loss -> SHORT win: **18**
- SHORT better: **24/29**

### Validation
- N **21**
- BUY: **1/21 = 4.76% WR**, **-$55.312**
- SHORT: **12/21 = 57.14% WR**, **+$21.751**
- BUY loss -> SHORT win: **12**
- SHORT better: **19/21**

The opposite-direction opportunity transfers across both discovery and validation.

## Static-parent hindsight hybrid
Keep original static BUY for the 89 trades that eventually reach +0.50%, and replace the exact 50 hindsight NO+0.50 trades with mirrored SHORT from entry.

Result:
- **93W/46L = 66.91% WR**
- **+$332.571**
- PF **4.627**
- max DD **13.546**
- loss streak **3**

70% of 139 requires **98 wins**. Static parent has 65 wins, so needs +33. This hindsight direction hybrid adds **+28 net wins**, reaching 93 wins, so **direction switching alone on the NO+0.50 cohort is not enough to reach 70% when paired with the raw static parent**.

## Stronger per-trade best-direction ceiling
For context only, selecting the better of static BUY vs static SHORT per trade in hindsight gives:
- **108/139 = 77.70% WR**
- **+$458.948**

This is not a strategy, but it proves that under the same fixed TP/SL/hold geometry, more than 70% of Saturdays have at least one profitable direction available.

## Cross-check with the already-frozen S5.7G management champion
S5.7G `NO_BULL_TOP_Q_30` is already frozen at:
- **76W/63L = 54.68% WR**
- **+$111.240 on 139/139**

Because S5.7G can only act after a +0.50% hinge, all 50 NO+0.50 trades are unchanged from the static parent under this management layer. Therefore their contribution remains **2 wins / -$162.439** inside the S5.7G total.

Replacing only those exact hindsight 50 NO+0.50 trades with the S6.0 mirrored SHORT outcomes, while preserving frozen S5.7G management for the remaining trades, produces the following **derived hindsight full-stack capacity**:
- wins: **76 - 2 + 30 = 104**
- **104/139 = 74.82% WR**
- **+$356.611**
- PF **6.090**
- max DD **10.043**
- loss streak **2**
- discovery: **78.31% WR**, **+$239.687**
- validation: **69.64% WR**, **+$116.924**

This derived stack is still hindsight because the NO+0.50 label is unknowable at entry. It is NOT a deployable strategy. But it demonstrates that the user's 70% full-coverage target is structurally feasible only when **direction selection and adaptive management are combined**, not when either layer is used alone.

## Interpretation
The key Saturday problem is now clearer:
1. once BUY proves +0.50%, the long cohort is already strong (historically ~70.8% WR under the static parent before adaptive management);
2. the 50 trades that never prove +0.50% are overwhelmingly bad as BUYs;
3. many of those same timestamps are profitable as SHORTs, and this transfers D/V;
4. therefore the main missing intelligence is a **causal pre-entry direction selector**, not more post-entry BUY exit tuning.

## Research decision
**S6 dynamic-direction branch is justified.**

Do not use the hindsight NO+0.50 label live. Do not flip all Saturdays to SHORT. Do not tune entry timing from this oracle result.

The clean next milestone is to build a **pre-entry causal feature atlas** using only information available before 18:00 WIB, with labels based on which frozen direction outcome is economically preferable. The goal is to see whether BUY-proven / SHORT-opportunity days can be separated without future leakage.

A7.19/A7.26/S5.7G remain preserved. No live BBC modification is made.

## Execution
- Successful workflow run: **32031664923**
- Artifact: `s60-output`, ID **9289133591**
- Script: `research/s60_saturday_dynamic_direction_oracle.py`
