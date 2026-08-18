# Friday F6.33 — Fake Bounce vs Slow Recovery +30→+60 Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched; F6.29/F6.31/F6.32 remain failed and are NOT frozen.**

## Cohorts
- slow winners F6.32 cut at +30m: **2**
- fake-confirm losers F6.32 released at +25/+30m: **3**
- all guarded losers: **4**
- external cross-control: **13 winners vs 9 true-dead**

## +35m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/4**; external winner/dead **13/8**
- `post30_higher_close_share`: strength **1.000** (higher=winner), med W/L **1.0000/0.0000**; LOO med/min **1.000/1.000**; external **0.784** same direction
- `post30_cum_taker`: strength **0.833** (higher=winner), med W/L **0.2139/-0.1171**; LOO med/min **0.750/0.667**; external **0.635** same direction
- `post30_current_taker`: strength **0.833** (higher=winner), med W/L **0.2139/-0.1171**; LOO med/min **0.750/0.667**; external **0.635** same direction
- `post30_positive_flow_share`: strength **0.583** (higher=winner), med W/L **0.5000/0.0000**; LOO med/min **0.667/0.500**; external **0.620** same direction
- state `current_higher_close` W/fake-L **100.0%/0.0%**; external W/dead **69.2%/12.5%**; agree **True**
- state `current_green` W/fake-L **100.0%/0.0%**; external W/dead **69.2%/12.5%**; agree **True**
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/66.7%**; external W/dead **23.1%/87.5%**; agree **True**
- state `current_higher_high` W/fake-L **100.0%/66.7%**; external W/dead **69.2%/12.5%**; agree **True**

## +40m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/3**; external winner/dead **13/6**
- `post30_higher_close_share`: strength **0.917** (higher=winner), med W/L **0.7500/0.0000**; LOO med/min **0.875/0.833**; external **0.897** same direction
- `post30_higher_high_share`: strength **0.833** (higher=winner), med W/L **1.0000/0.5000**; LOO med/min **0.833/0.750**; external **0.808** same direction
- `post30_cum_taker`: strength **0.833** (higher=winner), med W/L **0.1411/-0.1081**; LOO med/min **0.750/0.667**; external **0.769** same direction
- `post30_full_chain_share`: strength **0.750** (higher=winner), med W/L **0.2500/0.0000**; LOO med/min **0.750/0.500**; external **0.808** same direction
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/100.0%**; external W/dead **30.8%/100.0%**; agree **True**
- state `current_higher_high` W/fake-L **100.0%/33.3%**; external W/dead **53.8%/0.0%**; agree **True**
- state `persistent_recovery_flow_now` W/fake-L **50.0%/0.0%**; external W/dead **46.2%/0.0%**; agree **True**
- state `current_full_chain` W/fake-L **50.0%/0.0%**; external W/dead **30.8%/0.0%**; agree **True**

## +45m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/3**; external winner/dead **13/5**
- `cum_taker_after10`: strength **1.000** (higher=winner), med W/L **0.0314/-0.0178**; LOO med/min **1.000/1.000**; external **0.708** same direction
- `post30_cum_taker`: strength **1.000** (higher=winner), med W/L **0.2337/-0.1124**; LOO med/min **1.000/1.000**; external **0.800** same direction
- `post30_higher_close_share`: strength **0.917** (higher=winner), med W/L **0.8333/0.0000**; LOO med/min **0.875/0.833**; external **0.815** same direction
- `post30_higher_low_share`: strength **0.833** (higher=winner), med W/L **0.6667/0.3333**; LOO med/min **0.833/0.750**; external **0.808** same direction
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/100.0%**; external W/dead **30.8%/100.0%**; agree **True**
- state `current_flow_positive` W/fake-L **100.0%/33.3%**; external W/dead **69.2%/40.0%**; agree **True**
- state `current_higher_low` W/fake-L **100.0%/33.3%**; external W/dead **76.9%/60.0%**; agree **True**
- state `current_higher_close` W/fake-L **100.0%/33.3%**; external W/dead **53.8%/40.0%**; agree **True**

## +50m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/3**; external winner/dead **13/5**
- `cum_taker_after10`: strength **1.000** (higher=winner), med W/L **0.0590/-0.0107**; LOO med/min **1.000/1.000**; external **0.708** same direction
- `post30_cum_taker`: strength **1.000** (higher=winner), med W/L **0.2440/-0.0541**; LOO med/min **1.000/1.000**; external **0.754** same direction
- `post30_positive_flow_share`: strength **0.917** (higher=winner), med W/L **0.7500/0.2500**; LOO med/min **0.875/0.833**; external **0.692** same direction
- `post30_higher_close_share`: strength **0.917** (higher=winner), med W/L **0.7500/0.2500**; LOO med/min **0.875/0.833**; external **0.808** same direction
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/100.0%**; external W/dead **30.8%/100.0%**; agree **True**
- state `flow_persistent_after_turn` W/fake-L **100.0%/0.0%**; external W/dead **23.1%/0.0%**; agree **True**
- state `current_higher_high` W/fake-L **100.0%/0.0%**; external W/dead **53.8%/40.0%**; agree **True**
- state `current_full_chain` W/fake-L **50.0%/0.0%**; external W/dead **30.8%/0.0%**; agree **True**

## +55m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/3**; external winner/dead **13/5**
- `ema7_dist_r`: strength **1.000** (higher=winner), med W/L **0.0799/-0.0385**; LOO med/min **1.000/1.000**; external **0.831** same direction
- `post30_cum_taker`: strength **1.000** (higher=winner), med W/L **0.2309/-0.0480**; LOO med/min **1.000/1.000**; external **0.692** same direction
- `post30_higher_close_share`: strength **1.000** (higher=winner), med W/L **0.7000/0.2000**; LOO med/min **1.000/1.000**; external **0.723** same direction
- `post30_positive_flow_share`: strength **0.917** (higher=winner), med W/L **0.7000/0.4000**; LOO med/min **0.875/0.833**; external **0.523** same direction
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/100.0%**; external W/dead **30.8%/100.0%**; agree **True**
- state `current_above_ema7` W/fake-L **100.0%/0.0%**; external W/dead **76.9%/20.0%**; agree **True**
- state `ema7_persistent_after_reclaim` W/fake-L **100.0%/0.0%**; external W/dead **69.2%/20.0%**; agree **True**
- state `persistent_recovery_now` W/fake-L **100.0%/0.0%**; external W/dead **69.2%/20.0%**; agree **True**

## +60m causal snapshot
- alive slow-winner/fake-confirm-loser/all-loss: **2/3/3**; external winner/dead **13/5**
- `post30_cum_taker`: strength **1.000** (higher=winner), med W/L **0.1914/-0.0444**; LOO med/min **1.000/1.000**; external **0.677** same direction
- `post30_taker_change`: strength **1.000** (lower=winner), med W/L **-0.4035/0.2397**; LOO med/min **1.000/1.000**; external **0.800** same direction
- `post30_higher_close_share`: strength **1.000** (higher=winner), med W/L **0.5833/0.3333**; LOO med/min **1.000/1.000**; external **0.700** same direction
- `post30_higher_high_share`: strength **0.917** (higher=winner), med W/L **0.6667/0.3333**; LOO med/min **0.875/0.833**; external **0.808** same direction
- state `new_low_after30_vs_25_30` W/fake-L **0.0%/100.0%**; external W/dead **30.8%/100.0%**; agree **True**
- state `current_above_ema7` W/fake-L **50.0%/0.0%**; external W/dead **61.5%/0.0%**; agree **True**
- state `ema7_persistent_after_reclaim` W/fake-L **50.0%/0.0%**; external W/dead **61.5%/0.0%**; agree **True**
- state `persistent_recovery_now` W/fake-L **50.0%/0.0%**; external W/dead **61.5%/0.0%**; agree **True**

## Guardrail
Everything after +30m is descriptive for a *later* decision only. Do not use this run to claim the prior +30m cut was knowable, and do not tune timing or numeric thresholds from these tiny cohorts.
