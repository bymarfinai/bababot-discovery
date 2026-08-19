# BTC Tuesday A5.11 — Forward Shadow Status

**Status: READY — frozen model + end-to-end parity validated; awaiting first pristine forward Tuesday.**

**Research/shadow only. Live BBC untouched. No exchange orders are created.**

- Ledger rows: **0**
- Pending settlement: **0**
- Settled true-forward rows: **0**
- True-forward paper PnL: **$0.00**
- Frozen model fingerprint: `4b3227c5b8a2d4636725f6e079d4c6e2d0948f1f1627e93919f6ebfa3f59dc83`
- Model freeze parity: **PASS**
- End-to-end August implementation parity: **PASS**
- Scheduled snapshot: **Tuesday 06:00 WIB** (`Monday 23:00 UTC`)
- Scheduled settlement: **Tuesday 12:10 WIB** (`Tuesday 05:10 UTC`)
- First eligible new forward snapshot: **Tuesday, 2026-08-25 06:00 WIB**

Frozen observation stack:
- Tuesday A5.11 paper SELL, unchanged.
- G1 frozen current-state probabilities, telemetry only.
- G6 exact prior-168h weekly SELL health, telemetry only.
- G7 diagnostic weight, telemetry only.

Evidence controls:
- snapshot features are hard-capped at `T-5m` even if GitHub Actions starts late;
- snapshot fields are write-once;
- settlement is allowed only after the frozen 6h horizon;
- jobs are idempotent per Tuesday date;
- G1 is never retrained during the protocol;
- G1/G6/G7 telemetry cannot veto or resize the canonical A5.11 paper observation.

August 4/11/18 are parity fixtures and are not counted as new forward evidence.
