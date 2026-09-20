# BNB B38-S8 — Loss Recovery / Avoidance Matrix

**Scientific identity:** `BNB_B38_S8_LOSS_RECOVERY_MATRIX_V1`

## Purpose

Identify which frozen B38-S5 losses are:
1. convertible to WIN by a causal execution change,
2. avoidable before entry,
3. structurally irreducible under the tested mechanics,

while explicitly measuring how many existing baseline WINs each change preserves or sacrifices.

No detector sub-filter is introduced.

## Baseline

Exact B38-S5:
- entry state machine = B38-S3;
- structural SL reference = B38-S3;
- target mapping:
  - IMMEDIATE_CLEAN -> TP1
  - IMMEDIATE_SWEEP -> TP1
  - DELAYED_CLEAN -> TP1
  - DELAYED_SWEEP -> TP2.

Baseline loss attribution comes from B38-S7:
- ZONE_NOT_1ZW_VALID
- ENTRY_LATE_AFTER_1ZW_MOVE
- SL_FALSE_STOP_BEFORE_VALID_REBOUND
- TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND

## Frozen counterfactual mechanics

These are diagnostics, not final selections.

### C1 NO_CHASE_AFTER_1ZW
At entry decision time, skip the trade if:
- +1ZW diagnostic close was already achieved before or at entry; OR
- entry_price >= demand_high + 1ZW.

This is fully known at entry.
Report skipped baseline wins and skipped baseline losses.

### C2 CLOSE_BASED_STRUCTURAL_INVALIDATION
Keep entry and selected target unchanged.
Replace intrabar SL touch with:
- first completed 15m close strictly below the same frozen SL reference.

Exit a loss at that invalidating 15m close.
A target touched by any 5m bar before that 15m close wins first.

Report actual realized loss R at the invalidating close, which may be worse than -1R.

### C3 DELAYED_SWEEP_USE_TP1
Only DELAYED_SWEEP_RECLAIM changes selected target from TP2 to already-known TP1.
All other modes unchanged.
Same frozen intrabar SL-touch execution.

### C4 CAP_TARGET_AT_1ZW
Keep all entries.
If +1ZW level is above entry and below the frozen selected target:
- diagnostic target becomes +1ZW.
Otherwise keep frozen target.

Same frozen intrabar SL-touch execution.

No late trade is skipped in C4.

### C5 CLOSE_INVALIDATION_PLUS_1ZW_CAP
Combine C2 + C4.
No trade is removed.

## Evaluation

For each DEV and REF period and each candidate:
- resolved trades;
- WIN / LOSS;
- WR;
- baseline WIN retention;
- baseline WIN lost;
- baseline LOSS converted to WIN;
- baseline LOSS skipped;
- trade-count reduction;
- expectancy R;
- total R;
- profit factor;
- max loss streak;
- max drawdown R.

Also report a matrix by baseline loss-attribution category:
- converted to WIN;
- skipped;
- still LOSS;
- ambiguous/unresolved.

## Interpretation rules

A candidate can only be described as a plausible improvement if:
- it converts baseline losses;
- and its baseline-WIN retention is explicitly shown.

No candidate is declared final in S8.

## Stop rule

Do not:
- tune thresholds;
- add mode filters;
- choose candidates after outcome and relabel as preregistered;
- hide sacrificed baseline wins;
- treat skipped losses as converted wins.
