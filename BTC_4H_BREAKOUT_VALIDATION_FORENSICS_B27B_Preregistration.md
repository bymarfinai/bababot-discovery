# B27B Preregistration — 4H Breakout Validation Forensics

Purpose: explain why frozen B27A 4H previous-bar breakout performs materially worse in reference_validation than external/development. This is forensic diagnosis only, not a new trading rule and not a strategy optimization.

Frozen source setup: B27A 4H, R2. Entry/exit logic is not changed.

Primary comparison periods are the existing B27A partitions: external, development, reference_validation. Validation is additionally split by calendar year and quarter.

Diagnostics fixed before reading outputs:
1. Overall partition metrics.
2. Validation by year and quarter.
3. Validation by LONG vs SHORT.
4. Validation by stop-distance buckets: <1%, 1-1.5%, 1.5-2%, 2-3%, >=3%.
5. Validation by breakout-candle body-ratio buckets: <25%, 25-50%, 50-75%, >=75%.
6. Validation by breakout close extension beyond previous bar high/low, normalized by previous bar range: <10%, 10-25%, 25-50%, >=50%.
7. For validation losses, favorable excursion before exit in R units: fraction that reached >=0.5R and >=1R before eventual loss.

Metrics: N, WR, net PF, net expectancy/trade, total net. Existing B27A illustrative $500 notional and $0.40 fee convention is retained for comparability.

No thresholds from this forensic report may be treated as a validated filter. Any filter suggested by these results requires a new preregistered experiment.

Research only; live BBC unchanged.
