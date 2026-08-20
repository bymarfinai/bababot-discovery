# BTC H1 AMD + FVG Distribution Expansion AMD3 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test the materially different Distribution target implied by AMD2. AMD2 showed that FVG mitigation entries are common, but using the opposite accumulation boundary as TP almost never provides net RR >= 1:1. AMD3 keeps the AMD2 entry mechanism unchanged and tests whether Distribution is better represented by a full measured expansion beyond the accumulation range.

## Market / timeframe
- BTCUSDT USD-M perpetual
- Completed **1H only** for signal, entry and management
- No 1m / 5m / 15m signal logic
- Official Binance historical 1H data through available 2026-08-18 archive

## Frozen AMD/FVG sequence — unchanged from AMD2
- Session opens: Asia 00:00 UTC / 07:00 WIB; London 07:00 UTC / 14:00 WIB; New York 13:00 UTC / 20:00 WIB.
- Accumulation = exactly three completed H1 candles immediately before session open.
- Manipulation = first H1 session candle only; one-side sweep beyond accumulation extreme and close back inside the accumulation range.
- Exact opposite FVG = manipulation candle + immediately following two completed H1 candles, same frozen AMD1 geometry.
- After FVG confirmation, wait max 6 completed H1 candles for first touch of the near FVG boundary.
- SHORT entry = bearish FVG near/lower boundary; LONG entry = bullish FVG near/upper boundary.
- Structural SL = manipulation extreme.
- Conservative fill-candle ordering retained: fill-candle SL counts adverse-first; fill-candle TP is not credited.
- Max hold = 6 completed H1 candles from mitigation fill candle.

## NEW frozen Distribution target
Let `RANGE = acc_high - acc_low`.

- SHORT measured Distribution TP = `acc_low - RANGE`.
- LONG measured Distribution TP = `acc_high + RANGE`.

This is a single **1.0x accumulation-range extension**. There is no 0.25x / 0.5x / 1.5x / 2.0x grid and no post-result target selection.

## RR eligibility
A filled structurally valid setup is an AMD3 primary trade only when its measured Distribution target provides modeled **net reward >= net loss after 0.15% round-trip fee**.

Using raw fractions from entry:
- structural risk = distance(entry, SL) / entry;
- target distance = distance(entry, measured Distribution TP) / entry;
- eligible iff `target_distance >= structural_risk + 0.0030`.

Ineligible events remain diagnostics only; target is not shortened to force a trade.

## Secondary diagnostics — not selectors
For context only, report:
- FVG mitigation fill rate;
- RR-eligibility rate;
- whether the opposite accumulation boundary is reached after entry before structural SL;
- fixed synthetic net-1R execution using the same entry/SL, strictly as a comparison to AMD2.

No diagnostic may replace the frozen measured Distribution TP.

## Evidence partitions
- External untouched relative to this target hypothesis: 2020-01-01 through 2021-12-31.
- Reference development: 2022-01-01 through 2025-03-17.
- Reference validation: 2025-03-18 through 2026-07-29.
- August post-cutoff: 2026-08-01 through available archive data before 2026-08-20.

The 1.0x expansion target was frozen before reading any AMD3 outcome. No side/session is selected from validation, external or August.

## Required outputs
For each partition and fixed side/session:
- exact FVG count;
- mitigation fills and fill rate;
- measured-expansion RR-eligible count;
- TP / SL / TIME;
- decisive WR;
- PnL and expectancy at $500 reference notional;
- median structural risk;
- median modeled net RR;
- external chronological four-block stability;
- opposite-boundary reach diagnostic;
- fixed net1R diagnostic.

## Promotion gates
`AMD3_EXPANSION_SUPPORTED = PASS` only if aggregate frozen mechanism has:
- reference-validation eligible N >= 25, decisive WR >= 60%, PnL > 0;
- external eligible N >= 40, decisive WR >= 60%, PnL > 0;
- at least 3/4 external chronological blocks with N >= 8 and PnL > 0.

`AMD3_80_CANDIDATE = PASS` only if:
- validation eligible N >= 20 and decisive WR >= 80%;
- external eligible N >= 30 and decisive WR >= 80%;
- at least 3/4 external blocks N >= 5 and decisive WR >= 70%;
- positive validation and external PnL.

## Anti-rescue lock
After result, do NOT:
- retune the 1.0x expansion to another multiple;
- alter accumulation length;
- allow later manipulation candles or later FVGs;
- change the FVG entry boundary or choose midpoint/partial mitigation;
- change mitigation or hold windows;
- isolate London SHORT / NY LONG / any side-session post-hoc;
- add EMA, ATR, std-dev, volume, OI, taker or weekday filters.

Any such mechanism requires a new preregistered experiment and independent evidence.