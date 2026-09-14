# BNB LONG Reset V1 — H03 Primary Discovery PERSISTED

## Verdict

**PRIMARY_PASS**

Frozen habitat:
- Symbol: **BNBUSDT perpetual**
- Side: **LONG**
- Habitat: **03:00–04:00 WIB**
- Anchors: **03:00, 03:15, 03:30, 03:45 WIB**
- Development: **2022–2024**
- OOS: **SEALED / not evaluated**

Selected frozen primary character:

**`drive_60m__LOW`**

Definition: the causal same-anchor percentile of the prior completed 60-minute directional drive is in the LOW state, using the frozen 60-observation rolling reference with minimum 40 prior observations.

Workflow provenance:
- H03 prereg commit: `546959d0480c...`
- H03 runner commit: `d942c06acbd7...`
- Trigger/head SHA: `5fbd904cd163cafc188950886775bfca01b93ab7`
- GitHub Actions run: **34807471101**
- Artifact ID: **10333169367**
- Artifact SHA256: `74acae912d8ad6912d74cd43b71f1a7dba72c10972cf3bca1d506cf4ed7500dd`

The base H00 runner prints an H00 label in its report heading; direct event verification confirms all 4,384 evaluated habitat events are **03:xx WIB**. This is a cosmetic report-label issue only.

## Pooled Development structural economics

| Metric | H03 `drive_60m__LOW` |
|---|---:|
| Selected observations | **1,382** |
| Approx signals/week | **8.83** |
| Consensus WR | **57.74%** |
| Mean consensus return | **+0.0841%** |
| Median consensus return | **+0.0936%** |
| Consensus PF | **1.341** |
| Raw $/signal @ $500 reference | **+$0.42** |
| Raw cumulative equivalent @ $500 | **+$580.84** |
| Raw gross positive equivalent @ $500 | **+$2,284.09** |
| Raw gross negative equivalent @ $500 | **-$1,703.25** |
| Avg winning observation @ $500 | **+$2.86** |
| Avg losing observation @ $500 | **-$2.92** |
| Raw additive max DD equivalent @ $500 | **-$213.04** |
| Max loss streak | **13** |

Dollar figures above are **raw structural diagnostic equivalents**, using the standing reference `$10 margin × 50x = $500 notional`. Leverage is not applied by the structural runner itself.

### Execution economics status

- Executable gross PnL: **N/A — no final hold/TP/SL construction yet**
- Fees/slippage: **N/A — not modeled at primary structural stage**
- Executable net PnL: **N/A**
- Executable max DD: **N/A**
- Position overlap handling: **N/A at primary stage**
- Final TP/SL/hold: **N/A**

Therefore the raw $ figures must not be interpreted as realized or net trading PnL.

## Year robustness

| Year | N | WR | Mean | PF | Raw $/signal @ $500 | Raw total @ $500 | Raw DD @ $500 | LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2022 | 417 | 53.48% | +0.0265% | 1.082 | +$0.13 | +$55.15 | -$147.10 | 12 | PASS |
| 2023 | 474 | 58.86% | +0.0337% | 1.155 | +$0.17 | +$79.93 | -$139.65 | 13 | PASS |
| 2024 | 491 | 60.29% | +0.1816% | 1.870 | +$0.91 | +$445.76 | -$81.22 | 12 | PASS |

All three years satisfy the frozen minimum year gate. Two of three years have WR >55%, satisfying the aggregate era requirement.

## Horizon robustness

| Horizon | N | WR | Mean | PF | Raw $/signal | Raw total | Raw DD | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 60m | 1,382 | 58.76% | +0.0423% | 1.209 | +$0.21 | +$292.11 | -$233.38 | PASS |
| 120m | 1,382 | 57.45% | +0.0786% | 1.293 | +$0.39 | +$543.30 | -$300.90 | PASS |
| 240m | 1,382 | 57.60% | +0.1313% | 1.344 | +$0.66 | +$907.10 | -$228.63 | PASS |

**3/3 horizons supportive.** These are diagnostics only and do not authorize selecting 240m as the final executable holding period.

## Quarter-hour anchor robustness

| Anchor WIB | N | WR | Mean | PF | Raw $/signal | Raw total | Raw DD | LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 03:00 | 345 | 57.39% | +0.0569% | 1.224 | +$0.28 | +$98.07 | -$73.16 | 5 | PASS |
| 03:15 | 347 | 59.65% | +0.1122% | 1.491 | +$0.56 | +$194.60 | -$61.40 | 5 | PASS |
| 03:30 | 347 | 56.48% | +0.0899% | 1.344 | +$0.45 | +$156.04 | -$82.43 | 6 | PASS |
| 03:45 | 343 | 57.43% | +0.0770% | 1.319 | +$0.39 | +$132.12 | -$42.49 | 5 | PASS |

**4/4 anchors supportive.**

## Frozen primary gate result

- Pooled gate: **PASS**
- Horizon gate: **PASS (3/3)**
- Era gate: **PASS**
- Anchor gate: **PASS (4/4)**

Therefore H03 is promoted to:

**PRIMARY_PASS → H03 STRUCTURAL STRESS / SECONDARY CONFIRMATION**

The hour scan stops here. **H04 is not eligible while H03 stress testing remains unresolved.** OOS remains sealed. No H02 rescue rule or H02 secondary is inherited automatically into H03.
