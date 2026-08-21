# BTC Weekly Liquidity Sweep + Order-Flow Resolution B18 — Preregistration

**Revision:** B18_V1  
**Status:** FROZEN BEFORE RESULT

## Research question
Can a causal liquidity sweep at a predefined objective pool, resolved with contemporaneous Binance Futures taker flow, identify high-precision BTCUSDT weekly entries better than structure alone?

This is a new experiment family. It must not rescue or retune B11/B13/B15/B16/B17 after seeing OOS results.

## Data / execution
- Instrument: BTCUSDT Binance USD-M Futures.
- Structural execution timeframe: H1.
- Order-flow source: underlying 15m futures klines aggregated causally.
- Signal must be complete before entry.
- Entry: next H1 open after completed signal H1.
- Weekly scan: Monday 00:00 UTC through Saturday 12:00 UTC.
- Maximum one routed trade per week; no forced fallback.
- Outcome: same frozen weekly economics used by B13-B17: +1.15% favorable price / -0.85% adverse price, 0.15% round-trip fee => net +1.00% TP / -1.00% SL; same-bar adverse-first; exit no later than week end.
- Live BBC must remain untouched.

## Frozen partitions
- External untouched: 2020-01-01 through 2021-12-31 complete ISO weeks (103).
- Development: 2022-01-01 through 2024-12-31 complete ISO weeks (156).
- Reference validation: 2025-01-01 through 2026-07-29 complete ISO weeks (81).
- August 2026: diagnostic only.

## Objective liquidity pools
Only these three families are allowed in B18_V1:
1. Previous UTC day high / low (`PDH`, `PDL`).
2. Previous complete ISO week high / low (`PWH`, `PWL`).
3. Previous complete W1 volume-profile value-area high / low (`W1_VAH`, `W1_VAL`) using the same causal 24-bin/70% value-area construction as B13-B17.

Equal highs/lows, session highs/lows, swing clustering, tolerance sweeps, and manually selected levels are excluded from B18_V1.

## Literal H1 sweep event
The level must be known before the signal H1 begins.

For an upper liquidity pool (`PDH`, `PWH`, `W1_VAH`):
- Signal H1 opens at/below the level.
- Signal H1 high trades strictly above the level.
- `REV_SHORT`: H1 closes back below the level => buy-side sweep/reclaim, SHORT direction.
- `CONT_LONG`: H1 closes above the level => accepted breakout, LONG direction.

For a lower liquidity pool (`PDL`, `PWL`, `W1_VAL`):
- Signal H1 opens at/above the level.
- Signal H1 low trades strictly below the level.
- `REV_LONG`: H1 closes back above the level => sell-side sweep/reclaim, LONG direction.
- `CONT_SHORT`: H1 closes below the level => accepted breakout, SHORT direction.

First qualifying event per active level instance + archetype only. No rescue by later touches of the same instance.

## Frozen 15m order-flow measurements
For every completed signal H1:
- `hour_flow`: taker imbalance over the signal H1, `2*taker_buy_quote/quote_volume - 1`.
- `flow3h`: same imbalance over the 3h window ending at entry.
- `flow6h`: same over 6h ending at entry.
- `breach_flow`: taker imbalance of the first 15m bar that actually breaches the liquidity level.
- `final15_flow`: taker imbalance of the last completed 15m bar of the signal H1.

All values are transformed into signed values:
- trade-side signed flow = + when aggression points in proposed trade direction.
- sweep-side signed breach flow = + when aggression points into the swept liquidity.

No order-book snapshots, reconstructed bid/ask delta, or unavailable historical L2 data are inferred.

## Frozen flow variants
Every structural archetype is evaluated with exactly these variants:
1. `RAW`: no flow filter.
2. `H1_FLOW`: trade-side signed `hour_flow > 0`.
3. `FLOW3`: trade-side signed `flow3h > 0`.
4. `PERSIST`: trade-side signed `hour_flow > 0` AND `flow3h > 0` AND `flow6h > 0`.
5. `MICRO`: sweep-side signed `breach_flow > 0` AND trade-side signed `final15_flow > 0` AND trade-side signed `hour_flow > 0`.
6. `MICRO_PERSIST`: `MICRO` plus trade-side signed `flow3h > 0`.

No numeric imbalance threshold other than zero is allowed in B18_V1. No z-score/percentile threshold search is allowed after OOS inspection.

## Development selection
Atomic rule = `POOL|ARCHETYPE|FLOW_VARIANT`.

Rules with development N < 20 are not eligible as PRIMARY. Among eligible rules, PRIMARY is selected by:
1. highest Wilson lower bound,
2. then WR,
3. then PF,
4. then N,
5. deterministic rule name.

A TOP4 router is also frozen from development by taking the best rule from four distinct `(pool family, archetype)` buckets when available. Each week the earliest qualifying candidate among TOP4 wins; rule rank breaks exact-time ties.

## Gates
### B18_HIGH_PRECISION
PASS only if the frozen PRIMARY or TOP4 router has, in both external and reference validation:
- N >= 20,
- WR >= 70%,
- positive expectancy,
- PF > 1.5,
- max losing streak <= 2,
- at least 3/4 chronological blocks positive when block sample exists.

### B18_ROBUST_WEEKLY_100
A separate aspirational diagnostic requiring 100% weekly coverage and zero losses in both external and reference validation. It is expected to be difficult; failure does not authorize fallback or retuning.

## Interpretation discipline
- Historical 100% is not a future guarantee.
- A winning filter that fails external or validation is rejected as overfit.
- A flow variant is only meaningful if it improves OOS precision versus its own RAW structural archetype without collapsing to a trivial sample.
- No post-result changes to pool definitions, scan cutoff, flow windows, threshold, entry timing, TP/SL, or tie-breaking are allowed.
