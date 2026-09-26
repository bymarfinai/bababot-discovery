# SOL Indicator Relationship Discovery — Stage 4C Result

**High 24h location only; exact Stage 4 DEV tertiles reused.**

| Context | Partition | OI HIGH N | OI HIGH L/S | OI LOW N | OI LOW L/S | delta-D | Class |
|---|---|---:|---:|---:|---:|---:|---|
| High-location + Taker BUY high | development | 5317 | 47.4%/40.5% | 1010 | 36.1%/50.0% | 20.8% | REPLICATED_CONDITIONAL |
| High-location + Taker BUY high | validation_2025 | 2250 | 46.6%/38.0% | 738 | 29.5%/52.6% | 31.6% | REPLICATED_CONDITIONAL |
| High-location + Taker BUY high | validation_2026 | 1399 | 41.0%/30.1% | 594 | 28.1%/39.6% | 22.4% | REPLICATED_CONDITIONAL |
| High-location + Taker SELL high | development | 986 | 51.3%/36.2% | 3783 | 43.5%/42.5% | 14.1% | REPLICATED_CONDITIONAL |
| High-location + Taker SELL high | validation_2025 | 756 | 49.9%/35.1% | 1862 | 34.7%/47.0% | 27.2% | REPLICATED_CONDITIONAL |
| High-location + Taker SELL high | validation_2026 | 397 | 51.4%/24.7% | 1078 | 28.9%/36.4% | 34.1% | REPLICATED_CONDITIONAL |

## Interpretation guardrail

The contrast isolates whether OI expansion vs contraction changes directional outcome while both price location and taker state are held fixed.
It does not yet establish temporal causality; sequence ordering remains Stage 5A.

**Status: SOL_INDICATOR_RELATIONSHIP_S4C_COMPLETED**
