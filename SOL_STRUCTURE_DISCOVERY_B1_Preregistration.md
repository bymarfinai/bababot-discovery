# SOL Structure Discovery B1 — Preregistration

## Decision and boundary

B1 searches for repeatable **dynamic price structures** on SOLUSDT. It does not optimize an entry, TP, SL, hold, clock, anchor, position size, or execution rule.

The prior economic-first hourly lineage is closed after 0/7 DD15 shortlist candidates validated OOS. B1 may use only the frozen Development partition (`2022-01-01 <= signal < 2025-01-01`) for discovery. External, Reference Validation, and August data remain unopened by B1.

## Observation and causality

- Source: Binance USD-M SOLUSDT 5-minute OHLC, aggregated to completed 15-minute bars.
- A structure is observed only at the close of its final 15-minute bar.
- All rolling thresholds are computed from bars completed before or at that observation as explicitly defined in the implementation.
- Forward response starts on the next 5-minute bar. No same-bar hindsight is allowed.
- To limit serial duplication, retain only the first event for the same family/variant/direction within a rolling 8-hour cooldown.

## Frozen families and variants

Exactly three economically interpretable families are authorized, with exactly three neighboring variants each:

1. `IMPULSE_PULLBACK`: impulse lengths 3, 4, and 6 completed 15-minute bars, followed by a two-bar controlled pullback. The impulse must be directionally efficient and large relative to causal ATR; the pullback must oppose the impulse, retrace 20–60%, and not break the impulse origin. Direction follows the impulse.
2. `COMPRESSION_EXPANSION`: compression lengths 4, 6, and 8 bars followed by one displacement close outside the compression range. The prior range must be compressed relative to its causal historical median; the displacement bar must have a large body and range. Direction follows the breakout.
3. `SWEEP_RECLAIM`: causal swing lookbacks 8, 12, and 20 bars. The final bar must sweep one side of the prior range, reclaim it on close, have a dominant rejection wick, and not sweep both sides. Direction is away from the swept side.

No additional family, clock split, indicator, threshold scan, or post-result replacement is authorized in B1.

## Forward-response measurements

For each retained event, use the structure-close price as a neutral reference and measure the subsequent 5-minute path at 1h, 2h, 4h, and 8h:

- direction-adjusted close return normalized by causal 15-minute ATR;
- maximum favorable excursion (MFE) / ATR;
- maximum adverse excursion (MAE) / ATR;
- whether +1 ATR is reached before -1 ATR; same-5-minute dual touches are unresolved, not wins;
- UTC clock distribution for concentration audit.

The primary horizon is 4h. Other horizons are robustness evidence, not alternatives from which a winner may be chosen.

## Frozen character gate

A variant passes Development only when all conditions hold:

- total retained events >= 180 and each of 2022, 2023, and 2024 has >= 40;
- at least 120 events resolve the symmetric 4h barrier test;
- resolved 4h `+1 ATR before -1 ATR` win rate is strictly >55%;
- mean direction-adjusted 4h return is >0;
- median 4h MFE/MAE ratio is >=1.15 (zero MAE is protected by a fixed epsilon);
- at least three of four horizon mean direction-adjusted returns are >0;
- each of 2022, 2023, and 2024 has positive mean direction-adjusted 4h return;
- no single UTC hour contributes >25% of retained events.

A family is promoted only if at least two of its three neighboring variants pass. At most one representative per passing family is selected: the passing variant with the highest minimum yearly mean direction-adjusted 4h return, then higher 4h resolved win rate, then larger sample. Maximum B1 shortlist size is three.

## Outcomes and stop rule

- `B1_PASS`: at least one family satisfies neighborhood robustness; freeze the selected representatives before any validation.
- `B1_NO_PASS`: no family qualifies; stop B1 without threshold repair or extra variants.

B1 cannot authorize live or shadow trading. Validation and executable-rule work require a later, separately preregistered stage.
