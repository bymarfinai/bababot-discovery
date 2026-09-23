# BNB B41-S1 — Causal Structural Wall Discovery Preregistration

## Objective

Construct a causal BNBUSDT daily structural-wall map. S1 evaluates wall construction and stability only. It does **not** evaluate entry, direction, win rate, TP, SL, reversal success, or breakout success.

## Frozen data

- Instrument: Binance Futures BNBUSDT
- Raw bars: the same 5m Binance Vision source and normalization used by B31/B40.
- Research interval: 2022-01-01 through 2026-08-26.
- Session definition: UTC calendar day.
- A wall for day D may use only completed sessions strictly before D.

## Primary wall family: empirical excursion walls

For each completed UTC session:

- upside excursion = session_high / session_open - 1
- downside excursion = 1 - session_low / session_open

For day D, use the previous **60 completed UTC sessions**, with no current-day information.

Separate upside and downside distributions are retained; symmetry is not imposed.

Frozen wall levels:

- EQUILIBRIUM = current UTC session open
- UPPER_MID = open * (1 + trailing upside excursion Q50)
- UPPER_WALL = open * (1 + trailing upside excursion Q80)
- UPPER_EXTREME = open * (1 + trailing upside excursion Q95)
- LOWER_MID = open * (1 - trailing downside excursion Q50)
- LOWER_WALL = open * (1 - trailing downside excursion Q80)
- LOWER_EXTREME = open * (1 - trailing downside excursion Q95)

No quantile search is permitted in S1.

## Secondary reference family: realized-volatility wall

Diagnostic only; not a replacement for the empirical wall family.

- Compute close-to-close log return for each completed UTC session.
- sigma20 = sample standard deviation of the previous 20 completed daily log returns.
- RV1 upper = open * exp(+sigma20)
- RV1 lower = open * exp(-sigma20)

No multiplier search is permitted in S1.

## S1 outputs

1. One causal daily wall map.
2. Geometry/order integrity audit.
3. Availability by year and DEV/REF split.
4. Wall-distance distribution and time stability.
5. Asymmetry diagnostics between upside and downside walls.
6. Frozen wall-definition signature.

## Explicit exclusions

S1 must not calculate:
- wall touch rate,
- HOD/LOD capture,
- reversal probability,
- breakout probability,
- future MFE/MAE,
- entry or trade returns,
- TP/SL,
- win rate or expectancy.

Those belong to B41-S2 and later.

## Readiness rule

The wall library is READY only if:

1. Every eligible research session has a causal 60-session history.
2. All empirical levels are finite.
3. Ordering is valid on 100% of eligible sessions:
   LOWER_EXTREME <= LOWER_WALL <= LOWER_MID < EQUILIBRIUM < UPPER_MID <= UPPER_WALL <= UPPER_EXTREME.
4. At least 100 eligible sessions exist in every research year represented.
5. No current-session high, low, or close is used in wall formation.

Passing S1 means only that a stable, causal wall library exists. It does not establish predictive edge.
