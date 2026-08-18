# Friday F6.35 — Remaining +20m False-Cut Winner Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched; F6.34 remains same-sample diagnostic and is NOT frozen.**

## Cohorts
- primary no-divergence +20 cuts: **1 future winner vs 5 losers**; winner `2024-01-19`
- branch-matched +20-alive WATCH control: **8 winners vs 6 true-dead**
- branch D/V: **5/2** W/dead and **3/4** W/dead
- broad control: **13 winners vs 9 true-dead**

## Strongest +20m features with direction agreement in primary + branch + broad + available D/V
- `pre_last_upper_wick_ratio`: primary **1.000 higher=winner** (winner/loss med 0.1571/0.0367); branch **0.958**; broad **0.821**; D 0.800, V 1.000
- `pre_last_body_ratio`: primary **0.600 lower=winner** (winner/loss med 0.4744/0.6311); branch **0.896**; broad **0.778**; D 0.900, V 1.000
- `range_pos4h`: primary **0.800 higher=winner** (winner/loss med 0.4581/0.1714); branch **0.854**; broad **0.632**; D 0.700, V 0.917
- `retr_from_high4h`: primary **0.800 lower=winner** (winner/loss med 0.5419/0.8286); branch **0.854**; broad **0.632**; D 0.700, V 0.917
- `pre240_entry_pos`: primary **0.800 higher=winner** (winner/loss med 0.4581/0.1714); branch **0.854**; broad **0.632**; D 0.700, V 0.917
- `b3_upper_wick_ratio`: primary **1.000 lower=winner** (winner/loss med 0.0149/0.3270); branch **0.833**; broad **0.726**; D 0.800, V 0.917
- `b3_body_ratio`: primary **1.000 higher=winner** (winner/loss med 0.5665/0.3636); branch **0.792**; broad **0.744**; D 0.900, V 0.833
- `pre240_dist_high_r`: primary **0.600 lower=winner** (winner/loss med 1.0257/1.0695); branch **0.792**; broad **0.641**; D 0.900, V 0.917
- `seq_ema7_hold_streak`: primary **0.500 higher=winner** (winner/loss med 0.0000/0.0000); branch **0.750**; broad **0.714**; D 0.800, V 0.917
- `b2_ret_r`: primary **0.800 lower=winner** (winner/loss med -0.1505/-0.1030); branch **0.750**; broad **0.667**; D 0.700, V 0.667
- `pre240_dist_low_r`: primary **0.800 higher=winner** (winner/loss med 0.8725/0.2949); branch **0.750**; broad **0.615**; D 0.500, V 0.833
- `b4_quote_volume`: primary **1.000 lower=winner** (winner/loss med 34035842.6044/62701855.0150); branch **0.729**; broad **0.556**; D 0.900, V 0.750

## Natural boolean clues
- `seq_current_higher_low`: primary winner/loss-rate **100.0%/60.0%**; branch W/dead **100.0%/66.7%**; broad W/dead **61.5%/44.4%**; agree branch/broad **True/True**
- `b4_higher_low`: primary winner/loss-rate **100.0%/60.0%**; branch W/dead **100.0%/66.7%**; broad W/dead **61.5%/44.4%**; agree branch/broad **True/True**
- `guard_new_lower_low`: primary winner/loss-rate **0.0%/40.0%**; branch W/dead **0.0%/33.3%**; broad W/dead **38.5%/55.6%**; agree branch/broad **True/True**
- `guard_taker_improves`: primary winner/loss-rate **100.0%/60.0%**; branch W/dead **87.5%/66.7%**; broad W/dead **92.3%/77.8%**; agree branch/broad **True/True**
- `seq_current_higher_high`: primary winner/loss-rate **0.0%/80.0%**; branch W/dead **62.5%/83.3%**; broad W/dead **53.8%/66.7%**; agree branch/broad **True/True**
- `b4_higher_high`: primary winner/loss-rate **0.0%/80.0%**; branch W/dead **62.5%/83.3%**; broad W/dead **53.8%/66.7%**; agree branch/broad **True/True**
- `pre_last_red`: primary winner/loss-rate **100.0%/100.0%**; branch W/dead **50.0%/100.0%**; broad W/dead **46.2%/100.0%**; agree branch/broad **False/False**
- `seq_ema7_reclaim_any`: primary winner/loss-rate **0.0%/0.0%**; branch W/dead **75.0%/33.3%**; broad W/dead **61.5%/22.2%**; agree branch/broad **False/False**
- `seq_current_above_ema7`: primary winner/loss-rate **0.0%/0.0%**; branch W/dead **75.0%/33.3%**; broad W/dead **61.5%/22.2%**; agree branch/broad **False/False**
- `seq_unrepaired_now`: primary winner/loss-rate **100.0%/80.0%**; branch W/dead **25.0%/66.7%**; broad W/dead **38.5%/66.7%**; agree branch/broad **False/False**
- `b4_high_touched_ema7`: primary winner/loss-rate **0.0%/40.0%**; branch W/dead **87.5%/50.0%**; broad W/dead **76.9%/44.4%**; agree branch/broad **False/False**
- `seq_struct_repair_any`: primary winner/loss-rate **0.0%/0.0%**; branch W/dead **62.5%/33.3%**; broad W/dead **38.5%/22.2%**; agree branch/broad **False/False**

## Guardrail
There is only one remaining primary winner. A perfect-looking separator is not evidence by itself. The only useful output is a causal hypothesis whose direction also persists in the larger branch-matched and broad controls. No rule is promoted from this run.
