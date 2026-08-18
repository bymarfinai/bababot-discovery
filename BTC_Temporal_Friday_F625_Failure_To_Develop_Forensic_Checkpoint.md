# Friday F6.25 — Failure-to-Develop / Wrong-Direction Forensic

**Status: COMPLETE — FORENSIC ONLY; NO MANAGEMENT RULE TUNED OR PROMOTED.**
**Live BBC untouched; frozen Friday stack unchanged.**

## Cohort parity
- latest five-layer stack PnL: **+138.329**
- failure-to-develop cohort: **24** = D 13 / V 11
- SL/TIMEOUT: **16 / 8**; strict immediate sink **1**
- aggregate parent PnL **-77.360**; median MFE **0.247R**, MAE **1.071R**, peak favorable timing **25.0m**

## Methodological guardrail
Checkpoint features are judged both against all winners and against hard slow-start winners that also have not reached +0.5R at the same checkpoint. This avoids promoting an obvious "has not moved yet" discriminator. No threshold/action PnL optimization is performed.

## Top strictly pre-entry stable separators
- `pre_last_body_ratio`: strength full/D/V 0.667/0.648/0.701, higher=loss; med loss/control 0.6339/0.3859
- `pre_last_upper_wick_ratio`: strength full/D/V 0.651/0.646/0.643, lower=loss; med loss/control 0.0591/0.2200
- `pre_ema_spread`: strength full/D/V 0.594/0.600/0.602, higher=loss; med loss/control -0.0002/-0.0006
- `pre_last_lower_wick_ratio`: strength full/D/V 0.609/0.586/0.654, lower=loss; med loss/control 0.1521/0.2314
- `pre_ema20_slope60`: strength full/D/V 0.566/0.590/0.610, higher=loss; med loss/control -0.0006/-0.0006
- `pre_taker30`: strength full/D/V 0.618/0.644/0.558, higher=loss; med loss/control 0.0044/-0.0683
- `ret120`: strength full/D/V 0.554/0.542/0.597, higher=loss; med loss/control -0.0010/-0.0017
- `pre_ema7_slope30`: strength full/D/V 0.605/0.629/0.528, higher=loss; med loss/control -0.0003/-0.0013

## Top HARD-control trajectory separators
### +5m — target/slow-winner N 23/64
- `cp5_mfe_r`: strength full/D/V 0.654/0.583/0.682, lower=loss; med 0.1258/0.1538
- `cp5_taker`: strength full/D/V 0.586/0.580/0.573, lower=loss; med 0.0729/0.1537
- `cp5_tail2_taker`: strength full/D/V 0.586/0.580/0.573, lower=loss; med 0.0729/0.1537
- `cp5_red_frac`: strength full/D/V 0.634/0.572/0.689, higher=loss; med 1.0000/0.0000
- `cp5_progress_r`: strength full/D/V 0.638/0.564/0.700, lower=loss; med -0.0240/0.0788
- `cp5_mae_r`: strength full/D/V 0.543/0.527/0.518, higher=loss; med 0.0780/0.0502
### +10m — target/slow-winner N 22/58
- `cp10_mfe_r`: strength full/D/V 0.771/0.734/0.763, lower=loss; med 0.1277/0.2336
- `cp10_progress_r`: strength full/D/V 0.693/0.680/0.747, lower=loss; med -0.0242/0.1352
- `cp10_red_frac`: strength full/D/V 0.669/0.662/0.702, higher=loss; med 0.5000/0.5000
- `cp10_lower_high_frac`: strength full/D/V 0.679/0.676/0.659, higher=loss; med 1.0000/0.0000
- `cp10_ema7_dist_r`: strength full/D/V 0.649/0.645/0.646, lower=loss; med -0.0647/0.0255
- `cp10_taker`: strength full/D/V 0.619/0.668/0.571, lower=loss; med -0.0072/0.0822
### +15m — target/slow-winner N 21/53
- `cp15_mfe_r`: strength full/D/V 0.784/0.757/0.778, lower=loss; med 0.1321/0.2543
- `cp15_progress_r`: strength full/D/V 0.654/0.651/0.705, lower=loss; med -0.0252/0.1300
- `cp15_red_frac`: strength full/D/V 0.654/0.642/0.688, higher=loss; med 0.6667/0.3333
- `cp15_ema7_dist_r`: strength full/D/V 0.630/0.608/0.699, lower=loss; med -0.0803/0.0243
- `cp15_below_ema7`: strength full/D/V 0.650/0.607/0.739, higher=loss; med 1.0000/0.0000
- `cp15_last3_progress_slope`: strength full/D/V 0.574/0.592/0.608, lower=loss; med -0.0066/0.0358
### +30m — target/slow-winner N 20/37
- `cp30_progress_r`: strength full/D/V 0.674/0.683/0.727, lower=loss; med -0.0166/0.1032
- `cp30_mfe_r`: strength full/D/V 0.696/0.679/0.627, lower=loss; med 0.1835/0.2887
- `cp30_ema7_dist_r`: strength full/D/V 0.662/0.626/0.736, lower=loss; med -0.0337/0.0528
- `cp30_below_ema7`: strength full/D/V 0.599/0.556/0.723, higher=loss; med 1.0000/0.0000
- `cp30_taker`: strength full/D/V 0.600/0.630/0.555, lower=loss; med 0.0028/0.0274
- `cp30_mae_r`: strength full/D/V 0.551/0.543/0.600, higher=loss; med 0.2076/0.2002
### +60m — target/slow-winner N 15/22
- `cp60_mfe_r`: strength full/D/V 0.809/0.825/0.938, lower=loss; med 0.1884/0.3333
- `cp60_progress_r`: strength full/D/V 0.712/0.714/0.719, lower=loss; med -0.1022/0.0070
- `cp60_ema20_dist_r`: strength full/D/V 0.588/0.579/0.594, lower=loss; med -0.0770/-0.0574
- `cp60_below_ema20`: strength full/D/V 0.592/0.567/0.688, higher=loss; med 1.0000/1.0000
- `cp60_tail2_taker`: strength full/D/V 0.597/0.556/0.688, higher=loss; med 0.0470/-0.1898
- `cp60_below_ema7`: strength full/D/V 0.571/0.552/0.625, higher=loss; med 1.0000/1.0000

## Guardrail
Any next action test must be predeclared from a causal mechanism that survives the hard slow-start-winner control. Do not tune checkpoint timing or numeric cutoffs on this sample.
