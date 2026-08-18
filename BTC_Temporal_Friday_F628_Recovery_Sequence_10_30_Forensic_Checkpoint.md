# Friday F6.28 — Recovery Sequence +10m → +30m Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched; F6.26 remains failed and is NOT frozen.**

## Objective
Treat +10m as WATCH, then test whether recovery persistence through +15/+20/+25/+30m causally separates true-dead from future winners.

- true-dead: **9** (D 4 / V 5)
- false-winner: **13** (D 9 / V 4)

## +15m causal snapshot
- alive dead/winner: **9 / 13**; already exited dead/winner: **0 / 0**
- continuous `ema7_dist_r`: strength full/D/V **0.590/0.583/0.750**, lower=dead
- continuous `reaccel_share`: strength full/D/V **0.521/0.556/0.525**, lower=dead
- continuous `repair_score_now`: strength full/D/V **0.504/0.583/0.575**, lower=dead
- continuous `progress_r`: strength full/D/V **0.650/0.556/0.500**, higher=dead
- state `current_higher_low` dead vs winner rate full **44.4%/15.4%**, gap D/V **+13.9pp/+35.0pp**
- state `current_higher_high` dead vs winner rate full **55.6%/23.1%**, gap D/V **+13.9pp/+30.0pp**
- state `current_higher_close` dead vs winner rate full **44.4%/53.8%**, gap D/V **-19.4pp/-15.0pp**
- state `current_reaccel` dead vs winner rate full **11.1%/15.4%**, gap D/V **-11.1pp/-5.0pp**

## +20m causal snapshot
- alive dead/winner: **9 / 13**; already exited dead/winner: **0 / 0**
- continuous `ema7_failure_share`: strength full/D/V **0.714/0.778/0.775**, higher=dead
- continuous `ema7_hold_streak`: strength full/D/V **0.714/0.778/0.775**, lower=dead
- continuous `ema7_dist_r`: strength full/D/V **0.607/0.639/0.650**, lower=dead
- continuous `struct_repair_share`: strength full/D/V **0.590/0.667/0.600**, lower=dead
- state `ema7_reclaim_any` dead vs winner rate full **22.2%/61.5%**, gap D/V **-55.6pp/-35.0pp**
- state `current_above_ema7` dead vs winner rate full **22.2%/61.5%**, gap D/V **-55.6pp/-35.0pp**
- state `current_higher_low` dead vs winner rate full **44.4%/61.5%**, gap D/V **-30.6pp/-15.0pp**
- state `unrepaired_now` dead vs winner rate full **66.7%/38.5%**, gap D/V **+55.6pp/+15.0pp**

## +25m causal snapshot
- alive dead/winner: **9 / 13**; already exited dead/winner: **0 / 0**
- continuous `ema7_failure_share`: strength full/D/V **0.628/0.639/0.750**, higher=dead
- continuous `ema7_hold_streak`: strength full/D/V **0.598/0.583/0.750**, lower=dead
- continuous `cum_taker_after10`: strength full/D/V **0.598/0.583/0.650**, lower=dead
- continuous `persistent_bear_share`: strength full/D/V **0.543/0.583/0.550**, higher=dead
- state `ema7_reclaim_any` dead vs winner rate full **55.6%/61.5%**, gap D/V **-5.6pp/-15.0pp**
- state `unrepaired_now` dead vs winner rate full **44.4%/38.5%**, gap D/V **+5.6pp/+15.0pp**
- state `current_higher_high` dead vs winner rate full **77.8%/61.5%**, gap D/V **+44.4pp/-15.0pp**
- state `current_reaccel` dead vs winner rate full **66.7%/53.8%**, gap D/V **+55.6pp/-35.0pp**

## +30m causal snapshot
- alive dead/winner: **9 / 13**; already exited dead/winner: **0 / 0**
- continuous `cum_taker_after10`: strength full/D/V **0.632/0.611/0.650**, lower=dead
- continuous `persistent_bear_share`: strength full/D/V **0.585/0.556/0.650**, higher=dead
- continuous `ema7_failure_share`: strength full/D/V **0.620/0.542/0.825**, higher=dead
- continuous `below_entry_share`: strength full/D/V **0.513/0.583/0.550**, higher=dead
- state `current_higher_close` dead vs winner rate full **22.2%/53.8%**, gap D/V **-5.6pp/-50.0pp**
- state `current_higher_low` dead vs winner rate full **44.4%/69.2%**, gap D/V **-5.6pp/-60.0pp**
- state `false_bounce_now` dead vs winner rate full **22.2%/15.4%**, gap D/V **+2.8pp/+20.0pp**
- state `current_struct_repair` dead vs winner rate full **22.2%/38.5%**, gap D/V **+16.7pp/-50.0pp**

## Natural adaptive states (predeclared, not promoted)
- +15m `unrepaired_now`: dead/winner **88.9%/84.6%**; D/V gap **+0.0pp/+30.0pp**
- +15m `unrepaired_with_flow`: dead/winner **55.6%/53.8%**; D/V gap **+19.4pp/-10.0pp**
- +15m `false_bounce_now`: dead/winner **0.0%/0.0%**; D/V gap **+0.0pp/+0.0pp**
- +15m `recovery_chain_now`: dead/winner **0.0%/7.7%**; D/V gap **+0.0pp/-25.0pp**
- +15m `recovery_chain_flow_now`: dead/winner **0.0%/0.0%**; D/V gap **+0.0pp/+0.0pp**
- +20m `unrepaired_now`: dead/winner **66.7%/38.5%**; D/V gap **+55.6pp/+15.0pp**
- +20m `unrepaired_with_flow`: dead/winner **44.4%/38.5%**; D/V gap **+30.6pp/-5.0pp**
- +20m `false_bounce_now`: dead/winner **0.0%/0.0%**; D/V gap **+0.0pp/+0.0pp**
- +20m `recovery_chain_now`: dead/winner **22.2%/38.5%**; D/V gap **-33.3pp/-10.0pp**
- +20m `recovery_chain_flow_now`: dead/winner **22.2%/30.8%**; D/V gap **-33.3pp/+15.0pp**
- +25m `unrepaired_now`: dead/winner **44.4%/38.5%**; D/V gap **+5.6pp/+15.0pp**
- +25m `unrepaired_with_flow`: dead/winner **33.3%/38.5%**; D/V gap **-19.4pp/+15.0pp**
- +25m `false_bounce_now`: dead/winner **0.0%/7.7%**; D/V gap **-11.1pp/+0.0pp**
- +25m `recovery_chain_now`: dead/winner **44.4%/46.2%**; D/V gap **+16.7pp/-35.0pp**
- +25m `recovery_chain_flow_now`: dead/winner **44.4%/46.2%**; D/V gap **+16.7pp/-35.0pp**
- +30m `unrepaired_now`: dead/winner **33.3%/38.5%**; D/V gap **-30.6pp/+40.0pp**
- +30m `unrepaired_with_flow`: dead/winner **33.3%/30.8%**; D/V gap **-19.4pp/+40.0pp**
- +30m `false_bounce_now`: dead/winner **22.2%/15.4%**; D/V gap **+2.8pp/+20.0pp**
- +30m `recovery_chain_now`: dead/winner **22.2%/38.5%**; D/V gap **+16.7pp/-50.0pp**
- +30m `recovery_chain_flow_now`: dead/winner **22.2%/30.8%**; D/V gap **+27.8pp/-50.0pp**

## Guardrail
This milestone may identify a recovery sequence worth freezing next, but it does not cut a trade. The next management test must predeclare ONE timing/state architecture from these causal results, then measure loss saved versus future winners damaged on the frozen five-layer stack.
