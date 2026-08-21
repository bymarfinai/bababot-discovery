# BTC Weekly Auction-Quality Breakout / Sweep B19 — Preregistration

## Purpose
Test whether the weak precision of B18 is primarily caused by an overly literal event definition rather than by weak order-flow information.

B19 changes the structural event detector only. Economics, causal execution, partitions, and the previously observed order-flow persistence concept remain frozen.

Live BBC must remain untouched.

## Data / partitions
Reuse the causal Binance BTCUSDT futures 15m feed and H1 execution conventions used by B13–B18.

Frozen research partitions:
- external: complete ISO weeks in 2020-01-01 <= week < 2022-01-01
- development: complete ISO weeks in 2022-01-01 <= week < 2025-01-01
- reference_validation: complete ISO weeks in 2025-01-01 <= week < 2026-07-30
- August 2026: diagnostic only

Weekly scan window: Monday 00:00 UTC through Saturday 12:00 UTC.
Maximum one selected trade per week per rule. No forced fallback.

## Execution / economics
- Signal information must be completed before entry.
- Entry = next H1 open after the final required confirmation candle.
- LONG favorable underlying move = +1.15%; adverse = -0.85%.
- SHORT symmetric.
- Round-trip fee = 0.15%, therefore net target approximately +1% / -1%.
- Same-H1 ambiguity = adverse-first.
- Position resolves only within the same ISO week.

## Family A — W1 VAH auction-quality continuation
Use the same causal prior-completed-week W1 value profile construction as B15–B18.

Base breakout bar `b` requires:
1. active prior-week VAL/VAH are known before `b`;
2. `open[b] <= VAH` and `close[b] > VAH`;
3. inside-value approach: among H1 bars b-3..b-1, all three closes are <= VAH and at least two closes are >= VAL;
4. breakout candle ATR14 is finite.

Frozen quality variants:
- `AQ10_NIR1`: breakout close displacement >= 0.10 ATR above VAH; next completed H1 close remains > VAH.
- `AQ25_NIR1`: displacement >= 0.25 ATR; next completed H1 close remains > VAH.
- `AQ10_NIR2`: displacement >= 0.10 ATR; next two completed H1 closes both remain > VAH.

No retest is required. This explicitly tests acceptance/no-immediate-rejection, distinct from B16 retest logic.

For each structural variant, also test a frozen `+PERSIST` version requiring directional futures taker imbalance > 0 over each of the completed 1h, 3h, and 6h windows ending immediately before entry. No magnitude threshold is allowed.

Thus the W1 VAH rule universe is exactly six rules.

## Family B — qualified liquidity sweep / failed auction
Frozen liquidity pools:
- previous day high / low (`PDH`, `PDL`)
- previous week high / low (`PWH`, `PWL`)

The source level must be fully known before the event. Only the first H1 touch/sweep of each active level instance is eligible; once touched, that instance cannot generate a later rescue event.

Upper-pool SHORT sweep bar `s`:
- open <= level;
- high > level;
- penetration `(high-level)/ATR14` is in [0.10, 0.50];
- close < level (reclaim).

Lower-pool LONG is mirrored:
- open >= level;
- low < level;
- penetration `(level-low)/ATR14` in [0.10, 0.50];
- close > level.

Failed-auction confirmation:
- the immediately following completed H1 candle must also close on the reclaimed side of the same level;
- level instance must still be active;
- entry is the next H1 open after this confirmation.

Frozen variants:
- `FAILED_AUCTION_RAW`: structural definition only.
- `FAILED_AUCTION_FLOW`: additionally require sweep-bar taker imbalance in the sweep direction > 0 AND confirmation-bar taker imbalance in the trade/reversal direction > 0.

No 15m micro-sequence rule is permitted in B19 because B18 MICRO/MICRO_PERSIST failed OOS.

## Development selection
Development may rank the frozen rules by:
1. N >= 20 eligibility,
2. Wilson lower bound,
3. WR,
4. PF,
5. N,
6. lexical tie-break.

Freeze PRIMARY from development only.
Also report every frozen atomic rule OOS so the structural effect is visible even if PRIMARY fails.

## Success gates
Primary high-quality gate requires, in BOTH external and reference validation:
- N >= 15,
- WR >= 65%,
- positive expectancy,
- PF >= 1.30,
- no OOS retuning.

Aspirational robust-100 diagnostic additionally requires WR=100% in both OOS partitions; it is not assumed attainable.

For W1 VAH specifically, compare each quality rule against the known B15/B18 RAW W1 VAH baseline. Improvement must not be inferred from development alone.

## Prohibited rescue
After results are visible, do not alter:
- 0.10 / 0.25 ATR displacement thresholds,
- NIR1 / NIR2 definition,
- three-bar inside-value approach,
- 0.10–0.50 ATR sweep penetration band,
- first-touch rule,
- H1/3h/6h persistence sign condition,
- level families,
- TP/SL/fee,
- scan cutoff,
- partitions.

No equal-high/low addition, regime filter, ML classifier, threshold sweep, or live BBC modification is authorized by B19.
