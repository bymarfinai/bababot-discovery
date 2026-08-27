# ETH Transfer — M7 Post-H2 Target / Exit Atlas

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
With M5 entry identity frozen, discover how far LONG winners extend after H2 before the frozen execution-window end. H2 is a milestone, not TP.

## Frozen entries
- ALT_0330 F95
- RAW_0530 F90
- LONDON F90
- RAW_2330 F95

No other clock or entry level may enter M7. SHORT is excluded.

## Causal identity
Use corrected-M2 chronology exactly: K1 OPP0, completed causal leave, first eligible raw 5m bar immediately after leave, initial level fill strictly before terminal H2/opposite. H2 is the first later bar whose high reaches H.

For an entry whose corrected-M2 outcome is not H2, all post-H2 targets are structural misses. For an H2 entry, extension measurement begins on the H2 bar itself because the position was already open before that bar.

## Frozen target atlas
Let R=H-L. Test exactly:
- E05 = H + 0.05R
- E10 = H + 0.10R
- E15 = H + 0.15R
- E20 = H + 0.20R
- E25 = H + 0.25R
- E30 = H + 0.30R
- E40 = H + 0.40R
- E50 = H + 0.50R

No intermediate/deeper target may be added after results.

For each target report by major partition, August telemetry, and pooled-major:
- frozen entry N and H2 N/rate;
- wick/high target reach among H2 and among all entries;
- completed-close acceptance at/above target among H2 and among all entries;
- median minutes H2→first wick reach;
- median minutes fill→first wick reach;
- H2 max-high and max-close extension distributions.

Also report first completed close > H and session-end unresolved rate. No PnL is calculated.

## Frozen structural target screen
A habitat × E target is `TARGET_PASS` only if:
1. every major partition has at least 20 H2 paths;
2. every major partition has wick target reach among H2 >=60%;
3. pooled-major wick target reach among H2 >=70%;
4. pooled-major target reach among all frozen entries >=55%;
5. pooled-major completed-close acceptance among H2 >=50%.

The M7 candidate for a habitat is the **deepest** target that passes. If none pass, the habitat remains `TARGET_NOT_LOCKED`. This is a structural candidate only, not a final economic TP.

## Exit boundary
If no target is reached, the only descriptive time boundary is the already-frozen execution-window end. M7 does not search alternate holding periods or trailing exits.

## Prohibited
No M6 stop/invalidation is combined with targets; no PnL, PF, expectancy, fees, leverage, position sizing, trailing stop, break-even, new entry confirmation, new clock/level, SHORT resurrection, or M8 automatic execution.

## Mandatory assertions
- raw ETH 5m coverage >=99.5%;
- locked entry set is exact;
- corrected leave chronology is used;
- every H2 used is after the fill bar;
- target prices equal H + E*R exactly;
- first-reach timestamps are at/after H2 and before execution-window end;
- non-H2 entries cannot be counted as post-H2 target reaches;
- H2-bar extension is allowed;
- synthetic chronology tests pass.

**Research only. Stop after M7 result persistence.**