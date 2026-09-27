# SOL Indicator Relationship Discovery — Stage 7H Preregistration

**Status:** FROZEN BEFORE TRUE-L2 OUTCOME ANALYSIS  
**Parent:** Stage 7G found no replicated directional feature from Binance Vision bookDepth or raw aggTrades.  
**Purpose:** test whether **true price-level L2 dynamics**—add/cancel, refill, defense, sweep and liquidity reaction—contain directional information that aggregate depth buckets and trade imbalance missed.

## 1. Frozen base universe

Research events remain the exact frozen R3 directional episode onsets already used in Stage 7F/7G.

Frozen direction mapping, regime/state grammar, TP/SL objective and labels are unchanged:
- TP = +1.00%
- SL = -1.00%
- RR = 1:1
- primary directional anatomy = TP versus SL among 4H-resolved onset events
- TIME excluded from TP-vs-SL anatomy but reported separately.

No Stage-6 cell, side, threshold or outcome definition may be changed in 7H.

## 2. True-L2 source requirements

A source may enter outcome-bearing Stage 7H only if it provides:
- price-level bid/ask updates, not percentage-band aggregates;
- exchange timestamp and/or recorder timestamp;
- enough information to reconstruct book state causally;
- initial snapshot or documented snapshot+diff reconstruction;
- sequence/order integrity checks or sequence identifiers where the exchange supplies them;
- historical availability spanning DEV 2023–24, 2025 and 2026.

### Candidate source A — Tardis Binance USDS-M Futures
Expected dataset:
- exchange: binance-futures
- data type: incremental_book_L2
- symbol: SOLUSDT
- captured Binance depth stream + generated initial depth snapshot;
- normalized rows containing price, amount, side, timestamp/local_timestamp and snapshot/update information.

Tardis documentation states Binance USDS-M historical data is available for all instruments since 2019-11-17; incremental depth is recorded at the fastest Binance feed cadence and book integrity is checked against Binance sequence numbers.

### Candidate source B — Binance official Historical Futures Order Book
Expected type:
- T_DEPTH tick-by-tick level-2 data.

This source is considered operationally eligible only if the environment has an API key authorized/whitelisted for historical order-book download. Public current REST depth is not a historical substitute.

## 3. Stage 7H-A — feasibility audit

Before any outcome-bearing L2 result:

1. Audit free Tardis SOLUSDT incremental_book_L2 samples for:
   - 2023-01-01
   - 2024-01-01
   - 2025-01-01
   - 2026-01-01
   - 2026-09-01
2. Parse header/schema.
3. Verify both bid and ask rows exist.
4. Verify snapshots exist.
5. Verify timestamps are monotonic enough for replay.
6. Measure compressed/uncompressed size and update count.
7. Verify an order book can be reconstructed from the first snapshot forward.
8. Check only whether a configured TARDIS_API_KEY is present; never print or persist its value.
9. Check only whether Binance historical-L2 credentials appear configured; never print or persist secret values.

A successful free-sample audit proves **schema/replay feasibility only**, not full-history research coverage.

## 4. Full-history access gate

Outcome-bearing Stage 7H-B/C may run only if one of these is true:

- Tardis full-history access is available for SOLUSDT 2023-01-01 through 2026-09-24; or
- Binance official T_DEPTH historical access is available for the same required periods.

Free first-of-month samples are **not** sufficient for DEV→2025→2026 performance validation and must never be extrapolated as if they were random/full-history coverage.

If no full-history credential is available:
- Stage 7H stops at source/replay feasibility;
- no fake TP-vs-SL result is generated;
- exact replay and feature specification is still frozen so data can be plugged in later without redesign.

## 5. Frozen L2 event mechanics for full-history stage

If full-history access passes, every event uses only updates with timestamp <= R3 onset.

Book reconstruction:
- initialize from latest valid snapshot before event;
- replay ordered incremental updates;
- zero quantity removes level;
- future-nearest updates are forbidden;
- event is invalid if sequence integrity is broken or snapshot is too stale.

Primary observation windows ending at onset:
- 5 seconds
- 15 seconds
- 30 seconds
- 60 seconds
- 5 minutes

## 6. Frozen mechanism families

No ML is allowed in first true-L2 anatomy. Exact deterministic families:

### A. Same-side liquidity support/opposition
Direction-normalized:
- near-touch liquidity within 5 / 10 / 25 / 50 bps;
- same-side versus opposite-side depth imbalance;
- nearest large resting level distance.

### B. Add / cancel pressure
For each window:
- same-side added notional;
- same-side cancelled notional;
- opposite-side added notional;
- opposite-side cancelled notional;
- normalized add-minus-cancel pressure.

### C. Refill / repeated defense
At a price level:
- level is reduced by aggressive interaction or quantity decrease;
- quantity subsequently reappears/increases at the same price inside the frozen window;
- count and refill notional are measured.

### D. Pull-before-touch
- resting liquidity on the intended path is removed while price is approaching;
- same concept measured on protective-side liquidity;
- no motive such as spoofing is inferred.

### E. Sweep / reclaim
- sequential depletion/removal of multiple adjacent levels;
- followed by restoration/reclaim in the opposite direction before onset.
This is a structural label only, not proof of liquidation or manipulation.

### F. Book response efficiency
- signed mid-price movement per net same-direction liquidity removal/addition;
- tests whether book pressure actually produces price response.

## 7. Direction normalization

Every L2 metric is expressed relative to the frozen R3 trade side.

Positive = structurally supportive of the frozen R3 direction.
Negative = structurally opposing it.

This prevents separate threshold mining for LONG and SHORT.

## 8. Discovery/validation discipline

If full-history access passes:
- thresholds are learned only from DEV 2023–24;
- 2025 and 2026 are untouched validation;
- single-family anatomy precedes any feature combination;
- no outcome-based feature deletion;
- no post-hoc threshold rescue.

A later executable 7H combination must be separately preregistered and still target:
- >=1 trade/day
- >=70% TP-hit WR
- TP >=1%
- RR >=1:1
- positive net expectancy after cost.

## 9. Guardrails

- No synthetic L2 from OHLCV.
- No percentage-band bookDepth treated as price-level L2.
- No current REST snapshot backfilled into historical timestamps.
- No claim of spoofing, absorption, liquidation or institutional intent from pattern alone.
- Free sample dates are feasibility samples only.
- Secrets/API keys are never logged or persisted.

**STAGE7H_A_FROZEN_BEFORE_SOURCE_AUDIT**
