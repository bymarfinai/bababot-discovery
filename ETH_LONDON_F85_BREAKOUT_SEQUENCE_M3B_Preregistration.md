# ETH London F85 — Breakout Sequence Audit M3B

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Use the already-corrected ETH M2 London F85 cohort to answer two simple questions:

1. After the first High attack and the F85 pullback, on which numbered attack does ETH first confirm a breakout above the frozen London High?
2. After that confirmed breakout, does price continue immediately, retest the old High first and then continue, fall back into the range, or remain unresolved by the New York execution end?

This is one descriptive structural milestone only. It does not optimize entries, stops, targets, clocks, or filters.

## Frozen cohort
- Instrument: Binance USD-M ETHUSDT perpetual, raw 5-minute candles.
- Use only rows from the persisted corrected M2 candidate file `ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Candidates.csv` where:
  - habitat = `LONDON`;
  - side = LONG;
  - level = F85;
  - filled = true.
- The corrected M2 chronology is mandatory; the superseded +10-minute M2 chronology is forbidden.
- Frozen London reference: 08:00–13:30 UTC.
- Frozen New York execution: 13:30–20:00 UTC.
- Frozen reference High = H, Low = L, range R = H-L.
- F85 remains exactly `L + 0.85R`.
- No new clock, level, or filter may be introduced.

## Numbered High attacks
Attack numbering starts from the original first High-pressure episode that created the setup:
- Attack #1 = original first distinct High visit before the F85 pullback.
- After the F85 fill, the next distinct approach to High is Attack #2, then #3, #4, etc.

A distinct attack episode begins when, after at least one 5-minute bar away from High, a later bar either:
- touches High with `high >= H` while `close <= H`; or
- confirms breakout with `close > H`.

Consecutive High-touch bars are one attack episode. If a later bar in the same episode closes above H, the breakout belongs to that same attack number.

Confirmed breakout = first completed raw 5-minute candle with `close > H` after the F85 fill.
The breakout candle is not counted as an extra attack if it belongs to an already-open attack episode.

For every filled setup persist:
- breakout occurred or not by execution end;
- breakout attack number;
- breakout timestamp;
- minutes from F85 fill to breakout.

## Post-breakout path
Define `E20 = H + 0.20R` only as a fixed continuation checkpoint, not an optimized take-profit.

After the breakout is confirmed, classify exactly one path:

1. `E20_ON_BREAKOUT_BAR` — the breakout candle itself already has `high >= E20`.
2. `DIRECT_CONTINUATION` — on a later candle, E20 is reached before any retest of H.
3. `RETEST_THEN_CONTINUATION` — before E20, a later candle retests H (`low <= H`) but closes at/above H, and E20 is subsequently reached before any completed close below H.
4. `BACK_IN_RANGE_BEFORE_E20` — a completed candle closes below H before E20 is reached, whether or not a holding retest happened first.
5. `UNRESOLVED_BY_END` — none of the above resolves before the execution window ends.

For causality, all events after breakout are evaluated in chronological raw 5-minute order. On a single post-breakout candle where E20 is touched and the candle also closes below H, classify conservatively as `BACK_IN_RANGE_BEFORE_E20` because intrabar order is unknown. The exception is the breakout candle itself: if its high already reaches E20 it is reported separately as `E20_ON_BREAKOUT_BAR`.

## Outputs
Report by external, development, reference-validation, August, and pooled-major:
- F85 filled setups;
- breakout count and breakout rate;
- breakout distribution by Attack #2, #3, #4, #5, and #6+;
- no breakout by execution end;
- median minutes F85 fill to breakout;
- post-breakout path counts and percentages.

Persist one row per setup plus compact summary tables.

## Mandatory assertions
1. Input M2 status must equal `ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY`.
2. Every audited setup must exactly match one persisted corrected-M2 London F85 filled identity.
3. Attack #1 is historical setup identity and attack counting after F85 starts at #2.
4. Consecutive High-touch candles remain one attack episode.
5. A breakout within an already-open attack episode inherits that episode number.
6. Breakout requires completed 5-minute `close > H`.
7. Post-breakout classification uses no future information before the breakout close.
8. No clock, F-level, stop, filter, or runner is optimized.
9. Raw 5-minute coverage must remain at least 99.5%.

**Research only. Stop after this M3B result is persisted. Do not run M3/M4 automatically and do not modify live BBC.**
