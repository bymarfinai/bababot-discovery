# SOL LONG H1 Early Invalidation — A6 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A6 changes only the parent pre-break exit. A4 H2 recovery is not used for Development selection.

## Central Development

| Lane | Triggers | Winners triggered | Losers triggered | Winner preserved | PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ | Gross-loss reduction | Blocks nonneg/adequate | Pass |
|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---|
| P30_D12 | 121 | 59 | 62 | 78.6% | 1.26→1.07 | $-240.21 | 1.12→0.93 | $-240.21 | $121.21 | 0/6 | NO |
| P30_D12_M07 | 91 | 43 | 48 | 84.4% | 1.26→1.19 | $-108.71 | 1.12→1.04 | $-108.71 | $130.86 | 2/6 | NO |
| P60_D22 | 69 | 30 | 39 | 89.1% | 1.26→1.16 | $-126.27 | 1.12→1.03 | $-126.27 | $22.51 | 1/6 | NO |
| P60_D22_M06 | 44 | 18 | 26 | 93.5% | 1.26→1.24 | $-34.78 | 1.12→1.10 | $-34.78 | $54.20 | 2/6 | NO |

## Decision

- Frozen lane: **NONE**.
- Validation: **No Development lane passed**.

**Status: SOL_LONG_H1_EARLY_INVALIDATION_A6_REJECTED**

If supported, the next stage must integrate the frozen early-invalidation rule with the frozen H2 recovery mechanism and recompute episode economics causally. If rejected, do not salvage it with OOS threshold retuning.

Research only. Live Baba Bot remains unchanged.
