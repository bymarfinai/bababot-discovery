# SOL Indicator Relationship Discovery — Stage 7H-A Source Audit

**True price-level L2 feasibility; no trading outcomes read.**

| Date | HTTP | Compressed | Schema | Snapshot | Bid+Ask | Replay | Rows sampled |
|---|---:|---:|---|---|---|---|---:|
| 2023-01-01 | 200 | 86,225,972 | PASS | YES | YES | PASS | 3,532 |
| 2024-01-01 | 200 | 382,367,838 | PASS | YES | YES | PASS | 11,261 |
| 2025-01-01 | 200 | 167,457,270 | PASS | YES | YES | PASS | 7,000 |
| 2026-01-01 | 200 | 126,625,962 | PASS | YES | YES | PASS | 4,953 |
| 2026-09-01 | 200 | 200,060,578 | PASS | YES | YES | PASS | 3,050 |

Sample replay gate: **PASS**.

## Access gate

- Tardis key configured: **YES**
- Authenticated non-sample Tardis day accessible: **NO**
- Binance API key configured: **YES**
- Binance API secret configured: **YES**

Credential values are never printed or persisted.

## Decision

**REPLAY FEASIBILITY: PASS; FULL-HISTORY ACCESS: NOT AVAILABLE IN THIS WORKFLOW.**
The source/schema is valid, but free first-of-month samples cannot be used as a substitute for DEV→2025→2026 full-history testing.

**Status: SOL_INDICATOR_RELATIONSHIP_S7H_A_REPLAY_FEASIBLE_ACCESS_REQUIRED**
