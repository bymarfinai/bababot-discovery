# SUN2.1 — F-/S-/U+ Reversal vs Retracement Forensic

**Status: COMPLETE — forensic only; live BBC untouched.**

## State baseline
- SELL: D N 5, WR 60.0%, PnL $+23.05, PF 4.03; V N 7, WR 28.6%, PnL $-18.09, PF 0.42; Full N 12, WR 41.7%, PnL $+4.96, PF 1.13.
- BUY: D N 5, WR 40.0%, PnL $-18.68, PF 0.20; V N 7, WR 71.4%, PnL $+14.86, PF 1.96; Full N 12, WR 58.3%, PnL $-3.82, PF 0.90.

## Natural reversal routers
| Rule | D | V | Full |
|---|---|---|---|
| sustained_up: true BUY / false SELL | N 5, WR 60.0%, PnL $+10.23, PF 1.91 | N 7, WR 57.1%, PnL $-10.43, PF 0.55 | N 12, WR 58.3%, PnL $-0.20, PF 0.99 |
| upper_half24: true BUY / false SELL | N 5, WR 20.0%, PnL $-24.16, PF 0.10 | N 7, WR 71.4%, PnL $+14.86, PF 1.96 | N 12, WR 50.0%, PnL $-9.31, PF 0.78 |
| above_ema20: true BUY / false SELL | N 5, WR 40.0%, PnL $-9.27, PF 0.51 | N 7, WR 71.4%, PnL $+10.04, PF 1.65 | N 12, WR 58.3%, PnL $+0.77, PF 1.02 |
| ema_bull: true BUY / false SELL | N 5, WR 40.0%, PnL $-9.27, PF 0.51 | N 7, WR 57.1%, PnL $+10.89, PF 1.69 | N 12, WR 50.0%, PnL $+1.61, PF 1.05 |
| last4_buyflow: true BUY / false SELL | N 5, WR 80.0%, PnL $+29.78, PF 9.53 | N 7, WR 57.1%, PnL $-4.99, PF 0.79 | N 12, WR 66.7%, PnL $+24.79, PF 1.93 |
| first12_up: true BUY / false SELL | N 5, WR 60.0%, PnL $+0.82, PF 1.05 | N 7, WR 57.1%, PnL $-4.59, PF 0.80 | N 12, WR 58.3%, PnL $-3.77, PF 0.90 |
| last4_up: true BUY / false SELL | N 5, WR 40.0%, PnL $-9.27, PF 0.51 | N 7, WR 71.4%, PnL $+9.02, PF 1.58 | N 12, WR 58.3%, PnL $-0.25, PF 0.99 |
| sustained_up AND upper_half24: true BUY / false SELL | N 5, WR 60.0%, PnL $+10.23, PF 1.91 | N 7, WR 57.1%, PnL $-10.43, PF 0.55 | N 12, WR 58.3%, PnL $-0.20, PF 0.99 |

## Conservative agreement
- sustained_up + upper_half24: trades 7/12 (BUY 6, SELL 1, WAIT 5).
- D N 3, WR 33.3%, PnL $-8.65, PF 0.23; V N 4, WR 75.0%, PnL $+3.60, PF 1.46; Full N 7, WR 57.1%, PnL $-5.05, PF 0.73.

## Guardrail
Forensic only. N=12 (D=5,V=7) is small and this history has been inspected before; no rule is promoted from this step.
