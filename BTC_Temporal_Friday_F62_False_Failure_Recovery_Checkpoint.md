# BTC Temporal Friday F6.2 — False Failure Recovery Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; NO ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen cohort
`FAILURE_60 = alive at +60m AND progress60 <= 0 AND taker60 < 0 AND ema20_dist60 <= 0`.

Cohort: **28 trades, 7W/21L = 25.00%, PnL -$44.485**.
- Discovery: 15 trades, 4W/11L = 26.67%, -$11.150.
- Validation: 13 trades, 3W/10L = 23.08%, -$33.335.

## False-failure evidence
Even inside FAILURE_60, recovery is common:
- 20/28 later reclaim entry.
- 14/28 later reach +0.5R (+0.35%).
- 8/28 later reach +1R (+0.70%).

This explains why F6.1's blanket +60m cut damaged winners.

## Strongest causal +60m separators of eventual winner vs loser
- `progress60`: AUC full/D/V **0.796 / 0.795 / 0.800**.
  - winner median **-0.0417%** vs loser **-0.2187%**.
- `mfe60`: AUC **0.755 / 0.727 / 0.800**.
  - winner median **+0.2515%** vs loser **+0.1319%**.
- `mae60`: AUC **0.320 / 0.341 / 0.300** (lower is better).
  - winner median **0.2463%** vs loser **0.3287%** adverse excursion.

Interpretation: recoverable failures are generally **shallower failures**: less negative at +60m, had shown more favorable excursion, and suffered less adversity.

Several weaker context clues have consistent direction, but none justify a rule yet.

## Binary screen
No fixed natural binary recovery signal passed the predeclared Discovery + Validation transfer screen.

Therefore:
- do **not** cut every FAILURE_60;
- do **not** choose a post-hoc numeric cutoff from the medians above;
- no classifier/action is promoted from F6.2.

## Verdict
**FORENSIC PASS.** The problem is severity/geometry of failure rather than a clean yes/no failure state. A next milestone, if continued, should test a **frozen severity-based candidate** derived without threshold hunting, ideally using a natural R-based boundary and then checking management economics in D/V.

## Execution
- Workflow run: **32036107210** — success.
- Artifact: `f62-output`, ID **9290751203**.
- Script: `research/f62_friday_false_failure_recovery_forensic.py`.
