# B27FA — BNB Hour-by-Hour Structural Discovery: 00:00 WIB

Status: PREREGISTERED BEFORE RESULT REVEAL

## Intent
Test one clock anchor at a time. B27FA evaluates only the 00:00 WIB anchor using a common structural template so later hourly milestones can be compared apples-to-apples. This milestone does not define or test an entry, TP, SL, PnL, repair mechanism, or live rule.

## Data partition
- Symbol: BNBUSDT
- Source: existing repository 5m historical loader
- Discovery partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC, exclusive
- Required 5m coverage: >=99.5%
- External, reference-validation, and August partitions remain unused.

## Frozen clock geometry
Timezone: Asia/Jakarta (WIB, UTC+7).

For each local calendar day:
- reference window: 00:00 <= t < 04:00 WIB
- execution window: 04:00 <= t < 08:00 WIB
- H = maximum 5m high in reference
- L = minimum 5m low in reference
- R = H-L

All seven weekdays are included because BNB trades continuously.

## Frozen LONG structural state machine
The state machine mirrors the causal B27EM K1/leave/H2 logic but is applied to this fixed clock geometry.

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

## Interpretation gate
This is structural discovery, not trading WR.

For later hour-to-hour comparison, label 00:00 WIB as:
- STRONG_STRUCTURAL if causal_leave >= 100 and H2_rate >= 70%
- PROMISING_STRUCTURAL if causal_leave >= 60 and H2_rate >= 65%
- otherwise WEAK_STRUCTURAL

The label is only a prioritization device for subsequent entry discovery. It cannot be described as a profitable setup.

## Stop rule
B27FA stops after the 00:00 WIB structural result is persisted. Do not test 01:00 WIB, do not invent an entry, and do not reveal holdout partitions in this milestone.
