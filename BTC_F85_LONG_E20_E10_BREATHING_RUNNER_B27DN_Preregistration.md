# B27DN — F85 LONG E20 Touch + E10 Breathing Floor — Preregistration

## Purpose
Test whether giving the post-E20 runner a small structural breathing room can preserve more continuation upside while reducing the give-back/WR damage seen in B27DL.

## Evidence status
This hypothesis was generated from the already-observed B27DM wick-reject anatomy (median E20 rejection close around E14). Therefore B27DN is an exploratory optimization on previously inspected history, not pristine unseen OOS evidence.

## Frozen operating portfolio
Use the exact B27DK 4-zone candidate stream and filters:
- ALT_0330: TOUCH_FIRST_HALF.
- RAW_0530: B27DJ RANGE_COMPLETED_SECOND_HALF.
- LONDON 08:00: Same-Bar F85 baseline.
- RAW_2330: B27DJ RANGE_COMPLETED_SECOND_HALF.

Entry logic, F35 invalidation, reference geometry, notional, fee, partitions and data source remain unchanged.

## Frozen exit variant
Name: `E20_TOUCH_E10_BREATHING_STEP10_RUNNER`.

Let `R = H-L`, `E10 = H + 0.10R`, and `E20 = H + 0.20R`.

1. Before E20 is reached, management is identical to B27DK: a completed 5m close below F35 invalidates; otherwise continue.
2. The first 5m bar whose high reaches E20 arms the runner; do not take fixed E20 TP.
3. Starting from the next 5m bar, the protective floor is E10, not E20. The arming bar itself cannot be stopped by the newly created floor.
4. Floor execution is causal/hard:
   - if the next/subsequent bar opens at or below the known floor, exit at that open;
   - otherwise if the bar low touches the floor, exit at the floor and make the exit available after that completed 5m bar for portfolio locking.
5. The floor ratchets only from completed 5m closes and never decreases:
   - close >= E30 -> floor becomes at least E20;
   - close >= E40 -> floor becomes at least E30;
   - close >= E50 -> floor becomes at least E40;
   - and so on, always one 0.10R milestone behind the highest completed-close milestone.
6. If the execution window ends first, exit at execution-end open exactly as in prior experiments.
7. No alternate initial floor (E05/E12/E15), step size, candle timeframe, arm level, or partial-take-profit percentage is tested inside B27DN.

## Exact portfolio rescore
Because runner exits can extend holding time, B27DN must rerun the same global one-BTC-position chronological lock over the full candidate stream. Do not simply replace PnL on previously accepted trades.

## Reporting
Report fixed E20, prior B27DL runner, and B27DN for pooled-major where possible. For B27DN report every partition and each zone: N, WR, PF, expectancy, net PnL, blocked trades, max loss streak, armed count, floor exits and time exits.

## Interpretation
B27DN is considered a promising exploratory improvement only if pooled-major net exceeds fixed E20, PF remains >= 1.80, WR remains >= 70%, accepted N remains >=80% of fixed-E20 N, and every major partition stays net positive. Also explicitly report whether it beats B27DL on net PnL and whether WR improves versus B27DL.

Research/operating exit experiment only. Live BBC remains unchanged.