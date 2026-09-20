# BNB B37-S2 — Visual-Family Winner/Loser Structural Anatomy Preregistration

**Scientific identity:** `BNB_B37_S2_VISUAL_ANATOMY_V1`

## Purpose

Step 2 only. Freeze the 201-event B37-S1B VISUAL_EQUIVALENT family and determine which pre-retest structural characteristics distinguish bullish continuation from demand failure.

This is an anatomy/discovery study, **not yet a production detector and not an entry optimization**.

## Frozen population

- BNBUSDT.
- Exact 5m source / identity from B31.
- Exact H1 and H4 reconstruction from B37-S1.
- Frozen B37-S1B VISUAL_EQUIVALENT definition.
- Development only: retests from 2022-01-01 through 2024-12-31.
- 2025-2026 remains unopened.

## Structural outcome race

For each first H1 retest at time T, using only bars strictly after T:

- `WIN_CONTINUATION`: first H1 close **above the frozen pre-retest expansion_high** occurs before any H1 close below demand_low.
- `LOSS_INVALIDATION`: first H1 close **below demand_low** occurs before any H1 close above expansion_high.
- `AMBIGUOUS_SAME_BAR`: a single H1 bar spans both structural barriers in a way whose intrabar ordering cannot be known. This applies only if bar high > expansion_high and bar low < demand_low while its close cannot provide a unique close-barrier result; excluded from winner/loser anatomy.
- `UNRESOLVED`: neither close barrier resolves before 2024-12-31.

Outcome uses no TP, SL, PnL, fee, leverage, or fixed-return threshold.

## Frozen pre-retest anatomy features

All features below must be computable no later than the first-retest H1 close.

### Higher-timeframe geometry
1. `demand_width_pct` = (demand_high-demand_low) / demand_mid.
2. `h4_bos_clearance_zw` = (h4_bos_close-broken_h4_level) / demand_width.
3. `expansion_above_bos_zw` = (expansion_high-h4_bos_close) / demand_width.
4. `expansion_from_demand_zw` = (expansion_high-demand_high) / demand_width.

### Time / path geometry
5. `activation_to_touch_h`.
6. `expansion_to_touch_h`.
7. `pullback_bars` = completed H1 bars after expansion pivot and before retest.
8. `pullback_depth` = (expansion_high-touch_low)/(expansion_high-demand_high).

### Retest anatomy
9. `penetration_zone_fraction` = (demand_high-touch_low)/demand_width.
10. `touch_close_zone_fraction` = (touch_close-demand_low)/demand_width.
11. `touch_close_location` = (touch_close-touch_low)/(touch_high-touch_low).
12. `touch_body_ratio` = abs(touch_close-touch_open)/(touch_high-touch_low).
13. `touch_lower_wick_ratio` = (min(touch_open,touch_close)-touch_low)/(touch_high-touch_low).

### Immediate approach anatomy
Using H1 bars immediately before the retest, never after it:
14. `approach_lower_close_share_3`: share of the last up-to-3 close-to-close steps that are downward.
15. `approach_slope_3_zw`: (last pre-touch close - close three bars earlier)/demand_width when available.
16. `approach_compression_3v3`: median range of last 3 pre-touch bars / median range of prior 3 pre-touch bars when six bars exist.

### Frozen categorical structural flags
17. `strict_exact`.
18. `touch_bullish`: touch_close > touch_open.
19. `distal_sweep_reclaim`: touch_low < demand_low AND touch_close >= demand_low.
20. `proximal_reclaim`: touch_close > demand_high.
21. `both_lh_ll`: lower-high and lower-low were both present in the frozen S1B path.

## Comparison method

No numeric threshold scan is allowed.

For continuous features:
- winner N / loser N;
- winner median;
- loser median;
- median difference;
- Cliff's delta;
- same directional median separation by 2022, 2023, 2024.

For categorical flags:
- winner prevalence;
- loser prevalence;
- prevalence difference;
- per-year direction.

A feature is called **stable-directional** only when:
- the pooled difference is non-zero; and
- every year with >=10 WIN and >=10 LOSS observations shows the same difference direction.

This does not make the feature a detector rule. Step 3 must preregister any rule derived from these observations before validation.

## Output

Persist:
- frozen 201-event ledger with outcome label;
- outcome census;
- continuous feature comparison;
- categorical feature comparison;
- per-year separation table;
- result report naming no more than four strongest stable structural separators.

## Stop rule

Do not:
- optimize thresholds;
- add time-of-day/day-of-week;
- add indicators, ATR gates, derivatives, funding, volume filters;
- alter S1B membership;
- open 2025-2026;
- test trade economics.

If no stable separator exists, Step 2 reports that directly.
