# BTC H1 Failed / Inversion FVG Retest IFVG1 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test whether the frequent AMD4 stop-side excursion can be traded causally only after the original FVG has objectively failed, rather than mechanically reversing every AMD4 loss.

Frozen sequence:

`exact AMD/FVG -> completed H1 close through far FVG edge -> first retest of that far edge from the opposite side -> enter in direction of FVG failure -> target manipulation extreme`

This is materially different from AMD1-AMD4. It does not change target interpolation or stop distance inside the old reversal trade. The information state changes: an additional completed H1 acceptance close through the FVG is required before any trade can exist.

## Market / timeframe
- BTCUSDT USD-M perpetual.
- Decision / signal timeframe: **1H only**.
- No 1m / 5m / 15m signal logic.
- Historical source: official Binance Futures archive via the existing repository loader.

## Inherited frozen AMD/FVG construction
Use the exact AMD1 definitions without alteration:
- fixed session opens only: Asia 00:00 UTC / 07:00 WIB, London 07:00 UTC / 14:00 WIB, New York 13:00 UTC / 20:00 WIB;
- accumulation = exactly the 3 completed H1 candles immediately before session open;
- manipulation = first H1 session candle only, one-sided sweep with close back inside accumulation range;
- exact opposite 3-candle FVG = manipulation candle + immediately following 2 H1 candles;
- bearish FVG after HIGH sweep: middle candle bearish and `third_high < manipulation_low`, zone `[third_high, manipulation_low]`;
- bullish FVG after LOW sweep: middle candle bullish and `third_low > manipulation_high`, zone `[manipulation_high, third_low]`;
- no later-FVG search, no size/body/ATR/volume filters.

## 1. Objective FVG failure / inversion
Search only the first **6 completed H1 candles after FVG confirmation** (the same post-confirmation horizon used by AMD2/AMD4).

### Original bearish FVG -> inversion LONG candidate
- Near FVG edge = `fvg_low = third_high`.
- Far FVG edge = `fvg_high = manipulation_low`.
- The FVG is considered failed only when a completed H1 candle **closes strictly above the far edge**: `close > fvg_high`.
- A mere wick through the far edge is not failure.
- Because a close above the far edge necessarily traverses the zone, it also satisfies the required FVG mitigation/touch before acceptance failure.

### Original bullish FVG -> inversion SHORT candidate
- Near FVG edge = `fvg_high = third_low`.
- Far FVG edge = `fvg_low = manipulation_high`.
- The FVG is considered failed only when a completed H1 candle **closes strictly below the far edge**: `close < fvg_low`.
- A mere wick through the far edge is not failure.

If no qualifying completed close occurs within the frozen 6H failure-search horizon, event = `NO_FAILURE`.

## 2. Retest entry after confirmed failure
Retest search begins on the **next H1 candle after the failure-close candle**; the failure candle itself cannot be the entry.
Wait at most **6 completed H1 candles**.

### Inversion LONG
- Entry = failed bearish FVG far edge = `fvg_high`.
- Fill occurs when a later H1 low <= entry.
- This is a retest from above after the market has closed above the failed bearish FVG.

### Inversion SHORT
- Entry = failed bullish FVG far edge = `fvg_low`.
- Fill occurs when a later H1 high >= entry.
- This is a retest from below after the market has closed below the failed bullish FVG.

If no retest occurs within 6H, event = `NO_RETEST`.

## 3. Stop / invalidation
The stop is the opposite / near edge of the original FVG, not the manipulation extreme.
- Inversion LONG: SL = original bearish FVG near/lower edge = `fvg_low`.
- Inversion SHORT: SL = original bullish FVG near/upper edge = `fvg_high`.

The trade is structurally invalid if entry is not strictly between SL and TP in the correct direction.

## 4. Target
Target is the original manipulation liquidity extreme.
- Inversion LONG: TP = manipulation HIGH.
- Inversion SHORT: TP = manipulation LOW.

No alternative target, measured move, accumulation boundary, partial target, or trailing exit is tested in IFVG1.

## 5. Minimum economics
Modeled round-trip fee = **0.15%**.
A trade is eligible only when the frozen TP distance provides modeled **net reward >= net loss (minimum net RR 1:1)**.
Equivalent raw-distance condition:
- `target_distance >= stop_risk + 0.30%` of entry.

No trade is forced when geometry fails this requirement.

## 6. Execution / ambiguity
- Max hold = **6 completed H1 candles from retest fill candle**.
- On the fill candle, SL is adverse-first if reachable.
- TP is **not credited on the fill candle**, because the OHLC bar may have touched TP before the retest limit entry occurred.
- On later candles, if TP and SL are both reachable within the same H1 bar, SL is counted first.
- TIME exit uses the sixth H1 candle close in signed trade direction, less fee.

## Evidence partitions
- Historical robustness / external relative to this frozen rule: 2020-01-01 through 2021-12-31.
- Reference development: 2022-01-01 through 2025-03-17.
- Reference validation: 2025-03-18 through 2026-07-29.
- August diagnostic: 2026-08-01 through available completed archive data before 2026-08-20.
- No session / side / clock is selected from validation, external, or August.

## Required outputs
For every partition, and descriptive fixed side/session cells:
- exact AMD+FVG count;
- failure-close count and rate;
- failure -> retest fill count and rate;
- net-RR>=1:1 eligible trade count;
- TP / SL / TIME;
- decisive WR;
- PnL and expectancy at $500 reference notional;
- median stop risk and median modeled net RR;
- external chronological 4-block stability.

## Promotion gates
`IFVG1_SUPPORTED = PASS` only if the same frozen aggregate rule has:
- reference-validation eligible N >= 25, decisive WR >= 60%, PnL > 0;
- historical robustness eligible N >= 40, decisive WR >= 60%, PnL > 0;
- at least 3/4 chronological robustness blocks with N >= 8 and PnL > 0.

`IFVG1_80_CANDIDATE = PASS` only if:
- validation eligible N >= 20 and decisive WR >= 80%, PnL > 0;
- robustness eligible N >= 30 and decisive WR >= 80%, PnL > 0;
- at least 3/4 robustness blocks have N >= 5 and decisive WR >= 70%.

## Anti-rescue lock
After result, do NOT:
- enter immediately on the failure close instead of retest;
- change close-through to wick-through or add a close buffer;
- choose midpoint / partial / deep FVG retest entries;
- change the 6H failure or retest windows;
- move stop outside/inside the near edge;
- change TP away from manipulation extreme;
- isolate London/Asia/NY or LONG/SHORT because a small cell looks good;
- alter accumulation/FVG geometry or add filters.

Any such mechanism requires a new preregistered experiment and must be treated as hypothesis-generating after IFVG1.