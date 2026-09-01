# ETH B27DX — S7D Event-Quality Conjunction — Preregistration

## Purpose
Test whether ETH B27DX needs a conjunction of independently causal event-quality properties rather than any single property alone.

Prior frozen tests established:
- S7A: absolute fill timing / range-completion timing alone did not pass the 75% Development quality gate.
- S7B: post-leave retrace compression was not discriminative.
- S7C: single-bar K1 rejection improved PF in some clocks but did not reach the WR gate.

S7D introduces no new raw feature and no new numeric cutoff. It only tests predeclared conjunctions of already-defined causal features.

## Frozen strategy layer
- LONG, R300, X360.
- Clocks 05:00, 09:00, 10:00, 16:00 UTC.
- F75 entry, E25 target, F20 completed-close invalidation.
- Same data, weekdays, partitions, fees, notional, corrected B27DX grammar and next-bar chronology as S7A-S7C.
- No runner, leverage, or live-code changes.

## Frozen component features
A. `SINGLE_BAR_K1_REJECTION`: K1 touch episode is exactly one completed 5m touch bar before leave.
B. `FILL_FIRST_HALF`: F75 entry bar occurs at or before minute 180 of X360.
C. `RANGE_COMPLETED_SECOND_HALF`: the frozen H/L reference range finishes forming at or after minute 150 of R300.

All are known by entry.

## Only new eligible conjunctions
1. `A__B` = SINGLE_BAR_K1_REJECTION + FILL_FIRST_HALF.
2. `A__C` = SINGLE_BAR_K1_REJECTION + RANGE_COMPLETED_SECOND_HALF.
3. `A__B__C` = all three.

No other combinations and no alternative cutoffs are allowed.

## Development promotion gate
A conjunction is eligible for Development promotion only if:
- N >= 20,
- retention >= 40% of BASE candidates for that clock,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

If multiple conjunctions pass for a clock, select deterministically by:
1. fewer component features,
2. higher retention,
3. fixed lexical order A__B, A__C, A__B__C.

No PF-max selection.

## Historical replication gate
Only the frozen Development-selected conjunction is opened in External and Reference Validation. Both independently require:
- N >= 10,
- retention >= 30%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Validation cannot alter the conjunction.

## Portfolio rescore
Only replicated clock+conjunction streams are combined. Rerun global chronological one-position lock separately for each major partition. Report 0 bps and 5 bps stress.

## BTC-quality diagnostic
Pooled-major primary requires WR >=71.9%, PF >=2.22, expectancy >=+$1.26/trade, every major partition PF>1 and net>0, plus pooled 5 bps PF>=1 and net>=0.

## Statuses
- `ETH_S7D_CAUSAL_AUDIT_FAILED`
- `ETH_S7D_NO_DEV_CONJUNCTION`
- `ETH_S7D_DEV_CONJUNCTIONS_NOT_REPLICATED`
- `ETH_S7D_CONJUNCTIONS_REPLICATED_BELOW_BTC`
- `ETH_S7D_CONJUNCTION_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Evidence label: exploratory historical replication; the component hypotheses were generated on inspected history. Research only.