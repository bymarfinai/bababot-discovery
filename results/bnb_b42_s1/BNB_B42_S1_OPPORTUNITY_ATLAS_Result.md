# BNB B42-S1 — 1% Opportunity Atlas Result

**Status: BNB_B42_S1_OPPORTUNITY_ATLAS_READY**

Signature: `ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd`

## Integrity
- vectorbt: **1.1.0**
- 5m rows: **498,240**, coverage **100.000000%**
- normalized raw SHA256: `95ad73ce949a6e622a1b7e120eeaa23d853de2a0f4cd9c6f1533b20c37ee2334`
- decision timestamps: **163,009**
- directional candidates: **326,018**

## Daily opportunity supply

| Period | Days | >=1 WIN day | >=1 LONG | >=1 SHORT | Q25 wins/day | Median | Q75 | >=5/day | >=10/day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 1699 | 98.76% | 95.59% | 94.88% | 71.0 | **92.0** | 96.0 | 98.06% | 97.00% |
| DEV | 1096 | 98.72% | 95.53% | 95.44% | 77.0 | **94.0** | 96.0 | 97.99% | 97.17% |
| REF | 603 | 98.84% | 95.69% | 93.86% | 65.0 | **87.0** | 96.0 | 98.18% | 96.68% |

## Directional candidate outcomes

| Period | Side | Outcome | N |
|---|---|---|---:|
| DEV | LONG | AMBIGUOUS | 26 |
| DEV | LONG | LOSS | 45,963 |
| DEV | LONG | TIMEOUT | 15,872 |
| DEV | LONG | WIN | 43,355 |
| DEV | SHORT | AMBIGUOUS | 26 |
| DEV | SHORT | LOSS | 43,355 |
| DEV | SHORT | TIMEOUT | 15,872 |
| DEV | SHORT | WIN | 45,963 |
| REF | LONG | AMBIGUOUS | 4 |
| REF | LONG | LOSS | 23,010 |
| REF | LONG | TIMEOUT | 12,036 |
| REF | LONG | WIN | 22,743 |
| REF | SHORT | AMBIGUOUS | 4 |
| REF | SHORT | LOSS | 22,743 |
| REF | SHORT | TIMEOUT | 12,036 |
| REF | SHORT | WIN | 23,010 |

## Interpretation
- S1 measures *opportunity existence*, not predictability.
- A WIN means a causal next-5m-open entry had +1% touched before -1% within 12h.
- No hindsight-selected setup is promoted from S1.

## Decision
**BNB_B42_S1_OPPORTUNITY_ATLAS_READY**

Movement supply is sufficient. Advance to B42-S2 fingerprint discovery with frozen S1 labels.
