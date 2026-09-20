# BNB B38-S4 — Frozen Adaptive Execution Score

**2022-2024 DEVELOPMENT EXECUTION CHARACTERIZATION — NOT OOS**

Integrity passed: **788 parent events -> 690 frozen ENTRY plans + 98 frozen cancellations**.

Target/SL ordering is resolved from exact **5m bars strictly after each 15m entry close**. Same-5m target+SL touches are reported as ambiguous.

## Pooled structural-objective policies

| Policy | Plans | Resolved | W-L | Hit rate | Median win R | Expectancy | Total R | PF | W streak | L streak | Max DD | Ambig | Unres |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TP1_FULL_EXIT | 688 | 685 | 358-327 | 52.3% | 0.87R | 0.09R | 64.00R | 1.20 | 7 | 8 | 20.38R | 3 | 0 |
| TP2_FULL_EXIT | 596 | 594 | 266-328 | 44.8% | 1.02R | 0.02R | 12.25R | 1.04 | 6 | 10 | 24.45R | 2 | 0 |
| TP3_FULL_EXIT | 501 | 500 | 199-301 | 39.8% | 1.14R | -0.05R | -27.39R | 0.91 | 6 | 8 | 32.08R | 1 | 0 |

## By adaptive execution mode — TP1

| Mode | Resolved | W-L | Hit rate | Median win R | Expectancy | PF | Max L streak | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DELAYED_CLEAN_RECLAIM | 137 | 81-56 | 59.1% | 0.97R | 0.25R | 1.62 | 4 | 9.07R |
| DELAYED_SWEEP_RECLAIM | 72 | 38-34 | 52.8% | 0.84R | 0.06R | 1.12 | 4 | 7.74R |
| IMMEDIATE_CLEAN_RECLAIM | 411 | 205-206 | 49.9% | 0.87R | 0.06R | 1.11 | 7 | 16.51R |
| IMMEDIATE_SWEEP_RECLAIM | 65 | 34-31 | 52.3% | 0.68R | 0.02R | 1.05 | 6 | 8.74R |

## By adaptive execution mode — TP2

| Mode | Resolved | W-L | Hit rate | Median win R | Expectancy | PF | Max L streak | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DELAYED_CLEAN_RECLAIM | 110 | 52-58 | 47.3% | 1.04R | 0.05R | 1.09 | 7 | 9.74R |
| DELAYED_SWEEP_RECLAIM | 64 | 33-31 | 51.6% | 0.95R | 0.16R | 1.34 | 3 | 5.59R |
| IMMEDIATE_CLEAN_RECLAIM | 357 | 155-202 | 43.4% | 1.03R | 0.01R | 1.01 | 8 | 24.88R |
| IMMEDIATE_SWEEP_RECLAIM | 63 | 26-37 | 41.3% | 0.94R | -0.09R | 0.84 | 6 | 16.00R |

## Year stability

| Policy | 2022 hit / Exp | 2023 hit / Exp | 2024 hit / Exp |
|---|---:|---:|---:|
| TP1_FULL_EXIT | 51.7% / 0.08R | 53.4% / 0.11R | 51.7% / 0.08R |
| TP2_FULL_EXIT | 46.3% / 0.07R | 45.3% / 0.04R | 42.9% / -0.04R |
| TP3_FULL_EXIT | 37.6% / -0.12R | 45.5% / 0.09R | 37.0% / -0.12R |

## Ambiguity sensitivity

Main expectancy excludes same-5m ambiguous outcomes. A separately persisted sensitivity treats every ambiguous outcome as -1R; no rule is changed from that sensitivity.

## S4 interpretation boundary
These results describe the frozen adaptive execution engine with equal 1R risk per signal. They are **not** a dollar portfolio simulation, do not include fees/slippage, and do not establish independent OOS validation.
No entry, SL, TP, mode, or RR filter was changed after outcomes were read.
