# ETH London -> New York M9 Post-Breakout Profit Protection — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Diagnose and test whether the M8 E15/F50 static configuration fails primarily because trades that have already structurally succeeded at `close > H` are allowed to give back too much before E15 or the distant F50 invalidation.

M9 freezes the validated structure and changes only post-breakout protection.

## Frozen trade structure
- ETHUSDT perpetual, raw 5m.
- London reference 08:00-13:30 UTC.
- New York active session 13:30-20:00 UTC.
- LONG K1 OPP0 only.
- Entry: exact M5 `F90 EARLY_RECLAIM`, next raw 5m open.
- Static target: `E15 = H + 0.15R`.
- Pre-breakout invalidation: completed 5m close below `F50 = L + 0.50R`.
- Entry notional: $500.
- Base fee: $0.40 round-trip, matching M8.
- Stress: 5 bps adverse execution, matching M8.

No entry, target, pre-breakout invalidation, clock, indicator, or regime retuning is allowed.

## Frozen causal breakout event
`STRICT_BREAKOUT` is the first completed raw 5m candle after entry with `close > H` before pre-breakout F50 close-invalidation.

The breakout is known only when that candle completes. Therefore a post-breakout floor becomes exchange-active on the **next raw 5m bar**.

## Frozen variants
One static baseline plus exactly three post-breakout floor variants:

1. `BASE_F50`: M8 E15/F50 unchanged.
2. `BO_FLOOR_F90`: after strict breakout confirmation, activate floor at F90 on next bar.
3. `BO_FLOOR_F95`: after strict breakout confirmation, activate floor at F95 on next bar.
4. `BO_FLOOR_H`: after strict breakout confirmation, activate floor at H on next bar.

No E-level staircase and no trailing logic in M9.

## Post-breakout floor execution semantics
For the first active bar and every later bar until exit:
1. If bar open <= active floor, exit at bar open (`FLOOR_GAP_OPEN`).
2. Else if bar low <= active floor, exit at exact floor (`FLOOR_TOUCH`).
3. Else if bar high >= E15, exit at exact E15 target (`TARGET`).
4. Otherwise continue.

The order above is frozen because the floor is an already-active protective order at the start of the bar, while the E15 limit is also resting. When both floor and target are spanned inside one OHLC bar and open is between them, intrabar order is unknowable from 5m OHLC; such bars are tagged `AMBIGUOUS_BOTH` and the trade is excluded from promotion metrics but reported separately. No optimistic target-first assumption is allowed post-breakout.

Before breakout, M8 semantics remain unchanged: resting E15 target is checked before completed-close F50 invalidation because the latter is only known at bar completion.

## Required diagnostic decomposition
For each major partition and pooled major, classify every M5 executed trade into:
- `NO_BREAKOUT_FAIL`: never gets strict breakout before F50/time/target;
- `BREAKOUT_TO_E15`: strict breakout then reaches E15;
- `BREAKOUT_GIVEBACK`: strict breakout occurs but E15 is not reached before static F50/time exit under baseline;
- `E15_SAME_OR_BEFORE_BO_BAR`: target reached no later than breakout confirmation bar, if applicable.

Report count and contribution to baseline PnL for each class. This decomposition is the primary answer to why Development fails.

## Economic outputs
Per variant / partition / pooled-major at 0bps and 5bps:
- N and ambiguous-excluded N;
- actual WR (`PnL > 0`);
- TP count/rate;
- floor-exit count/rate;
- close-invalidation count;
- time-exit count;
- PF;
- expectancy;
- net;
- max loss streak;
- median win and median loss;
- median hold minutes.

## Frozen promotion screen
A post-breakout floor variant is `SCREEN_PASS` only if, excluding ambiguous-both trades:
1. each major partition has N >= 15;
2. each major partition actual WR >= 70%;
3. each major partition PF >= 1.00;
4. each major partition expectancy > 0 and net > 0;
5. pooled-major actual WR >= M8 E15/F50 pooled WR (75.8%);
6. pooled-major PF >= M8 E15/F50 pooled PF (1.40);
7. pooled-major 5bps PF > 1 and net > 0;
8. Development PF must improve from M8 E15/F50 PF 0.90 to >=1.00.

Primary ranking among passing variants: actual WR first, then PF, expectancy, 5bps PF.

## Interpretation guardrails
- Do not choose a floor by pooled performance if Development remains negative.
- Do not add dynamic staircases after seeing M9 results in the same run.
- Do not retune F90/F95/H into intermediate fractions.
- If no floor passes, report the failure mode; next work must be separately preregistered.

## Mandatory assertions
1. Exact M5 F90 EARLY_RECLAIM executed cohort reproduced.
2. M8 BASE_F50 E15 economics reproduced exactly within floating tolerance.
3. Breakout floor never becomes active on the breakout bar itself.
4. No floor exit occurs before strict breakout.
5. Ambiguous post-breakout bars are never silently resolved optimistically.
6. No bar after 20:00 UTC is used.
7. ETH raw 5m coverage >=99.5%.

Research only. Live BBC unchanged.