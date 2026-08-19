# BTC AOH1 — Asia Open HIGH Sweep / Failed-Acceptance Confirmation Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Why this test exists
The preregistered three-session study found the strongest fixed cell at `ASIA_OPEN + HIGH->SHORT`:
- N68;
- 43 TP / 25 SL;
- gross structural 1R decisive WR 63.24%;
- last30% WR 66.67%.

That cell was discovered using 2023-12-02 through 2026-07-30, so the present confirmation rule must not be accepted from that same period alone.

## Frozen market / time
- BTCUSDT USD-M perpetual;
- official Binance Futures 5m klines, aggregated causally to completed 15m candles;
- Asia Open anchor = **00:00 UTC / 07:00 WIB**;
- frozen liquidity level = **previous completed UTC calendar-day HIGH**;
- event search window = first **90 minutes** after Asia Open;
- one first qualifying setup maximum per UTC date.

## Frozen AOH1 sequence
A valid SHORT setup requires all of the following, in order:

### 1. Sweep + reclaim candle
Within 00:00-01:30 UTC, a completed 15m candle:
- trades strictly **above previous-day HIGH**;
- closes strictly **below previous-day HIGH**.

This is the reclaim candle. Its actual HIGH becomes the structural stop level.

### 2. Failed-acceptance confirmation candle
The **immediately following completed 15m candle** must:
- be bearish: `close < open`;
- close strictly **below the LOW of the reclaim candle**.

No later confirmation candle may substitute. If the immediate next 15m candle fails, that day's candidate is WAIT.

### 3. Executable entry
- SHORT at the **next 15m open after the confirmation candle fully closes**;
- if entry is at or above the structural stop, skip as invalid;
- no same-candle or historical-price entry.

## Structural stop and NET minimum 1:1 RR
- `SL = reclaim candle HIGH`;
- gross structural risk fraction `r = (SL-entry)/entry`.

Modeled round-trip fee is frozen at `f = 0.15% = 0.0015` of notional.

A gross 1R target is not sufficient because fees make net reward smaller than net loss. Therefore AOH1 freezes the target so that **net reward equals net loss magnitude**:

- net loss at SL = `r + f`;
- require net win = `raw_reward - f = r + f`;
- therefore `raw_reward = r + 2f`;
- SHORT TP = `entry * (1 - (r + 0.0030))`.

Thus every decisive TP/SL has modeled **net RR >=1:1** after the frozen 0.15% round-trip cost.

No RR sweep is permitted after result.

## Exit mechanics
- evaluate only 5m bars after executable entry;
- if TP and SL touch in the same 5m candle, count SL/adverse first;
- max hold 6h;
- if neither is touched, exit at 6h close and report TIME separately;
- reference notional $500.

## Evidence partitions
### Reference / design sample
`2023-12-02 <= timestamp < 2026-07-30`.
This period is **not independent acceptance evidence**, because `ASIA_OPEN HIGH` was selected from it.

### External earlier validation
`2022-01-01 <= timestamp < 2023-12-02`.
This interval predates and was not used by the three-session study. It is the primary external historical validation.

### August true post-cutoff
`2026-08-01 <= timestamp < 2026-08-20`, limited to completed official archives available at run time.

## Required reporting
For each partition report:
- eligible reclaim candidates;
- confirmed AOH1 trades;
- confirmation rate;
- TP / SL / TIME;
- decisive WR;
- all-trade net-positive rate;
- total PnL at $500 notional;
- average/median structural risk;
- average raw target distance;
- 60m / 120m / 240m signed return diagnostics;
- every August event.

For the external 2022-2023 trades also report four chronological blocks.

## Promotion rules
`AOH1_EXTERNAL_SUPPORT` requires external 2022-2023:
- confirmed trades N >=20;
- decisive WR >=65%;
- positive total PnL after fee;
- at least 3/4 chronological blocks positive.

`AOH1_80_CANDIDATE` requires external 2022-2023:
- confirmed decisive N >=20;
- decisive WR >=80%;
- total PnL >0;
- at least 3/4 chronological blocks each with WR>50%;
- zero causality/integrity violations.

Reference-sample 80% alone cannot promote the rule.

## Guardrails
- no 1m data;
- no Asia-open time shift;
- no 90m window change;
- no alternate previous-day level;
- no confirmation substitution or extra confirmation candle;
- no body/wick/EMA/taker/OI/funding filter;
- no direction flip;
- no fee change;
- no RR/TP/SL/hold sweep;
- no selecting weekdays/weekends after result;
- no live BBC changes.
