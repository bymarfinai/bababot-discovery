# BTC Market-State MS2 — Intraday Positioning / Squeeze Preregistration

**Status:** FROZEN BEFORE MS2 RESULT OBSERVATION  
**Parent evidence:** MS1 returned `NO_80_STATE_FOUND_MS1`; MS2 does not retune MS1 thresholds. It introduces a materially new information set: official Binance USD-M daily metrics archives (open interest and trader-position ratios).  
**Live BBC:** untouched.

## Hypothesis
The missing information in MS1 is not another price indicator but **crowding and leverage state**. A high-probability directional impulse may require a causal combination of:
- volatility compression;
- leverage/open-interest buildup;
- crowd direction;
- top-trader vs global positioning divergence;
- aggressive taker flow / first acceptance.

This specifically tests whether short-squeeze and long-squeeze states can be recognized **before** the major move.

## Data
- BTCUSDT USD-M perpetual 1h candles, 2024-01-01 through available 2026-08-20.
- Official Binance Data Vision `daily/metrics/BTCUSDT` archives, consumed only at metric timestamps at or before each completed feature hour.
- Funding from the same official archive/recent-source helper used in repaired MS1.
- No news labels, no post-event liquidation totals, no future OI.

## Frozen execution / label
Identical to MS1 for direct comparability:
- completed feature bar at `t`;
- entry next 1h open;
- 6h horizon;
- LONG TP +1.50%, SL -0.80%; SHORT mirrored;
- adverse-first if both touched in one 1h bar;
- TIME = non-win;
- 0.15% modeled round-trip fee for expectancy.

## New causal positioning features
At each `t`, latest metric snapshot at or before `t` is allowed. Changes use snapshots no later than `t-1h` / `t-4h`.

1. `oi_value_chg_1h` — percent change in sum open-interest value over ~1h.
2. `oi_value_chg_4h` — percent change over ~4h.
3. `global_ls` — global account long/short ratio.
4. `global_ls_chg_1h` — 1h change.
5. `top_pos_ls` — top-trader position long/short ratio.
6. `top_pos_ls_chg_1h` — 1h change.
7. `top_account_ls` — top-trader account long/short ratio.
8. `top_vs_global` — `top_pos_ls / global_ls - 1`.
9. `taker_ls_metric` — Binance metric taker long/short volume ratio when available.

Carry forward from MS1 only as context:
- `compression_6_24`;
- `breakout_pos_24`;
- `ret_4h`;
- kline `taker_imbalance_3h`;
- `rel_quote_volume_24`;
- `funding_z_30` / funding sign.

## Discovery / validation
- Chronological 70% discovery / 30% validation.
- All quantile thresholds estimated only on discovery and frozen.
- q30/q70 for most state features; q20/q80 for breakout position.

## Frozen LONG atoms
- `COMPRESSED`: compression <= q30.
- `OI_BUILD_1H`: OI value change 1h >= q70.
- `OI_BUILD_4H`: OI value change 4h >= q70.
- `GLOBAL_SHORT`: global LS <= q30.
- `TOP_SHORT`: top position LS <= q30.
- `TOP_MORE_SHORT`: top_vs_global <= q30.
- `GLOBAL_SHORTING`: global LS 1h change <= q30.
- `TOP_SHORTING`: top position LS 1h change <= q30.
- `AGG_BUY`: kline taker imbalance >= q70.
- `METRIC_BUY`: taker LS metric >= q70.
- `HIGH_BREAKOUT_POS`: breakout position >= q80.
- `HIGH_VOLUME`: relative quote volume >= q70.
- `LOW_FUNDING`: funding z <= q30.

## Frozen SHORT atoms
Exact directional mirror:
- `COMPRESSED`.
- `OI_BUILD_1H`.
- `OI_BUILD_4H`.
- `GLOBAL_LONG`: global LS >= q70.
- `TOP_LONG`: top position LS >= q70.
- `TOP_MORE_LONG`: top_vs_global >= q70.
- `GLOBAL_LONGING`: global LS 1h change >= q70.
- `TOP_LONGING`: top position LS 1h change >= q70.
- `AGG_SELL`: kline taker imbalance <= q30.
- `METRIC_SELL`: taker LS metric <= q30.
- `LOW_BREAKOUT_POS`: breakout position <= q20.
- `HIGH_VOLUME`.
- `HIGH_FUNDING`: funding z >= q70.

## Search space
For LONG and SHORT separately:
- evaluate all 3-atom and 4-atom conjunctions only;
- no hour/day/session split;
- no alternative TP/SL/hold;
- no threshold sweep;
- no excluding August or any losing block.

## 80-state gates
A state is an MS2 candidate only if all:
1. discovery N >= 40;
2. discovery WR >= 80%;
3. validation N >= 15;
4. validation WR >= 75%;
5. pooled WR >= 80%;
6. discovery and validation expectancy > 0 after modeled fee;
7. validation opportunities appear in >=3 chronological quartiles.

`MS2_VALIDATED_80` additionally requires validation WR >=80%.

If none passes: `NO_80_POSITIONING_STATE_MS2`.

## 19–20 Aug audit
After discovery candidate selection is frozen, print the pre-impulse positioning snapshot for the strongest 6h upside impulse beginning 19–20 Aug 2026 and report active atoms / whether any discovery-qualified state fired. This event cannot define a threshold.

## Anti-rescue lock
Do not after MS2:
- change q30/q70/q20/q80;
- add liquidation totals observed after the move;
- carve out a session/day;
- alter TP/SL/hold;
- add 5th+ atoms to force purity;
- isolate one trader-ratio cell post-hoc.

A future liquidation-orderbook family must be independently preregistered and must use genuinely causal pre-move data.
