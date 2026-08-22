# B27AU — BTC London->NY SHORT F15 E20 Hybrid Loss Decomposition — Result

**Audit status: PASS.** B27AT E20 identities/totals reproduced exactly before attribution.

Pooled-major N: **163**; realized total: **$-15.058**.

## 1. Activated vs not activated

| Group | N | WR | PF | Exp/trade $ | Total $ | Mean win $ | Mean loss $ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Activated | 92 | 92.4% | 49.134 | 2.808 | 258.349 | 3.103 | -0.767 |
| Not activated | 71 | 2.8% | 0.008 | -3.851 | -273.407 | 1.100 | -3.994 |
| All | 163 | 53.4% | 0.946 | -0.092 | -15.058 | 3.056 | -3.697 |

## 2. PnL by exit reason

| Exit reason | N | Total $ | Avg $ |
|---|---:|---:|---:|
| PRE_ACT_CLOSE_INVALIDATION_F65 | 42 | -216.426 | -5.153 |
| TIME_EXIT_SESSION_END | 29 | -56.981 | -1.965 |
| PROFIT_CEILING_GAP_OPEN | 62 | +128.106 | +2.066 |
| PROFIT_CEILING_HIT | 30 | +130.243 | +4.341 |

## 3. Pre-activation invalidation tail

Pre-activation F65 invalidations: **42 / 163 (25.8%)**; total **$-216.426**.
Overshoot above F65 on the completed-close exit: median **0.088R**, P75 **0.133R**, P90 **0.232R**, max **0.350R**.

## 4. Activated path: winners vs losers

| Activated path | N | Median trough below L | Median realized exit below L | Median capture | Median giveback | Total PnL $ |
|---|---:|---:|---:|---:|---:|---:|
| Winners | 85 | 0.645R | 0.178R | 23.1% | 0.501R | +263.716 |
| Losers | 7 | 0.632R | -0.128R | 0.0% | 0.730R | -5.367 |
| All activated | 92 | 0.643R | 0.165R | 21.3% | 0.528R | +258.349 |

## 5. Loss concentration

- Worst 5 trades contribute **18.5%** of pooled gross losses ($52.075); exit mix: PRE_ACT_CLOSE_INVALIDATION_F65:5.
- Worst 10 trades contribute **30.4%** of pooled gross losses ($85.524); exit mix: PRE_ACT_CLOSE_INVALIDATION_F65:10.

## 6. Runner attribution after E20

For activated trades only, exact mechanical exit at E20 would contribute **$+261.742**. Actual hybrid contribution from those same activated trades is **$+258.349**. Runner delta vs exact E20 = **$-3.393**.
Keeping non-activated trades unchanged, the diagnostic exact-E20 total would be **$-11.666** versus actual hybrid **$-15.058**. This is attribution only, not a proposed strategy.

## Diagnosis

1. **Primary drag before activation:** non-activated trades contribute **$-273.407**. These never earn the E20 floor, so the hybrid cannot protect them.
2. **Runner also destroys value after activation:** relative to an exact E20 exit, the frozen runner gives back **$3.393** across activated trades.
3. **Loss tail is concentrated:** worst 10 trades account for **30.4%** of all gross losses.
4. No threshold or filter was selected in this audit; this is causal attribution only. Live BBC unchanged.
