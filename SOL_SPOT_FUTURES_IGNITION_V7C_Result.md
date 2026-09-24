# SOL Spot-vs-Futures Ignition V7C — Verified Result

Run ID: 35961724321
Head SHA: 61caa1e556631c84a8b4760ff3576a386b2334f5
Status: SUCCESS
Artifact ID: 10792657912

Coverage:
- 19,849 frozen NEW_LONG_BUILD rising-edge events.
- 2023 futures+spot coverage: 99.99%.
- 2024 futures+spot coverage: 100.00%.

2024 parent baseline:
- N 1,347
- WR 47.74%
- 25.42 trades/week
- expectancy -0.192%/trade
- mean weekly -4.88%

Best V7C configuration:
- SPOT_ONLY / RandomForest / 90th percentile
- N 573
- WR 48.34%
- 10.81 trades/week
- expectancy -0.194%/trade
- mean weekly -2.10%

Forensics:
- zero stable differentiators under the preregistered same-sign abs(SMD)>=0.10 rule.
- strongest consistent spot feature: 15m inter-aggTrade interval, SMD -0.153 in 2023 but only -0.062 in 2024.
- major spot-vs-futures divergence features were tiny or changed sign between 2023 and 2024.
- SPOT_CROSS did not beat SPOT_ONLY.

Interpretation:
Spot corroboration versus futures aggression does not distinguish true from false NEW_LONG_BUILD ignition with useful strength. The public compressed-trade-sequence family is exhausted under V7B/V7C stop rules. No raw-trade or 2025/2026 OOS confirmation is authorized from this family.

Remaining true-microstructure path:
- genuine L2 order-book replay / replenishment/depletion is still untested;
- current CoinDesk L2 path is BLOCKED_DATA_ACCESS because COINDESK_API_KEY is not configured.

Research implication:
The dominant bottleneck is now the parent event definition, not lack of more aggregate flow features. Future discovery should change the trigger architecture or obtain genuine L2 data; it should not retune futures/spot delta thresholds.

VERDICT: NO_V7C_PROMOTION_GATE__PUBLIC_TRADE_SEQUENCE_FAMILY_STOP