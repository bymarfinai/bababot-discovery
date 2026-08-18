# SUN1.9 — Sunday16 Dynamic BUY / SELL / WAIT

**Status: COMPLETE — discovery-selected natural-state router; validation report-only; live BBC untouched.**

## State decisions

| State | N | Decision | D chosen WR | D chosen PnL | V chosen WR | V chosen PnL |
|---|---:|---|---:|---:|---:|---:|
| F+|S+|U+ | 20 | **SELL** | 46.2% | $+19.34 | 42.9% | $-0.03 |
| F+|S+|U- | 14 | **WAIT** | - | $+0.00 | - | $+0.00 |
| F+|S-|U+ | 26 | **WAIT** | - | $+0.00 | - | $+0.00 |
| F+|S-|U- | 10 | **SELL** | 100.0% | $+41.98 | 100.0% | $+28.41 |
| F-|S+|U+ | 23 | **WAIT** | - | $+0.00 | - | $+0.00 |
| F-|S+|U- | 21 | **BUY** | 50.0% | $+14.93 | 57.1% | $+11.37 |
| F-|S-|U+ | 12 | **SELL** | 60.0% | $+23.05 | 28.6% | $-18.09 |
| F-|S-|U- | 13 | **SELL** | 57.1% | $+29.36 | 83.3% | $+40.32 |

## Combined engine
- Trades **76/139** (54.7% coverage); SELL 55, BUY 21, WAIT 63.
- Full: WR **57.89%**, PnL **$+190.64**, PF **2.01**, DD $19.94.
- Discovery: trades 46/83, WR **58.70%**, PnL **$+128.66**, PF **2.35**.
- Validation: trades 30/56, WR **56.67%**, PnL **$+61.97**, PF **1.66**.

## Guardrail
Same historical sample was already inspected in SUN1.7/SUN1.8. This is a diagnostic router, not untouched OOS validation.
