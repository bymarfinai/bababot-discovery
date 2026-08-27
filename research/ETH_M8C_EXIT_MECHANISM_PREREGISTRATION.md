# ETH Transfer — M8C Exit Mechanism Discovery — Preregistration

## Purpose
Test whether the negative/fragile economics seen in verified M8B are caused by the post-H2 profit-taking mechanism rather than by entry identity or pre-H2 protection.

## Frozen upstream inputs
- Entry identities remain frozen from M5: ALT_0330 F95; RAW_0530 F90; LONDON F90; RAW_2330 F95.
- Pre-H2 protection candidates remain frozen from verified M6:
  - ALT_0330: HARD_TOUCH F50; CLOSE_NEXT_OPEN F55.
  - RAW_0530: HARD_TOUCH F35; CLOSE_NEXT_OPEN F50.
  - LONDON: HARD_TOUCH F35; CLOSE_NEXT_OPEN F55.
  - RAW_2330: HARD_TOUCH F55; CLOSE_NEXT_OPEN F65.
- Primary M7 target remains frozen per habitat: ALT E30; RAW0530 E30; LONDON E25; RAW2330 E15.
- Pre-H2 invalidation semantics remain exactly as M8B: protection is active only through H2. No post-H2 use of M6 stop unless explicitly defined by an exit mechanism below.

## Frozen exit mechanisms
Each entry is evaluated under both frozen M6 pre-H2 protection modes and exactly these four post-H2 mechanisms. No other target levels, percentages, trailing distances, or time grids are permitted in M8C.

1. `H2_FULL_EXIT`
   - If H2 occurs before pre-H2 invalidation, exit 100% at H (the structural H2 touch price).
   - If invalidated before H2, use the frozen M6 protection execution.

2. `H2_HALF_M7_HALF`
   - If H2 occurs, realize 50% of notional at H.
   - Keep the remaining 50% for the frozen M7 target.
   - After H2, no M6 stop is active. Remaining half exits at M7 target or session-end open.
   - Fees are scaled by realized notional using the same M8B fee rate: $0.40 round-trip per $500 full notional, applied pro-rata to each leg.

3. `BE_AFTER_H2_M7`
   - Keep 100% position after H2 for the frozen M7 target.
   - Beginning with the first 5m bar strictly after the H2 bar, activate a hard break-even floor at the original entry price.
   - If a post-H2 bar touches both break-even and target, count break-even first (conservative same-bar ordering).
   - Otherwise target or session-end open exits the trade.

4. `H_CLOSE_FAILURE_M7`
   - Keep 100% position after H2 for the frozen M7 target.
   - Beginning with the H2 bar close, if a completed 5m candle closes below H, exit at the next 5m open.
   - Target wick is checked before the close-failure signal within a bar; if the target was touched intrabar, target wins because the fill exists before bar close.
   - Otherwise session-end open exits the trade.

## Economics
- Illustrative notional: $500.
- Full-position round-trip fee: $0.40, identical to M8B.
- Partial leg fees are pro-rated by notional.
- Win rate = net PnL > 0.
- PF = gross positive net-PnL sum / absolute gross negative net-PnL sum.

## Frozen economic promotion screen
A mechanism/protection pair can be called `SCREEN_PASS` for a habitat only if **each** major partition (`external`, `development`, `reference_validation`) has:
- at least 30 resolved trades;
- WR >= 70%;
- net expectancy > $0/trade;
- PF >= 1.20.

August remains telemetry only and is not part of the promotion gate.

## Selection rule
- Do not select by pooled result alone.
- If one or more pairs pass, select the pair maximizing the minimum major-partition net expectancy, then minimum PF, then minimum WR.
- If none pass, report `NONE_PASS` and only describe the least-bad pooled candidates; do not promote them.

## Research boundary
M8C may change only the post-H2 exit mechanism. Entry identity, M6 protection levels, H2 semantics, M7 primary target, fee model, partitions, and economic gates are frozen. No live deployment is authorized.
