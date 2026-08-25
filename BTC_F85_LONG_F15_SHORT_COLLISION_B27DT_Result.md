# B27DT — F85 LONG + F15 SHORT Collision / Portfolio Interference Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**B27DQ LONG parity: PASS.** Pooled-major N=227, WR=72.2%, PF=2.25, net=$+289.76, max loss streak=3.

## LONG_PROTECTED — incremental SHORT without displacing any B27DQ LONG

| Set | Standalone N | Standalone WR | PF | Standalone Net | Blocked by LONG | Blocked by SHORT | Added N | Added WR | Added PF | Added Net | Combined Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SHORT_2000 | 56 | 76.8% | 2.81 | $+77.73 | 0 | 0 | 56 | 76.8% | 2.81 | $+77.73 | $+367.49 |
| SHORT_0430 | 73 | 74.0% | 1.15 | $+13.34 | 0 | 0 | 73 | 74.0% | 1.15 | $+13.34 | $+303.10 |
| SHORT_0330 | 89 | 73.0% | 1.09 | $+12.08 | 1 | 0 | 88 | 72.7% | 1.08 | $+9.95 | $+299.71 |
| SHORT_0300 | 67 | 76.1% | 1.33 | $+27.29 | 0 | 0 | 67 | 76.1% | 1.33 | $+27.29 | $+317.05 |
| SHORT_2100 | 69 | 65.2% | 1.54 | $+42.66 | 0 | 0 | 69 | 65.2% | 1.54 | $+42.66 | $+332.42 |
| SHORT_0000 | 65 | 66.2% | 1.60 | $+39.26 | 0 | 0 | 65 | 66.2% | 1.60 | $+39.26 | $+329.02 |
| SHORT6_BASKET | 419 | 71.8% | 1.43 | $+212.36 | 1 | 97 | 321 | 71.7% | 1.53 | $+189.10 | $+478.86 |

## FIRST_SIGNAL_WINS — LONG and SHORT compete for one BTC slot

| Set | Total N | Total WR | PF | Combined Net | Delta | LONG N | LONG WR | LONG Net | SHORT N | SHORT WR | SHORT Net | Displaced LONG | SHORT blocked by LONG | LONG blocked by SHORT | Class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SHORT_2000 | 283 | 73.1% | 2.34 | $+367.49 | $+77.73 | 227 | 72.2% | $+289.76 | 56 | 76.8% | $+77.73 | 0 | 0 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT_0430 | 300 | 72.7% | 1.94 | $+303.10 | $+13.34 | 227 | 72.2% | $+289.76 | 73 | 74.0% | $+13.34 | 0 | 0 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT_0330 | 315 | 72.4% | 1.83 | $+299.71 | $+9.95 | 227 | 72.2% | $+289.76 | 88 | 72.7% | $+9.95 | 0 | 1 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT_0300 | 294 | 73.1% | 2.01 | $+317.05 | $+27.29 | 227 | 72.2% | $+289.76 | 67 | 76.1% | $+27.29 | 0 | 0 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT_2100 | 296 | 70.6% | 2.07 | $+332.42 | $+42.66 | 227 | 72.2% | $+289.76 | 69 | 65.2% | $+42.66 | 0 | 0 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT_0000 | 292 | 70.9% | 2.11 | $+329.02 | $+39.26 | 227 | 72.2% | $+289.76 | 65 | 66.2% | $+39.26 | 0 | 0 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |
| SHORT6_BASKET | 548 | 71.9% | 1.81 | $+478.86 | $+189.10 | 227 | 72.2% | $+289.76 | 321 | 71.7% | $+189.10 | 0 | 1 | 0 | FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE |

## Mechanical readout

Best LONG-protected incremental set: **SHORT6_BASKET**, adds $+189.10; combined $+478.86.
Best FIRST_SIGNAL set: **SHORT6_BASKET**, delta $+189.10; displaced baseline LONG=0.

Guardrail: six SHORT clocks were selected after B27DR inspection; B27DT is exploratory historical portfolio-interference evidence, not pristine OOS validation.

Research only; live BBC unchanged.
