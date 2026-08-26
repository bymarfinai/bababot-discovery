# B27EA — Tuesday A5.11 Independent Portfolio Revalidation — Result

Raw 5m control coverage: **100.0000%**. Frozen Tuesday historical parity: **PASS**.

A5.11 standalone: **N=139, WR=64.0%, PF=1.69, net=$+130.33**.

## Chronological stability

| Block | N | WR | PF | Net |
|---|---:|---:|---:|---:|
| B1 | 17 | 52.9% | 0.63 | $-13.16 |
| B2 | 17 | 52.9% | 1.77 | $+20.27 |
| B3 | 18 | 55.6% | 1.56 | $+13.63 |
| B4 | 17 | 58.8% | 1.60 | $+18.20 |
| B5 | 17 | 76.5% | 2.27 | $+24.11 |
| B6 | 18 | 72.2% | 3.54 | $+30.19 |
| B7 | 17 | 58.8% | 1.40 | $+10.69 |
| B8 | 18 | 83.3% | 2.85 | $+26.39 |

Positive blocks: **7/8**; first83 net=$+54.11; last56 net=$+76.22; stability **PASS**.

## Adverse slippage — A5.11 standalone

| bps/fill | N | WR | PF | Net |
|---:|---:|---:|---:|---:|
| 0 | 139 | 64.0% | 1.69 | $+130.33 |
| 2 | 139 | 61.9% | 1.52 | $+102.62 |
| 5 | 139 | 50.4% | 1.28 | $+61.03 |
| 10 | 139 | 47.5% | 0.97 | $-8.34 |

5bps execution gate: **FAIL**.

## One-BTC portfolio compatibility

| Portfolio | N | WR | PF | Net | Tuesday accepted | Tuesday net | Displaced current |
|---|---:|---:|---:|---:|---:|---:|---:|
| CURRENT_LONG_SHORT20 | 283 | 73.1% | 2.34 | $+367.49 | 0 | $+0.00 | 0 |
| PLUS_TUESDAY_A511 | 417 | 69.8% | 2.06 | $+488.57 | 139 | $+130.33 | 5 |

Portfolio gate (N>283, net improves, WR>=70%, PF>=1.80, <=5 displaced, incremental net>0): **FAIL**.

**Status: `B27EA_TUESDAY_A511_THIRD_EDGE_NOT_SUPPORTED`.**

Evidence limitation: A5.11 is frozen reused-history with insufficient pristine forward observations. B27EA is compatibility/revalidation only. Pre-B27DX control is used and must be rerun after the known LONG causal correction. No live exchange writes changed.
