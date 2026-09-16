# BNB B29-B2S — Prospective Event-Close Shadow Confirmation — Preregistration

## Scientific identity
`B29-B2S-v1`

B2S is a prospective confirmation phase for the frozen B1J character and the only B2-v1 entry mechanism that survived every development gate: `E0_EVENT_CLOSE`.

B2S does **not** change or rescue B2-v1. B2-v1 remains formally rejected because its frozen 2025+2026 reference hit was 56.96% versus a preregistered 57.00% gate. B2S asks whether the unchanged event-close behavior continues on observations that occur strictly after B2 was frozen.

No TP, SL, leverage, fees, dollar PnL, sizing, or live orders are authorized in B2S.

## Prospective start
The B2 evidence commit was created at 2026-09-15 06:45:05 UTC. To avoid boundary ambiguity, the first eligible decision timestamp is the next 15-minute grid point:

`SHADOW_START = 2026-09-15T07:00:00Z` (14:00 WIB)

No event before this timestamp may ever enter the B2S ledger or checkpoint statistics.

## Frozen character
Direction: **LONG**.

At completed 15-minute decision bar `t`:
1. Base event: `sweep_low_60 == 1` under frozen A1 semantics (bar trades below prior 60-minute low and closes back at/above it).
2. Same-family base-event cooldown: 60 minutes, applied to all causal `sweep_low_60` base events before character filtering.
3. At exact `t-15m`, `path_state == CONT_DOWN`:
   - `disp_atr_360 < -0.75`, and
   - `disp_atr_60 < -0.25`.
4. Event reclaim strength: `close_location >= 0.50`.
5. Event reclaim body: `body_range < 0.33`.

No hour, session, day, regime, or additional character clause is permitted.

## Frozen entry
`E0_EVENT_CLOSE` only.

Entry timestamp = event decision timestamp `t`, using the completed event-bar close conceptually as the market-entry reference. B2S evaluates direction only and does not model spread/slippage/fees yet.

Primary outcome = LONG close-to-close return from `t` to exact `t+60m`.
- WIN if return > 0.
- LOSS if return <= 0.
- PENDING until exact `t+60m` is fully closed.

Auxiliary outcomes are frozen at event-anchor +15, +30, +120, and +360 minutes for diagnostics only. They cannot change B2S promotion status.

## Market data policy
For prospective observations, use Binance USD-M Futures `BNBUSDT` 5-minute klines fetched after the B2 freeze.

The engine must:
- fetch enough prehistory to compute A1 features causally;
- ignore the still-open 5-minute bar;
- use the exact B29-A1 feature implementation for structure/path/liquidity semantics;
- require exact 5-minute continuity through every feature and outcome window;
- never backfill an event from before `SHADOW_START`;
- deduplicate events by event timestamp;
- persist first-seen timestamp and never rewrite an already-matured historical outcome unless a tooling/data-integrity correction is explicitly documented.

A fresh prospective exchange feed is intentionally allowed here. The immutable A1 artifact remains the historical source identity, while B2S must observe genuinely new bars that did not exist at the time B2 was frozen.

## Fixed primary checkpoint
B2S remains `WARMUP` until **30 matured character events** have accumulated.

At the first run where matured N reaches or exceeds 30, freeze the **first 30 matured events by event timestamp** as the primary B2S checkpoint. Later observations cannot alter this primary checkpoint verdict.

### PASS / promote to B3
The first-30 checkpoint is `PASS` only if all are true:
- wins >= 17 / 30 (>=56.67%);
- median signed +60m return > 0;
- first 15 events have >=8 wins;
- second 15 events have >=8 wins;
- no data-integrity failure or duplicate event timestamps.

Status: `BNB_B29_B2S_PROSPECTIVE_SHADOW_PASS`.

A PASS only promotes the frozen character + event-close entry to historical TP/SL discovery (B3). It is not READY TO TRADE.

### REJECT
If the first-30 checkpoint fails any PASS gate, status becomes:

`BNB_B29_B2S_PROSPECTIVE_SHADOW_REJECT`.

Do not retune the character or entry after that result.

### Before 30 matured events
Status:

`BNB_B29_B2S_PROSPECTIVE_SHADOW_WARMUP`.

The report may show descriptive hit rate, pending events, and signed returns, but no early PASS may be declared.

## Ongoing ledger
After the primary checkpoint freezes, continue appending later prospective events as monitoring evidence, but never revise the frozen first-30 verdict.

## Stop rule
Do not rescue B2S-v1 by:
- changing the 30-event checkpoint;
- changing 17/30 to a lower win count;
- changing first-half/second-half gates;
- adding filters or excluding inconvenient events;
- changing the +60m primary outcome;
- modifying the B1J character or E0 event-close entry;
- proceeding to TP/SL before B2S PASS.

No live orders are authorized by B2S.