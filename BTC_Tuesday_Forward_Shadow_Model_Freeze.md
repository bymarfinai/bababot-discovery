# Tuesday A5.11 Forward Shadow — Frozen G1 Model State

**Status: PARITY PASS — eligible for immutable forward inference.**

- Training rows: **23,304**
- Cutoff: **2026-07-30 00:00:00+00:00**
- Frozen SELL prior: **44.1126%**
- Fingerprint: `4b3227c5b8a2d4636725f6e079d4c6e2d0948f1f1627e93919f6ebfa3f59dc83`
- sklearn at freeze: `1.9.0`

## August implementation parity
- pipeline vs serialized max abs diff: `1.110e-16`
- serialized vs G1 August max abs diff: `5.960e-10`
- weekly mean pSELL vs G6 August max abs diff: `5.551e-17`

This state is telemetry-only and must not be retrained during the forward protocol.
Live BBC is untouched.
