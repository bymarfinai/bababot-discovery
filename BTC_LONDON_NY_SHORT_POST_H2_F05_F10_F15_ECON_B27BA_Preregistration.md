# B27BA — BTC London->NY SHORT Post-H2 F05/F10/F15 Economic Comparison — Preregistration

## Question
After a valid second Low retest (H2) and causal leave, does changing only the retrace entry zone among F05, F10, and F15 improve the existing E20 full-position hybrid economics?

## Frozen source semantics
- BTCUSDT 5m dataset and partitioning are unchanged.
- London High/Low are frozen source-session levels.
- SHORT lineage is the existing B27AY/B27AZ post-H2 cohort: K1 Low visit -> causal leave #1 -> valid distinct Low retest #2 (low <= L, close >= L, close <= H) -> collapse the H2 episode -> causal leave #2.
- Entry eligibility begins only after leave #2 completes.
- Candidate entry prices are fixed before results: F05=L+0.05R, F10=L+0.10R, F15=L+0.15R, where R=H-L.
- A candidate must fill strictly before the next terminal Low revisit/direct breakdown/opposite High close-break, using the exact B27AZ scan semantics.

## Frozen economics
Only the entry fraction changes.
- Pre-activation invalidation boundary remains F65=L+0.65R, triggered by completed 5m close > F65 and exited at the actual close.
- Profit-lock activation remains E20_DOWN=L-0.20R.
- Fill bar cannot activate E20.
- Intrabar E20 touch on a later bar precedes a same-bar later close invalidation.
- Once E20 is reached, 100% of the position remains open; initial profit ceiling is E20 from the causal runner state, with the same strict 3-bar pivot-high ratchet used by B27AQ/B27AT/B27AY. Ceiling may only move down.
- Gap/open >= ceiling exits at actual open; otherwise high >= ceiling exits at ceiling; otherwise session-end open.
- Notional=$500; combined fee=$0.40 per trade.
- No confirmation, regime, EMA, candle feature, damage-control rule, alternate target, partial TP, or alternate runner is added.

## Mandatory audit gates before interpretation
1. Dataset must reproduce 698,112 5m rows and 100% coverage.
2. B27AZ clean post-H2 windows must reproduce external/development/reference_validation/august = 13/42/14/1.
3. Candidate fill counts must reproduce B27AZ: F05=28 pooled-major, F10=37 pooled-major, F15=42 pooled-major; F15 partition fills must reproduce 10/26/6/1.
4. Generalized simulator at F15 must reproduce B27AY partition and pooled-major N, WR, PF, expectancy, total PnL, and E20 activation counts/rates to numerical tolerance before F05/F10 are interpreted.

## Frozen selection rule
A candidate is formally eligible only if, in EACH external, development, and reference_validation partition:
- expectancy >= 0; and
- PF >= 1.0.

Among eligible candidates, select the highest pooled-major total PnL. If none qualifies, selected candidate = NONE. Also report the highest pooled-major PnL candidate diagnostically even if it fails robustness.

No post-hoc intermediate fractions (for example F07/F12), stop changes, or threshold search are allowed in B27BA.

Research only. Live BBC remains unchanged.
