# SOL LONG 15:00 UTC RC30_C2 Delayed Confirmation — A34 Preregistration

## Purpose
A33 showed that post-entry +5/+10m follow-through is informative, but entering first and then cutting weak recoveries is too costly after 5bps stress. A34 therefore tests the same frozen A30/A33 follow-through states as **pre-entry confirmation**.

This is not a new threshold search. It reuses the exact A33 fixed states:
- +5m close >= H + 0.10R
- +10m close >= H + 0.12R

The frozen 15UTC parent remains R360 / 15:00 UTC / E0_RESTING_H -> E40. A23 resting recovery remains rejected.

## Exact RC30_C2 precursor
For a frozen parent loser:
1. Start observing at the parent exit.
2. Within the next 30 minutes, require the second completed close > H.
3. If E40 is touched before the second reclaim close, no recovery trade is created.
4. The second close > H is the RC30_C2 signal.

## Frozen A34 family
1. `DC5_C10`
   - Do not enter immediately after RC30_C2.
   - Observe the first completed 5m bar after the signal.
   - Enter next open only if its close >= H + 0.10R.

2. `DC10_C12`
   - Do not enter immediately after RC30_C2.
   - Observe through the second completed 5m bar after the signal.
   - Enter next open only if the second close >= H + 0.12R.

3. `DC5_OR10`
   - Enter next open after the first qualifying condition: +5m close >= H+0.10R, otherwise +10m close >= H+0.12R.

If E40 is touched before delayed entry, the recovery is skipped rather than credited.

## Recovery lifecycle after delayed entry
- Entry: next open after the qualifying completed confirmation close.
- Target: original E40 = H + 0.40R; not credited on the delayed-entry bar.
- Invalidation: completed close <= H -> exit next open.
- Otherwise time exit at the same frozen recovery-window end.
- One recovery only; no averaging; no H3/H4 retry.

## Development gates
A lane may pass only if all hold:
- recovery N >= 60;
- raw recovery PF > 1.20 and 5bps PF > 1.05;
- raw and 5bps recovery expectancy/net > 0;
- raw and 5bps overlay PF and net improve versus parent-only 15UTC;
- episode WR uplift >= 4 percentage points raw and >= 3 points at 5bps;
- episode rescue rate >= 30%;
- at least 4/6 adequate Development blocks positive raw and at least 4/6 positive 5bps.

Winner selection: highest 5bps overlay-net improvement, then 5bps overlay PF, raw overlay-net improvement, episode-WR uplift, then earlier/simpler confirmation.

## Frozen OOS gates
Only the Development winner may be opened OOS. It must:
- improve raw and 5bps net and PF on both Central External and Central Reference Validation;
- keep raw and 5bps recovery net positive on both Central OOS partitions;
- improve episode WR by >= 2 percentage points raw and >= 1 point at 5bps on both Central OOS partitions;
- have >=3/4 support rows positive for raw recovery net, 5bps recovery net, raw overlay-net improvement, and 5bps overlay-net improvement.

No neighboring threshold/window scan and no OOS retuning are authorized.

Research only. Live Baba Bot remains unchanged.
