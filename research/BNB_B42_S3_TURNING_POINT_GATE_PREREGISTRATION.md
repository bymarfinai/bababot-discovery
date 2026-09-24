# BNB B42-S3 — Causal Turning-Point Event Gate Preregistration

## Objective

Reduce the B42-S1 every-15-minute universe to causal price-location events that can plausibly mark a turning point before applying any classifier.

Parent facts frozen before S3:
- B42-S1 proves +1%/-1% movement supply exists on 98.76% of days.
- B42-S2 generic every-candle OHLCV/indicator classifier failed (2024 WR 45.17%, REF WR 44.16%).
- Therefore S3 tests event-location gating, not more generic threshold tuning.

No S2 REF result is used to tune S3 event definitions.

## Parent label

Use B42-S1 labels unchanged:
- decision = completed 15m timestamp;
- entry = next 5m open;
- TP = +1%;
- SL = -1%;
- horizon = 12h;
- WIN when TP is first touched before SL;
- LOSS when SL first;
- AMBIGUOUS conservative non-win;
- TIMEOUT neither.

## Frozen event families

Exactly three symmetric turning-point concepts, six directional families.

### E1/E2 — Causal Q80 expected-range wall reclaim/reject

For each UTC day:
- use only the prior 60 completed UTC days;
- daily upper excursion = high/open - 1;
- daily lower excursion = 1 - low/open;
- current-day projected upper wall = current UTC-day open × (1 + prior60 Q80 upper excursion);
- current-day projected lower wall = current UTC-day open × (1 - prior60 Q80 lower excursion).

LONG E1:
- completed 15m low <= lower wall;
- completed 15m close > lower wall.

SHORT E2:
- completed 15m high >= upper wall;
- completed 15m close < upper wall.

Only the first qualified event per side per UTC day is retained.

### E3/E4 — Confirmed swing sweep reclaim/reject

Use the already-causal B31 15m 2-left/2-right confirmed swing convention.

LONG E3:
- current completed 15m low sweeps below last confirmed swing low;
- current close reclaims at/above that swing level.

SHORT E4:
- current high sweeps above last confirmed swing high;
- current close rejects at/below that swing level.

60-minute same-family cooldown.

### E5/E6 — Prior-24h extreme sweep reclaim/reject

Prior 24h extreme excludes the current bar and uses the previous 96 completed 15m bars.

LONG E5:
- current low < prior-24h low;
- current close >= prior-24h low.

SHORT E6:
- current high > prior-24h high;
- current close <= prior-24h high.

60-minute same-family cooldown.

## Frozen confluence family

C2PLUS:
- same completed 15m decision timestamp;
- same direction;
- at least two distinct concepts among Q80, SWING, PRIOR24H trigger simultaneously.

No weighted score and no after-the-fact selection of combinations.

## Outcome metrics

For every family and C2PLUS, report separately for:
- DEV 2022-2024;
- REF 2025-2026 through 2026-08-26;
- each calendar year.

Metrics:
- N;
- events per 365 days;
- unique event days and event-days share;
- WIN / LOSS / TIMEOUT / AMBIGUOUS counts;
- WIN rate over all events (WIN/N);
- resolved WR = WIN/(WIN+LOSS+AMBIGUOUS), TIMEOUT excluded only as descriptive;
- mean realized R using S2 convention:
  - WIN +1R;
  - LOSS -1R;
  - AMBIGUOUS -1R;
  - TIMEOUT signed 12h return divided by 1%, clipped [-1,+1].
- median first-touch minutes for WIN and LOSS.

## Robust event-candidate gate

Standalone E1-E6 is nominated only if all hold:
- DEV N >=150;
- REF N >=75;
- DEV WIN rate >=55%;
- REF WIN rate >=52%;
- DEV mean realized R >0;
- REF mean realized R >0;
- at least 4 of 5 calendar years have WIN rate >=50%.

C2PLUS uses smaller sample gates:
- DEV N >=75;
- REF N >=40;
- same WR/R/year robustness requirements.

Status:
- >=1 nominated family: `BNB_B42_S3_TURNING_POINT_GATE_READY`
- none: `BNB_B42_S3_NO_ROBUST_TURNING_POINT_EVENT`

Passing S3 does not validate an 80% strategy. Nominated events may advance to S4 event-only ranking/confirmation.
