# BNB B37-S3 — Named Structural Detector Candidates Preregistration

**Scientific identity:** `BNB_B37_S3_STRUCTURAL_CANDIDATES_V1`

## Purpose

Step 3 converts the Step-2 anatomy observations into a **small set of named, causal, mechanically detectable structural hypotheses**.

This phase does **not** validate edge, compare win rates, optimize thresholds, open 2025-2026, or test economics.

## Frozen parent family

All candidates are subsets of the frozen B37-S1B `VISUAL_EQUIVALENT` family:

`H4 structural demand -> bullish expansion/new high -> corrective pullback -> first H1 return to H4 demand -> retest close holds demand`

Parent population in 2022-2024 = 201 events.

## Design rule

Only structural boundaries with direct geometric meaning may be used:
- `demand_low`
- `demand_high`
- `h4_bos_close`
- `expansion_high`
- `demand_width = demand_high - demand_low`
- H1 retest OHLC

No percentile, quantile, grid search, arbitrary learned threshold, clock filter, indicator, derivative data, ATR gate, or outcome-guided parameter search is allowed.

## Candidate C1 — PROXIMAL_RECLAIM

**Name:** `H4D_H1_PROXIMAL_RECLAIM`

Parent visual-equivalent structure AND:

`touch_close > demand_high`

Interpretation:
- price enters the H4 demand interaction;
- the first H1 retest does not merely survive;
- it closes back above the proximal edge of demand.

This is the cleanest direct translation of the strongest Step-2 reaction observation.

## Candidate C2 — CLEAN_PROXIMAL_RECLAIM

**Name:** `H4D_H1_CLEAN_PROXIMAL_RECLAIM`

C1 AND:

`touch_low >= demand_low`

Interpretation:
- proximal reclaim occurs;
- there is no distal violation of the H4 demand candle during the retest.

No sweep-depth threshold is introduced.

## Candidate C3 — BULLISH_PROXIMAL_RECLAIM

**Name:** `H4D_H1_BULLISH_PROXIMAL_RECLAIM`

C1 AND:

`touch_close > touch_open`

Interpretation:
- proximal reclaim occurs;
- the first H1 demand-interaction candle itself resolves bullish.

This is independent of wick depth and does not require C2.

## Candidate C4 — CONTROLLED_EXPANSION_CLEAN_RECLAIM

**Name:** `H4D_H1_CONTROLLED_EXPANSION_CLEAN_RECLAIM`

C2 AND:

`expansion_high - h4_bos_close <= demand_width`

Interpretation:
- price does not extend more than one native demand-zone width above the H4 BOS close before returning;
- the retest remains clean and closes above proximal demand.

The one-zone-width boundary is a native structural unit, not a fitted numeric threshold.

## Step-3 outputs

Persist for the frozen 201 events:
- candidate membership flags;
- candidate support counts by 2022/2023/2024;
- overlap matrix;
- candidate specification report.

**Do not include outcome labels or winner/loss rates in Step 3 outputs.**

## Stop rule

No candidate may be modified based on its later validation performance. Any changed rule receives a new scientific identity.
