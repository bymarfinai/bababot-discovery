# Sunday T-Method Reset — ST0 to ST3

**Status: COMPLETE — Tuesday A5.0-A5.3 methodology rebuilt for Sunday; live BBC untouched.**

## Parent
- Sunday 16:00 WIB SELL / TP2.5 / SL1.4 / hold18h: N 139, WR **47.48%**, PnL **$+63.60**, PF **1.14**.

## ST0 path anatomy
- Winner median MFE 2.51%, MAE 0.46%.
- Loser median MFE 0.41%, MAE 1.50%.

## ST1 unconditional protection frontier

| Hinge | Lock | Actions | WR | PnL | D PnL | V PnL |
|---:|---:|---:|---:|---:|---:|---:|
| 0.50% | 0.20% | 97 | 69.06% | $-110.95 | $-68.06 | $-42.89 |
| 0.80% | 0.32% | 82 | 59.71% | $-5.63 | $+30.03 | $-35.67 |
| 1.00% | 0.40% | 76 | 57.55% | $+3.39 | $-0.46 | $+3.85 |
| 1.50% | 0.60% | 54 | 49.64% | $-9.59 | $-10.74 | $+1.15 |

## ST2 conditional RUNNER vs PROTECT

Same conceptual Tuesday rule, normalized to Sunday: after favorable hinge, PROTECT only if trigger close retains <=70% of hinge and cumulative MAE >=25% of SL; lock at 40% of hinge. Otherwise RUNNER.

| Hinge | Actions D/V | Full WR | Full PnL | D PnL | V PnL |
|---:|---:|---:|---:|---:|---:|
| 0.50% | 3/2 | 47.48% | $+45.22 | $+46.22 | $-1.00 |
| 0.80% | 2/1 | 48.20% | $+44.01 | $+45.21 | $-1.20 |
| 1.00% | 0/1 | 47.48% | $+53.10 | $+53.90 | $-0.80 |
| 1.50% | 0/0 | 47.48% | $+63.60 | $+53.90 | $+9.70 |

## ST3 discovery-selected Sunday candidate
- Selected favorable hinge **0.50%**; lock **0.20%**.
- Parent $+63.60 -> candidate **$+45.22** (delta **$-18.37**).
- WR 47.48% -> **47.48%**; PF 1.14 -> **1.10**; DD $61.50 -> **$54.52**.
- Discovery: 48.19%, $+46.22; validation: 46.43%, $-1.00.
- Positive chronological blocks **5/8**.

## Guardrail
Discovery selects only the natural favorable hinge. Validation is report-only, but the broader Sunday history was previously inspected, so this is same-sample methodology reset, not untouched OOS.
