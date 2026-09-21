# SOL Score-3 SELL Missing-B Temporal Character V1 — Result

- 5m coverage: **99.772490%**
- Frozen character: **approach_bars + reclaim_delay_h1_bars >= 2**.
- Entry / SL / structural-completion exit unchanged.
- 2020-2025 is discovery evidence; 2026 is the frozen holdout.

## Discovery replay 2020-2025

- Baseline N: **55**
- Selected N / retention: **34 / 61.82%**
- Structural-event rate: **61.82% -> 70.59%**
- Gross WR: **58.18% -> 67.65%**
- Gross mean R / PF: **0.229 / 1.804**
- 10 bps mean R / PF: **0.171 / 1.562**
- 20 bps mean R / PF: **0.113 / 1.349**
- Existing gross-winner retention: **71.88%**

## Untouched 2026 holdout through 2026-09-21 00:00 UTC

- Baseline Missing-B N: **12**
- Selected N / retention: **4 / 33.33%**
- Structural-event rate: **75.00% -> 75.00%**
- Structural-event capture: **33.33%**
- Gross WR: **58.33% -> 50.00%**
- Gross mean R / PF: **0.237 / 1.474**
- 10 bps mean R / PF: **0.143 / 1.255**
- 20 bps mean R / PF: **0.048 / 1.078**

### Frozen gates

**Sample**
- PASS — baseline_missing_b_n_ge_5
- FAIL — selected_n_ge_5
- FAIL — selected_retention_ge_40pct

**Structural**
- PASS — selected_event_rate_ge_65pct
- FAIL — selected_event_rate_gt_baseline

**Trading**
- FAIL — gross_wr_ge_60pct
- PASS — gross_mean_r_gt_0
- PASS — gross_pf_ge_1_15
- PASS — net10_mean_r_gt_0
- PASS — net10_pf_ge_1_10
- PASS — net20_mean_r_ge_0
- PASS — net20_pf_ge_1_00

**VERDICT: MISSING_B_TEMPORAL_CHARACTER_HOLDOUT_INSUFFICIENT_SAMPLE**

No 2026 subgroup mining or post-holdout rule rescue was performed.
