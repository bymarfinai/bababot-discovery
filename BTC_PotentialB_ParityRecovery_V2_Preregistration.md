# BTC Potential B — Historical Parity Recovery V2 Preregistration

**FROZEN BEFORE V2 AUGUST RESULT. Research-only. Live BBC untouched.**

V1 full-session reconstruction was `PARITY_UNRESOLVED` and materially overcounted the preserved historical Potential B benchmarks. V2 corrects only implementation ambiguity, using historical benchmark matching rather than August performance.

## Preserved benchmark
- recent ~240d base: 17/24 SELL directional wins;
- recent aggressive taker-buy subset: 11/15;
- full ~960–971d aggressive subset: 43/67.

## V2 parity candidate set
All candidates retain the same Potential B path:
`pre-London HOD frozen -> HOD breakout -> two consecutive completed 5m closes above HOD -> optional failure/trap -> SELL next causal 15m open`.

V2 locks two corrections consistent with a London-open event study:
- only **Monday–Friday UTC dates** are eligible;
- event search is limited to the initial London-open window, with parity-only candidates **60 / 90 / 120 minutes**.

Finite historical parity dimensions:
- London open 07:00 or 08:00 UTC;
- trigger `CONFIRM2` or `TRAP_BACK_BELOW`;
- initial event window 60 / 90 / 120 minutes.

Aggressive subset remains `taker-buy quote share > 0.50` on the second above-HOD confirmation bar. Entry remains next 15m open after completed trigger. Outcome remains next 60m SELL direction.

Canonical V2 variant is chosen solely by minimum absolute error versus `(24,17,15,11,67,43)` on data ending 2026-07-30. August is never used to select clock/window/trigger.

After parity selection, replay 2026-08-01 onward using available completed official Binance 5m data and separately report the unchanged TP1%/SL1% 6h diagnostic. No 1m data.

No post-result window/threshold/direction/TP-SL rescue is allowed.

CI trigger note: workflow existed before this push; no research rule changed.
