# ETH LONG B27AC-Adapt — E10 Profit-Lock Runner — Preregistration

## Question
Can the frozen ETH F75 LONG family preserve the B27Z E10 profit milestone while still capturing additional upside by converting E10 from a fixed TP into a causal hard profit floor plus structural runner?

## Frozen cohorts
1. BLIND_F75 — exact B27W-Adapt F75 fills, fixed baseline B27Z E10+D60/F15.
2. EARLY_RECLAIM — exact B27AA-Adapt executed EARLY_RECLAIM entries, primary cohort.
3. SAME_BAR_REJECTION — exact B27AA-Adapt executed SAME_BAR_REJECTION entries, diagnostic.

No entry redetection, F-level change, clock change, or confirmation tuning.

## Frozen pre-E10 protection
- completed-close invalidation below F15
- E10 = H + 0.10R
- H2 remains a milestone only
- no upper TP in hybrid mode

## E10 activation
E10 is reached on the first raw 5m bar with high >= E10.
If that same bar later closes below F15, the pre-E10 F15 close invalidation exits at its actual close; the E10 floor is not retroactively active inside the touch bar.

If the E10-touch bar completes without F15 close invalidation:
- E10 becomes a resting hard profit floor effective from the NEXT 5m bar.
- on any later bar, if open <= active floor, exit at actual open;
- else if low <= active floor, exit at active floor.

## Structural ratchet
After E10 activation, a strict 3-bar pivot low centered on i-1 becomes known only at completion of bar i when low[i-1] < low[i-2] and low[i-1] < low[i]. Only bars from entry onward may form pivots.

A newly confirmed pivot above the active floor ratchets the floor upward, effective only from the next bar. The floor never decreases. No ATR, percentage trail, alternate pivot width, EMA, body, volume, or regime filter.

If still open at session end, exit at session-end open.

## Economics
USD 500 notional; USD 0.40 round-trip fee.

## Frozen primary gate
On EARLY_RECLAIM, `ETH_LONG_B27AC_ADAPT_PRIMARY_HYBRID_SUPPORTED` requires:
1. hybrid expectancy > fixed E10 baseline expectancy in external, development, and reference_validation;
2. hybrid PF >=1.00 in each major partition;
3. pooled-major hybrid net > pooled-major fixed baseline net.

Blind and SAME_BAR are diagnostics; August telemetry only.

Research only; no live changes.