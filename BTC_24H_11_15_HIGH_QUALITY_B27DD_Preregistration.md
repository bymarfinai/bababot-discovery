# B27DD — BTC 11–15 WIB R100 High-Quality Filter Frontier — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the only currently positive RR-compliant SHORT clock (04-08 UTC / 11-15 WIB) can be filtered into a sparse high-quality setup with at least 60 pooled-major trades, trading WR >70%, PF >1, positive expectancy, and positive total net PnL, while keeping nominal RR >=1:1.

This is research only. No live BBC file or production rule is modified.

## Frozen economic base
- Source lineage: B27CS/B27DC exact F05 SHORT cohort.
- Clock: only `04-08 UTC` / `11-15 WIB`.
- Candidate: `R100` only; actual-fill reward-scaled stop with nominal RR exactly 1:1.
- Clock TP: frozen B27CR/B27CS `T15`.
- Parent baseline must reproduce 96 pooled-major fills and B27DC 11-15 R100 no-abort economics.
- Partitions: development selects; external and reference_validation are reused confirmation only. No untouched holdout exists; B27DA remains insufficient.

## Frozen causal risk score
Reuse the already-frozen B27CV logistic model at checkpoint `FILL`.
- Training remains exactly the original historical development BAD-vs-GOOD training from B27CV.
- Do not retrain, add features, change regularization, or tune model hyperparameters.
- At inference, score every 11-15 R100 F05 fill regardless of eventual outcome label.
- FILL features are causal at entry and contain no post-entry candles.

Quantile cutoffs are distribution-only and must be computed from the **development 11-15 FILL bad-risk scores without consulting economic outcomes**:
- `Q75`: 75th percentile of development FILL bad-risk probability.
- `Q65`: 65th percentile of development FILL bad-risk probability.
Lower score means lower predicted catastrophic-risk.

## Frozen entry filters
Evaluate exactly these five entry filters, no others:
1. `BASE` — retain every 11-15 R100 F05 fill.
2. `NO_SIDEWAYS` — retain only causal 4H regime BULL or BEAR; block SIDEWAYS.
3. `LOW_BAD_Q75` — retain `fill_bad_prob <= Q75`.
4. `LOW_BAD_Q65` — retain `fill_bad_prob <= Q65`.
5. `NO_SIDEWAYS_LOW_BAD_Q75` — both `NO_SIDEWAYS` and `LOW_BAD_Q75`.

Do not delete a regime or threshold after seeing results.

## Frozen post-entry management variants
For every retained entry filter evaluate exactly two management variants:
- `NO_ABORT` — original R100 B27CS path.
- `REFINED_ABORT` — exact causal B27CZ/B27DC refined state machine, with inference correction from B27DC: every trade still alive at +10/+15 is scored, including eventual OTHER outcomes. Abort is executed at the open of the first 5m bar available at the +15 decision timestamp. Frozen thresholds:
  - +10 SAFE probability >= 0.5898635948838399;
  - +15 SAFE probability >= 0.6079191233470493;
  - PLUS15_ONLY requires `max_bull_body_r4 >= 0.28173076923076923`.

No new abort threshold or timing may be tried.

## Candidate count
Exactly 5 entry filters × 2 management variants = 10 frozen candidates.

## Development selection
Selection is development-only. A candidate is development-eligible when:
- retained development trades >= 20;
- WR >= 65%;
- PF > 1.00;
- expectancy > 0;
- total net PnL > 0.

If multiple are eligible, select lexicographically by:
1. highest WR;
2. highest PF;
3. highest retained trade count;
4. fixed candidate order as listed above, with NO_ABORT before REFINED_ABORT for ties.

If none are development-eligible, selected candidate is `NONE` and verdict must be NOT SUPPORTED.

## Final high-quality target gate
A development-selected candidate is a B27DD high-quality candidate only if all are true after freezing the development selection:

### Pooled major hard target
- trades >= **60**;
- WR > **70%**;
- PF > **1.00**;
- expectancy > 0;
- total net PnL > 0;
- nominal RR minimum >= **1:1**.

### Reused confirmation guardrails
For both external and reference_validation independently:
- trades >= 15;
- PF > 0.90;
- total net PnL must not be materially catastrophic relative to its retained sample (report exact values; no post-hoc deletion).

Additionally pooled reused external+validation must have:
- WR >= 65%;
- PF > 1.00;
- expectancy > 0;
- total net PnL > 0.

If any hard target or reused confirmation requirement fails, verdict is `B27DD_HIGH_QUALITY_NOT_SUPPORTED`.
If all pass, verdict is `B27DD_HIGH_QUALITY_REUSED_CANDIDATE` only; fresh confirmation is still required before promotion.

## Required reporting
Report development candidates first, then external/reference_validation and pooled major for the selected rule. Include for every candidate:
- N/trades retained;
- retention rate from 11-15 baseline;
- WR;
- PF;
- expectancy/trade;
- total net PnL;
- average win/loss;
- max drawdown;
- max losing streak;
- abort count/rate;
- nominal RR minimum.

Also report retained regime composition and Q75/Q65 numeric thresholds.

## Mandatory assertions
1. Raw BTC source remains 698,112 5m rows, 100% coverage.
2. 11-15 R100 baseline reproduces 96 pooled-major trades and partition counts from B27DC.
3. Every retained trade has nominal RR >=1.0.
4. B27CV FILL model is reproduced without retraining changes.
5. Q75/Q65 use development score distribution only, not outcomes.
6. Post-entry refined abort exactly matches B27DC causal inference semantics.
7. No external/reference_validation result changes development selection.
8. No live BBC file changes.
