# SOL Score-4 Directional Character Robustness V1 — Preregistration

## Objective

Stress-test the already-frozen Score-4 directional character using only data already available before the fresh cutoff.

This is a retrospective robustness audit, NOT independent validation and NOT a new discovery/search exercise.

Frozen architecture:
- SELL_SIDE Score-4 -> ACCEPT
- BUY_SIDE Score-4 -> ACCEPT only if:
  - time_to_fill_min <= 15
  - directional_improvement_range_units <= 0.21471170803

No threshold may be changed as a result of this audit.

## Data scope

Use only:
- 2020-2024
- 2025
- 2026 entries before 2026-08-26 00:00 UTC

Fresh/post-cutoff data are excluded from all robustness statistics.

## Primary robustness checks

### 1. Exact-rule pooled BUY_SIDE stability

Pool all pre-cutoff BUY_SIDE Score-4 trades.

The exact frozen rule passes this check only if:
1. accepted BUY N >= 8
2. accepted BUY structural-event rate >= 50%
3. event-rate lift vs unfiltered BUY >= +20 percentage points
4. accepted BUY structural-completion mean R > 0
5. accepted BUY PF >= 1.20

### 2. Temporal consistency

Evaluate these periods separately:
- 2020-2024
- 2025
- 2026 pre-cutoff

A period is evaluable for BUY-side consistency when accepted BUY N >= 2.

A period is supportive only if:
- accepted BUY event rate >= unfiltered BUY event rate
- accepted BUY mean R >= unfiltered BUY mean R

Temporal robustness passes if:
- at least 2 periods are evaluable
- every evaluable period is supportive

A non-evaluable period is reported but does not count as pass or fail.

### 3. Leave-one-accepted-trade-out stability

Using pooled pre-cutoff accepted BUY trades, remove one accepted trade at a time.

Pass if:
- mean R remains > 0 in at least 80% of leave-one-out cases
- structural-event rate remains >= 50% in at least 80% of cases

This checks whether the result is dominated by one accepted trade.

### 4. Frozen-threshold neighborhood sensitivity

This is sensitivity analysis only; no variant can replace the frozen rule.

Evaluate all 9 combinations:

time_to_fill_min <= {10, 15, 20}

AND

directional_improvement_range_units <= {
  0.171769366424,
  0.214711708030,
  0.257654049636
}

These correspond to a narrow neighborhood around the frozen 15-minute / 0.21471170803 rule.

A neighborhood variant is supportive when:
- accepted BUY N >= 5
- accepted BUY event rate > unfiltered pooled BUY event rate
- accepted BUY mean R > 0

Neighborhood robustness passes if at least 6 of 9 variants are supportive.

No best variant is selected.

### 5. Out-of-construction retrospective check

Pool 2025 + 2026 pre-cutoff BUY_SIDE Score-4 trades only.

The exact frozen rule passes if:
- accepted BUY N >= 3
- accepted BUY event rate >= unfiltered BUY event rate + 10 percentage points
- accepted BUY mean R > unfiltered BUY mean R
- accepted BUY mean R > 0

Also compute an exact random-subset exceedance diagnostic:
among all subsets of the same size as the accepted BUY set, report the fraction whose event rate AND mean R are both at least as high as the frozen accepted set.

This exceedance statistic is descriptive only.

### 6. Bootstrap stability

On pooled pre-cutoff accepted BUY trades, run 20,000 nonparametric bootstrap resamples with fixed seed 42017.

Report:
- P(mean R > 0)
- P(event rate >= pooled unfiltered BUY event rate)
- 5th/50th/95th percentile mean R
- 5th/50th/95th percentile event rate

Bootstrap passes if:
- P(mean R > 0) >= 75%
- P(event rate >= unfiltered BUY event rate) >= 75%

This is retrospective stability evidence only.

### 7. SELL_SIDE auto-accept stability

Pool all pre-cutoff SELL_SIDE Score-4 trades.

Pass if:
- pooled SELL mean R > 0
- pooled SELL PF >= 1.20
- at least 2 of the 3 reporting periods have positive SELL mean R

### 8. Full architecture uplift

Compare all accepted Score-4 trades vs all unfiltered Score-4 trades over the full pre-cutoff pool.

Pass if:
- accepted event rate > unfiltered event rate
- accepted mean R > unfiltered mean R
- accepted PF > unfiltered PF
- accepted cumulative R > 0

## Verdict

If all eight primary robustness checks pass:

`SCORE4_DIRECTIONAL_CHARACTER_RETROSPECTIVELY_ROBUST`

Otherwise:

`SCORE4_DIRECTIONAL_CHARACTER_RETROSPECTIVELY_FRAGILE`

Neither verdict is independent validation.

Fresh-holdout rule and thresholds remain unchanged regardless of this audit.

POST_CUTOFF_DATA=EXCLUDED
