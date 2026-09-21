# SOL Score-3 SELL Missing-C Hard-Failure Universe V1 — Preregistration

## Objective

Re-audit the full SOL tradable universe after removing only one previously identified structural hard-failure cohort:

**Score-3 SELL_SIDE with cond_C == 0 while cond_A == cond_B == cond_D == 1.**

No other detector, entry, stop, exit, TP, session, hour, indicator, or numeric threshold is changed.

## Rationale

Prior anatomy work showed the Missing-C cohort is consistently destructive, while Missing-B is regime-dependent and should not be removed wholesale.

The frozen universe for this audit is therefore:

- Score-3 BUY_SIDE: keep all.
- Score-3 SELL_SIDE:
  - keep Missing-A;
  - keep Missing-B;
  - **drop Missing-C only**;
  - keep Missing-D.
- Score-4 SELL_SIDE / LONG: keep.
- Score-4 BUY_SIDE / SHORT: remain excluded as previously frozen.

## Execution stack

Unchanged from SOL Final Tradable Universe Audit V1:
- existing Score-3 / Score-4 entry router;
- RECLAIM_EXTREME initial stop;
- structural-completion / outcome-known-time exit;
- no adaptive TP;
- no session/hour filter.

## Observation window

2020 through **2026-09-21 00:00:00 UTC**.

This is a retrospective robustness audit, not an untouched validation claim.

## Audit integrity

The exact robustness framework and gate thresholds from `SOL_FINAL_TRADABLE_UNIVERSE_AUDIT_V1` are reused without modification:
- core trade/economic gates;
- component gates;
- leave-one-year-out gates;
- bootstrap gates;
- rolling-20 gates;
- 10/20/30 bps friction stress gates.

Additional descriptive fields may report:
- trade retention vs prior universe;
- gross-winner retention vs prior universe;
- removed Missing-C cohort economics;
- removed cohort yearly distribution.

These additional fields do not change the frozen pass/fail gates.

## Stop rule

If the reduced universe fails the existing robustness gates, do not rescue the result inside this V1 with:
- additional structural filters;
- session/hour filters;
- entry rerouting;
- TP/SL changes;
- modified friction assumptions;
- altered gate thresholds.
