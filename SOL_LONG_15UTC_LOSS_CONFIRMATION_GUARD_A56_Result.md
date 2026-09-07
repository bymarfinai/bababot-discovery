# SOL LONG 15:00 UTC Loss Confirmation Guard — A56 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A56 executes the only A55-authorized binary characteristic, `M0_CLOSE_L25`, at the next 5m open whenever it occurs live before breakout confirmation. The future-relative `15m before terminal` label is not used in execution.

## Identity audit versus A53 G1_PRE_L25

| Partition | A56 exits | A53 exits | Exact identity |
|---|---:|---:|---:|
| development | 52 | 52 | NO |
| external | 19 | 19 | YES |
| reference_validation | 35 | 35 | YES |

Identity exact across all partitions: **False**.

## Economics

| Partition | Variant | WR | PF | Net | Exp/trade | DD | Week+ | 5bps WR | 5bps PF | 5bps Net | 5bps Exp | Guard exits | Winners guarded | Winner flips | Winner ΔPnL | Loss ΔPnL | ΔNet |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASELINE | 40.6% | 1.28 | $338.91 | $0.56 | $148.06 | 58.0% | 40.3% | 1.14 | $188.66 | $0.31 | 0 | 0 | 0 | $0.00 | $0.00 | $0.00 |
| development | A56_M0_L25 | 39.1% | 1.27 | $320.21 | $0.53 | $121.20 | 59.2% | 38.8% | 1.13 | $169.96 | $0.28 | 52 | 9 | 9 | $-116.38 | $97.68 | $-18.70 |
| external | BASELINE | 40.9% | 1.55 | $419.82 | $1.49 | $130.72 | 64.7% | 40.6% | 1.43 | $349.57 | $1.24 | 0 | 0 | 0 | $0.00 | $0.00 | $0.00 |
| external | A56_M0_L25 | 39.5% | 1.46 | $360.91 | $1.28 | $134.91 | 63.2% | 39.1% | 1.35 | $290.66 | $1.03 | 19 | 4 | 4 | $-129.86 | $70.95 | $-58.91 |
| reference_validation | BASELINE | 44.5% | 1.57 | $263.33 | $0.78 | $64.85 | 65.1% | 43.9% | 1.35 | $179.08 | $0.53 | 0 | 0 | 0 | $0.00 | $0.00 | $0.00 |
| reference_validation | A56_M0_L25 | 42.7% | 1.49 | $235.00 | $0.70 | $79.19 | 63.9% | 42.4% | 1.29 | $150.75 | $0.45 | 35 | 6 | 6 | $-66.32 | $37.99 | $-28.33 |

## Development block deltas

| Block | N | Raw ΔNet | 5bps ΔNet |
|---:|---:|---:|---:|
| 0 | 85 | $13.04 | $13.04 |
| 1 | 105 | $-14.10 | $-14.10 |
| 2 | 111 | $-26.73 | $-26.73 |
| 3 | 94 | $6.83 | $6.83 |
| 4 | 103 | $28.10 | $28.10 |
| 5 | 103 | $-25.83 | $-25.83 |

Positive Development blocks: **3/6 raw**, **3/6 stress**.

Development support gate: **FAIL**.
External gate: **FAIL**.
Reference Validation gate: **FAIL**.

## Decision

**Status: SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY_MISMATCH**

If identity is exact, A56 closes the loop: A55's pre-terminal M0 candle anatomy is real, but converting that state into a live hard exit is exactly the already-tested A53 PRE_L25 guard. No new live rule is authorized unless the full preregistered economics gate passes.

Research only. Live Baba Bot remains unchanged.
