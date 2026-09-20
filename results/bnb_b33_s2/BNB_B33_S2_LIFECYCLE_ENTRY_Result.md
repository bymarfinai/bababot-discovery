# BNB B33-S2 — Lifecycle-Phase Entry Discovery Result

**Status: BNB_B33_S2_NO_ENTRY_PASSED**

B33-S1 lifecycle detectors are frozen. No economics was simulated.

## Canonical evidence
- S2 science run: `35484684738`
- Head: `d9a194cac0fcff867ed415a7c5978b8a6cab7cec`
- Artifact: `10596963672`
- Artifact SHA256: `7833df4b3065c4ddc75fd05aadf79487e78e96efcd64fcdfddc503bb61e1c4f7`
- Science step and artifact upload: **SUCCESS**
- Runner persistence collided with a concurrent branch advance; canonical compact evidence is persisted here.

## Integrity
- Raw rows: **506,880**
- Coverage: **100.000000%**
- Raw SHA256: `35831265b8520ad286834b44cd63594fed3413f51d0ee30497c93b83e1fe88d8`
- A1 ret15 max diff: **9.99634403032e-17**
- A1 close-location max diff: **1.11022302463e-16**
- All 16 B33-S1 parent detector counts matched.

## Result
No lifecycle phase produced a preregistered entry policy that passed the frozen 2022-2024 development gate.

- Development PASS: **0/16**
- 2025-2026 reference opened: **0/16**
- Eligible for B33-S3 economics: **0/16**

## Strongest development policy per phase

| Detector | Phase | Side | Entry | N | +60 hit | Wilson LCB | Worst era | +30 | +120 |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| F1LE | EARLY | LONG | Native-level retest | 3,014 | **54.05%** | **52.26%** | **52.36%** | 52.95% | 52.29% |
| F1LM | MATURE | LONG | Pullback reclaim | 1,126 | 53.02% | 50.10% | 49.71% | 50.53% | 51.78% |
| F2LE | EARLY | LONG | Native-level retest | 2,222 | 51.89% | 49.81% | 50.71% | 49.95% | 49.86% |
| F2LM | MATURE | LONG | Native-level retest | 323 | 51.70% | 46.27% | 50.00% | 48.92% | 49.54% |
| F3LE | EARLY | LONG | Phase-mid retest | 501 | 49.10% | 44.75% | 45.24% | 48.50% | 47.50% |
| F3LM | MATURE | LONG | Phase-extreme break | 237 | 51.05% | 44.72% | 45.95% | 50.63% | 47.68% |
| F4LE | EARLY | LONG | Native-level retest | 1,480 | 53.04% | 50.49% | 49.80% | 53.18% | 52.70% |
| F4LM | MATURE | LONG | Pullback reclaim | 1,527 | 53.24% | 50.73% | 50.79% | 53.18% | 53.05% |
| F1SE | EARLY | SHORT | Native-level retest | 3,143 | 50.91% | 49.16% | 50.00% | 50.18% | 49.60% |
| F1SM | MATURE | SHORT | Native-level retest | 393 | 50.38% | 45.46% | 48.72% | 47.84% | 51.65% |
| F2SE | EARLY | SHORT | Phase-mid retest | 3,179 | 47.72% | 45.99% | 46.62% | 46.05% | 46.40% |
| F2SM | MATURE | SHORT | Follow-through displacement | 982 | 48.47% | 45.36% | 46.29% | 48.37% | 47.35% |
| F3SE | EARLY | SHORT | Native-level retest | 417 | 46.04% | 41.32% | 42.96% | 47.72% | 45.56% |
| F3SM | MATURE | SHORT | Native-level retest | 206 | 47.57% | 40.86% | 46.48% | 47.57% | 47.57% |
| F4SE | EARLY | SHORT | Phase-mid retest | 1,597 | 49.72% | 47.27% | 48.37% | 47.59% | 49.78% |
| F4SM | MATURE | SHORT | Phase-mid retest | 989 | 50.46% | 47.34% | 48.82% | 47.93% | 48.13% |

## Lifecycle interpretation
The clearest EARLY improvement is F1 LONG:
- EARLY native-level retest: **54.05%**
- MATURE best policy: **53.02%**

But the EARLY result still fails the frozen pooled **55%** hit gate. It also fails the auxiliary requirement because neither +30 nor +120 reaches **53%**.

Other families do not show a consistent EARLY advantage:
- F2 LONG remains around 52% or lower.
- F3 LONG is not improved by moving earlier.
- F4 LONG is about 53% in both phases, with MATURE slightly higher.
- SHORT phases are mostly near/below 50%.

## Decision
**BNB_B33_S2_NO_ENTRY_PASSED**

The hypothesis that full structure confirmation is systematically too late is not supported strongly enough under B33. No B33 economics is authorized.
