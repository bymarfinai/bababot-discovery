# ETH Native London->New York Retest-to-Breakout Discovery — Z2 Preregistration

## Purpose
Discover, without importing BTC entry levels, **how deep ETH typically retests after the first High-pressure visit before a later strict upside breakout** inside the ETH-native clock selected by Z1.

This milestone answers only:

> After a causal High K1 OPP0 touch episode and leave, which frozen reference-range retrace level is most robustly followed by a later strict 5m close above H?

This is a structural retest-to-breakout diagnostic. It is **not** an entry rule, TP/SL test, PnL backtest, or live promotion.

## Frozen upstream clock
Canonical Z1 result:
- status: `ETH_NATIVE_LONDON_NY_CLOCK_Z1_SUPPORTED`
- reference start: **18:30 WIB / 11:30 UTC**
- reference duration: **5h30** = 66 raw 5m bars
- execution start: **00:00 WIB / 17:00 UTC**
- execution duration: **6h30** = 78 raw 5m bars
- LONG High-pressure side only

The clock is frozen. Z2 does not rescan clocks.

## Data and partitions
- ETHUSDT Binance Futures raw 5m only.
- Same historical coverage and partition definitions as `research/eth_london_ny_liquidity_pressure_m1.py`.
- Major partitions remain `external`, `development`, and `reference_validation`.
- Execution start must be weekday, matching Z1.
- Require exactly 66 reference bars and 78 execution bars.
- Require raw 5m coverage >= 99.5%.

## Frozen reference range
For each complete session:
- `H = max(high)` over the completed 5h30 reference window.
- `L = min(low)` over the completed 5h30 reference window.
- require `H > L`.
- range fraction is measured from `L=0` to `H=1`.

## K1 OPP0 pressure identity
Reuse B27Q-style High pressure semantics:
1. Strict close-breaks are evaluated before touch counting.
2. High touch: `high >= H` and `close <= H`.
3. Low touch: `low <= L` and `close >= L`.
4. The signal is the **first distinct High visit** while zero Low visits are known: High K1 / OPP0.
5. If Low is visited first, a later High visit is not OPP0.
6. A strict `close > H` or `close < L` before K1 means no eligible setup.
7. A bar touching both H and L before a signal is ambiguous and cannot create K1.

## Contiguous K1 touch episode and causal leave
The K1 bar starts the first High-touch episode.

A bar remains in that same episode while `high >= H` and `close <= H`, with no strict terminal break.

The causal leave is the **first completed subsequent 5m bar that is no longer a High touch**, provided that bar itself is not a strict upside/downside break.

No retest may be credited on the leave bar. Retest eligibility begins on the **immediately following raw 5m bar**.

If strict `close > H` or `close < L` occurs before a causal leave is established, the setup has no post-leave retest window.

## Retest grid — full ETH range discovery
Freeze the complete 5%-step grid:

`F95, F90, F85, F80, F75, F70, F65, F60, F55, F50, F45, F40, F35, F30, F25, F20, F15, F10, F05`

For fraction `f`, level price is:

`L + f * (H - L)`

For LONG, a level is retested when an eligible non-terminal bar has `low <= level_price`.

Because levels are nested, one bar may establish several shallower/deeper retest states. Each exact level is evaluated independently.

## Causal retest -> breakout chronology
For each raw 5m bar after the causal leave:
1. evaluate strict terminal closes first;
2. if `close > H`, classify `TARGET_BREAK` and stop the session;
3. if `close < L`, classify `OPPOSITE_BREAK` and stop the session;
4. only if the bar is non-terminal may it establish previously unseen retest levels;
5. a retest becomes known only at that bar's close;
6. therefore a breakout/opposite terminal bar can never establish a same-bar retest.

This guarantees the target is genuinely **after** a completed retest.

If neither strict break occurs by execution end, classify `NO_BREAK`.

## Per-level outcome
For each exact fraction and partition report:
- complete sessions;
- K1 OPP0 setups;
- setups with a causal leave;
- retest count after leave;
- retest rate among causal-leave setups;
- later strict target break count (`close > H`);
- later strict opposite break count (`close < L`);
- no-break count;
- target-break rate among retests;
- resolved same-side rate = target / (target + opposite);
- Wilson 95% lower bound for target-break rate;
- median minutes retest -> target for winners;
- median retest elapsed minutes from execution start.

Persist one row per setup-level with K1, leave, retest, terminal timestamps for chronology audit.

## Development-only candidate selection
The native retest level is selected **only from development (2022-2024)**. External and reference-validation are not visible to ranking.

A development level is eligible only when:
- >= 50 causal retests;
- target-break rate >= 70%;
- resolved same-side rate >= 85%.

Local-stability gate: both adjacent 5%-step levels (when they exist) must each have:
- >= 40 causal retests;
- target-break rate >= 65%;
- resolved same-side rate >= 80%.

Among eligible + locally stable levels, rank by:
1. highest Wilson 95% lower bound target rate;
2. highest raw target-break rate;
3. highest resolved same-side rate;
4. larger retest count;
5. shallower fraction as deterministic final tie-break only.

The local-stability rule is fixed before observation to avoid choosing a single isolated spike.

## Historical replication gate
After development chooses one exact level, reveal external and reference-validation.

The selected exact level replicates only if **each** partition has:
- >= 30 causal retests;
- target-break rate >= 65%;
- resolved same-side rate >= 80%;
- target breaks > opposite breaks.

No pooled rescue is allowed.

## Mandatory assertions
1. Z1 clock is exactly 11:30 UTC reference start and 17:00 UTC execution start.
2. K1 OPP0 semantics are strict-break-first and first-distinct-High-visit based.
3. Consecutive High-touch bars remain one K1 episode.
4. Leave must be a completed non-High-touch, non-terminal bar.
5. First retest-eligible bar is exactly the raw 5m bar immediately after leave.
6. Leave bar cannot establish retest.
7. Strict terminal is evaluated before retest on every eligible bar.
8. Breakout bar cannot create a same-bar retest.
9. Opposite-break bar cannot create a same-bar retest.
10. Every target breakout timestamp is strictly later than its credited retest timestamp.
11. Every retest level equals the frozen reference fraction exactly.
12. All 19 grid levels are run; no post-result grid edits.
13. Selection uses development only; replication partitions are read only afterward.
14. Synthetic LONG paths covering consecutive K1 touches, leave, next-bar retest, breakout-after-retest, same-bar breakout/retest rejection, leave-bar retest rejection, opposite-after-retest, and no-break must pass before persistence.

## Prohibited in Z2
- entry execution or limit-fill promotion;
- reclaim/confirmation filters;
- TP/SL, trailing, break-even, runner;
- fees, leverage, PnL, PF, expectancy;
- changing the Z1 clock;
- adding/removing grid levels after observing output;
- using external/reference-validation to choose the level.

Stop after Z2. The selected retest zone, if replicated, is structural evidence only.
