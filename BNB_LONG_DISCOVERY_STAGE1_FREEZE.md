# BNB LONG Character Discovery Reset V1 — Stage 1 Freeze

Status: **FROZEN BEFORE NEW DISCOVERY RUNS**

Branch: `bnb-long-character-discovery-reset-v1`

## 1. Scope

- Symbol: **BNBUSDT**
- Side: **LONG only**
- Discovery unit: **one fixed 1-hour WIB habitat at a time**
- First habitat when Stage 2 begins: **00:00–01:00 WIB (H00)**
- SHORT discovery is explicitly out of scope until the LONG pipeline produces a validated ready-to-trade character or the LONG program is formally stopped.

## 2. Discovery Objective

The only objective of Character Discovery is:

> Find a repeatable structural market character inside one fixed WIB hour that materially distinguishes viable BNBUSDT LONG opportunities from failed/noisy LONG opportunities.

Character Discovery is **not** the stage for optimizing TP, SL, leverage, position sizing, execution timing, or maximizing headline win rate.

A discovery candidate must represent a market structure that can be explained and reproduced, not merely a parameter combination that happened to score well historically.

## 3. One Experiment = One Hour

Each discovery experiment covers exactly one WIB habitat.

Examples:
- H00 = 00:00–01:00 WIB
- H01 = 01:00–02:00 WIB
- ...
- H23 = 23:00–00:00 WIB

Hours may not be merged, widened, shifted, or combined during the discovery of that hour merely to improve results.

## 4. Primary Character vs Secondary Confirmation

Every hour must be evaluated in two layers:

### Primary Character
The structural reason the LONG opportunity exists. It must describe the underlying market condition and must remain interpretable.

### Secondary Confirmation
An optional filter that removes false/noisy signals while preserving the same primary structure.

A secondary confirmation may not silently replace the primary character or become an increasingly specific rescue rule after weak results are observed.

## 5. Allowed Structural Families

Stage 2 may inspect structural information from the following broad families without pre-selecting the winning combination:

- market regime / directional context
- price location versus reference trend structure
- swing / local high-low structure
- reclaim / rejection behavior
- range location and compression / expansion context
- momentum state
- volatility state
- pre-entry structural context

These are structural families, **not frozen thresholds**. Numerical thresholds and exact character definitions must be discovered only from Development data and then frozen before validation.

## 6. Forbidden During Character Discovery

The following are prohibited as rescue mechanisms:

- changing the target hour after seeing weak results
- merging neighboring hours to inflate performance
- optimizing TP/SL as part of character discovery
- tuning leverage or position sizing
- adding filters only because a candidate failed a gate
- repeatedly relaxing thresholds until a PASS appears
- selecting a character based primarily on peak WR
- reading unseen/OOS results while still modifying the character
- using prior B28-series winners as mandatory templates for the new search

## 7. Historical Work Treatment

All prior BNB branches, including B28I, B28M, B28P and related experiments, remain preserved as historical research.

For Reset V1 they are **archive/reference only** and do not receive automatic promotion, preferential treatment, or parameter inheritance.

The new discovery must be able to rediscover a similar structure independently if that structure is genuinely robust.

## 8. Data Separation Rule

To prevent leakage:

- **Development:** 2022-01-01 through 2024-12-31
- **Unseen/OOS reference validation:** 2025-01-01 through 2026-07-30

Character search and all threshold formation occur only on Development data.

The OOS period must remain unopened for candidate-specific tuning until a Development character has been frozen and promoted to validation.

## 9. Stage Boundary

Stage 1 ends when this document is committed.

No new backtest, hour scan, threshold optimization, or OOS evaluation is part of Stage 1.

Stage 2 begins with **H00 (00:00–01:00 WIB)** and must use this frozen scope without changing it after seeing H00 results.

## 10. Reset Principle

The reset discards **methodological drift**, not historical evidence.

The target is not to finish all 24 hours. The target is to find the first structural character strong enough to deserve validation, then stop scanning and validate it.
