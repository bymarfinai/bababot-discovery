# SOL Indicator Relationship Discovery — Stage 7G-B Result

**Historical Binance Vision SOLUSDT bookDepth; backward-only causal alignment.**

## Source/event coverage

| Partition | Events | Current snapshot | All 17 features | age p50 | age p95 |
|---|---:|---:|---:|---:|---:|
| development | 3096 | 98.8% | 98.4% | 29.0s | 30.0s |
| validation_2025 | 1968 | 98.8% | 96.8% | 28.0s | 30.0s |
| validation_2026 | 1749 | 98.8% | 95.5% | 29.0s | 30.0s |

Source gate: **PASS**.

## Frozen single-feature replication atlas

| Feature | DEV ΔTP | 2025 ΔTP | 2026 ΔTP | Class |
|---|---:|---:|---:|---|
| depth_imb5_change_15m | 5.2% | 4.5% | 3.9% | WEAK_OR_UNSTABLE |
| notional_imb1_change_15m | 4.1% | 5.9% | 2.8% | WEAK_OR_UNSTABLE |
| depth_imb1_change_15m | 4.1% | 5.9% | 2.8% | WEAK_OR_UNSTABLE |
| signed_depth_imb_1 | 3.4% | 1.4% | 6.7% | WEAK_OR_UNSTABLE |
| signed_depth_imb_5 | 3.4% | 1.5% | 0.6% | WEAK_OR_UNSTABLE |
| signed_notional_imb_1 | 3.3% | 1.8% | 5.8% | WEAK_OR_UNSTABLE |
| signed_depth_slope_1to5 | -2.9% | -0.7% | 1.3% | WEAK_OR_UNSTABLE |
| notional_imb1_change_1m | -2.8% | -3.1% | 1.3% | WEAK_OR_UNSTABLE |
| depth_imb1_change_1m | -2.7% | -2.6% | 1.3% | WEAK_OR_UNSTABLE |
| signed_notional_imb_5 | 2.3% | 2.9% | 1.2% | WEAK_OR_UNSTABLE |
| signed_notional_imb_2 | 2.2% | 3.6% | 0.5% | WEAK_OR_UNSTABLE |
| signed_depth_imb_2 | 2.1% | 3.6% | -0.1% | WEAK_OR_UNSTABLE |
| signed_notional_slope_1to5 | -1.8% | 1.0% | 0.8% | WEAK_OR_UNSTABLE |
| depth_imb5_change_5m | -0.7% | 1.8% | 3.6% | WEAK_OR_UNSTABLE |
| depth_imb1_change_5m | 0.2% | -1.1% | 3.7% | WEAK_OR_UNSTABLE |
| depth_imb5_change_1m | 0.2% | -0.1% | 2.7% | WEAK_OR_UNSTABLE |
| notional_imb1_change_5m | 0.1% | -1.4% | 3.4% | WEAK_OR_UNSTABLE |

## Replicated features

- none

BookDepth here is cumulative depth/notional in percentage bands, not raw per-price L2. Therefore these results do not prove exact wall placement, spread behavior, sweep, or absorption.

**Status: SOL_INDICATOR_RELATIONSHIP_S7G_B_COMPLETED_NO_REPLICATED_FEATURE**
