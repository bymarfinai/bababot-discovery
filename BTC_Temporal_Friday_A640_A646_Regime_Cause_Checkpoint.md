# BTC Temporal Friday15 — A6.40 to A6.46 Regime Cause Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** CAUSE ANALYSIS COMPLETE — NO NEW TRADING RULE PROMOTED  
**Reference:** A6.33 Friday15 BUY provisional champion  
**Live BBC:** untouched

## Executive diagnosis

The A6.33 max drawdown is not primarily caused by EMA damage-control, funding, a simple trend regime, or a longer loss streak. It is a **structural payoff inversion** in Friday15 BUY behavior during roughly 2025-05-09 through 2026-01-30.

The immediate loss mechanism is:

1. broader 24h volatility is somewhat lower,
2. 30-120m before 15:00 WIB local participation/range expands sharply,
3. the move is seller-led,
4. open interest often falls (deleveraging/unwind rather than new short build),
5. top-trader position ratios are unusually long-skewed relative to both top-trader account counts and the global account ratio,
6. a setup that historically mean-reverted after 15:00 changes into downside continuation.

Crucially, several of these same pre-entry states were **profitable in discovery** and become strongly negative later. Therefore they are best interpreted as markers/mechanisms of a non-stationary regime, not stable filters that can be safely promoted from this sample.

## A6.40 — Broad pre-entry regime attribution

Strictly pre-entry features: 6h/24h/7d return, Friday morning return, 24h realized volatility/range, completed-1H EMA20/EMA50 structure/slopes.

Most distinct macro feature was RV24:
- PRE_DD median ~2.4315%
- DD median ~2.0315%
- POST median ~2.2952%
- standardized DD-vs-PRE effect ~-0.624

EMA/trend features were much smaller and/or did not reverse post-DD. Thus 1H EMA structure is not a convincing root cause.

## A6.41 — Causal rolling volatility regime

Classified each Friday using only prior 26 Fridays.

Below trailing-median RV24 was weaker overall:
- low-vol: N62, WR56.45%, PnL +$16.370, avg +$0.264/Friday
- other: N50, WR66.00%, PnL +$99.897, avg +$1.998/Friday

But low-vol frequency did not uniquely identify the bad regime:
- PRE ~52.08%
- DD ~56.41%
- POST ~60.00%

Therefore **low volatility is a broad headwind, not the DD cause**.

## A6.42 — Pre-entry microstructure attribution

The bad regime is much more distinct in the 30-120m immediately before entry.

60m relative activity:
- volume/24h-median PRE mean ~1.408 vs DD ~2.020 vs POST ~1.426
- range/24h-median PRE ~0.964 vs DD ~1.165 vs POST ~0.952

Candle bodies are also larger in DD, while pre-entry 60-120m flow remains seller-biased. The key change is not merely seller flow frequency; the **payoff after that state changes**.

## A6.43 — Natural composite stress state

No optimized thresholds:
- expansion = 60m volume ratio >1 AND 60m range ratio >1
- seller-led = taker imbalance <0 AND 60m return <0
- stress_core = expansion + seller-led

`stress_core` results:
- discovery after warmup: N13, WR69.23%, +$29.820, avg +$2.294, PF5.015
- validation: N12, WR25.00%, -$36.668, avg -$3.056, PF0.127

Occurrence rate:
- PRE 22.92%
- DD 33.33%
- POST 4.00%

This is strong evidence of **payoff inversion**, not a timeless bad-state filter.

## A6.44 — Binance funding attribution

Official Binance Data Vision USD-M BTCUSDT funding history was aligned to every Friday.

Causal latest funding strictly before entry:
- PRE mean +0.008758%
- DD +0.004277%
- POST +0.002157%

Trailing prior-24h average:
- PRE +0.009967%
- DD +0.005249%
- POST +0.001297%

Funding became even lower post-DD while Friday15 performance recovered. Positive vs non-positive prior funding produced almost identical full-sample WR (~60.87%) and similar expectancy.

**Funding level is rejected as the root cause.** Exact 08:00 UTC funding was kept descriptive only and was not used as a causal predictor.

## A6.45 — Futures positioning attribution

Official Binance Data Vision daily metrics, 138/138 Friday coverage, latest snapshot ~5m before entry.

The strongest distinct positioning feature is top-trader **position** long/short ratio:
- PRE mean 1.5036
- DD mean 1.8252
- POST mean 1.1223
- standardized DD-vs-PRE effect ~+0.953
- DD-vs-POST ~+2.315

By contrast global account L/S ratio is nearly unchanged PRE→DD:
- PRE 1.4560
- DD 1.4592
- POST 1.5180

Thus the weak regime is characterized by **large top-trader position-size long skew**, not a broad market-wide long-account skew.

The initial hypothesis that seller pressure plus rising OI represented new short build was rejected. During DD:
- seller-led + OI-value DOWN: N17, WR41.18%, PnL -$30.396
- seller-led + OI-value UP: N5, WR60.00%, PnL +$2.712

So the damaging state is more consistent with **deleveraging / long unwind** than fresh short accumulation.

## A6.46 — Crowding + unwind attribution

Natural divergence measures:

Top-position vs global-account divergence:
- PRE mean +18.44%
- DD +55.34%
- POST -18.86%

Top-position vs top-account divergence:
- PRE +9.34%
- DD +32.86%
- POST -23.26%

This makes top-trader long crowding a very strong **regime marker**.

However it is NOT a stable standalone bad-state signal. In PRE_DD, `crowded_both` was extremely profitable:
- N40, WR82.5%, +$107.598

During DD:
- N27, WR48.15%, -$10.530

POST:
- N5, WR100%, +$23.274

The most direct mechanism remains `stress_unwind` = seller-led local expansion + OI-value non-increasing:
- discovery: N15, WR80.0%, +$38.576, avg +$2.572
- validation: N10, WR20.0%, -$36.477, avg -$3.648

Adding crowding does not turn this into a stable detector; the same state was excellent earlier and poor later.

## Scientific verdict

1. **A6.33 management did not create the main DD.** Earlier A6.39 showed parent-only DD would be worse.
2. **EMA/trend state is not the root cause.**
3. **Low 24h volatility contributes but does not identify the bad regime.**
4. **Funding does not explain the regime change.**
5. **The bad period has a distinctive derivatives/microstructure signature:** top-trader positions heavily long-skewed, local seller-led participation expansion, and frequent OI unwind before entry.
6. The actual edge failure is a **response-function inversion**: pre-entry seller-led unwind used to exhaust and mean-revert after 15:00; later it began continuing lower.
7. Because the same state is profitable in the earlier discovery period, using it now as a hard entry filter would be retrospective regime fitting.
8. The legitimate production response is not to claim a perfect pre-entry predictor from this sample. It is to keep A6.33 provisional, monitor the payoff of these causal state variables forward/OOS, and only promote a regime switch after new data demonstrates stable conditional behavior.

## Current strategy status

A6.33 remains unchanged:
- N138
- WR60.87%
- PnL +$141.025
- PF1.720
- max DD $46.318
- LS4

No live code changed. No entry occurrence removed. No A6.40-A6.46 diagnostic state promoted as a trading rule.
