# B27FH — BNB Hourly Structural Sweep Batch: 10:00–13:00 WIB

Status: PREREGISTERED BEFORE ANY B27FH RESULT REVEAL

## Intent
Continue the frozen BNB hour-by-hour structural discovery as one preregistered four-clock batch. B27FH evaluates exactly 10:00, 11:00, 12:00, and 13:00 WIB using the same causal structural template as B27FA–B27FG. All four clocks are fixed before any B27FH result is generated or inspected.

This milestone does not define or test an entry, TP, SL, PnL, repair mechanism, weekday filter, or live rule.

## Data partition
- Symbol: BNBUSDT
- Source: existing repository 5m historical loader
- Discovery partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC, exclusive
- Required 5m coverage: >=99.5%
- External, reference-validation, August, and other holdout partitions remain unused.

## Frozen clocks
Timezone: Asia/Jakarta (WIB, UTC+7).

For each anchor A in {10:00, 11:00, 12:00, 13:00} WIB and each local calendar day:
- reference window: A <= t < A+4h
- execution window: A+4h <= t < A+8h
- H = maximum 5m high in reference
- L = minimum 5m low in reference
- R = H-L

Thus:
- 10:00: reference 10:00–14:00, execution 14:00–18:00 WIB
- 11:00: reference 11:00–15:00, execution 15:00–19:00 WIB
- 12:00: reference 12:00–16:00, execution 16:00–20:00 WIB
- 13:00: reference 13:00–17:00, execution 17:00–21:00 WIB

All seven weekdays are included because BNB trades continuously. No clock or weekday may be removed after results are revealed.

## Frozen LONG structural state machine
Use the exact causal B27EM/B27FA–B27FG K1/leave/H2 logic.

SEEK_K1:
- close > H or close < L before K1 => BREAK_BEFORE_K1
- H structural visit: high >= H and close <= H
- L structural visit: low <= L and close >= L
- simultaneous H+L event => AMBIGUOUS_BOTH_BOUNDARIES
- K1 qualifies only when the first H visit occurs with zero prior L visits
- k1_signal timestamp is the end of the completed 5m K1 candle

K1_EPISODE:
- while high >= H and close <= H, remain in the same K1 episode
- first completed candle that is not part of the same H episode is the causal leave
- leave_ts is the end of that completed 5m candle

AFTER_LEAVE:
- H2 arrival: high >= H
- opposite structural break: close < L
- if both occur on the same 5m candle => AMBIGUOUS_H2_VS_OPPOSITE_BREAK
- if neither occurs by execution-window end => NO_H2_BY_END

No same-bar favorable ordering is assumed.

## Frozen outputs
For every anchor and pooled comparison, report complete sessions, K1 qualified count/rate, causal leaves, H2 arrivals, opposite breaks, ambiguous events, no-H2-by-end, H2/causal-leave rate, resolved H2 share, and median minutes leave->H2. Also persist per-anchor weekday breakdowns.

## Frozen benchmark before B27FH
Completed clocks:
- 00:00 WIB: 137 causal leaves, 105 H2, H2/leave 76.6%
- 01:00 WIB: 162 causal leaves, 132 H2, H2/leave 81.5%
- 02:00 WIB: 162 causal leaves, 126 H2, H2/leave 77.8%
- 03:00 WIB: 142 causal leaves, 96 H2, H2/leave 67.6%
- 04:00 WIB: 142 causal leaves, 108 H2, H2/leave 76.1%
- 05:00 WIB: 141 causal leaves, 94 H2, H2/leave 66.7%
- 06:00 WIB: 148 causal leaves, 104 H2, H2/leave 70.3%
- 07:00 WIB: 149 causal leaves, 114 H2, H2/leave 76.5%
- 08:00 WIB: 143 causal leaves, 113 H2, H2/leave 79.0%
- 09:00 WIB: 161 causal leaves, 118 H2, H2/leave 73.3%

Current structural leader before B27FH reveal: 01:00 WIB at 81.5% H2/leave.

## Frozen interpretation gate
These are structural outcomes, not trading WR.

For each of 10:00–13:00 independently:
- STRONG_STRUCTURAL if causal_leave >= 100 and H2_rate >= 70%
- PROMISING_STRUCTURAL if causal_leave >= 60 and H2_rate >= 65%
- otherwise WEAK_STRUCTURAL

The labels are prioritization devices only and cannot be described as profitable setups.

## Anti-adaptation rule
All four clocks must run from this same preregistration and same code path. Do not change state-machine logic, thresholds, dataset, weekdays, or output definitions after seeing an earlier clock in this batch.

## Stop rule
B27FH stops after results for exactly 10:00, 11:00, 12:00, and 13:00 WIB are persisted and compared with the frozen 00:00–09:00 benchmark. Do not test 14:00 WIB or later, do not define an entry, and do not reveal holdout partitions in this milestone.
