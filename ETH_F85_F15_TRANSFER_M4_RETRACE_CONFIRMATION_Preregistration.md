# ETH F85/F15 Transfer — M4 Retrace + Confirmation Entry Refinement

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Test whether corrected-M2 trigger-level fills should be treated as **setup activation**, followed by a deeper retrace and causal reclaim before executable entry.

M4 answers one question only:

> After a valid corrected-M2 LONG level fill, does waiting for a deeper retrace and completed 5m reclaim improve H2-arrival quality while retaining enough opportunity?

This is an entry-refinement audit. It is **not** a TP/SL or PnL backtest.

## Upstream gate
M4 may run only if corrected M2 status equals:

`ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY`

The M2 +10-minute eligibility output is superseded and forbidden.

## Candidate universe
Use **every LONG habitat × level** whose corrected-M2 pooled-major row is tagged `SCREEN_PASS`.

Do not manually cherry-pick only M3-favored levels.

SHORT is absent because corrected M2 produced no SHORT `SCREEN_PASS` level.

## Frozen structural identity
Unchanged from corrected M2:
- ETHUSDT Binance USD-M perpetual;
- raw 5m event clock;
- frozen reference H/L/R;
- K1 OPP0;
- completed causal leave;
- first eligible bar immediately after leave;
- initial corrected-M2 level fill strictly before H2/opposite terminal;
- H2 and opposite-break identity unchanged.

## Initial trigger fill
For a corrected-M2 LONG survivor level with fraction `f`, the first valid M2 fill remains the **setup activation time**.

M4 does not reinterpret the initial fill as an executable trade.

## Frozen retrace grid
After the initial trigger fill, test adverse retrace distances:

- D05 = `f - 0.05R`
- D10 = `f - 0.10R`
- D15 = `f - 0.15R`
- D20 = `f - 0.20R`
- D25 = `f - 0.25R`
- D30 = `f - 0.30R`
- D35 = `f - 0.35R`
- D40 = `f - 0.40R`

No deeper or intermediate parameter may be added after results are seen.

## Causal retrace rule
For distance D:
1. Search starts on the raw 5m bar **after** the initial M2 fill bar.
2. A retrace becomes armed when a completed bar has `low <= retrace_price`.
3. The initial fill bar cannot satisfy the deeper-retrace requirement because intrabar order relative to the initial fill is unknown.
4. Search terminates if the original M2 terminal occurs before a valid confirmation.

## Confirmation rule
Once retrace is armed:
- the first completed 5m bar with `close > retrace_price` is the reclaim confirmation;
- the retrace-touch bar itself may also be the confirmation bar if its completed close is above the retrace price, because the bar low necessarily occurred before the completed close;
- no candle-color, body-size, EMA, volume, or other confirmation filter is allowed in M4.

## Executable entry
Entry is the **next raw 5m bar open** immediately after the completed reclaim bar.

The entry is valid only if:
- the reclaim bar itself is strictly before the original M2 terminal bar;
- the next-open bar exists inside the frozen execution window;
- next-open entry time is not after the original terminal bar.

If the next-open bar is the H2 terminal bar, entry at that bar open is valid because the open occurs before the later intrabar H2 event.

No entry price is inferred from OHLC order inside the confirmation bar.

## Outcome
The original corrected-M2 terminal remains frozen:
- `H2` = structural success after executable confirmation entry;
- `OPPOSITE`, `AMBIGUOUS`, or `NO_H2` = structural non-H2 outcome.

M4 does not alter terminal identity.

## Required outputs
For every habitat × initial level × retrace distance × partition and pooled-major:
- baseline corrected-M2 filled N;
- baseline H2 rate;
- retrace armed N/rate;
- reclaim confirmed N/rate;
- executable next-open entries N/rate;
- H2 N/rate among executable entries;
- H2-rate delta vs baseline;
- baseline-H2 winner capture rate;
- baseline failure rejection rate;
- median trigger-fill → entry minutes;
- median executable entry fraction `(entry_open-L)/R`;
- median entry improvement vs original trigger fraction `f - entry_fraction`;
- median entry → H2 minutes for H2 outcomes.

Persist one-row-per-candidate-per-distance audit file.

## Frozen screen
A habitat × initial level × D gets `SCREEN_PASS` only if:
1. every major partition has at least 20 executable entries;
2. pooled-major executable-entry availability is at least 40% of corrected-M2 fills;
3. pooled-major H2 rate is at least **3 percentage points above** its corrected-M2 baseline H2 rate;
4. no major partition H2 rate is more than 5 percentage points below its own corrected-M2 baseline;
5. pooled-major H2 rate is at least 75%.

No pooled-only rescue is allowed for the partition sample-size requirement.

## Ranking if multiple depths pass
Within each habitat × initial level, rank passing depths by:
1. highest pooled-major H2 rate;
2. then higher executable-entry N;
3. then shallower retrace distance.

This ranking is descriptive only. M4 does not promote a live strategy.

## Prohibited in M4
- TP / E20 / E20_DOWN;
- stop selection or optimization;
- F35/F65 invalidation promotion;
- candle body or EMA filters;
- fees, leverage, PnL, PF, expectancy;
- new clocks or new initial trigger levels;
- SHORT resurrection;
- M5 automatic execution.

## Mandatory assertions
1. Corrected M2 status gate passes.
2. M4 candidate universe equals corrected-M2 LONG `SCREEN_PASS` universe exactly.
3. Initial M2 fill identity is unchanged.
4. Retrace search begins only on the bar after initial fill.
5. Reclaim uses completed close only.
6. Entry is exactly next 5m open after reclaim.
7. Reclaim bar is strictly before terminal; entry may equal an H2 terminal bar open but never occur after terminal.
8. Original M2 terminal identity is unchanged.
9. Raw 5m coverage >=99.5%.
10. Synthetic tests verify same-bar retrace+reclaim, no initial-fill-bar retrace credit, and next-open-on-H2-bar chronology.

**Research only. Stop after M4 result persistence. No M5 automatic execution.**
