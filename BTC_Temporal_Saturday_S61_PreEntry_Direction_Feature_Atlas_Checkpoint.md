# BTC Temporal Saturday S6.1 — Pre-Entry Causal Direction Feature Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; CAUSAL PRE-ENTRY DIRECTION INFORMATION EXISTS; NO CLASSIFIER/RULE YET  
**Research only:** live BBC untouched

## Frozen purpose
S6.0 proved substantial hindsight BUY-vs-SELL capacity. S6.1 asks whether that preference leaves a causal footprint **before** Saturday 18:00 WIB entry.

No trading rule, classifier, threshold optimization, or post-entry feature is used here.

## Causal boundary
- Entry: Saturday **18:00 WIB / 11:00 UTC**.
- Latest feature candle: completed 5m candle ending before entry; no information at/after entry is used.
- Features are based only on pre-entry return/trend, EMA geometry, prior-range location, realized volatility, taker flow, volume regime, and last-candle morphology.
- Outcome labels are hindsight targets only.

## Frozen direction outcomes
Static BUY and mirrored static SHORT use the same 18:00 WIB entry and TP2.6% / SL1.2% / max18h geometry.

Across 139 Saturdays:
- `SHORT_BETTER`: **61**
- `BUY_BETTER_OR_EQUAL`: **78**
- `BUY_ONLY_WIN`: **65**
- `SHORT_ONLY_WIN`: **43**
- `BOTH_LOSE`: **31**
- `BOTH_WIN`: **0**
- decisive one-direction-wins cases: **108/139**

Discovery/validation taxonomy remains well populated:
- Discovery: BUY_ONLY 40 / SHORT_ONLY 25 / BOTH_LOSE 18
- Validation: BUY_ONLY 25 / SHORT_ONLY 18 / BOTH_LOSE 13

## Robust continuous separation
Descriptive screen only: D and V AUC must be on the same side of 0.50 and full |AUC-0.50| >=0.07. No feature cutoff is selected.

| Feature | Full AUC (higher => SHORT better) | Discovery | Validation | Interpretation |
|---|---:|---:|---:|---|
| `dist_4h_high` | **0.681** | **0.693** | **0.642** | closer to prior 4h high -> SHORT-favoring |
| `dist_1h_high` | **0.650** | **0.662** | **0.599** | closer to prior 1h high -> SHORT-favoring |
| `ema7_20_spread` | **0.644** | **0.664** | **0.602** | more bullish EMA spread -> SHORT-favoring |
| `ema20_dist` | **0.635** | **0.659** | **0.570** | farther above EMA20 -> SHORT-favoring |
| `ret60` | **0.632** | **0.646** | **0.587** | stronger prior 1h return -> SHORT-favoring |
| `ret120` | **0.624** | **0.658** | **0.557** | stronger prior 2h return -> SHORT-favoring |
| `ema7_slope60` | **0.620** | **0.630** | **0.608** | stronger fast-EMA slope -> SHORT-favoring |
| `ema20_slope60` | **0.615** | **0.630** | **0.575** | stronger trend slope -> SHORT-favoring |
| `ret240` | **0.606** | **0.618** | **0.562** | stronger prior 4h return -> SHORT-favoring |
| `rv1h` | **0.426** | **0.454** | **0.424** | lower 1h volatility -> SHORT-favoring |
| `rv4h` | **0.392** | **0.418** | **0.358** | lower 4h volatility -> SHORT-favoring |

Several weaker location/slope features also pass the descriptive screen, but they are highly redundant with the trend family.

## Decisive BUY-only vs SHORT-only audit
This removes the 31 BOTH_LOSE cases and asks only whether the pre-entry state distinguishes the 65 BUY-only winners from the 43 SHORT-only winners.

Strongest stable features:

| Feature | Full AUC (SHORT-only high) | Discovery | Validation |
|---|---:|---:|---:|
| `dist_4h_high` | **0.674** | **0.702** | **0.618** |
| `dist_1h_high` | **0.652** | **0.678** | **0.587** |
| `ema7_20_spread` | **0.650** | **0.683** | **0.589** |
| `ret120` | **0.639** | **0.657** | **0.607** |
| `ret60` | **0.639** | **0.673** | **0.569** |
| `ema20_dist` | **0.635** | **0.668** | **0.558** |
| `ema7_slope60` | **0.631** | **0.654** | **0.593** |
| `ema20_slope60` | **0.630** | **0.647** | **0.593** |
| `volume_ratio_1h_24h` | **0.369** | **0.427** | **0.298** |
| `ret240` | **0.608** | **0.633** | **0.562** |

Thus the separation is not merely caused by untradeable BOTH_LOSE cases.

## Exact median geometry — decisive cases
`SHORT_ONLY_WIN` vs `BUY_ONLY_WIN`:
- 4h distance from high: **-0.207% vs -0.349%**
- 1h distance from high: **-0.120% vs -0.172%**
- prior 60m return: **+0.055% vs -0.060%**
- EMA7/EMA20 spread: **+0.012% vs -0.016%**
- 4h realized volatility: **0.407% vs 0.462%**
- recent 1h volume vs average hourly 24h: **0.338x vs 0.464x**

The same broad direction survives D/V. Example `dist_4h_high` medians:
- Discovery SHORT-only **-0.180%** vs BUY-only **-0.460%**
- Validation SHORT-only **-0.210%** vs BUY-only **-0.272%**

## Natural binary checks
These are fixed sign/context checks, not optimized thresholds.

### Above EMA20
SHORT_BETTER rate:
- Discovery: **54.29%** above EMA20 vs **31.25%** below
- Validation: **55.56%** above vs **41.38%** below

### Prior 60m return positive
- Discovery: **50.00%** SHORT_BETTER vs **33.33%** when nonpositive
- Validation: **56.67%** vs **38.46%**

These simple sign tests support the continuous result.

## Critical mechanism
The emerging Saturday direction effect is **counter-trend / exhaustion-like**, not simple momentum-following:

> **quiet bullish extension near recent highs before 18:00 WIB tends to favor SHORT; weaker / farther-from-high pre-entry structure tends to favor BUY.**

This does NOT yet mean “if bullish then short” is a finished rule.

## Redundancy guard
Many passing trend features are strongly correlated. Examples on the 139 rows:
- `ema7_20_spread` vs `ret60`: ~**0.92**
- `ema7_20_spread` vs `ema7_slope60`: ~**0.96**
- `ema20_dist` vs `ret60`: ~**0.94**

Therefore S6.1 should **not** be interpreted as 14 independent signals. The evidence clusters into roughly three distinct causal dimensions:
1. **Extension/location** — especially distance to prior 4h/1h high.
2. **Trend/momentum** — return / EMA spread / EMA slopes (highly redundant with each other).
3. **Quietness/activity** — lower realized volatility and, in decisive cases, lower recent volume ratio are SHORT-favoring.

## S6.1 verdict
**FORENSIC PASS.** Pre-entry data contains stable BUY-vs-SELL information across discovery and validation, including the decisive one-direction-wins subset.

This materially justifies continuing the S6 dynamic-direction branch.

However:
- no cutoff has been chosen;
- no features have been combined;
- no classifier has been trained;
- no WR/PnL claim is made for a causal direction strategy yet;
- the S6.0 74.82% full-stack number remains hindsight capacity, not deployable performance.

## Research decision
If continuing, the clean next milestone is **S6.2 — Frozen Low-Dimensional Direction Candidate Test**:
- freeze a deliberately small, non-redundant candidate set from S6.1;
- suggested dimensions: `dist_4h_high` (extension), one trend feature such as `ret60` or `ema7_20_spread`, and one activity feature such as `rv4h` / volume ratio;
- use chronological walk-forward / train-only thresholds or a simple regularized classifier;
- all preprocessing/thresholds must be fitted on past data only;
- test BUY-vs-SELL selection on future folds with 139/139 coverage;
- do not touch the frozen S5.7G management layer until causal direction selection itself is established.

## Execution
- Successful workflow run: **32032443059**
- Artifact: `s61-output`, ID **9289421220**
- Script: `research/s61_preentry_direction_feature_atlas.py`
- No live BBC modification.
