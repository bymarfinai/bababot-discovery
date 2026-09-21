# BNB B40-S1 — Demand Survival vs Expansion Universe Preregistration

## Objective
Rebuild the demand-zone research layer from first principles.

B40 separates two different questions:
1. SURVIVAL: when price retests a structurally-created H1 demand candidate, does the zone actually hold or become consumed?
2. EXPANSION: among zones that survive, does the reaction have enough room/continuation to expand materially?

This avoids mixing zone validity, reaction quality, and target room into one WR number.

## Non-use of B39 outcome filters
B39/D1 remains a benchmark only.
No B39 D1 condition, threshold, entry, SL, TP, or winner label is used to define B40 demand candidates.

## H1 demand-candidate construction
A B40 demand candidate is created only from information available by the completed H1 BOS candle.

### 1. Confirmed structural high
Use the existing causal H1 pivot convention:
- pivot high at bar i if high[i] is greater than highs of i-2, i-1, i+1, i+2;
- pivot becomes known at i+2.

### 2. Bullish BOS
A completed H1 close must cross from at/below a confirmed swing-high level to above it.
The broken swing may only be used once.

### 3. Source/base discovery
Do NOT use "last bearish candle before BOS".

For each BOS, walk backward from the BOS candle and identify the contiguous source/base immediately preceding the directional departure into the BOS.

Operational v1, frozen before outcome inspection:
- define the departure leg as the terminal run ending at the BOS candle in which H1 closes make net upward progress toward the broken level;
- walk backward up to 8 H1 bars from BOS;
- stop source-base expansion once a prior bar is clearly part of the preceding directional leg rather than the local base;
- source base must contain 1–4 contiguous completed H1 candles;
- candidate base is selected by local compression/overlap around the departure origin, not candle color.

Because source extraction itself is the research object, S1 must persist all alternative causal source descriptors needed for audit:
- base_low/high
- base candle count
- body/range compression
- overlap ratio
- prior local low
- protected_low
- departure start/end
- BOS displacement
- imbalance/FVG descriptors
- pre-departure sweep descriptors

S1 may not select a "best" source feature using future retest outcomes.

### 4. Protected low
protected_low = minimum low of the frozen source/base.
From departure start through BOS close, protected_low must not be violated.
If violated before BOS confirmation, reject the candidate.

### 5. Zone bounds
For S1:
- demand_low = base_low
- demand_high = base_high

No proximal-line optimization, body-only zone, 50% zone, or candle-open shortcut is allowed.

### 6. Activation
Candidate activates only after BOS H1 candle closes.

## First retest
Use the first 15m bar after activation whose range intersects [demand_low, demand_high].
Only first retest is used in S1.

## Survival outcome
Survival must be separate from expansion.

Frozen primary survival definition:
- SURVIVE if, after first retest, price reaches +0.50 zone-risk before a clean structural consumption event;
- CONSUMED if price closes 15m below protected_low before reaching +0.50 zone-risk;
- AMBIGUOUS if both resolution conditions occur within the same unresolved 15m ordering window;
- CENSORED if neither occurs before the 24h horizon or dataset end.

zone-risk for S1 outcome normalization:
- anchor = first-retest 15m close
- risk = anchor - protected_low
- candidate excluded only if risk <= 0.

This is outcome normalization only, not a final live entry/SL.

## Expansion outcome among survivors
For all normalizable candidates also report:
- >=0.5R
- >=1.0R
- >=1.5R
- >=2.0R
- maximum favorable excursion within 24h
- time to each threshold

A zone can therefore be:
- CONSUMED
- SURVIVED_LOCAL_ONLY: reaches 0.5R but not 1R
- EXPANDER_1R: >=1R
- STRONG_1_5R: >=1.5R
- EXTREME_2R: >=2R

These labels do not redefine whether the demand survived.

## Structural descriptors to persist
All must be causal by BOS close or by first retest time as explicitly separated.

### Formation-time descriptors
- source/base width and candle count
- base overlap/compression
- departure candle count
- departure net progress
- departure efficiency
- BOS overshoot above broken swing
- BOS body/range
- FVG/imbalance presence and size
- pre-departure local-low sweep
- protected-low distance
- source age at activation

### Retest-time descriptors
- zone age at first retest
- whether zone was touched/mitigated previously (must be false for first-retouch universe by construction)
- approach slope
- approach efficiency
- approach overlap/compression
- last 1/2/3 bar bearish progress
- approach displacement strength
- local liquidity sweep immediately before/in retest

Formation and retest features must never use bars after first-retouch close.

## Required S1 outputs
- total candidate count DEV/REF and by year
- survival / consumed / censored census
- >=0.5/1/1.5/2R rates
- threshold timing
- distribution of formation descriptors
- distribution of retest descriptors
- raw candidate ledger

No feature ranking, filter selection, or detector promotion is allowed in S1.

## Split
- DEV: 2022-01-01 through 2024-12-31
- REF: 2025-01-01 through raw-data endpoint

REF is a confirmation partition, not pristine OOS after later inspection.

## Purpose of S1
Create a clean, auditable universe where later steps can ask:
A. what separates SURVIVED from CONSUMED?
B. among SURVIVED, what separates LOCAL_ONLY from real EXPANSION?

S1 itself answers neither with a tuned rule.
