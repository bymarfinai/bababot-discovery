# SOL Regime + Phase V2 — Stage 6B Feature Engine Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 6B builds causal lifecycle / remaining-energy features only.

It MUST NOT:
- assign EARLY_EXPANSION / HEALTHY_CONTINUATION / MATURE_TREND / EXHAUSTION / TRANSITION,
- optimize phase thresholds,
- inspect forward returns, TP/SL, future MFE/MAE, or trade outcomes,
- use 2025 or 2026 rows.

## Data boundary
- Raw source: Binance Vision SOLUSDT perpetual futures 5m.
- Raw warmup fetch: 2022-12-01.
- Feature output: 2023-01-01 through 2024-12-31 only.
- Existing Stage-2 causal structure features are consumed unchanged.
- Existing Stage-3 raw regime score switches and Stage-4 regime age/state are allowed only as context features; V1 regime labels are not ground truth.

## Frozen raw aggregation
- 1H bars require exactly 12 constituent 5m bars.
- EMA7 / EMA20 use the same pandas EWM convention as Stage 2.
- ATR14 uses Wilder EWM alpha=1/14.
- Event/clock calculations use completed 1H bars only.
- Feature row at bar open timestamp t represents information known at bar close t+1H and becomes actionable at decision_time=t+1H.

## Frozen event clocks

### Directional impulse clock
Reuse the already-disclosed Stage-5F causal impulse definition, without retuning:

BULL impulse start:
- `h1_ret_3 / h1_atr_norm >= +1.0`
- previous completed bar was below +1.0
- `h1_ema20_slope3_atr > 0`

BEAR is the exact sign mirror.

### Structure-break clock
BULL:
- rising edge of `h1_break_above_last_high`

BEAR:
- rising edge of `h1_break_below_last_low`

### Raw-score directional switch clock
- Stage-3 provisional regime changes into BULL / BEAR.

### Structural-renewal clock
- BULL: a fresh 24H high is made AND the completed 1H close is above the prior 24H high.
- BEAR: fresh 24H low AND completed close is below prior 24H low.

This is a local renewal event, not a phase label.

### Pullback clock
Directional pullback is tracked separately for BULL and BEAR.

BULL pullback starts on the first completed 1H bar where:
- the bar low touches/breaches EMA7,
- prior completed close was above EMA7,
- a same-side impulse or structure-break anchor exists within the preceding 72H.

It ends on the first later completed 1H bar where:
- close > EMA7,
- close > open.

BEAR is symmetric:
- high touches/breaches EMA7,
- prior close below EMA7,
- reclaim ends when close < EMA7 and close < open.

No future persistence is required.

## Frozen feature families

### 1. Event clocks / age
For each side:
- hours since impulse start
- hours since structure break
- hours since Stage-3 raw-score switch
- hours since structural renewal
- hours since fresh 24H extreme
- hours since pullback start
- hours since completed pullback end
- latest completed pullback duration
- Stage-4 regime duration (context only)

All event clocks are backward-looking and capped only for storage at 240H; absence remains NaN.

### 2. Consumed directional move
For each side:
- aligned return since latest impulse
- aligned MFE since latest impulse
- aligned adverse excursion since latest impulse
- aligned return since latest structure break
- aligned MFE since latest structure break
- aligned adverse excursion since latest structure break
- current distance from EMA20 in ATR units
- current distance from protected swing in ATR units
- 3H / 6H / 12H / 24H aligned return
- 24H aligned displacement percentile over trailing 168H

### 3. Marginal progress / renewal
For each side:
- new favorable excursion over trailing 1H / 3H / 6H / 12H
- fresh-extreme count over 6H / 12H / 24H
- hours since fresh 24H extreme
- acceptance distance beyond prior-24H extreme in ATR units
- close-above/below-prior-24H-extreme flag
- aligned progress per unit close-path over 6H / 12H / 24H
- efficiency change: aligned efficiency 6H minus aligned efficiency 24H

### 4. Pullback quality
For each side:
- active pullback flag
- current pullback age
- current pullback depth from pre-pullback extreme in ATR units
- latest completed pullback duration
- latest completed pullback max depth ATR
- latest completed pullback reclaim body fraction
- latest completed pullback reclaim close-location value
- latest completed pullback post-reclaim favorable progress after 1H / 3H
- failed reclaim count over trailing 24H

Post-reclaim progress is only populated after the relevant completed hours have elapsed; it is never backfilled onto earlier rows.

### 5. Directional efficiency / persistence
For each side:
- aligned close fraction 6H / 12H / 24H
- signed efficiency 6H / 12H / 24H
- aligned EMA20 slope ATR
- aligned EMA spread / ATR
- mean-cross and overlap features inherited from Stage 2
- aligned candle-body fraction rolling 6H

### 6. Stretch / maturity
For each side:
- cumulative aligned move since impulse in ATR units
- cumulative aligned MFE since impulse in ATR units
- impulse age
- structure-break age
- count of same-side structural renewals in trailing 24H / 72H
- distance from EMA20 ATR
- distance from protected swing ATR
- trailing 24H aligned return percentile over 168H

### 7. Exhaustion / rejection observables
For each side:
- adverse wick fraction on current bar
- adverse wick fraction rolling 3H / 6H
- current range / ATR
- current volume / trailing-24H median volume
- current close-location value, side aligned
- failed fresh-break flag: intrabar fresh 24H extreme but close back inside prior 24H boundary
- failed fresh-break count 6H / 24H
- efficiency decay (6H vs 24H)
- favorable-excursion increment ratio: 3H increment / 12H increment
- pullback depth trend: current/latest depth vs prior completed pullback depth where available

### 8. Volatility / balance
- ATR normalized
- ATR vs 72H median
- ATR percentile 168H
- ATR slope 6H
- 24H range / ATR
- mean-cross 12H / 24H
- overlap 12H / 24H
- range/path 12H / 24H
- prior-24H boundary touch count over 12H
- failed escape count 24H
- compression ratio: 6H realized range / 24H realized range

## Mandatory Stage-6B audits
1. Stage-6A status is TAXONOMY_FROZEN.
2. Stage-2 status is FEATURE_ENGINE_VALID.
3. Raw 5m coverage from 2022-12-01 through 2024-12-31 >=99.5%.
4. Every exported 1H row is built from exactly 12 5m bars.
5. Output contains only 2023 and 2024.
6. Recomputed ATR-normalized price/EMA features match Stage-2 causal features within 1e-10 where both are finite.
7. Event clocks are non-negative and equal zero on their event bar.
8. Event anchor timestamp is never after the feature decision time.
9. Active pullback ages are non-negative; completed pullback statistics never appear before pullback completion.
10. Post-reclaim +1H/+3H progress is never populated before 1H/3H has elapsed.
11. Selected feature prefix replay matches full-history calculation at four frozen checkpoints within 1e-10 / exact categorical equality.
12. No output field contains future/outcome/TP/SL/trade-result labels.
13. At least 98% of rows after the first 168H DEV warmup have finite core non-event continuous features.
14. BULL/BEAR side formulas are implemented through one symmetric side-feature function; no side-specific numeric threshold differences are allowed.

Stage 6B passes only if all mandatory audits pass.
