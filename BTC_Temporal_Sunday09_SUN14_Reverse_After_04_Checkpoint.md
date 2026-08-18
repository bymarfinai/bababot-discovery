# Sunday 09:00 WIB — SUN1.4 Reverse BUY after SELL +0.4%

**Status: COMPLETE — causal next-5m reversal; discovery-only selection; live BBC untouched.**

## First leg
- SELL 09:00 TP0.4 / SL1.5 / 18h: full TP/SL/timeout **101/11/27**.
- Reverse triggers D/V/full: **68/33/101**.
- Trigger time median **250m** (P25 70, P75 460).

## Discovery-selected reverse BUY
- hold **8h**, TP **0.6%**, SL **1.3%**, RR 0.46.
- Reverse D: WR **66.18%**, PnL **$+5.71**, PF **1.07**.
- Reverse V: WR **72.73%**, PnL **$+15.14**, PF **1.50**.
- Reverse full: WR **68.32%**, PnL **$+20.85**, PF **1.18**.

## Combined chain
- D **$+11.58**, WR 60.24%, PF 1.08.
- V **$-42.00**, WR 50.00%, PF 0.65.
- Full **$-30.42**, WR 56.12%, PF 0.88.

## Reverse 0.4/0.4 reference
- 1h: reverse D -62.38, V -6.62, full -69.00; full WR 37.6%; chain -120.27
- 2h: reverse D -54.86, V -3.34, full -58.20; full WR 45.5%; chain -109.47
- 4h: reverse D -53.76, V -7.93, full -61.69; full WR 48.5%; chain -112.96
- 6h: reverse D -58.92, V -4.26, full -63.17; full WR 51.5%; chain -114.45
- 8h: reverse D -56.20, V -2.51, full -58.70; full WR 54.5%; chain -109.98
- 12h: reverse D -55.41, V -5.45, full -60.86; full WR 53.5%; chain -112.14

## Guardrail
Reverse parameters selected on discovery only. Validation report-only. Reverse entry is next 5m open, never intrabar wick.
