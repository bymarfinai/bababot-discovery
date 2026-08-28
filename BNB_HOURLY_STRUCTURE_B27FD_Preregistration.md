# B27FD — BNB Hour-by-Hour Structural Discovery: 03:00 WIB

Status: PREREGISTERED BEFORE RESULT REVEAL

## Intent
Continue the one-clock-at-a-time BNB structural search. B27FD evaluates only the 03:00 WIB anchor using the exact same structural template as B27FA/B27FB/B27FC so the clocks can be compared apples-to-apples. This milestone does not define or test an entry, TP, SL, PnL, repair mechanism, or live rule.

## Data partition
- Symbol: BNBUSDT
- Source: existing repository 5m historical loader
- Discovery partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC, exclusive
- Required 5m coverage: >=99.5%
- External, reference-validation, and August partitions remain unused.

## Frozen clock geometry
Timezone: Asia/Jakarta (WIB, UTC+7).

For each local calendar day:
- reference window: 03:00 <= t < 07:00 WIB
- execution window: 07:00 <= t < 11:00 WIB
- H = maximum 5m high in reference
- L = minimum 5m low in reference
- R = H-L

All seven weekdays are included because BNB trades continuously.

## Frozen LONG structural state machine
Use the exact causal B27EM/B27FA/B27FB/B27FC K1/leave/H2 logic.

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
Pooled and weekday breakdowns must report:
- complete sessions
- K1 qualified count/rate
- causal leave count/rate
- H2 arrivals
- opposite breaks before H2
- ambiguous H2/opposite events
- no-H2-by-end
- H2 / causal-leave rate
- resolved H2 share = H2 / (H2 + opposite break), excluding ambiguous/no-event
- median minutes leave->H2 among H2 arrivals

## Frozen benchmark
Prior completed clocks:
- B27FA / 00:00 WIB: 137 causal leaves, 105 H2, H2/leave 76.6%
- B27FB / 01:00 WIB: 162 causal leaves, 132 H2, H2/leave 81.5%
- B27FC / 02:00 WIB: 162 causal leaves, 126 H2, H2/leave 77.8%

The current structural leader before B27FD reveal is 01:00 WIB.

## Interpretation gate
This is structural discovery, not trading WR.

Label 03:00 WIB as:
- STRONG_STRUCTURAL if causal_leave >= 100 and H2_rate >= 70%
- PROMISING_STRUCTURAL if causal_leave >= 60 and H2_rate >= 65%
- otherwise WEAK_STRUCTURAL

The label is only a prioritization device for subsequent entry discovery. It cannot be described as a profitable setup.

## Stop rule
B27FD stops after the 03:00 WIB structural result is persisted. Do not test 04:00 WIB, do not invent an entry, and do not reveal holdout partitions in this milestone.
