# ETH Transfer — M6 Stop / Invalidation Atlas

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Discover structurally viable downside protection for the M5-locked LONG entries without using target, PnL, PF, fees, leverage, or expectancy.

## Frozen entry set
Only these M5-locked entries may be audited:
- ALT_0330 F95
- RAW_0530 F90
- LONDON F90
- RAW_2330 F95

All entry identity, fill timestamps, frozen H/L/R, H2/opposite/no-H2 terminal identity, and corrected +5m leave chronology remain unchanged from corrected M2. SHORT is excluded.

## Protection grid
For each entry fraction `f`, test exactly the relative adverse distances:
`D05,D10,D15,...,D85`, where stop fraction = `f-D` and stop price = `L + (f-D)*R`.
No finer or wider grid may be added after results.

## Mode A — HARD_TOUCH
A hard stop is touched when raw-5m `low <= stop_price`.
- Fill bar is included. If the fill bar also touches the stop, count it as stopped conservatively and report same-fill-bar frequency.
- For H2 winners, report both (i) pre-H2 survival excluding the H2 bar and (ii) conservative survival including the H2 bar. Selection uses conservative survival; equality with the stop is a stop.
- For non-H2 paths, a stop touch through the frozen terminal/session window counts as failure capture.

## Mode B — CLOSE_NEXT_OPEN
Close invalidation is armed by the first completed raw-5m bar with `close < stop_price`, starting with the fill bar.
- The invalidation bar must be strictly before an original terminal bar if a terminal exists.
- Exit is executable only at the immediately following raw-5m open inside the frozen execution window.
- If that next-open bar is the H2 terminal bar, the exit occurs at its open before the later intrabar H2 event and therefore kills that H2 winner.
- No wick-only close invalidation and no candle/EMA/volume filter.

## Required metrics
For each habitat × mode × D × major partition and pooled-major report:
- fills and baseline H2 rate;
- H2 winners N;
- winner survival N/rate;
- winner kill rate;
- resulting structural H2 success = surviving H2 winners / all fills;
- failures N;
- failure rejection/capture N/rate;
- among paths not invalidated, conditional H2 rate;
- median minutes fill→failure invalidation;
- stop fraction; and for HARD_TOUCH, same-fill-bar stop rate plus pre-H2 survival diagnostic.

Persist one-row-per-fill-per-distance detail with first stop/invalidation timestamps.

## Frozen structural viability screen
A habitat × mode × D is `STRUCTURAL_PASS` only if:
1. every major partition still has >=30 fills;
2. pooled-major winner survival >=90%;
3. every major partition winner survival >=85%;
4. pooled-major failure rejection/capture >=30%;
5. pooled-major resulting structural H2 success >=75%.

No pooled rescue for winner-survival partition failures.

## Ranking
Within each habitat and mode, if multiple D pass, rank by:
1. higher pooled failure rejection;
2. higher pooled winner survival;
3. tighter distance (smaller D).

HARD_TOUCH and CLOSE_NEXT_OPEN are **not** ranked against each other in M6 because their realized exit prices are economically different. M6 may nominate one structural candidate per mode per habitat, or NONE.

## Mandatory assertions
- corrected M2 status is exact;
- locked candidate set is exact and each remains corrected-M2 SCREEN_PASS;
- raw 5m coverage >=99.5%;
- H2 winner terminal is strictly after entry fill;
- hard-stop equality counts as touched;
- close invalidation uses completed close and exact next-open execution;
- no close invalidation on/after original terminal;
- synthetic tests cover same-fill hard stop, H2-bar hard-stop ambiguity, close invalidation immediately before H2, and no invalidation after terminal.

## Prohibited
No TP/E20, extension target selection, PnL, PF, expectancy, fees, leverage, position sizing, confirmation redesign, new entry level/clock, SHORT resurrection, or automatic M7.

**Stop after M6 result persistence.**