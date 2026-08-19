# BTC Potential B — August 2026 True-OOS Replay Preregistration

**FROZEN BEFORE AUGUST RESULT. Research-only. Live BBC untouched.**

## Objective
Replay the previously tested **Potential B** BTC London/session event-sequence on August 2026 data without changing the strategy after seeing August.

Known historical benchmark from the earlier Potential B study:
- recent ~240d base HOD-break sequence: **17/24 = 70.83%** 60m SELL directional wins;
- aggressive-buyer subset (`taker buy share >50%` on the confirmation bar): **11/15 = 73.33%**;
- full ~960–971d aggressive-flow aggregate: **43/67 = 64.18%**.

## Canonical information set
- BTCUSDT USD-M perpetual, Binance Futures;
- 5m completed candles;
- current-day **high-of-day formed before London open** is frozen at London open;
- observe the first relevant London event only;
- core path: **HOD break -> 2 consecutive completed 5m closes above frozen HOD -> aggressive taker buyers -> contrarian SELL**;
- trigger must be complete before entry;
- entry is the next causal **15m open** after confirmation;
- historical comparison target is SELL direction over the next **60m**.

## Legacy parity reconstruction — NOT strategy tuning
The old repository contains two historical London-hour conventions (07:00 UTC and 08:00 UTC), and the archived conversation preserves the benchmark counts but not the exact clock implementation. Therefore, before reading August performance, the runner will evaluate a finite parity set using **historical data only through 2026-07-30**:

1. London open = 07:00 UTC or 08:00 UTC;
2. trigger = second consecutive 5m close above frozen HOD (`CONFIRM2`) or first subsequent 5m close back below frozen HOD after that confirmation (`TRAP_BACK_BELOW`).

All variants use:
- frozen HOD from 00:00 UTC to London open, exclusive;
- first qualifying sequence per UTC date;
- search ends at 16:00 UTC;
- aggressive subset = taker-buy quote / total quote volume > 0.50 on the **second above-HOD confirmation candle**;
- entry = next 15m open strictly after trigger completion;
- 60m SELL win = close after 60m < entry price.

The canonical replay variant is selected **only by closeness to the already-known historical benchmark** `(24,17,15,11,67,43)`. August rows are never used for parity selection. If no variant approximately reproduces the historical benchmark, August output is labeled `PARITY_UNRESOLVED` rather than pretending it is exact Potential B.

## August true-OOS window
- target: **2026-08-01 through 2026-08-19**;
- only completed official Binance Data Vision 5m bars actually available at run time are used;
- partial/unavailable current-day archives are not fabricated or forward-filled.

## Primary August outputs
For the historically selected variant, report separately:
1. base Potential B events;
2. aggressive-buyer subset (`>50%`);
3. 60m directional SELL WR and signed return;
4. every event date/time so there is no selective omission.

## >1% move diagnostic
Because the current research objective is moves larger than 1%, the replay also measures—without changing the Potential B trigger—whether each entry reaches:
- SELL favorable **-1.00%** before adverse **+1.00%**;
- adverse-first on a same 5m candle is counted conservatively as loss;
- max observation 6h;
- 0.15% round-trip fee and $500 reference notional are reported as a separate execution diagnostic.

This >1% diagnostic does **not** redefine the historical Potential B benchmark.

## Guardrails
- no 1m data;
- no change to 50% aggressive-flow threshold;
- no TP/SL sweep;
- no choosing 07:00 vs 08:00 based on August;
- no direction flip after result;
- no extra filter after seeing losers;
- no live code changes.
