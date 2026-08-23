# B27CV — BTC 24H F05 SHORT Full-Loser Separability Anatomy — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** Exact B27CS executable F05 identity reproduced: external 183 / development 297 / validation 172 / pooled major 652. Labels: BAD High-break 78 / GOOD clock-target 348 / OTHER 226.

**Classifier anatomy only:** detector trading WR/PF/expectancy/PnL are **N/A**. Models and thresholds were trained/selected development-only; external/reference_validation are reused-data confirmation, not untouched OOS.

## Primary checkpoint detector readout

| Checkpoint | Mode | Dev AUC | Threshold | External BAD caught / GOOD cut | Validation BAD caught / GOOD cut | Reused supported |
|---|---|---:|---:|---|---|---|
| RECLAIM | SAFE | 0.757 | 0.653 | 5/23 (21.7%) / 11/98 (11.2%) | 5/17 (29.4%) / 16/91 (17.6%) | NO |
| RECLAIM | AGGRESSIVE | 0.757 | 0.580 | 6/23 (26.1%) / 19/98 (19.4%) | 6/17 (35.3%) / 26/91 (28.6%) | NO |
| FILL | SAFE | 0.781 | 0.650 | 5/23 (21.7%) / 10/98 (10.2%) | 5/17 (29.4%) / 14/91 (15.4%) | NO |
| FILL | AGGRESSIVE | 0.781 | 0.573 | 6/23 (26.1%) / 18/98 (18.4%) | 5/17 (29.4%) / 25/91 (27.5%) | NO |
| PLUS5 | SAFE | 0.842 | 0.678 | 5/23 (21.7%) / 11/98 (11.2%) | 4/17 (23.5%) / 19/91 (20.9%) | NO |
| PLUS5 | AGGRESSIVE | 0.842 | 0.563 | 9/23 (39.1%) / 26/98 (26.5%) | 8/17 (47.1%) / 25/91 (27.5%) | NO |
| PLUS10 | SAFE | 0.845 | 0.590 | 8/23 (34.8%) / 15/98 (15.3%) | 5/17 (29.4%) / 17/91 (18.7%) | NO |
| PLUS10 | AGGRESSIVE | 0.845 | 0.549 | 8/23 (34.8%) / 17/98 (17.3%) | 6/17 (35.3%) / 19/91 (20.9%) | NO |
| PLUS15 | SAFE | 0.886 | 0.608 | 9/23 (39.1%) / 14/98 (14.3%) | 8/17 (47.1%) / 15/91 (16.5%) | NO |
| PLUS15 | AGGRESSIVE | 0.886 | 0.410 | 9/23 (39.1%) / 22/98 (22.4%) | 13/17 (76.5%) / 25/91 (27.5%) | NO |

## Six clocks independently — SAFE operating points

| WIB | Checkpoint | BAD caught/all | GOOD cut/all | Precision among flagged |
|---|---|---:|---:|---:|
| 07-11 | RECLAIM | 0/13 (0.0%) | 10/76 (13.2%) | 0.0% |
| 07-11 | FILL | 0/13 (0.0%) | 9/76 (11.8%) | 0.0% |
| 07-11 | PLUS5 | 3/13 (23.1%) | 6/76 (7.9%) | 33.3% |
| 07-11 | PLUS10 | 6/13 (46.2%) | 13/76 (17.1%) | 31.6% |
| 07-11 | PLUS15 | 8/13 (61.5%) | 9/76 (11.8%) | 47.1% |
| 11-15 | RECLAIM | 1/5 (20.0%) | 0/36 (0.0%) | 100.0% |
| 11-15 | FILL | 1/5 (20.0%) | 0/36 (0.0%) | 100.0% |
| 11-15 | PLUS5 | 1/5 (20.0%) | 0/36 (0.0%) | 100.0% |
| 11-15 | PLUS10 | 1/5 (20.0%) | 0/36 (0.0%) | 100.0% |
| 11-15 | PLUS15 | 1/5 (20.0%) | 3/36 (8.3%) | 25.0% |
| 15-19 | RECLAIM | 7/17 (41.2%) | 10/55 (18.2%) | 41.2% |
| 15-19 | FILL | 6/17 (35.3%) | 7/55 (12.7%) | 46.2% |
| 15-19 | PLUS5 | 5/17 (29.4%) | 13/55 (23.6%) | 27.8% |
| 15-19 | PLUS10 | 9/17 (52.9%) | 12/55 (21.8%) | 42.9% |
| 15-19 | PLUS15 | 11/17 (64.7%) | 11/55 (20.0%) | 50.0% |
| 19-23 | RECLAIM | 12/25 (48.0%) | 20/95 (21.1%) | 37.5% |
| 19-23 | FILL | 12/25 (48.0%) | 21/95 (22.1%) | 36.4% |
| 19-23 | PLUS5 | 14/25 (56.0%) | 24/95 (25.3%) | 36.8% |
| 19-23 | PLUS10 | 17/25 (68.0%) | 20/95 (21.1%) | 45.9% |
| 19-23 | PLUS15 | 18/25 (72.0%) | 11/95 (11.6%) | 62.1% |
| 23-03 | RECLAIM | 1/8 (12.5%) | 0/50 (0.0%) | 100.0% |
| 23-03 | FILL | 1/8 (12.5%) | 0/50 (0.0%) | 100.0% |
| 23-03 | PLUS5 | 2/8 (25.0%) | 0/50 (0.0%) | 100.0% |
| 23-03 | PLUS10 | 2/8 (25.0%) | 0/50 (0.0%) | 100.0% |
| 23-03 | PLUS15 | 1/8 (12.5%) | 1/50 (2.0%) | 50.0% |
| 03-07 | RECLAIM | 2/10 (20.0%) | 2/36 (5.6%) | 50.0% |
| 03-07 | FILL | 2/10 (20.0%) | 2/36 (5.6%) | 50.0% |
| 03-07 | PLUS5 | 2/10 (20.0%) | 0/36 (0.0%) | 100.0% |
| 03-07 | PLUS10 | 4/10 (40.0%) | 2/36 (5.6%) | 66.7% |
| 03-07 | PLUS15 | 6/10 (60.0%) | 3/36 (8.3%) | 66.7% |

## Regime splits — SAFE operating points

| Regime | Checkpoint | BAD caught/all | GOOD cut/all | Precision among flagged |
|---|---|---:|---:|---:|
| BULL | RECLAIM | 13/35 (37.1%) | 19/146 (13.0%) | 40.6% |
| BULL | FILL | 13/35 (37.1%) | 18/146 (12.3%) | 41.9% |
| BULL | PLUS5 | 14/35 (40.0%) | 24/146 (16.4%) | 36.8% |
| BULL | PLUS10 | 22/35 (62.9%) | 25/146 (17.1%) | 46.8% |
| BULL | PLUS15 | 22/35 (62.9%) | 19/146 (13.0%) | 53.7% |
| BEAR | RECLAIM | 5/31 (16.1%) | 12/154 (7.8%) | 29.4% |
| BEAR | FILL | 4/31 (12.9%) | 14/154 (9.1%) | 22.2% |
| BEAR | PLUS5 | 8/31 (25.8%) | 13/154 (8.4%) | 38.1% |
| BEAR | PLUS10 | 10/31 (32.3%) | 15/154 (9.7%) | 40.0% |
| BEAR | PLUS15 | 13/31 (41.9%) | 12/154 (7.8%) | 52.0% |
| SIDEWAYS | RECLAIM | 5/12 (41.7%) | 11/48 (22.9%) | 31.2% |
| SIDEWAYS | FILL | 5/12 (41.7%) | 7/48 (14.6%) | 41.7% |
| SIDEWAYS | PLUS5 | 5/12 (41.7%) | 6/48 (12.5%) | 45.5% |
| SIDEWAYS | PLUS10 | 7/12 (58.3%) | 7/48 (14.6%) | 50.0% |
| SIDEWAYS | PLUS15 | 10/12 (83.3%) | 7/48 (14.6%) | 58.8% |

## Top model signals by absolute coefficient

| Checkpoint | Rank | Feature | Coefficient |
|---|---:|---|---:|
| RECLAIM | 1 | `cat__clock_block_16-20` | -1.018 |
| RECLAIM | 2 | `cat__clock_block_04-08` | -0.868 |
| RECLAIM | 3 | `num__ema50_slope3_r4` | -0.570 |
| RECLAIM | 4 | `cat__clock_block_12-16` | +0.553 |
| RECLAIM | 5 | `cat__clock_block_00-04` | +0.548 |
| RECLAIM | 6 | `cat__clock_block_08-12` | +0.535 |
| FILL | 1 | `cat__clock_block_16-20` | -1.064 |
| FILL | 2 | `num__reclaim_pos_r4` | -0.937 |
| FILL | 3 | `cat__clock_block_04-08` | -0.802 |
| FILL | 4 | `num__ema50_slope3_r4` | -0.567 |
| FILL | 5 | `cat__clock_block_12-16` | +0.525 |
| FILL | 6 | `cat__clock_block_00-04` | +0.523 |
| PLUS5 | 1 | `num__rebreak_done` | -1.272 |
| PLUS5 | 2 | `cat__clock_block_16-20` | -1.064 |
| PLUS5 | 3 | `num__mfe_low_r4` | +0.962 |
| PLUS5 | 4 | `num__reclaim_pos_r4` | -0.775 |
| PLUS5 | 5 | `cat__clock_block_04-08` | -0.729 |
| PLUS5 | 6 | `num__mae_close_r4` | -0.687 |
| PLUS10 | 1 | `cat__clock_block_16-20` | -1.091 |
| PLUS10 | 2 | `num__mfe_low_r4` | +1.001 |
| PLUS10 | 3 | `cat__clock_block_04-08` | -0.710 |
| PLUS10 | 4 | `num__net_close_from_entry_r4` | +0.596 |
| PLUS10 | 5 | `num__closes_ge_f15` | +0.592 |
| PLUS10 | 6 | `num__closes_ge_f10` | -0.591 |
| PLUS15 | 1 | `cat__clock_block_16-20` | -0.990 |
| PLUS15 | 2 | `cat__clock_block_08-12` | +0.855 |
| PLUS15 | 3 | `cat__clock_block_04-08` | -0.845 |
| PLUS15 | 4 | `num__max_bull_body_r4` | +0.776 |
| PLUS15 | 5 | `cat__regime_BEAR` | -0.733 |
| PLUS15 | 6 | `num__higher_close_streak` | +0.572 |

Reused-supported detector operating points: **none**.

**Frozen verdict: `B27CV_FULL_LOSER_SEPARABILITY_NOT_SUPPORTED`.**

A detector candidate here only establishes separability. It does not prove that actually skipping/aborting trades is profitable; that requires a separate causal economic simulation. Live BBC unchanged.
