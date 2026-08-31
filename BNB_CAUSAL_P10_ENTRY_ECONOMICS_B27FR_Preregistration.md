# B27FR — BNB Causal P10 Entry Economics Preregistration

## Purpose

Convert the frozen BNB structural habitat into one executable, causal LONG entry rule and test its development-sample economics without any further temporal, threshold, TP, SL, weekday, or parameter optimization.

This milestone is an economics test, not a new structure search.

## Lineage and interpretation guard

- Parent: B27FQ execution-duration geometry audit.
- Frozen canonical geometry: reference `01:00–05:00 WIB`; execution `05:00–10:00 WIB`.
- Mandatory B27FQ reproduction gate: `1095` complete sessions, `167` causal leaves, `142` H2 arrivals.
- The B27FQ `142/167 = 85.03%` is a structural H2/leave rate, **not trading WR**.
- P10 was motivated by the earlier B27FM development diagnosis. Therefore B27FR remains a development/discovery economics test and must not be described as independent validation or holdout evidence.

## Frozen data universe

- Symbol: `BNBUSDT`.
- Existing repository 5-minute loader only.
- Timezone: `Asia/Jakarta`.
- Normalized local dates: `2022-01-02` through `2024-12-31`, inclusive.
- Require complete reference and execution windows for every session.
- Raw coverage gate: `>=99.5%`.
- No external/reference-validation/August/holdout data.
- All weekdays retained.

## Frozen geometry

For each local date:

- Reference: `[01:00, 05:00)` WIB.
- Execution: `[05:00, 10:00)` WIB.
- `H = max(reference high)`.
- `L = min(reference low)`.
- `R = H - L`.

No clock or duration re-selection is permitted in B27FR.

## Frozen causal K1 → leave state machine

Use the existing B27EM/B27FQ `classify_long` implementation unchanged.

Conceptually:

### SEEK_K1

- `close > H` or `close < L` before K1 => `BREAK_BEFORE_K1`.
- H visit: `high >= H and close <= H`.
- L visit: `low <= L and close >= L`.
- simultaneous H+L => `AMBIGUOUS_BOTH_BOUNDARIES`.
- K1 is only the first H visit with zero prior L visits.
- `k1_signal` is known only after the completed K1 5-minute candle.

### K1_EPISODE

- While `high >= H and close <= H`, remain in the same H episode.
- The first completed candle that is not part of that same H episode is the causal leave candle.
- `leave_ts` is the end of that completed leave candle.

### AFTER_LEAVE structural terminal convention

- H2 arrival: `high >= H`.
- Opposite break: `close < L`.
- Same-bar H2/opposite break remains ambiguous in the structural classifier.
- No favorable same-bar ordering may be introduced by B27FR.

## Frozen P10 causal signal

Only sessions with a causal leave are eligible.

The first post-leave candle is the 5-minute candle whose **start timestamp equals `leave_ts`**, matching B27FM.

The signal is known only after that first post-leave candle completes.

Signal requirements:

1. The first post-leave candle exists.
2. H2 has **not** already occurred on that candle: `first_high < H`.
3. Its completed close remains inside the P10 band immediately below H:
   - `H - 0.10*R <= first_close < H`.

No P05/P15/P20 or other threshold is tested.

## Frozen executable entry

- Entry is the **open of the next raw 5-minute candle** after the completed signal candle.
- If that next candle does not exist inside the execution window, skip as `NO_NEXT_BAR_FOR_ENTRY`.
- If entry open is `>= H`, skip as `ENTRY_AT_OR_ABOVE_H`; the structural target is no longer ahead of the executable entry.
- No limit-entry reconstruction and no intrabar hindsight.

## Frozen exits

For each entered LONG trade, inspect raw 5-minute bars from the entry bar through the end of the frozen execution window.

### Target

- Structural target price is exactly `H`.
- A bar with `high >= H` is a target-touch candidate.

### Invalidation

- Invalidation becomes known only after a completed candle with `close < L`.
- Normal invalidation exit is the **next raw 5-minute open**.
- If no next raw execution-window bar exists, use the final execution-window close.

### Same-bar target + invalidation ambiguity

If a post-entry candle has both `high >= H` and `close < L`, intrabar ordering is unknowable. B27FR must not award the favorable target. Classify it `AMBIGUOUS_TARGET_INVALIDATION` and use the same conservative exit convention as invalidation: next raw 5-minute open, or final execution close if no next bar exists.

### Session end

If neither target nor invalidation occurs, exit at the close of the final 5-minute execution candle (the candle ending at 10:00 WIB).

No other TP, SL, trailing stop, timeout, breakeven, partial exit, or discretionary rule is allowed.

## Frozen economics

Illustrative notional: `$500` per trade.

Fee convention inherited from the prior BNB frozen-economics lineage:

- round-trip fee return deduction = `0.0008` = 8 bps total = `$0.40` on $500 before price PnL effects.

Slippage stress levels are fixed at:

- `0 bps`, `2 bps`, `5 bps`, `10 bps` **per side**.

For LONG stress calculations:

- adjusted entry = `raw_entry * (1 + slip_bps/10000)`;
- adjusted exit = `raw_exit * (1 - slip_bps/10000)`;
- stressed gross return = `adjusted_exit / adjusted_entry - 1`;
- net return = stressed gross return - `0.0008` round-trip fee;
- net PnL = `$500 * net return`.

This deliberately applies adverse slippage to both entry and exit, including target exits.

Trading WR is defined as the fraction of entered trades with **net PnL > 0** under the stated fee/slippage profile. Structural target-hit rate is reported separately and must not be called WR.

Profit factor:

- sum positive net PnL / absolute sum negative net PnL;
- if there are no negative trades, report infinity.

## Required outputs

Persist:

- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Trades.csv`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Economics.csv`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Yearly.csv`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Exit_Reasons.csv`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Result.md`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Status.txt`
- `BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR_Run.log`

Report at minimum:

- raw coverage and reproduction gate;
- causal leaves and structural H2 count;
- P10 causal signals;
- skipped `ENTRY_AT_OR_ABOVE_H` / missing-next-bar counts;
- entered trade N;
- raw structural target-hit rate among entered trades;
- exit-reason counts;
- for each slippage stress: trading WR, PF, expectancy $/trade, net $, average win $, average loss $, max losing streak;
- yearly fee-only (`0 bps slippage`) N, WR, PF, expectancy, net;
- explicit statement that this is development-sample economics, not holdout validation.

## Frozen descriptive classification

Use the fee-inclusive, `0 bps` slippage profile as base and `5 bps` per-side as friction stress.

- `ECONOMIC_EDGE_SUPPORTED` only if:
  1. entered `N >= 20`;
  2. base PF `>= 1.25`;
  3. base expectancy `> 0` and base net PnL `> 0`;
  4. 5 bps stress PF `> 1.00` and 5 bps stress net PnL `> 0`.
- `ECONOMIC_EDGE_FRAGILE` if base PF `>=1.25` and base net/expectancy are positive, but the 5 bps stress requirement fails.
- otherwise `ECONOMIC_EDGE_NOT_SUPPORTED`.

The label is development evidence only and cannot authorize live trading.

## Prohibited after seeing results

Within B27FR do **not**:

- change reference/execution clocks;
- select 01:30 or 02:00 because they look better;
- tune P10;
- add weekdays, volatility, trend, volume, order-block, or regime filters;
- tune TP/SL/invalidation/session end;
- change fee/slippage assumptions after seeing outcomes;
- touch holdout data;
- call structural percentages trading WR.
