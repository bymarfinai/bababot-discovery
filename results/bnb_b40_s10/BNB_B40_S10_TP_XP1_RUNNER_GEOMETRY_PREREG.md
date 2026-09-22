# BNB B40-S10 — TP / XP1 Runner Geometry Preregistration

## Objective
Compare fixed take-profit geometry with frozen XP1-based target extension after the B40 stack has already frozen:
- real H1 demand construction,
- SD1 survival detector,
- MARKET_SD1_CLOSE entry,
- protected-low structural level,
- aligned 15m close structural invalidation.

S10 changes EXIT TARGET GEOMETRY ONLY.

## Frozen parent
Use B40-S7 MARKET_SD1_CLOSE cohort through the B40-S8 parent loader.

Expected cohort:
- DEV = 286 SD1 entries
- REF = 160 SD1 entries

Frozen entry:
- MARKET_SD1_CLOSE

Frozen structural invalidation:
- PROTECTED_LOW_CLOSE15
- every third completed raw 5m close after SD1 decision;
- target remains live intrabar before close-trigger;
- failure exits at actual completed close.

Frozen horizon:
- 24h from first retest.

## Frozen event geometry
Let:
- anchor = first-retouch 15m close
- event_risk = anchor - protected_low
- T0.5 = anchor + 0.50 * event_risk
- T1 = anchor + 1.00 * event_risk
- T1.5 = anchor + 1.50 * event_risk
- T2 = anchor + 2.00 * event_risk

Trade-R denominator for all S10 policies:
initial_risk = MARKET_SD1_CLOSE entry - protected_low

## Frozen XP1 state
XP1_FAST_PROOF60 activates live iff:
- price trades to/above T0.5,
- and that happens within <=60 minutes of FIRST RETEST.

Frozen XP1 signature:
3694b8e4ccfc089d7b65082b0acb784f0e77fdb873998542ee8ce12dfe69c3e8

Important:
- XP1 is evaluated from raw path causally;
- B40-S6 future SURVIVE labels are NOT used to decide runner activation;
- because the SD1 cohort excluded +0.5R resolutions before/on +15m, XP1 activation after entry remains observable post-entry.

## Exactly seven TP policies

### Fixed controls
1. FIXED_T1
   - 100% exit at T1.

2. FIXED_T15
   - 100% exit at T1.5.

3. FIXED_T2
   - 100% exit at T2.

### XP1 full-position extensions
4. XP1_EXTEND_T15
   - default target T1;
   - if XP1 activates before T1 exit, extend 100% target to T1.5;
   - if XP1 never activates by +60m, remain at T1.

5. XP1_EXTEND_T2
   - default target T1;
   - if XP1 activates before T1 exit, extend 100% target to T2;
   - otherwise remain at T1.

### XP1 partial + runner
6. XP1_SCALE50_T15
   - if XP1 does not activate: 100% exit at T1;
   - if XP1 activates: 50% exit at T1 and 50% runner exits at T1.5.

7. XP1_SCALE50_T2
   - if XP1 does not activate: 100% exit at T1;
   - if XP1 activates: 50% exit at T1 and 50% runner exits at T2.

The 50/50 split is frozen a priori as a neutral equal split.
No alternate weights are searched in S10.

## Causal ordering
On every raw 5m bar after SD1:
1. detect whether XP1 becomes active from a T0.5 trade within the 60m window;
2. resting target(s) may execute intrabar;
3. only after bar completion may the aligned 15m close failure trigger.

If a bar reaches T0.5 and a farther target on the same bar within the XP1 window, XP1 is considered active before the farther target because any continuous path to the farther upside level necessarily crosses T0.5 first.

No intrabar order is invented between multiple unrelated downside/upside events beyond this monotonic price-level implication.

## Structural failure after partial realization
If a partial TP has already realized and the remaining runner later hits the aligned 15m structural failure:
- realized R = realized partial target R + runner weight * actual close-based failure R.

No breakeven or trailing stop is introduced in S10.

## Unresolved runner at 24h
- realized closed portions remain realized;
- unresolved open portion contributes 0R in the S10 audit;
- no mark-to-market value is invented.

## Required metrics
For DEV, REF, and every year:
- XP1 activation count/rate
- final full-target hit count/rate
- any TP1 hit count/rate
- stop-before-any-target count
- stop-after-partial count
- unresolved count
- positive / negative / zero realized trade rates
- median/mean positive R
- median/mean negative R
- expectancy per signal
- total R
- PF
- max DD
- max loss streak
- median realized R
- 10th / 90th percentile R

### Runner diagnostics
For XP1 policies:
- XP1 activations
- XP1 activations reaching T1 / T1.5 / T2
- continuation rate T1 -> T1.5 and T1 -> T2 within XP1-active set
- runner giveback to structural failure after T1
- unresolved runner count
- incremental R versus FIXED_T1 on identical signals.

## Decision boundary
S10 does not select a policy from DEV alone.

A runner policy may advance only if:
1. expectancy improves versus FIXED_T1 in both DEV and REF;
2. REF does not rely on one exceptional year;
3. downside / drawdown does not deteriorate disproportionately;
4. the gain is not produced only by a tiny number of extreme T2 hits;
5. partial policies are evaluated on total realized trade R, not headline target-hit rate.

If full-position extension raises payoff but creates unstable giveback, partial + runner is preferred only if it improves both DEV and REF without hidden tail deterioration.

No final leverage or dollar PnL conversion is performed in S10.
