# BNB B29-B2S — Prospective Event-Close Shadow Result

**Status: BNB_B29_B2S_PROSPECTIVE_SHADOW_WARMUP**

B2S observes only new post-freeze BNB character events using the frozen B1J character and E0 event-close entry. No TP/SL, leverage, fees, sizing, dollar PnL, or live orders are included.

## Frozen identity

- Shadow start: `2026-09-15T07:00:00+00:00`
- Direction: LONG
- Character: `CONT_DOWN -> sweep_low_60 -> close_location>=0.50 -> body_range<0.33`
- Entry: event close (`E0_EVENT_CLOSE`)
- Primary outcome: exact event-anchor +60m close-to-close return
- Primary checkpoint: first 30 matured events; PASS requires >=17 wins, positive median +60m return, and >=8 wins in each 15-event half.

## Prospective data integrity

- Raw source: Binance USD-M Futures REST `BNBUSDT` 5m
- Raw rows: 288
- Raw span: 2026-09-14T00:00:00+00:00 -> 2026-09-15T00:00:00+00:00
- Raw coverage: 100.000000%
- Raw gaps: 0
- Integrity errors: 0

## Shadow ledger

- Total character events: 0
- Matured +60m events: 0 / 30 required
- Pending events: 0

## Current decision

**BNB_B29_B2S_PROSPECTIVE_SHADOW_WARMUP**

Continue prospective collection unchanged. Do not tune character/entry or proceed to TP/SL before the first-30 checkpoint passes.

No live orders were placed.
