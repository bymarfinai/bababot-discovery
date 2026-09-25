# SOL Donor Post-Shock Edge Extraction — Stage 4 Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION.**

## Purpose
Stage 3 showed that E0V1E / CCI_BB oversold entries do not survive BabaBot +1%/-1% first-hit execution. Stage 4 therefore treats donor signals only as **shock markers** and asks which causal post-shock states, observable by the next 1H open, distinguish TP-first from SL-first.

## OOS protection
- Only 2023 and 2024 may be used in Stage 4.
- 2023 = SEARCH.
- 2024 = INTERNAL VALIDATION.
- 2025 and 2026 are not scored, ranked, summarized, or inspected in Stage 4.
- Stage 5 remains the first external OOS test.

## Frozen execution
- Same donor signal implementation as Stage 3.
- Event population: UTC hours containing E0V1E OR CCI_BB signal.
- Decision time: next UTC 1H open.
- LONG only.
- One active position at a time.
- TP +1.00%; SL -1.00%.
- Same 5m candle TP+SL touch = SL first.
- Round-trip fee = 0.15%.
- No DCA / averaging / trailing / hold-until-recovery.
- Outcome labeling is capped at the end of its own calendar-year partition so SEARCH cannot use 2024 bars and INTERNAL VALIDATION cannot use 2025 bars.

## Frozen causal feature families
All are known at the decision time:
1. Donor identity/count: E0V1E, CCI_BB, overlap, within-hour signal counts.
2. Hour recovery geometry: 1H return, range, close-location-value, rebound from hour low, close distance from hour high, wick fractions.
3. Immediate follow-through: 5m/15m/30m return into entry; RSI/CCI recovery; EMA8 distance.
4. Post-last-shock path: minutes since last shock, close recovery, post-shock rebound, MFE, MAE.
5. Microstructure from completed 5m candles: rising closes/lows, close above prior 5m high.
6. Participation: last-15m volume versus preceding 45m normalized volume.
7. Context: completed 1H green state, prior 1H return, 1H EMA20 distance/slope, last fully completed 4H above EMA50.

## Frozen search procedure
- Numeric thresholds come only from SEARCH feature quantiles: 20%, 35%, 50%, 65%, 80%.
- For every threshold test both >= and <=.
- Boolean features test True and False.
- Evaluate rules with actual one-active-position execution.
- Univariate eligibility: >=1.0 trade/day and >=250 SEARCH trades.
- Rank eligible univariates by WR, then net expectancy, then trade/day; retain top 10.
- Evaluate pairwise AND rules using distinct features from those top 10.
- Pairwise eligibility: >=1.0 trade/day and >=250 SEARCH trades.
- Merge eligible univariate + pairwise rules and retain top 20 by SEARCH WR, then expectancy, then frequency.

## Frozen internal-validation promotion gate
A Stage-4 rule is promoted only if, in 2024:
- >=1.0 trade/day,
- WR >=60%,
- average net return after 0.15% fee > 0,
- WR deterioration from SEARCH <=7 percentage points.

If multiple rules pass, winner = highest 2024 WR, then SEARCH WR, then 2024 trade/day.
No threshold retuning after seeing 2024.
