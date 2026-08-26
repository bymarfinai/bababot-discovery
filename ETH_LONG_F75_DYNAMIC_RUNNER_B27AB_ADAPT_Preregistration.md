# ETH LONG B27AB-Adapt — Post-Breakout Dynamic Runner — Preregistration

## Question
Can the frozen ETH F75 LONG family improve realized economics by replacing the fixed E10 take-profit with a causal 5m structural runner after breakout acceptance?

## Frozen source cohorts
1. BLIND_F75 — exact B27W-Adapt F75 fills, fixed baseline from B27Z-Adapt E10+D60.
2. EARLY_RECLAIM — exact executed B27AA-Adapt EARLY_RECLAIM entries, primary cohort.
3. SAME_BAR_REJECTION — exact executed B27AA-Adapt SAME_BAR_REJECTION entries, diagnostic.

No entry redetection or F-level change.

## Frozen pre-breakout protection
- completed-close invalidation below F15 (D60 from F75)
- no fixed TP in runner mode
- H2 remains milestone only
- breakout acceptance = first completed raw 5m close > H

## Runner activation and trail
At the completed close of first close > H:
- runner becomes active;
- minimum trail is F15;
- active trail is max(F15, latest causally confirmed strict 3-bar pivot low known at that close).

A pivot low centered on bar i-1 becomes known only at close of bar i and requires low[i-1] < low[i-2] and low[i-1] < low[i]. Only bars from the frozen entry onward may form pivots.

After activation:
- on each completed bar, first test close < already-active trail; if true exit at that close;
- otherwise any newly confirmed pivot above trail ratchets trail upward for later bars;
- trail never decreases;
- no ATR/percentage/body/EMA/volume/regime parameter.
- if still open at session end, exit at session-end open.

## Economics
USD 500 notional, USD 0.40 round-trip fee.

## Frozen primary gate
B27AB_PRIMARY_RUNNER_SUPPORTED requires on EARLY_RECLAIM:
1. runner expectancy > fixed E10 baseline expectancy in external, development, and reference_validation;
2. runner PF >=1.00 in each major partition;
3. pooled-major runner net > pooled-major fixed baseline net.

Blind F75 and SAME_BAR are diagnostics only. August is telemetry only.

Research only; no live changes.