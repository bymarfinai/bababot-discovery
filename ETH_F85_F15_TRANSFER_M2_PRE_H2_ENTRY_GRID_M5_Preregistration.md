# ETH Transfer — M5 Entry Robustness & Final Selection

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Freeze the pre-H2 entry shortlist and test whether each candidate is stable through time before any stop/target/economic work.

## Upstream gate
M2 status must equal `ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY`.

## Frozen candidates
No new clock or level may enter M5:
- ALT_0330 F95
- RAW_0530 F90
- RAW_0530 F85
- LONDON F90
- RAW_2330 F95

All must already be corrected-M2 `SCREEN_PASS` candidates. SHORT and post-breakout candidates are outside M5.

## Data identity
Use corrected-M2 filled candidates and their frozen H2/opposite/no-H2 outcomes. No fill timing or terminal identity is changed. M5 does not download or regenerate a new signal set.

## Diagnostics
For each frozen candidate report:
- major-partition N and H2 rate;
- pooled-major N/H2 rate;
- full calendar years 2020–2025;
- partial 2026 separately;
- trailing 6-month windows anchored monthly, minimum N=6;
- trailing 12-month windows anchored monthly, minimum N=12;
- most recent 365 days ending at the frozen M2 cutoff, minimum N=12;
- H2-winner MAE P90/P95 using the frozen M2 `mae_ru` path metric;
- median fill-to-H2 minutes for winners.

## Frozen robustness screen
A candidate is `ROBUST_PASS` only if all are true:
1. it retains corrected-M2 `SCREEN_PASS` identity;
2. every major partition still has N>=30 and H2 rate>=70%;
3. at least 4 full calendar years have N>=10;
4. among eligible full years, >=75% have H2 rate>=70% and none is below 60%;
5. at least 24 eligible rolling-12M windows exist;
6. >=75% of eligible rolling-12M windows have H2 rate>=70% and the worst eligible rolling-12M rate is >=60%;
7. recent 365-day N>=12 and H2 rate>=70%.

Rolling 6M is diagnostic only because its samples are smaller.

## RAW_0530 head-to-head
Also decompose F90 vs F85 into common fills and incremental cohorts. This is descriptive and uses the same frozen outcomes.

## Final selection rule
- Single-candidate habitats are locked only if their candidate is `ROBUST_PASS`; otherwise habitat remains `NOT_LOCKED`.
- RAW_0530: if one candidate passes, select it; if neither passes, `NOT_LOCKED`; if both pass, select lexicographically by: higher worst rolling-12M rate, higher share of rolling-12M windows >=70%, higher recent-365D H2 rate, higher pooled H2 rate, lower winner MAE P90, then larger pooled N.
- No threshold or tie-breaker may change after results are seen.

## Prohibited
No TP, stop, E20/E20_DOWN, PnL, PF, expectancy, fees, leverage, confirmation redesign, new levels, new clocks, SHORT resurrection, or M6 automatic execution.

**Stop after M5 result persistence.**