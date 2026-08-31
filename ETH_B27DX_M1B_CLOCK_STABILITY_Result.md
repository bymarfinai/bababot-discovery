# ETH B27DX V2 — M1B Clock / Habitat Stability — Result

ETH raw 5m coverage: **100.0000%**.

M1B changes execution clock only: 14:00–18:00 UTC in frozen 30-minute steps. All M1 diagnostic economics remain unchanged.

| UTC clock | Dev + probes | Dev median PF | Dev median expectancy | External + probes | Validation + probes | Supported |
|---:|---:|---:|---:|---:|---:|---|
| 14:00 | 0/3 | 0.80 | -0.52 | 0/3 | 0/3 | NO |
| 14:30 | 0/3 | 0.57 | -1.22 | 1/3 | 3/3 | NO |
| 15:00 | 0/3 | 0.92 | -0.18 | 2/3 | 1/3 | NO |
| 15:30 | 3/3 | 2.01 | 1.05 | 2/3 | 1/3 | NO |
| 16:00 | 2/3 | 1.30 | 0.58 | 2/3 | 3/3 | YES |
| 16:30 | 3/3 | 1.30 | 0.62 | 2/3 | 0/3 | NO |
| 17:00 | 1/3 | 0.94 | -0.13 | 2/3 | 0/3 | NO |
| 17:30 | 1/3 | 1.09 | 0.17 | 0/3 | 0/3 | NO |
| 18:00 | 1/3 | 0.95 | -0.10 | 1/3 | 0/3 | NO |

## Anchor-local contiguous run

Supported run containing 16:00 UTC: **16:00**.
Contiguous first-to-last width: **0 minutes**.
Number of consecutive supported 30-minute clock points: **1**.

**Status: ETH_M1B_ANCHOR_SUPPORTED_BUT_ISOLATED**

Interpretation: 16:00 remains economically supported but does not satisfy the preregistered contiguous-width gate. Do not treat it as a stable temporal habitat yet.

August remains diagnostic only and did not affect support.
Research only. No exchange writes and no live BBC changes.
