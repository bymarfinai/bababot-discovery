# SOL Long Leg Onset V2 — Verified Result

Run ID: 35953233376
Head SHA: 7e801bfe9414695e36b159075b19f49f8ad4eb88
Status: SUCCESS
5m coverage: 99.76977%
Ex-post 1% reversal long legs: 4,430

Training label:
- first 25% of L2/L3/L5 leg amplitude
- fit on 2023 only
- threshold selected on 2024
- frozen transfer to 2025 and 2026

## Frozen transfer

| Target | Partition | WR | Trades/wk | Exp/trade | Mean weekly net | Median weekly net | Leg hit | Early hit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| L2 | 2024 | 36.24% | 4.32 | -0.063% | -0.27% | 0.00% | 7.7% | 7.5% |
| L2 | 2025 | 34.95% | 3.51 | -0.102% | -0.36% | 0.00% | 6.0% | 5.7% |
| L2 | 2026 | 46.27% | 1.91 | +0.305% | +0.58% | 0.00% | 7.1% | 6.7% |
| L3 | 2024 | 30.33% | 3.98 | +0.063% | +0.25% | +0.50% | 10.3% | 8.9% |
| L3 | 2025 | 25.27% | 3.51 | -0.133% | -0.47% | -0.60% | 7.7% | 7.4% |
| L3 | 2026 | 28.12% | 2.74 | +0.075% | +0.21% | 0.00% | 20.6% | 13.2% |
| L5 | 2024 | 16.87% | 3.13 | -0.130% | -0.41% | -1.15% | 11.2% | 11.2% |
| L5 | 2025 | 16.67% | 2.38 | -0.150% | -0.36% | -1.15% | 7.0% | 4.4% |
| L5 | 2026 | 15.66% | 2.37 | -0.138% | -0.33% | -1.15% | 16.3% | 4.7% |

## Interpretation

Explicitly training on the first 25% of ex-post large legs does not produce a robust causal onset detector from the current OHLCV/EMA/range/sweep feature set.

The opportunity is real, but onset predictability is not present in these price-derived features at the required strength.

Next research family should add independent ignition information, especially taker-flow imbalance, open-interest change, liquidation activity, funding/basis, and possibly order-book imbalance.

VERDICT: NO_ROBUST_ONSET_TRANSFER__PRICE_FEATURES_INSUFFICIENT
