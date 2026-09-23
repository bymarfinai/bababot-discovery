# SOL Options Wall Control Test V1 — Result

**Status: CONTROL_SAMPLE_ACCUMULATING**

## Confirmatory sample started

- Frozen control cutoff: **2026-09-23T04:52:00Z**
- First confirmatory anchor: **2026-09-23T04:52:39.000Z**
- Snapshot: `SOL_OPT_V1_20260923045239000`
- Anchor spot: **119.52769434**
- Forward horizon: **240 minutes**
- Current anchor state: **CENSORED / accumulating**
- Completed rank-1 60-minute touches: **0**

## Frozen candidate levels at anchor #1

| Side | OPTIONS | RANDOM_MATCHED | ROUND_5 | PRICE_PIVOT_1H |
|---|---:|---:|---:|---:|
| Lower rank 1 | 116.00 | 115.85 | 115.00 | 117.85 |
| Lower rank 2 | 112.00 | 110.73 | 110.00* | 117.62 |
| Lower rank 3 | 110.00 | 112.36 | 105.00 | 116.68 |
| Upper rank 1 | 120.00 | 119.85 | 120.00* | 119.99 |
| Upper rank 2 | 130.00 | 134.37 | 125.00 | NA |
| Upper rank 3 | 140.00 | 133.60 | 130.00* | NA |

`*` ROUND_5 overlaps an OPTIONS strike and therefore cannot independently establish options-specific information.

## Primary future test

Primary endpoint remains:

`NET_REACTION_60 = MFE_60 - MAE_60`

Primary comparison:
- OPTIONS rank 1
- versus RANDOM_MATCHED rank 1.

PRICE_PIVOT_1H rank 1 is the structural price-only benchmark.

ROUND_5 is diagnostic because round-number overlap with options strikes is retained rather than hidden.

## Sample gate

No conclusion is promoted until at least:

- 20 confirmatory OPTIONS rank-1 touches;
- 20 confirmatory RANDOM_MATCHED rank-1 touches;
- 10 confirmatory PRICE_PIVOT_1H rank-1 touches;
- 10 independent anchors.

The known 2026-09-22 touch at 116 remains exploratory only and contributes zero weight to the confirmatory control test.

No READY_TO_TRADE conclusion is permitted from this test alone.
