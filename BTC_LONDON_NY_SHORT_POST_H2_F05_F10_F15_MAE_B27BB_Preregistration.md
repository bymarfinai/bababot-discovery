# B27BB — BTC London→NY SHORT Post-Retest#2 F05/F10/F15 Winner MAE / Natural Stop-Distance Audit — Preregistration

## Question
After valid Low retest #2 and a causal leave, B27AZ/B27BA found F05/F10/F15 fills. Does each entry zone have a materially different natural adverse-excursion requirement before the trade reaches E20_DOWN, such that reusing the old fixed F65 stop unfairly penalizes shallower entry zones?

## Frozen lineage
- Source 5m BTCUSDT dataset/coverage and London→NY K1/OPP0 chronology are unchanged.
- Clean post-H2 windows are exactly B27AY/B27AZ.
- Candidate entry zones are exactly F05, F10, F15 from B27AZ/B27BA; no intermediate fractions.
- Entry must occur after valid retest #2 + causal leave and before the next Low revisit/direct breakdown/opposite break, exactly as B27AZ.
- The expected pooled-major fill identities are frozen at F05=28, F10=37, F15=42. F15 partition identities must remain external=10, development=26, validation=6, august=1.

## Structural winner definition
This is a stop-independent path audit. The old F65 stop is NOT applied.
- For each filled trade, starting from the exact fill bar, inspect raw 5m chronology.
- E20_DOWN = L - 0.20R.
- Fill bar itself cannot count as E20 activation, matching the established hybrid chronology.
- Starting from the next raw 5m bar, if low <= E20_DOWN, classify the trade as E20_REACHER and stop the winner path at that activation bar.
- If a completed 5m close > H occurs before E20, classify as NON_E20_OPPOSITE_BREAK and stop the failure path on that bar.
- Otherwise, if E20 is never reached before session end, classify as NON_E20_SESSION_END and stop at the last active 5m bar before the exact 20:00 session end.

## Adverse excursion
For SHORT, adverse excursion is upward.
For each path, normalize the maximum observed high as a fraction of the previous-London range:
`max_high_frac = (max_high - L) / R`.
Natural stop distance from the actual candidate entry is:
`required_D = max(0, max_high_frac - entry_fraction)`.

Two winner measurements are reported:
1. `pre_E20_required_D`: maximum high from fill bar through the bar immediately BEFORE E20 activation.
2. `conservative_through_E20_required_D`: maximum high from fill bar THROUGH the E20 activation bar.
The second is conservative because intrabar order within the activation bar is unknown.

Equality with a hypothetical stop is treated as stop touched.

## Frozen outputs
For each zone and each partition plus pooled-major:
- fills, E20 reachers, E20 rate;
- winner required-D P50/P75/P90/P95/max for pre-E20 and conservative-through-E20;
- non-E20 required-D P50/P75/P90/P95/max;
- descriptive winner survival at D = 0.10, 0.20, 0.30, 0.40, 0.50, 0.60R.

## Interpretation rule
Diagnostic only. B27BB selects NO stop and promotes NO strategy. No PnL, target change, runner change, regime gate, confirmation, or post-hoc fraction is allowed.
A later economic test may use these distributions, but that later test must be separately preregistered.

Research only; live BBC unchanged.
