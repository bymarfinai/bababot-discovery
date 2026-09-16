# BNB B29-B2S — Live Shadow Operation Note

Scientific identity remains `B29-B2S-v1`; this note changes no scientific rule.

## Frozen prospective identity
- Shadow start: `2026-09-15T07:00:00Z` / 14:00 WIB.
- Frozen LONG character: `CONT_DOWN -> sweep_low_60 -> close_location>=0.50 -> body_range<0.33`.
- Frozen entry: `E0_EVENT_CLOSE`.
- Primary outcome: exact event-anchor +60m close-to-close direction.
- Frozen first-30 checkpoint: >=17 wins, positive median +60m return, >=8 wins in events 1-15, and >=8 wins in events 16-30.

## Feed operation
The first GitHub-runner attempt to use Binance USD-M Futures REST returned HTTP 451. This was a tooling/geographic-access failure before any scientific evaluation and therefore is not a B2S reject.

The repository workflow was changed tooling-only to consume Binance Vision USD-M Futures daily 5m archives. The first successful Vision run had complete data only through 2026-09-15 00:00 UTC, which is earlier than the prospective shadow start, so its zero-event ledger must not be interpreted as evidence that no post-freeze setup occurred.

For timely observation between Binance Vision archive publication times, a separate hourly live shadow check uses current Binance USD-M Futures BNBUSDT 5m market data with the exact same frozen B2S rule. It is permitted to surface newly detected events and newly matured +60m outcomes early. Canonical repository persistence is cross-checked against Binance Vision when the corresponding archive becomes available.

No pre-shadow-start event may be added. No character, entry, horizon, or checkpoint gate may be changed between live detection and canonical archive persistence. Any discrepancy between live and canonical data must be treated as an integrity issue, not silently reconciled by changing an outcome.

## Current scientific status
`BNB_B29_B2S_PROSPECTIVE_SHADOW_WARMUP`

The first-30 checkpoint has not been reached. No TP/SL discovery or live order is authorized yet.
