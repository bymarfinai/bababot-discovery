# BNB B38-S5 — Frozen Adaptive Policy Candidate

**Scientific identity:** `BNB_B38_S5_ADAPTIVE_POLICY_V1`

## Purpose

Freeze one deployable adaptive execution policy derived from the already-frozen B38 structural principle and the B38-S4 development characterization.

This is the end of development-policy selection for this lineage. No additional target switching, mode filtering, RR filtering, or threshold tuning is allowed under this identity.

## Structural principle

`H1 bullish BOS -> causal H1 demand -> 15m expansion -> corrective return -> demand interaction -> reclaim state -> adaptive execution`

Entry and structural invalidation remain exactly B38-S3.

## Frozen execution-mode policy

### IMMEDIATE_CLEAN_RECLAIM
- Entry: first-touch 15m close above demand_high
- SL reference: H1 demand_low
- Exit objective: **TP1**, nearest already-known overhead structural objective

### IMMEDIATE_SWEEP_RECLAIM
- Entry: first-touch 15m close above demand_high after sweep below demand_low
- SL reference: actual first-touch sweep low
- Exit objective: **TP1**

### DELAYED_CLEAN_RECLAIM
- First touch closes inside demand and does not structurally invalidate
- Entry: first later 15m close above demand_high
- SL reference: H1 demand_low
- Exit objective: **TP1**

### DELAYED_SWEEP_RECLAIM
- First touch / pending phase includes sweep below demand_low without close acceptance below demand_low
- Entry: first later 15m close above demand_high
- SL reference: lowest sweep low observed through confirmation
- Exit objective: **TP2**, second already-known overhead structural objective

If the required objective does not exist at entry:
- status = `NO_POLICY_TARGET`
- do not substitute another target.

## Frozen structural target source

TP1/TP2 are exactly the B38-S3 causal ladder built at entry from:
1. already-confirmed 15m pivot highs above entry;
2. frozen pre-retest expansion high above entry;
3. already-confirmed H1 pivot highs above entry.

No fixed percentage target and no fixed R multiple is used.

## Development characterization

B38-S5 may score this composite policy on 2022-2024 only to summarize the already-developed candidate.

Those numbers are **not** independent validation because the TP mapping was chosen after B38-S4 outcomes were known.

## Prospective freeze

Policy identity becomes immutable from this commit onward.

Prospective validation must use market data whose bars occur strictly after:
**2026-09-20T06:30:00Z**.

Historical 2025-2026 data must not be presented as clean OOS evidence for B38-S5 because B38 was formulated after prior lineage reference results had already been seen.

## Forward-validation gate

A later prospective report may evaluate:
- trade count;
- W/L;
- realized R;
- expectancy R;
- profit factor;
- max loss streak;
- cumulative-R max drawdown;
- performance by execution mode.

No rule may be changed during forward validation.

## Stop rule

Under B38-S5 V1 do not:
- alter entry state machine;
- alter SL references;
- change TP assignment per mode;
- replace missing TP2 with TP1;
- filter modes;
- add RR thresholds;
- add time/session filters;
- add indicators, ATR, volume, funding, OI, or derivatives;
- use historical reference results to claim prospective validation.
