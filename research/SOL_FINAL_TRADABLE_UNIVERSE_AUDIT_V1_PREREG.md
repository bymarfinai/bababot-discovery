# SOL Final Tradable Universe Audit V1 — Preregistration

## Objective

Audit the robustness of the remaining SOL trading universe after the one-shot Score-4 SHORT rediscovery was stopped.

This experiment performs **no further discovery and no optimization**.

Frozen tradable universe:

1. Anatomy Score 3, both liquidity sides -> TRADE.
2. Anatomy Score 4 + SELL_SIDE liquidity -> LONG -> TRADE.
3. Anatomy Score 4 + BUY_SIDE liquidity -> SHORT -> SKIP / removed from tradable universe.

## Frozen execution stack

Detector:
- validated actionable structural-liquidity detector;
- anatomy score >= 3;
- same-reclaim-bar resolved events excluded.

Entry:
- Score 3 -> FIVE_MIN_REVERSAL_BREAK.
- Score 4 -> GAP_25.

Initial SL:
- RECLAIM_EXTREME.

Exit:
- no fixed TP;
- no trailing;
- no post-entry stop tightening;
- if initial SL survives, exit at first 5m open at or after frozen structural-outcome-known time.

No parameter may change during this audit.

## Evidence status

The architecture was assembled after inspecting historical and 2026 data.

Therefore **all data in this audit are retrospective**.

Observation end is frozen to:
**2026-09-21 00:00 UTC**

This audit can establish retrospective robustness, but cannot create independent validation.

## Core metrics

Report:
- N;
- event rate;
- gross win rate;
- mean/median R;
- PF;
- cumulative R;
- max DD;
- max losing streak;
- median holding time;
- BUY_SIDE and SELL_SIDE metrics;
- Score-3 and Score-4-LONG metrics;
- yearly metrics 2020-2026;
- half-year metrics;
- exit mix.

## Robustness tests

### 1. Core economics gates

All must pass:

- total N >= 250;
- mean R >= +0.08R;
- PF >= 1.20;
- cumulative R > 0;
- max DD <= 15R;
- max losing streak <= 8;
- at least 5 positive calendar years;
- no two consecutive negative calendar years.

### 2. Component gates

- Score 3 N >= 200;
- Score 3 mean R > 0;
- Score 3 PF >= 1.10;
- Score-4 SELL_SIDE N >= 20;
- Score-4 SELL_SIDE mean R > 0;
- Score-4 SELL_SIDE PF >= 1.20;
- BUY_SIDE mean R > 0;
- SELL_SIDE mean R > 0.

### 3. Leave-one-year-out robustness

For each exclusion year 2020-2026:
- recompute the full remaining sample;
- mean R must remain > 0;
- PF must remain >= 1.10.

All leave-one-year-out samples must pass.

### 4. Bootstrap robustness

Using deterministic seed 42 and 10,000 trade-level bootstrap resamples:

- P(mean R > 0) >= 99%;
- 5th percentile bootstrap mean R > 0;
- median bootstrap PF > 1.20.

Bootstrap is descriptive of trade-level sampling uncertainty; it does not create independent evidence.

### 5. Rolling path robustness

Sort trades chronologically.

For every rolling 20-trade block:
- calculate mean R and PF.

Required:
- at least 70% of rolling-20 blocks have mean R > 0;
- worst rolling-20 mean R > -0.35R.

### 6. Execution-friction stress

Apply total round-trip friction of:
- 10 bps;
- 20 bps;
- 30 bps;

converted per trade to R by:

`friction_R = (entry_price * round_trip_bps / 10000) / initial_risk_price`

and:
`net_R = gross_R - friction_R`.

Required:
- at 20 bps: mean net R > 0 and PF >= 1.10;
- at 30 bps: mean net R > 0.

No friction scenario may be used to alter entry/SL/exit.

## Decision

If every frozen gate above passes:

`SOL_FINAL_UNIVERSE_RETROSPECTIVELY_ROBUST`

Operational interpretation:
- architecture is suitable to freeze for forward/paper execution testing;
- it is NOT independently validated live trading economics.

If any gate fails:

`SOL_FINAL_UNIVERSE_NOT_ROBUST_AS_DEFINED`

No rescue parameter search is allowed in this V1.

## Stop rule

After this audit:
- do not reopen Score-4 SHORT;
- do not optimize TP or SL;
- do not add session/hour/indicator filters to rescue a failed gate.

Any next step must be either:
1. forward execution validation of the frozen stack; or
2. stop/reject the SOL production candidate if retrospective robustness is insufficient.
