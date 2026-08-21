# BTC Weekly W1 VAH True Microstructure R1 — Preflight

**Status: BLOCKED_DATA_ACCESS**

Market: `binance`  
Instrument: `BTC-USDT-VANILLA-PERPETUAL`  
Probe window: **5 minutes** before entry  
Requested L2 depth: **1000**

This is an access/coverage probe only. Candidate outcomes were not inspected.

## Message

COINDESK_API_KEY is not configured

## Interpretation

- `PREFLIGHT_PASS` means the configured account/instrument returned usable L2 replay and tick trades across the sampled historical dates. It is **not** a strategy result.
- `BLOCKED_DATA_ACCESS` means credentials, role, instrument mapping, or entitlement must be fixed before research can run.
- `BLOCKED_DATA_COVERAGE` means the source did not return required L2/trade data for at least one sampled historical period.
- Full >=90% per-partition coverage is still required by the preregistration before label analysis.
