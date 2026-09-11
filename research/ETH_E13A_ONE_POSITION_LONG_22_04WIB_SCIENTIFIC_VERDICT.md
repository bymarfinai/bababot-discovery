# ETH E13A — One-Position Sequential LONG 22:00–04:00 WIB Scientific Verdict

## Status
**ETH_E13A_NO_SEQUENTIAL_LONG_EXECUTION_PASSER**

Development/shadow only. OOS remained closed.

## Result-bearing run
- workflow run: **34577542724**
- job: **103193335059**
- head SHA: **b97ef78580a93a7de09f467fe4cfb45cd116a2ed**
- artifact: **10190245739**
- artifact SHA256: **929583f3695bc41583f0f4733b1dcca27878979ca68b0cfb4aad32d754d47e6c**
- raw ETHUSDT 5m coverage: **100.0000%**

## Formal result
**0 / 14 execution candidates passed the preregistered pooled + cross-era gates.**

The one-position constraint was applied causally: one accepted LONG at a time, all later signals skipped while busy, re-arm only after exit. Exit was the first completed 5m close with net PnL > $0 after the frozen $0.75 fee, with finite max-hold timeouts from 4h to 48h.

## Core finding
The sequential executor creates a very high hit rate but the first-positive-close payoff is too small to finance the rare timeout losses.

### FORMAL_ONLY
- 4h: N762, WR **85.17%**, net **-$339.61**, exp **-$0.45**, PF **0.601**, DD **$390.00**, timeout **14.83%**.
- 8h: N757, WR **89.56%**, net **-$214.21**, exp **-$0.28**, PF **0.715**, DD **$279.46**.
- 12h: N757, WR **91.68%**, net **-$180.57**, exp **-$0.24**, PF **0.752**, DD **$272.37**.
- 16h: N757, WR **93.00%**, net **-$133.20**, exp **-$0.18**, PF **0.806**, DD **$245.53**.
- 24h: N750, WR **95.20%**, net **-$224.57**, exp **-$0.30**, PF **0.712**, DD **$286.79**.
- 36h: N731, WR **96.17%**, net **-$108.30**, exp **-$0.15**, PF **0.836**, DD **$228.39**.
- 48h: N729, WR **96.84%**, net **-$72.73**, exp **-$0.10**, PF **0.883**, DD **$181.89**, timeout **3.16%**.

Across FORMAL_ONLY, median winning duration is about **20 minutes**. At 48h, only 23 of 729 trades time out, but those timeouts average about **-$27.07**, while the 706 first-positive winners average only about **+$0.78**. Thus a 96.84% WR is still economically negative.

### FORMAL_PLUS_NEARMISS
Adding the 22–23 E12J and 02–03 E12N near-miss entry characters does not fix the economics. Every max-hold candidate remains negative and has worse path risk than FORMAL_ONLY. At 48h: N1023, WR **95.70%**, net **-$266.18**, exp **-$0.26**, PF **0.750**, DD **$333.38**.

Therefore E12 near-miss hours are not promoted by E13A.

## Scientific interpretation
E13A rejects only the exact exit semantic **"close at the first net-positive 5m close"**. It does not reject the one-position sequential concept itself.

The mechanism is now clear: the executor harvests hundreds of tiny profits around +$0.8, then a small number of unresolved positions contribute losses one to two orders of magnitude larger. Increasing max hold raises WR and reduces timeout frequency, but timeout loss severity also grows; pooled expectancy stays negative in every tested case.

This is a payoff-distribution problem, not primarily a hit-rate problem.

## Next scientific action
Do not relax E13A gates or reinterpret its FAIL. A new preregistered experiment may retain the causal one-position semantics while testing a **minimum profit floor / target** before closing, because E13A establishes that merely being above break-even is economically insufficient.

For the next experiment, keep OOS closed and use FORMAL_ONLY as the primary entry policy because adding the two E12 near-miss hours consistently worsened Development economics in E13A.

Research/shadow only. No live promotion.