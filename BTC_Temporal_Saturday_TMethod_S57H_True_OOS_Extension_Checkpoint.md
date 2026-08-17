# BTC Temporal Saturday T-Method S5.7H — Frozen True-OOS Extension

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — TRUE-OOS OBSERVATION ONLY; FROZEN RULE UNCHANGED; ADAPTIVE BRANCH NOT YET EXERCISED  
**Research only:** live BBC untouched

## Frozen OOS protocol
- Research cutoff: **2026-07-30 00:00 UTC**.
- OOS entries scored: Saturday 18:00 WIB on **2026-08-01, 2026-08-08, 2026-08-15**.
- Only completed Binance 5m daily data through **2026-08-16** were appended.
- The S5.7G `NO_BULL_TOP_Q_30` rule was replayed with **zero definition changes**.
- Historical pre-cutoff candles were used only as EMA/path warmup, never as OOS scoring rows.
- August funding was obtained from Binance Futures public funding-history because Binance Vision does not publish the attempted daily fundingRate archive path before the monthly archive exists. Funding timing/formula remained the frozen S5.0 convention.

## Aggregate true-OOS result
- N: **3**
- Static parent: **-$9.724**, WR **0.00%**
- A7.19: **-$9.724**, WR **0.00%**
- Frozen S5.7G champion: **-$9.724**, WR **0.00%**
- Champion delta vs A7.19: **$0.000**
- Rejected hinges: **0**
- Champion actions: **0**

## Trade-by-trade
| Date | Parent | A7.19 | Champion | MFE | MAE | +0.5 reached? | Rejected? | Champion action? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-01 | **-$6.768** | -$6.768 | -$6.768 | **+0.109%** | **-1.270%** | NO | NO | NO |
| 2026-08-08 | **-$2.500** | -$2.500 | -$2.500 | **+0.281%** | **-0.432%** | NO | NO | NO |
| 2026-08-15 | **-$0.456** | -$0.456 | -$0.456 | **+0.200%** | **-0.150%** | NO | NO | NO |

Parent exit reasons:
- Aug 1: **SL** after 7h35m.
- Aug 8: **TIMEOUT** after 18h.
- Aug 15: **TIMEOUT** after 18h.

## Critical interpretation
The true-OOS observation is negative for the overall Saturday entry/parent strategy so far, but it is **not yet a test of the S5.7G adaptive recovery rule**.

All three unseen trades failed before the adaptive branch could become knowable:
> none of the three trades ever reached the frozen +0.50% hinge.

Therefore:
- there was no hinge candle to classify as ACCEPTED vs REJECTED;
- `NO_BULL_TOP_Q_30` had no eligible trade;
- A7.19 also remained `PRESERVE` on all three;
- champion PnL equals parent/A7.19 exactly.

The immediate OOS failure mode is therefore **lack of initial favorable impulse**, not failure of rejected-hinge recovery management.

This is important because the frozen Saturday research already established that trades which never reach +0.50 are historically the weakest cohort. The first three true-OOS Saturdays all landed in that weak regime.

## What must NOT be concluded
- Do not call S5.7G OOS-confirmed: it has had **zero OOS actions**.
- Do not call S5.7G OOS-failed: its trigger condition has also occurred **zero times**.
- Do not tune +0.50, upper-wick 50%, +30m, top-quartile definition, TP/SL, or A7.19 from these three observations.
- Do not retrofit a new early cut from only these three OOS losses.

## Research status after S5.7H
Same-sample ranking remains frozen:
1. `NO_BULL_TOP_Q_30`: **+$111.240 on 139/139**, S5.7G robust-tradeoff PASS.
2. `NO_POS_TAKER_60`: **+$110.238 on 139/139**, robust-tradeoff PASS.
3. A7.26 selective: **+$109.587 on 123/139**.
4. A7.19: **+$103.383 on 139/139**.

But true-OOS scoreboard is now separately recorded:
- **3 trades, 0 wins, -$9.724**.
- **0 rejected hinges / 0 adaptive actions**.

The disciplined next step is to keep the frozen rule unchanged and accumulate additional unseen Saturdays. A separate future forensic of the `NO +0.50` OOS state should only be considered after enough genuinely unseen examples exist; the current N=3 is not sufficient to redesign entry management.

## Execution
- First run `32030827517` failed only because the assumed Binance Vision daily fundingRate archive path returned HTTP 404. No strategy result was produced.
- Successful frozen-rule run: **32030989095**.
- Artifact: `s57h-output`, ID **9288895342**.
- No live BBC modification.
