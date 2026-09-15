# SOL V5 Batch 2C — Early Entry + Directional Management Verdict

Authoritative frozen run: `34915131850`
Artifact: `sol-v5-batch2c-early-entry-management` (ID `10376780187`)
Branch: `sol-v5-batch2c-early-entry-management`

## Result

- Evaluable HIGH_STATE trades 2022–2024: **2,763**
- Median policy duration: **5m**
- LOW_DIRECTION early exits: **93.56%**
- UP_CONFIRMED holds: **4.71%**

### Policy economics
- WR: **30.44%**
- expectancy: **-0.1554%**
- PF: **0.485**
- net PnL: **-$2,147.35** at $500 notional/trade
- max DD: **$2,157.67**
- max loss streak: **22**

### Unconditional HIGH_STATE +60m baseline
- WR: **42.02%**
- expectancy: **-0.1285%**
- PF: **0.795**
- net PnL: **-$1,774.74**
- max DD: **$1,826.08**

Paired expectancy delta: **-0.0270 pp**.

### Year stability
- 2022 policy expectancy **-0.1342%**, PF **0.585**, PnL **-$575.02**
- 2023 policy expectancy **-0.1596%**, PF **0.509**, PnL **-$598.38**
- 2024 policy expectancy **-0.1685%**, PF **0.378**, PnL **-$973.95**

### Exit reason diagnostic
- `LOW_DIRECTION_EXIT`: N=2,585, WR 28.01%, mean net **-0.2049%**
- `UP_CONFIRMED_HOLD60`: N=130, WR **83.85%**, mean net **+1.3694%**
- `DOWN_FIRST_EXIT`: N=41, WR 4.88%, mean net **-2.0017%**
- `SURVIVED_30_HOLD60`: N=6, WR 83.33%, mean net **+0.4446%**

## Gate audit
- PASS — policy N >= 1,500
- FAIL — positive policy expectancy
- FAIL — PF >= 1.10
- FAIL — paired expectancy improvement > 0
- FAIL — max DD no worse than baseline
- FAIL — positive PnL in >=2/3 years

# VERDICT: EARLY_ENTRY_MANAGEMENT_NOT_READY

Interpretation: V4 HIGH_STATE is an expansion habitat, not a directly tradable LONG entry. Entering every HIGH_STATE and attempting to repair the trade after +5m is too late and transaction-cost-heavy. The earlier positive immediate-state expectancy seen on later-selected Batch 2/2B episodes was conditional on information that became available after state detection and therefore was not an actionable t=0 selector.

Next architecture: test a **state-time directional selector** using only features available at HIGH_STATE onset. This asks whether the subset that will become UP_FIRST can be separated *before* price expansion starts, instead of waiting for post-state confirmation.

2025+ remains CLOSED.
