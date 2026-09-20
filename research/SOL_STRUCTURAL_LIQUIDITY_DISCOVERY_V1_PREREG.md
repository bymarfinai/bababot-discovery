# SOL Structural Liquidity Discovery V1 — Preregistration

## Objective

Discover which **pre-existing, causally-known price levels** on SOLUSDT behave like meaningful reversal liquidity for the detector.

This phase does NOT test:
- entry timing;
- stop-loss;
- take-profit;
- trade PnL;
- session filters;
- indicators.

A price level is only a **liquidity candidate** when it is known before price reaches it.

A swept level becomes a **STRUCTURAL_LIQUIDITY_EVENT** only when the sweep has an observable structural consequence:

**first sweep -> reclaim -> opposite H1 BOS/new-extreme state**

This is an operational market-structure definition. It does not claim knowledge of hidden orders or trader intent.

## Data discipline

- Symbol: SOLUSDT.
- Structural timeframe: H1 built causally from complete 5m bars.
- H4 candidate layer: complete UTC-aligned H4 bars.
- Observation window: 2020-01-01 through 2024-12-31 UTC.
- 2020-2022: descriptive discovery period.
- 2023-2024: frozen confirmation period.
- 2025+ CLOSED.
- Required 5m coverage >= 99.5%.

## Frozen pivot semantics

Use the repository's causal order-2 pivot semantics.

A pivot level becomes usable only after its confirmation bar has fully closed.

## Frozen candidate families

### 1. H1_SWING

Every confirmed H1 swing high / low.

- upper pivot = buy-side liquidity candidate;
- lower pivot = sell-side liquidity candidate;
- activation = close of the H1 confirmation bar;
- maximum active life = 14 calendar days;
- first sweep only.

This is the baseline family because earlier SOL work implicitly treated generic confirmed H1 pivots as liquidity references.

### 2. H1_EQUAL_CLUSTER

Two causally-confirmed same-side H1 pivots form a near-equal cluster when:

- the newer pivot occurs no more than 72 H1 bars after the older pivot;
- at the newer pivot's confirmation time, absolute price difference <= 0.25 x the median range of the previous 20 completed H1 bars.

Use only the latest prior same-side confirmed pivot to form the pair.

- upper-cluster level = max(two pivot highs);
- lower-cluster level = min(two pivot lows);
- activation = newer pivot confirmation close;
- maximum active life = 14 calendar days;
- first sweep only.

No tolerance adjustment after results.

### 3. H4_SWING

Every confirmed order-2 H4 swing high / low.

- H4 bars are built only from four complete H1 bars;
- activation = H4 confirmation-bar close;
- maximum active life = 14 calendar days;
- first sweep only.

### 4. PREVIOUS_DAY

Previous complete UTC day high / low.

- requires a complete 24-H1-bar source day;
- candidate activates at next UTC 00:00;
- expires at the following UTC 00:00;
- first sweep only.

### 5. PREVIOUS_WEEK

Previous complete Monday-00:00 to next-Monday-00:00 UTC week high / low.

- requires 168 complete H1 bars;
- candidate activates at next Monday 00:00 UTC;
- expires after seven calendar days;
- first sweep only.

## Direct first-sweep definition

A candidate can only be swept after activation and before expiry.

For an UPPER / BUY_SIDE candidate:

- sweep H1 opens <= level;
- H1 high trades strictly above level;
- this is the first post-activation breach.

For a LOWER / SELL_SIDE candidate:

- sweep H1 opens >= level;
- H1 low trades strictly below level;
- this is the first post-activation breach.

Record every first sweep regardless of reclaim.

## Frozen reclaim definition

Starting with the sweep H1 and ending two completed H1 bars later:

- UPPER sweep reclaim = first H1 close < swept level;
- LOWER sweep reclaim = first H1 close > swept level.

If no reclaim occurs in this 0-2 H1 window:
**ACCEPTED_OR_NO_RECLAIM**.

## Significant opposite structure

At the first-sweep time, use only pivots already causally confirmed.

For UPPER / BUY_SIDE sweep:
- structural reference = latest confirmed H1 swing LOW known before the sweep.

For LOWER / SELL_SIDE sweep:
- structural reference = latest confirmed H1 swing HIGH known before the sweep.

No future pivot can be used.

## Frozen structural-consequence definition

After reclaim, inspect at most 16 completed H1 bars. The reclaim bar itself counts as bar 1 of this 16-bar consequence window.

For an UPPER / BUY_SIDE sweep:

- success = first completed H1 close below the significant-low reference;
- failure/invalidation before BOS = completed H1 close above the sweep extreme.

For a LOWER / SELL_SIDE sweep:

- success = first completed H1 close above the significant-high reference;
- failure/invalidation before BOS = completed H1 close below the sweep extreme.

If opposite BOS occurs first:
**STRUCTURAL_LIQUIDITY_EVENT**.

If sweep-extreme acceptance occurs first:
**RECLAIM_FAILED_BEFORE_BOS**.

If neither occurs inside 16 H1 bars:
**RECLAIM_NO_BOS_WITHIN_WINDOW**.

Events whose full consequence window would cross 2025-01-01 are:
**RIGHT_CENSORED** and excluded from consequence-rate comparisons.

## Descriptive measurements

For every candidate:
- family;
- side;
- activation time;
- level;
- source age / geometry;
- expiry;
- swept or unswept;
- age to first sweep.

For every sweep:
- sweep depth;
- same-bar vs delayed reclaim;
- reclaim delay;
- significant opposite pivot;
- sweep-to-BOS delay;
- displacement in units of prior 20-H1 median range;
- BOS extension beyond significant pivot.

## Primary reporting

For each family and side, report:

1. candidate activations;
2. fully-observed candidate activations;
3. first-sweep count;
4. first-sweep rate;
5. reclaim rate among sweeps;
6. STRUCTURAL_LIQUIDITY_EVENT rate among sweeps;
7. STRUCTURAL_LIQUIDITY_EVENT rate among reclaimed sweeps;
8. median age-to-sweep;
9. yearly 2020-2024 structural-consequence rates.

## Frozen enrichment audit

The baseline is **H1_SWING on the same side**.

For each non-baseline `family|side`, call it
**STRUCTURALLY_ENRICHED_LIQUIDITY_FAMILY**
only if all are true in frozen 2023-2024 confirmation:

1. non-censored first-sweep N >= 30;
2. STRUCTURAL_LIQUIDITY_EVENT rate among sweeps exceeds same-side H1_SWING by >= 8 percentage points;
3. STRUCTURAL_LIQUIDITY_EVENT rate among reclaimed sweeps exceeds same-side H1_SWING by >= 8 percentage points;
4. its sweep structural-event rate exceeds same-side H1_SWING in 2023;
5. its sweep structural-event rate exceeds same-side H1_SWING in 2024.

No candidate-family definition, equal-level tolerance, lifetime, reclaim window, BOS window, or gate may be changed after seeing 2023-2024.

## Interpretation

The discovery question is not:

> Which visual level looks like liquidity?

It is:

> Which causally-known level family, when first swept, is disproportionately followed by reclaim and a real opposite structural break?

Only after this layer is understood may the project return to:
**full structural detector -> adaptive entry -> adaptive SL -> adaptive TP**.

2025_PLUS=CLOSED
