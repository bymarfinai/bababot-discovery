# BNB B38-S16 — Frozen Near-Cluster TP Economics Preregistration

## Objective
Test whether the S15 pre-TP1 continuation character improves total E2 economics without changing the E2 detector, entry, structural SL, or target definitions.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- Executable population:
  - DEV 440 = 325 WIN / 115 LOSS
  - REF 272 = 201 WIN / 71 LOSS
- S15 continuation character:
  - causal TP2 exists above TP1
  - `extension_gap_r <= 0.12184510703934905`
- This cut is the frozen DEV median from S15. It is not retuned in S16.

## Policies
All non-cluster trades stay at baseline TP1.

### P0_BASELINE_TP1
Full size exits at TP1.

### P1_CLUSTER_FULL_TP2
For frozen near-cluster trades, full size targets TP2 directly.
All other trades target TP1.

### P2_CLUSTER_HALF_TP1_HALF_TP2_STRUCTURAL
For frozen near-cluster trades:
- 50% realizes at TP1
- remaining 50% continues to TP2
- runner keeps the original frozen structural SL

### P3_CLUSTER_HALF_TP1_HALF_TP2_BE
For frozen near-cluster trades:
- 50% realizes at TP1
- remaining 50% targets TP2
- runner moves to break-even starting on the next 5m bar after TP1
All other trades target TP1.

## Required reporting
For DEV and REF:
- W/L and WR
- median winning R
- expectancy R/trade
- total R
- profit factor
- max drawdown and max loss streak
- baseline winners retained as profitable outcomes
- baseline winners converted to losses
- baseline losses converted to wins
- cluster trade count
- cluster-specific realized R

Also report annual stability (2022–2026).

## Decision boundary
No detector or threshold promotion occurs in this stage.
The near-cluster character is considered economically useful only if improvement is visible in REF as well as DEV and does not materially destroy baseline winner retention.
