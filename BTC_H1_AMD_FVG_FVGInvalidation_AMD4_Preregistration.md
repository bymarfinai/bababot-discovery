# BTC H1 AMD + FVG Invalidation Stop AMD4 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test whether the recurring `FVG mitigation -> opposite accumulation boundary` rotation observed descriptively in AMD3 can become executable at minimum net RR 1:1 when risk is defined by **FVG invalidation** rather than the full manipulation extreme.

This is materially different from AMD1-AMD3. The target is NOT retuned after AMD3: it returns to the original opposite accumulation boundary. The only changed causal mechanism is stop placement.

## Market / timeframe
- BTCUSDT USD-M perpetual.
- Decision and execution timeframe: completed **1H only**.
- No 1m / 5m / 15m signal logic.

## Frozen upstream AMD/FVG geometry
Identical to AMD2/AMD3:
- fixed session opens: Asia 00:00 UTC / 07:00 WIB, London 07:00 UTC / 14:00 WIB, New York 13:00 UTC / 20:00 WIB;
- accumulation = exactly three completed H1 candles immediately before session open;
- manipulation = first session H1 candle only, one-side sweep and close back inside accumulation range;
- exact opposite FVG = manipulation candle + next two H1 candles;
- bearish FVG: middle candle bearish and `high(third) < low(manipulation)`;
- bullish FVG: middle candle bullish and `low(third) > high(manipulation)`;
- wait maximum 6 completed H1 candles after FVG confirmation for first touch of the near FVG boundary;
- SHORT entry = bearish FVG near/lower edge = `high(third)`;
- LONG entry = bullish FVG near/upper edge = `low(third)`;
- no midpoint, partial-FVG, later-FVG, body-size, ATR, volume or session-side filter.

## New frozen risk definition — PRIMARY CHANGE
Use full FVG invalidation as the structural stop:
- SHORT: `SL = FVG far/upper edge = low(manipulation candle)`.
- LONG: `SL = FVG far/lower edge = high(manipulation candle)`.

No stop buffer, ATR padding, tick padding or manipulation-extreme fallback.

## Frozen target
Return to the original Distribution rotation boundary:
- SHORT TP = `acc_low`.
- LONG TP = `acc_high`.

A trade is executable only when the target lies in the intended direction and modeled target distance satisfies minimum **net RR >= 1:1 after 0.15% round-trip fee**:
- raw target distance >= raw stop risk + 0.30% of entry.

Events failing this geometry are `RR_INELIGIBLE`; target and stop are not altered to force a trade.

## Timing / ambiguity
- mitigation search max 6H after exact FVG confirmation;
- maximum hold 6 completed H1 candles from mitigation fill candle;
- fill candle: if stop is also touched, count SL adverse-first;
- fill-candle TP is never credited because OHLC cannot prove TP happened after the limit fill;
- from the next H1 candle onward, if TP and SL coexist in one candle, SL adverse-first;
- TIME exits at sixth H1 close, signed direction, less fee.

## Evidence partitions
Same historical partitions already frozen for AMD2/AMD3:
- external historical robustness: 2020-01-01 through 2021-12-31;
- development: 2022-01-01 through 2025-03-17;
- reference validation: 2025-03-18 through 2026-07-29;
- August diagnostic: 2026-08-01 through available completed archive before 2026-08-20.

These are not pristine concept-level OOS anymore because the AMD family has been repeatedly observed. They are OOS only relative to the newly frozen stop mechanism.

## Required outputs
For aggregate and each fixed side/session:
- exact FVG count;
- mitigation fill count/rate;
- FVG-stop structurally valid count;
- RR-eligible count/rate;
- TP/SL/TIME;
- decisive WR;
- PnL and expectancy at $500 reference notional;
- median raw risk and median modeled net RR;
- external chronological blocks.

Also report the corresponding AMD2 manipulation-extreme-stop RR-eligible counts as a non-selective geometry control, without changing either mechanism.

## Promotion gates
`AMD4_FVG_STOP_SUPPORTED = PASS` only if the same frozen aggregate mechanism has:
- validation RR-eligible N >= 25, decisive WR >= 60%, PnL > 0;
- external RR-eligible N >= 40, decisive WR >= 60%, PnL > 0;
- at least 3/4 external chronological blocks with N >= 8 and PnL > 0.

`AMD4_80_CANDIDATE = PASS` only if:
- validation RR-eligible N >= 20 and decisive WR >= 80%;
- external RR-eligible N >= 30 and decisive WR >= 80%;
- at least 3/4 external blocks N >= 5 and WR >= 70%;
- positive validation and external PnL.

## Anti-rescue lock
After seeing AMD4 results, do NOT:
- add a stop buffer beyond the FVG edge;
- use FVG midpoint / 25% / 75% entries;
- change the opposite accumulation boundary target;
- tune accumulation length;
- allow later manipulation or later FVG search;
- extend the mitigation or holding window;
- isolate London SHORT or any side/session because it looks good;
- add ATR/std-dev/volume/OI/taker filters on this same evidence.

Any such mechanism requires a genuinely new preregistered experiment.