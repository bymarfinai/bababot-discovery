# SOL LONG Visit-Break Anatomy — A1 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A1 asks only: **which distinct High visit becomes the upside breakout?** No entry, stop, TP, PnL, leverage, or fees are used.

Development habitat cells scanned: **216** = 9 references × 24 UTC clocks.
Topology-supported cells: **153**.

## Frozen Development structure

- Reference: **R240**.
- Execution start: **18:00 UTC**.
- Dominant breakout visit: **H2**.
- Same H2 dominant in **5/6** Development half-year blocks.
- H2 opportunity N: **173**.
- H2 breakout conversion: **74.0%**.
- Median post-break extension before reclaim: **0.208R**.

## H1-H5 anatomy at the frozen Development habitat

| Visit | Opportunity N | First-break N | Break conversion | Median extension | Reclaim <=30m |
|---|---:|---:|---:|---:|---:|
| H1 | 617 | 406 | 65.8% | 0.224R | 56.7% |
| H2 | 173 | 128 | 74.0% | 0.208R | 60.9% |
| H3 | 38 | 22 | 57.9% | 0.204R | 63.6% |
| H4 | 13 | 8 | 61.5% | 0.105R | 62.5% |
| H5 | 4 | 2 | 50.0% | 0.315R | 50.0% |

## OOS central confirmation

| Partition | Dominant visit | H-selected opportunity | Break conversion | Median extension |
|---|---:|---:|---:|---:|
| External | H1 | 50 | 70.0% | 0.165R |
| Reference Validation | H1 | 84 | 63.1% | 0.137R |

## Topology support

- Frozen clock support: **17:00 UTC / R240**.
- Frozen reference support: **R180 / 18:00 UTC**.
- Clock support preserves H2 in both OOS partitions: **NO**.
- Reference support preserves H2 in both OOS partitions: **NO**.

## Decision

**Status: SOL_LONG_VISIT_BREAK_A1_FAILED_OOS**

Development identified H2, but the exact visit-order structure did not survive every frozen OOS/topology gate. Do not proceed to entry optimization from this candidate without a new preregistered structural hypothesis.

Research only. Live Baba Bot remains unchanged.
