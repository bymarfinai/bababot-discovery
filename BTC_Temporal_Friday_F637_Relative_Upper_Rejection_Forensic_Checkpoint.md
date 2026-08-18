# Friday F6.37 — Relative Upper-Rejection Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched.**

## Cohorts
- primary F6.36 morphology signals: **1 winner vs 2 losers**
- branch-matched no-divergence control: **8 winners vs 6 true-dead**
- broad control: **13 winners vs 9 true-dead**

## Strongest relative continuous features with direction agreement
- `rel_last_upper`: primary **1.000 higher=winner** (0.1571/0.0193); branch **0.958**; broad **0.821**; D 0.800, V 1.000
- `rel_body_delta_prev3median`: primary **1.000 lower=winner** (0.1128/0.2330); branch **0.938**; broad **0.803**; D 0.900, V 1.000
- `rel_upper_delta_prev3max`: primary **0.500 higher=winner** (-0.3965/-0.5155); branch **0.750**; broad **0.709**; D 0.800, V 0.750
- `rel_upper_delta_prev3median`: primary **0.500 higher=winner** (-0.3544/-0.4110); branch **0.688**; broad **0.615**; D 0.900, V 0.667
- `rel_upper_delta_prev2max`: primary **0.500 higher=winner** (-0.3965/-0.5155); branch **0.604**; broad **0.598**; D 0.700, V 0.500
- `rel_upper_delta_prev1`: primary **1.000 higher=winner** (-0.3544/-0.5155); branch **0.583**; broad **0.650**; D 0.600, V 0.500
- `rel_last_body`: primary **1.000 higher=winner** (0.4744/0.3977); branch **0.896**; broad **0.778**; D 0.900, V 1.000
- `rel_body_delta_prev1`: primary **1.000 higher=winner** (0.3652/0.2829); branch **0.792**; broad **0.761**; D 0.600, V 1.000
- `rel_last_upper_share`: primary **1.000 higher=winner** (0.2988/0.0302); branch **0.771**; broad **0.654**; D 0.700, V 1.000
- `rel_last_lower`: primary **1.000 lower=winner** (0.3686/0.5829); branch **0.708**; broad **0.641**; D 0.700, V 0.833

## Natural relative-state clues
- `rel_body_contract3median`: primary W/L-rate **0.0%/0.0%**; branch W/dead **62.5%/0.0%**; broad W/dead **61.5%/11.1%**; agree branch/broad/DV **False/False/True**
- `rel_body_lt_prev1`: primary W/L-rate **0.0%/0.0%**; branch W/dead **62.5%/0.0%**; broad W/dead **53.8%/11.1%**; agree branch/broad/DV **False/False/True**
- `rel_last_red`: primary W/L-rate **100.0%/100.0%**; branch W/dead **50.0%/100.0%**; broad W/dead **46.2%/100.0%**; agree branch/broad/DV **False/False/True**
- `rel_wick_dominant`: primary W/L-rate **100.0%/100.0%**; branch W/dead **62.5%/16.7%**; broad W/dead **53.8%/33.3%**; agree branch/broad/DV **False/False/True**
- `rel_f636_morphology`: primary W/L-rate **100.0%/100.0%**; branch W/dead **62.5%/16.7%**; broad W/dead **53.8%/33.3%**; agree branch/broad/DV **False/False/True**
- `rel_upper_present`: primary W/L-rate **100.0%/100.0%**; branch W/dead **100.0%/66.7%**; broad W/dead **100.0%/66.7%**; agree branch/broad/DV **False/False/True**
- `rel_upper_localmax4`: primary W/L-rate **0.0%/0.0%**; branch W/dead **12.5%/0.0%**; broad W/dead **30.8%/11.1%**; agree branch/broad/DV **False/False/True**
- `rel_upper_gt_prev1`: primary W/L-rate **0.0%/0.0%**; branch W/dead **12.5%/0.0%**; broad W/dead **38.5%/22.2%**; agree branch/broad/DV **False/False/True**
- `rel_upper_gt_prev2max`: primary W/L-rate **0.0%/0.0%**; branch W/dead **12.5%/0.0%**; broad W/dead **30.8%/22.2%**; agree branch/broad/DV **False/False/True**
- `rel_last_upper_gt_lower`: primary W/L-rate **0.0%/0.0%**; branch W/dead **25.0%/16.7%**; broad W/dead **38.5%/22.2%**; agree branch/broad/DV **False/False/True**
- `rel_upper_share_gt_prev3median`: primary W/L-rate **0.0%/0.0%**; branch W/dead **12.5%/16.7%**; broad W/dead **23.1%/33.3%**; agree branch/broad/DV **False/False/True**
- `rel_rejection_expansion_composite`: primary W/L-rate **0.0%/0.0%**; branch W/dead **0.0%/0.0%**; broad W/dead **23.1%/11.1%**; agree branch/broad/DV **False/False/True**

## Primary 1W/2L detail
- `2024-01-19` discovery: parent +0.646; upper 0.1571; lower 0.3686; body 0.4744; upper-vs-prev3max -0.3965; body-vs-prev3med +0.1128; localmax4 False; contract3 False; composite False
- `2025-08-29` validation: parent -4.250; upper 0.0380; lower 0.6031; body 0.3588; upper-vs-prev3max -0.6506; body-vs-prev3med +0.2059; localmax4 False; contract3 False; composite False
- `2026-03-27` validation: parent -4.250; upper 0.0007; lower 0.5627; body 0.4366; upper-vs-prev3max -0.3805; body-vs-prev3med +0.2601; localmax4 False; contract3 False; composite False

## Guardrail
Primary is only 1 winner vs 2 losers and was selected from the same sample. A clean separator matters only if its direction also persists in branch-matched, broad, and available D/V controls. No numeric threshold, timing, or economic action is promoted from this run.
