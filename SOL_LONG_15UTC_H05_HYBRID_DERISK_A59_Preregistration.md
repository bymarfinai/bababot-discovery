# SOL LONG 15:00 UTC H05 Hybrid De-risk + H10 Re-arm — A59 Preregistration

## Research question

A52 established `POST_H05` as a replicated live-causal M2 danger state, while A53 showed that a **100% hard exit** at that state raises WR / reduces DD but destroys net expectancy in External and Reference Validation because valuable eventual winners are sacrificed. A54–A58 did not produce a replicated binary confirmation trigger that can replace H05 with a cleaner hard-exit rule.

A59 tests a different response architecture:

> When the frozen 15UTC parent enters `POST_H05`, can the strategy temporarily reduce exposure rather than exit, then restore exposure only after a frozen structural recovery level (`close > H+0.10R`) is causally regained?

This is an executable economics experiment. It does **not** search for a new predictor.

## Frozen parent

Unchanged SOL LONG 15UTC / R360 parent:

- entry geometry: `E0_RESTING_H`
- target: `E40 = H + 0.40R`
- notional: `$500`
- horizon: `720m`
- before breakout confirmation: structural failure when completed 5m close `< L`, executed next open
- after breakout confirmation: structural failure when completed 5m close `<= H`, executed next open
- parent target/terminal precedence remains frozen exactly as A2/A53
- partitions and parent sample counts remain frozen:
  - Development `N=601`
  - External `N=281`
  - Reference Validation `N=337`

Baseline replay must match the frozen parent exactly before A59 is valid.

## Why a static partial cut is not the primary test

For a fixed cut fraction `q` with no later state-dependent action,

`PnL_static_partial = (1-q) * PnL_parent + q * PnL_A53_H05_hard_guard`

and therefore

`Delta_static_partial = q * Delta_A53_H05_hard_guard`.

A53 H05 hard-guard raw deltas were:

- Development: `+$122.26`
- External: `-$93.46`
- Reference Validation: `-$19.64`

Hence any non-zero static convex partial cut necessarily retains the negative OOS sign. A59 therefore requires a **nonlinear causal re-arm**, not a cosmetic static blend.

## Primary executable variant — `HYB50_H05_H10_REARM`

Only one variant is authorized.

### 1. H05 de-risk trigger

Use the exact frozen A52/A53 H05 warning:

- breakout has already been confirmed by completed 5m close `> H`;
- a completed 5m candle closes `> H` and `<= H + 0.05R`;
- the trade is still live after frozen target / structural-terminal precedence.

The warning is known only at that candle close.

### 2. De-risk execution

At the **next 5m open** after the first valid H05 warning:

- exit exactly **50%** of the original `$500` notional;
- retain exactly **50%** under the original frozen parent target / structural-failure logic.

`50%` is a single neutral allocation chosen before results. There is no fraction grid and no neighboring allocation test.

### 3. Re-arm trigger

After de-risk execution, while the parent remains structurally live, restore the removed 50% only after the first completed 5m candle that closes:

`close > H + 0.10R`.

`H+0.10R` is not newly fitted: it is the already-frozen H10 structural coordinate used in A52–A54 and A57–A58.

The re-arm trigger is known only at the completed candle close.

### 4. Re-arm execution

At the next 5m open after that completed `close > H+0.10R`:

- re-enter exactly the removed **50%** notional;
- thereafter keep full exposure until the frozen parent target / terminal / timeout resolution.

### 5. One-shot state machine

Each trade may have at most:

- one H05 de-risk;
- one H10 re-arm.

After re-arm, no second de-risk is allowed even if H05 is revisited. No oscillating/cycling position logic is permitted.

### 6. Precedence / causality

For every completed 5m bar after entry:

1. frozen parent target resolution;
2. frozen parent structural-terminal resolution;
3. if still live, H05 de-risk warning or H10 re-arm warning as appropriate.

No warning may pre-empt a target or terminal event already resolved by that bar. Entry-candle H05 follows the same causal handling as A53: warning known at entry-candle close, de-risk at next bar open.

## PnL accounting

Raw PnL is computed leg-by-leg:

- pre-cut 50% leg: original entry -> de-risk execution;
- retained 50% leg: original entry -> frozen parent final execution;
- if re-armed, new 50% leg: re-arm execution -> frozen parent final execution.

The frozen parent path and final resolution are not changed by position size.

## 5bps stress accounting

The frozen baseline uses `5bps` all-in stress on the original `$500` trade.

A59 charges:

- baseline stress cost on the full original notional in every trade; plus
- if re-arm occurs, one additional 5bps round-trip stress cost on the re-armed 50% notional.

Thus:

- no re-arm: stress cost = `0.0005 * 500`;
- re-arm: stress cost = `0.0005 * 500 * (1 + 0.50)`.

This prevents extra hybrid turnover from receiving free execution.

## Development-first protocol

A59 must simulate and evaluate **Development first**.

External and Reference Validation hybrid results must not be computed/reported unless the Development support gate passes. Their frozen baseline metrics may be referenced only for reconciliation context.

No thresholds, size fractions, or execution rules may be changed after the Development result is opened.

## Development support gate

`HYB50_H05_H10_REARM` is Development-supported only if all are true versus frozen baseline:

1. raw Net increases;
2. 5bps Net increases;
3. raw PF increases;
4. 5bps PF increases;
5. 5bps WR is not lower;
6. raw max DD is not higher;
7. at least `4/6` frozen Development half-year blocks have positive raw DeltaNet;
8. at least `4/6` blocks have positive 5bps DeltaNet.

If any fail: status = `SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_DEVELOPMENT`; OOS remains unopened.

## OOS confirmation gate

Only if Development passes, the exact frozen variant is then run without modification in External and Reference Validation.

For **each** OOS partition all must hold versus its frozen baseline:

1. raw Net increases;
2. 5bps Net increases;
3. raw PF increases;
4. 5bps PF increases;
5. 5bps WR is not lower;
6. raw max DD is not higher.

Full support requires both OOS partitions to pass.

Possible final statuses:

- `SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_SUPPORTED`
- `SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_OOS`
- `SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_DEVELOPMENT`

## Required diagnostics

Report, at minimum:

- exact parent parity;
- N, WR, PF, expectancy, Net, max DD, max loss streak;
- same metrics under 5bps stress;
- H05 de-risk count;
- re-arm count and re-arm rate;
- de-risk-without-rearm count;
- parent winners de-risked;
- parent losers de-risked;
- winner raw PnL delta;
- loser raw PnL delta;
- total raw / 5bps DeltaNet;
- Development 6-block DeltaNet raw / stress.

Additional non-promotional diagnostics may describe target/failure composition among de-risked and re-armed trades, but may not create a new rule.

## Prohibitions

A59 may not:

- sweep cut fractions;
- test 25/33/40/60/67/75% after seeing 50%;
- move H05 or H10 thresholds;
- combine H05 with PRE_L25 or timers;
- use 1m A58 future-conditioned motifs as live filters;
- add posthoc calendar/week filters;
- retune on External or Reference Validation;
- convert a failed gate into support based only on WR aesthetics.

## Interpretation rule

A59 is specifically testing whether **temporary exposure reduction + causal structural re-arm** solves A53's winner-sacrifice problem.

If it fails, that is evidence against this simple hybrid architecture, not permission to optimize the fraction or recovery threshold posthoc.

Research only. Live Baba Bot remains unchanged.
