# BNB Economic-First B28P — Scientific Verdict

## Status
**BNB_ECONOMIC_FIRST_B28P_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34607162782**
- job ID: **103288306101**
- result-bearing head SHA: **a84c7c42ba73b2c940d871d7eb178078dcb79d90**
- artifact ID: **10266628399**
- artifact SHA256: **c8e94bd438879c0c6993e139cf99021226bcfe164bb1d7816de42bf717a5c898**
- artifact size: **1,217,666 bytes**
- targeted workflow conclusion: **success**
- raw BNBUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- BNBUSDT
- LONG only
- habitat: **15:00–16:00 WIB**
- anchors: **15:00 / 15:15 / 15:30 / 15:45 WIB** = **08:00 / 08:15 / 08:30 / 08:45 UTC**
- Development only
- exact same B28A–B28O 90-rule causal grammar, lookbacks, holds, fees, ranking and gates
- **3,240 candidates**
- no TP / no SL
- no weekday filter
- OOS unopened
- prior-hour winners and B27 structural coordinates excluded from ranking
- B28O's close `RV_MID__RANGE_HIGH / LB240 / hold360` near-miss received no preference

## Formal result
**0 / 3,240 candidates passed the full preregistered anchor-stability + pooled-economics/risk + all-era gate.**

Therefore B28P is a formal **FAIL**. No candidate is selected and no post-result substitution is allowed.

## Important near-misses
The following rows are descriptive only and remain formal failures:

- `DRIVE_UP__RV_HIGH / LB120 / hold960`: N **534**, WR **51.12%**, net **+$1,042.01**, exp **+$1.95**, PF **1.404**, DD **$640.50**, LS **15**, anchors **2/4**. Yearly WRs are **48.19% / 50.79% / 54.19%**. Large headline PnL is overwhelmed by pooled WR, risk, anchor and era failures.
- `EFF_HIGH__EXT_LOW / LB15 / hold960`: N **101**, WR **57.43%**, net **+$328.35**, exp **+$3.25**, PF **2.022**, DD **$56.82**, LS **4**, but anchors are **0/0** because sample size is too small for anchor evaluability; pooled N is also below 160 and 2024 WR is only **51.85%**. It remains a low-N rejected row.
- `RV_HIGH__RANGE_MID / LB120 / hold960`: N **202**, WR **53.47%**, net **+$251.78**, exp **+$1.25**, PF **1.305**, DD **$143.54**, LS **11**, anchors **3/4**; fails pooled WR, DD, LS and 2023 WR **45.45%**.
- `DRIVE_DOWN__STR_B40_60 / LB240 / hold240`: N **316**, WR **54.75%**, net **+$86.86**, exp **+$0.27**, PF **1.160**, DD **$75.31**, LS **5**, anchors **3/4**; pooled WR/expectancy/PF miss the gate and 2022 WR is only **46.60%**.
- `EFF_HIGH__RV_HIGH / LB360 / hold960`: N **424**, WR **53.30%**, net **+$792.96**, exp **+$1.87**, PF **1.350**, DD **$504.05**, LS **15**, anchors **1/4**; risk and stability failures dominate the positive net PnL.

No failed row is promoted.

## Transition interpretation
- 09:00–10:00 WIB (B28J): **FAIL**, 0 passers.
- 10:00–11:00 WIB (B28K): **FAIL**, 0 passers.
- 11:00–12:00 WIB (B28L): **FAIL**, 0 passers.
- 12:00–13:00 WIB (B28M): **PASS**, 4 passers; selected `RV_MID__RANGE_HIGH / LB30 / hold360`.
- 13:00–14:00 WIB (B28N): **FAIL**, 0 passers.
- 14:00–15:00 WIB (B28O): **FAIL**, 0 passers.
- 15:00–16:00 WIB (B28P): **FAIL**, 0 passers.

The current local sequence is therefore **three-hour unsupported cluster → one-hour robust rebound → three-hour unsupported cluster**. The second unsupported block is now **13:00–16:00 WIB**, matching the duration of the earlier 09:00–12:00 block so far, although it may still extend into later hours.

B28P is notably weaker than B28O from a robustness perspective. B28O contained a very close `RV_MID__RANGE_HIGH / LB240 / hold360` near-miss that missed the pooled loss-streak ceiling by only one. In B28P, no comparable near-pass appears: the highest-net rows are dominated by excessive drawdown, weak pooled WR, poor anchor support and inconsistent yearly behavior.

The descriptive grammar also shifts away from the B28M/B28O `RV_MID__RANGE_HIGH` family toward long-hold `DRIVE_UP__RV_HIGH` / high-volatility states. This is diagnostic only and cannot bias B28Q ranking.

This result does not prove there is no profitable implementation at 15:00–16:00 WIB. It means none of the preregistered 3,240 B28 LONG candidates passes the frozen economic, risk, anchor-stability and era-robustness requirements.

## Integrity
- Preregistered before economic output.
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No prior-hour coordinate preference.
- No B27 H2/P10 rescue.
- No post-result clock shift.
- No substitution of attractive failed rows.
- Workflow-registration retrigger altered only `.bnb-b28p-trigger`; preregistration and runner remained frozen.

## Next preregistered action
Continue the unchanged LONG-only economic-first sweep to **16:00–17:00 WIB**. Keep B28A–B28P outcomes frozen for later validation.
