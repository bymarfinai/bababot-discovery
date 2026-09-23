# BNB B41-S6I-L — LONG Pre-Touch Approach Habitat Anatomy Preregistration

## Objective

Test whether eventual B41 LONG losers differ from winners in the **market approach into the lower Q80 wall before the first touch**.

This stage deliberately avoids generic 4h/24h/7d regime, ATR, breadth, EMA, and Fibonacci families already covered elsewhere in the repository. It focuses on a new B41-specific information set: local 5m approach pressure, compression/expansion, chop/trend character, and first-touch timing.

No entry filter is constructed here.

## Frozen parents

- S5 signature: `5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241`
- S6H-L signature: `a24465be8cadff835f4fad1d4cd01db7dbff9d0f9fe3ee566f1971aded008232`
- Setup: LOWER Q80 + TF60 C2_RECLAIM_AFTER_CLOSE -> MARKET LONG.
- Outcome label: +180m market-entry aligned outcome >0 WINNER, <=0 LOSER.
- DEV 2022-2024; REF 2025-2026.

Expected valid parity:
- DEV 49 winners / 27 losers
- REF 24 winners / 18 losers

## Causal habitat window

All approach features use only completed 5m bars **strictly before the first Q80-touch bar**.

Fixed lookbacks:
- 30m = 6 completed 5m bars
- 60m = 12 completed 5m bars
- 120m = 24 completed 5m bars

Session features use only bars from the current frozen session open up to the completed bar immediately before first touch.

## Frozen failure-oriented features

Higher is preregistered as greater failure risk unless explicitly noted.

1. `down_velocity_30`
   - (close 30m before anchor - anchor close) / wall_distance.

2. `down_velocity_60`
   - same over 60m.

3. `down_velocity_120`
   - same over 120m.

4. `trend_eff_60`
   - abs(net 60m move) / sum(abs(5m moves)).
   - hypothesis: efficient one-way sell pressure raises failure risk.

5. `chop_60`
   - 1 - trend_eff_60.
   - separate preregistered alternative hypothesis: noisy approach may weaken the reclaim.

6. `down_bar_fraction_60`
   - fraction of 5m close-to-close changes <0 over the 60m window.

7. `range_30_norm`
   - pre-touch 30m high-low range / wall_distance.

8. `range_60_norm`
   - pre-touch 60m high-low range / wall_distance.

9. `range_expansion_30v60`
   - 30m range / 60m range.
   - higher means recent movement is concentrated/accelerating near the wall.

10. `return_vol_60`
    - standard deviation of 5m close returns over the 60m window.

11. `sign_flip_count_60`
    - count of sign changes in consecutive 5m close-to-close changes.

12. `touch_latency_min`
    - minutes from frozen session open to first Q80 touch.

13. `session_down_efficiency`
    - abs(session-open to pre-touch close net move) / cumulative absolute 5m close path from session open.
    - only when >=3 completed pre-touch bars.

14. `session_up_excursion_norm`
    - max(0, pre-touch session high - session open) / wall_distance.
    - hypothesis: a larger earlier upside excursion followed by a collapse to lower Q80 indicates reversal pressure and higher failure risk.

15. `wall_distance_pct`
    - wall_distance / session_open.
    - structural stretch diagnostic.

## Frozen composite

`APPROACH_PRESSURE_COMPOSITE` = equal-weight mean of DEV robust-scaled:
- down_velocity_60
- trend_eff_60
- down_bar_fraction_60
- range_expansion_30v60
- session_down_efficiency

Scaling = DEV median/IQR, fallback std then 1.0; unchanged in REF.

## Evaluation

Positive class = eventual LOSER.

For each feature and composite:
- DEV/REF failure AUC;
- winner/loser medians;
- yearly descriptive AUC when both classes exist.

## DEV nomination

DEV_NOMINATED if:
- winners >=30;
- losers >=20;
- failure AUC >=0.60.

## REF validation

Only DEV nominees can validate.

REF_VALIDATED if:
- winners >=20;
- losers >=15;
- failure AUC >=0.55.

No REF-only promotion.

## Gate

>=1 REF-validated approach precursor:
`APPROACH_HABITAT_PRECURSOR_FOUND`.

Otherwise:
`NO_STABLE_APPROACH_HABITAT_PRECURSOR`.

A positive result permits a separately preregistered entry-quality filter stage.

No filter threshold, SL, TP, WR optimization, PF, expectancy, leverage, fees/slippage, or PnL optimization.
