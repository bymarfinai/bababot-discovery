# BTC Potential B Mirror — LOD Breakdown / Seller Trap BUY Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Objective
Test the exact directional mirror of the current Potential B operational anchor, then replay it on August 2026 true post-cutoff data.

This is not a new clock/window search. The anchor is inherited from the historically closest Potential B parity reconstruction:
- London anchor: **07:00 UTC**;
- event window: **90 minutes** from 07:00 UTC;
- weekdays only;
- confirmation mode: **two consecutive completed 5m closes through the frozen level**;
- entry: next causal 15m open.

## Frozen mirror rule
For each Monday-Friday UTC date:
1. Freeze the current-day **LOD** using only 5m bars from 00:00 UTC up to 07:00 UTC exclusive.
2. During 07:00-08:30 UTC, find the **first** pair of consecutive completed 5m candles with both closes **below** the frozen LOD.
3. This second close is the completed confirmation candle.
4. Base signal = contrarian **BUY**.
5. Aggressive-seller subset = taker-buy quote share on the confirmation candle **< 0.50** (seller share >50%).
6. Entry = next 15m open strictly after confirmation completion.

This is exactly symmetric to the existing HOD / buyer-trap SELL framing. No reclaim candle, CHoCH, EMA, wick, OI, funding, premium, or extra support/resistance filter is added.

## Historical evaluation
- BTCUSDT USD-M perpetual;
- official Binance Futures 5m Data Vision;
- 2023-12-02 through 2026-07-30 exclusive;
- one first event maximum per eligible day;
- primary historical outcome: BUY directional return over next 60m from executable entry;
- win iff 60m close > entry.

Report:
- base and aggressive-seller subset;
- full sample;
- chronological first70% / last30% event split;
- four chronological blocks.

### 80% candidate gate
A mirror rule may be labeled `POTENTIAL_B_MIRROR_80_CANDIDATE` only if the **aggressive-seller subset** has:
- full N >=25 and WR >=80%;
- validation N >=10 and WR >=80%;
- discovery WR >=80%;
- at least 3/4 blocks with N>=5 and WR>50%;
- zero timestamp/causality violations.

Failure of this gate does not authorize threshold/window/direction rescue.

## >1% executable diagnostic
Without changing the trigger:
- BUY TP +1.00%;
- BUY SL -1.00%;
- max hold 6h;
- if TP and SL touch on the same 5m candle, adverse/SL first;
- timeout exits at actual 6h close;
- modeled round-trip fee 0.15%;
- $500 reference notional.

Report this diagnostic historically and for August separately.

## August true-OOS replay
- 2026-08-01 through 2026-08-19 target window;
- only completed official archives available at run time count;
- every August event must be listed; no selective omission.

## Guardrails
- no 1m data;
- no 07:00/08:00 clock selection after result;
- no 60/90/120-minute window selection after result;
- no 50% flow threshold change;
- no LONG/SHORT flip after result;
- no TP/SL/hold sweep;
- no extra filter based on losers;
- no live BBC changes.

CI trigger note: workflow already exists before this push; this note changes no research rule.
