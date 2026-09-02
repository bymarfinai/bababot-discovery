# ETH London -> New York M6 F90 Early-Reclaim Invalidation Anatomy — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Freeze the M5-supported **F90 EARLY_RECLAIM** execution and diagnose the native ETH downside excursion that separates eventual strict-breakout winners from non-winners.

M6 does **not** install a stop and does **not** optimize PnL. It is a structural risk-anatomy stage only.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- London reference 08:00-13:30 UTC.
- New York active session 13:30-20:00 UTC.
- LONG K1 OPP0 only.
- Exact persisted M5 `EARLY_RECLAIM` rows with `executed=True`.
- Entry timestamp and actual next-bar-open entry price are reused unchanged from M5.
- Historical partitions unchanged: external, development, reference_validation, August telemetry.

## Frozen outcome classes
For every executed M5 EARLY_RECLAIM trade:
- `WINNER` = M5 terminal is `STRICT_BREAKOUT` (first completed post-entry 5m close > frozen London H before any completed close < L).
- `NON_WINNER_OPPOSITE` = M5 terminal is `OPPOSITE_BREAK`.
- `NON_WINNER_TIME` = M5 terminal is `NO_BREAK_BY_END`.

No H2-based relabeling is allowed. H2 remains telemetry only.

## Frozen excursion window
- Start at the actual M5 entry bar open (`entry_bar_start`, `entry_px`).
- For a WINNER, excursion is measured through and including the strict-breakout bar because its close > H is only known at bar completion.
- For an OPPOSITE non-winner, excursion is measured through and including the opposite-break terminal bar.
- For a TIME non-winner, excursion is measured through the last raw 5m bar before 20:00 UTC.
- No post-terminal or post-session price is used.

## Frozen anatomy metrics
Normalize all prices to the completed London range: `fraction = (price-L)/(H-L)`.

Per executed trade persist:
- realized entry fraction;
- minimum raw 5m low fraction before terminal (`min_low_fraction`);
- wick MAE from actual entry in R units;
- minimum completed 5m close fraction before terminal (`min_close_fraction`);
- close-drawdown from actual entry in R units;
- minutes entry -> terminal;
- H2-after-entry telemetry;
- terminal class.

## Frozen structural boundary grid
No intermediate thresholds may be added after result inspection:

`F85, F80, F75, F70, F65, F60, F55, F50`

For each boundary report both:
1. wick breach: any raw 5m `low < boundary` before terminal;
2. completed-close breach: any raw 5m `close < boundary` before terminal.

Primary stop-relevant diagnostic is **completed-close breach**. Wick breach is telemetry.

## Required summaries
For each major partition and POOLED_MAJOR:
- executed N, winner N, non-winner N;
- winner/non-winner median and p75/p90 wick MAE;
- winner/non-winner median and p75/p90 close drawdown;
- median minimum close fraction;
- boundary table with winner close-breach rate, non-winner close-breach rate, and separation in percentage points;
- same wick-breach table as telemetry.

## Frozen structural boundary screen
A boundary is tagged `STRUCTURAL_CANDIDATE` only if all are true:
1. every major partition has at least 10 WINNER trades;
2. completed-close breach rate among WINNERs is <=15% in **each** major partition;
3. pooled-major completed-close breach rate among NON-WINNERs is >=40%;
4. pooled-major non-winner minus winner close-breach separation is >=25 percentage points.

Reference-validation non-winner count is expected to be small and is therefore reported as adequacy telemetry, not used as a separate minimum-N gate. No boundary is promoted to live trading by M6 even if it passes this structural screen.

## Interpretation guardrails
- Do not choose a level by maximum separation if it fails the frozen screen.
- Do not convert the result into an economic stop in the same run.
- Do not add ATR, EMA, volume, candle-body, timing, or regime filters.
- Do not change F90 EARLY_RECLAIM entry semantics.
- If no boundary passes, report none and diagnose the excursion overlap.

## Mandatory assertions
1. M5 EARLY_RECLAIM executed identity/timestamps/entry prices reproduce exactly.
2. Every winner terminal bar has completed `close > H`.
3. Every opposite terminal bar has completed `close < L`.
4. No bar after terminal or 20:00 UTC contributes to excursion.
5. `min_low_fraction <= min_close_fraction` within floating tolerance.
6. Boundary prices equal exact frozen London-range fractions.
7. Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.
