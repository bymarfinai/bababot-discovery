# B27DL — E20 Armed Step-10 Runner — Preliminary Raw-5m Replay

## Scope
This is a balanced targeted raw-candle replay, NOT the preregistered full 242-candidate global re-lock result.

Sample: 16 accepted fixed-E20 TP trades, exactly 4 per operating zone, spanning 2020, 2022, 2023 and 2024 where available. Raw paths were replayed from Binance Futures BTCUSDT 5m candles using the frozen B27DL runner mechanics.

Frozen runner remains unchanged from the preregistration: E20 high-touch arms the runner; E20 becomes a next-bar hard floor; completed-close E10 milestones ratchet the floor one step behind; no alternate threshold was tried.

## Balanced sample result

| Zone | N | Fixed E20 Net | Runner Net | Delta | Delta % | Improved | Same | Worse |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALT_0330 | 4 | +$39.22 | +$36.88 | -$2.34 | -6.0% | 0 | 2 | 2 |
| RAW_0530 | 4 | +$9.68 | +$6.44 | -$3.24 | -33.5% | 0 | 2 | 2 |
| LONDON | 4 | +$8.58 | +$8.75 | +$0.17 | +2.0% | 1 | 1 | 2 |
| RAW_2330 | 4 | +$8.99 | +$17.59 | +$8.60 | +95.7% | 2 | 1 | 1 |
| TOTAL | 16 | +$66.46 | +$69.66 | +$3.20 | +4.8% | 3 | 6 | 7 |

## Observed failure mode
The universal runner is frequently harmed when E20 is reached only by an intrabar wick. Because the newly armed E20 floor is intentionally causal and becomes effective on the next 5m bar, the next bar can open below E20 and force a lower gap-safe exit. This occurred in multiple ALT_0330, RAW_0530 and LONDON replays.

## Observed upside mode
RAW_2330 produced the clearest continuation examples. In the 2020-03-05 and 2022-02-08 samples, price continued through multiple structural extensions after E20, allowing the step-10 floor to ratchet substantially above the old fixed target.

## Interpretation guardrail
- The +$3.20 / +4.8% sample improvement is entirely driven by RAW_2330; the other three zones combined are worse than fixed E20 in this sample.
- Only 3/16 cases improved, 6/16 were unchanged, and 7/16 worsened.
- Therefore this sample does NOT support applying the runner universally across all four zones.
- It is suggestive that RAW_2330 may deserve a separately preregistered zone-specific runner test, but no such rule is promoted here.
- Full B27DL status remains unresolved until the preregistered exact 242-candidate chronological re-lock is executed.

Research only. Live BBC unchanged.