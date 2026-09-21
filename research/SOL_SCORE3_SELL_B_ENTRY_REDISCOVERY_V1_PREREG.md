# SOL Score-3 SELL-SIDE Missing-B Entry Rediscovery V1 — Preregistration

## Scope
One-shot entry-routing rediscovery for the existing SOL structural detector only.

Population is frozen to:
- anatomy_score == 3
- side == SELL_SIDE (long after sell-side liquidity sweep)
- cond_B == 0
- cond_A == cond_C == cond_D == 1

Interpretation: the setup is otherwise Score-3 valid, but the approach starts farther from the liquidity level than the frozen B condition permits.

## Why this experiment exists
The final tradable-universe audit showed Score-3 SELL-SIDE is the friction bottleneck. Missing-C is a structural hard-failure candidate, while Missing-B still contains many structural events/winners but current FIVE_MIN_REVERSAL_BREAK economics are weak. This experiment attempts to preserve those trades by changing entry geometry rather than deleting the cohort.

## Frozen data protocol
- Construction / route selection: 2020-2024 only.
- 2025 is not used for route selection and is opened only after a construction winner is frozen.
- 2026 is not opened in V1.
- Existing detector thresholds and labels are unchanged.
- Existing RECLAIM_EXTREME initial stop is unchanged.
- Existing structural-completion exit is unchanged.
- No session/hour/indicator filter and no new numeric threshold search.

## Frozen entry variants
Only entry forms that already exist in `sol_adaptive_entry_v1_actionable.py`:
1. BASELINE_MARKET
2. GAP_25
3. GAP_50
4. GAP_75
5. LIQUIDITY_LEVEL
6. RECLAIM_BODY_MID
7. RECLAIM_OPEN
8. FIVE_MIN_REVERSAL_BREAK

All use the existing 6-hour entry window and existing causal fill rules.

## Construction eligibility
FIVE_MIN_REVERSAL_BREAK is the current-route comparator.

A candidate route is eligible only if, on 2020-2024:
- filled trades >= 70% of current-route filled trades;
- structural-positive capture >= 70%;
- at least 75% of current-route gross-winning candidate IDs remain gross winners under the candidate;
- gross mean R > 0;
- 10 bps round-trip mean net R > 0;
- 10 bps PF >= 1.10;
- 20 bps round-trip mean net R > 0;
- 20 bps PF >= 1.05;
- at least 4 calendar years have positive gross cumulative R.

If multiple routes pass, freeze exactly one by:
1. highest 20 bps mean net R;
2. highest 20 bps PF;
3. highest current-winner retention;
4. highest filled N;
5. lexical variant name.

No post-result rescue or combination of routes is allowed.

## 2025 confirmation gates
Only the frozen construction winner is tested.

Required:
- signal N >= 10;
- filled N >= 8;
- structural-positive capture >= 60%;
- current-route gross-winner retention >= 70%;
- gross mean R > 0;
- 10 bps mean net R > 0;
- 10 bps PF >= 1.05;
- 20 bps mean net R >= 0;
- 20 bps PF >= 1.00.

If construction produces no eligible winner, 2025 remains unopened and the experiment stops.

If 2025 fails any quality gate, the route is rejected. No threshold tuning, session filtering, SL/TP change, or second route selection is permitted in V1.
