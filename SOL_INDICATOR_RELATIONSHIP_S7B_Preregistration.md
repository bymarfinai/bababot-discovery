# SOL Indicator Relationship Discovery — Stage 7B Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING EXECUTION  
**Parent:** Stage 7 failed the >=70% target using R3_STABLE_REGIME_CELLS with TP=1.00%, SL=1.00%, one active position.  
**Purpose:** determine whether failure is mainly stale/repeated entry timing and test a finite set of causal 5–30 minute entry confirmations.  
**Research only:** Stage-6 state definitions and Stage-7 R3 direction mapping remain frozen.

## 1. Frozen base rule

Stage 7B uses only the Stage-7 DEV-selected family:

`R3_STABLE_REGIME_CELLS`

LONG:
- SIDEWAYS + HIGHLOC_BUY_BUILD
- TRANSITION + HIGHLOC_SELL_ABSORPTION_LIKE

SHORT:
- BULL + DELEVERAGING
- SIDEWAYS + HIGHLOC_BUY_EXHAUSTION_LIKE
- SIDEWAYS + DELEVERAGING
- TRANSITION + HIGHLOC_BUY_EXHAUSTION_LIKE

No other Stage-6 state is added.

Execution economics remain fixed:
- TP = +1.00%
- SL = -1.00%
- RR = 1:1
- max hold = 4h from the **actual triggered entry**
- round-trip cost = 0.15%
- one active position
- same-bar TP+SL => conservative SL
- no cooldown.

## 2. Signal episode definition

At each 15m Stage-7 decision time, derive the frozen R3 direction: LONG / SHORT / NO_TRADE.

A **new directional episode** begins at time `t0` when:
- signal at `t0` is LONG or SHORT; and
- signal at `t0-15m` is not the same direction.

An episode remains the same directional episode while consecutive 15m decisions retain the same LONG/SHORT direction.

If the direction flips, the old episode ends and a new opposite episode begins.
NO_TRADE also ends the prior episode.

This definition is frozen before results.

## 3. Stage 7B-A — failure decomposition

Using the original Stage-7 R3 TP1/SL1 executed trades, report outcome TP/SL/TIME by:

### Episode age at entry
- ONSET = 0m
- 15m
- 30m
- 45–60m
- >60m

### First post-entry movement
For each trade:
- first completed 5m return in intended direction;
- intended-direction return after 15m;
- intended-direction return after 30m;
- first-15m MFE;
- first-15m MAE.

Report medians and TP/SL/TIME rates.

These diagnostics do not define new thresholds in Stage 7B.

## 4. Stage 7B-B — frozen trigger candidates

All candidates start only from a **new R3 directional episode**.

### T0_ONSET
Enter at raw 5m open at `t0`.

### T1_PRICE_CONFIRM_5M
Wait one complete 5m bar after `t0`.
Confirmation:
- LONG: 5m close > entry-anchor price at `t0`
- SHORT: 5m close < entry-anchor price at `t0`
If confirmed, enter at raw 5m open at `t0+5m`.

### T2_PRICE_CONFIRM_15M
Wait 15m after `t0`.
Confirmation:
- LONG: completed 15m-path final 5m close at `t0+10m` > entry-anchor price at `t0`
- SHORT: that close < entry-anchor price at `t0`
If confirmed, enter at raw 5m open at `t0+15m`.

### T3_PRICE_CONFIRM_30M
Same rule using the final completed 5m close before `t0+30m`.
If confirmed, enter at raw 5m open at `t0+30m`.

### T4_STATE_PERSIST_15M
Require the exact R3 directional signal at `t0+15m` to equal the onset direction.
Enter at raw 5m open at `t0+15m`.

### T5_STATE_PERSIST_30M
Require the same R3 directional signal at both `t0+15m` and `t0+30m`.
Enter at raw 5m open at `t0+30m`.

### T6_PERSIST15_AND_PRICE15
Require both T2 and T4.
Enter at `t0+15m`.

### T7_PERSIST30_AND_PRICE30
Require both T3 and T5.
Enter at `t0+30m`.

No additional confirmation threshold such as +0.10%, +0.25%, RSI, EMA, candle shape, or OI retuning may be introduced in this stage.

## 5. Trigger simulation

For each trigger:
- evaluate only complete episodes with enough future raw data;
- entry price = raw SOL 5m open at the trigger time;
- max hold 4h from triggered entry;
- TP/SL barriers are computed from the triggered entry, not from `t0`;
- one active position globally across triggered entries;
- while active, new eligible episodes are ignored;
- each DEV/2025/2026 partition simulated independently.

## 6. DEV trigger selection

A trigger is **TARGET_ELIGIBLE** on DEV only if:
- >=1.00 executed trade/day;
- target WR = TP / all trades >=70%;
- positive net expectancy after 0.15% round-trip cost;
- PF > 1.

If multiple pass:
1. highest target WR;
2. higher net expectancy;
3. higher trades/day;
4. shorter confirmation delay;
5. lexical name.

If none passes:
- diagnostic leader among triggers with >=1 trade/day:
  1. highest target WR;
  2. higher net expectancy;
  3. shorter delay.
- if none reaches >=1/day, highest trades/day then WR.

2025/2026 cannot alter trigger selection.

## 7. Frozen validation gate

The exact DEV-selected trigger is applied unchanged to 2025 and 2026.

Promotion requires DEV, 2025, and 2026 all satisfy:
- >=1.00 trade/day;
- target WR >=70%;
- positive net expectancy;
- PF >1.

If DEV has no TARGET_ELIGIBLE trigger, Stage 7B cannot promote a rule.

## 8. Side diagnostics

For the selected trigger, report LONG-only and SHORT-only metrics by partition.
No side may be deleted after validation in this stage.

## 9. Interpretation

Stage 7B tests a narrow hypothesis:

> Stage 7 may have failed because entering every available R3 condition included stale/repeated signals or because a short causal confirmation after state onset is required.

It does not reopen market-state discovery and does not permit arbitrary confirmation search.

**STAGE7B_FROZEN_BEFORE_RESULTS**
