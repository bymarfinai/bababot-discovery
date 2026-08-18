# Friday F6.30 — F6.29 False-Positive Winner Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched; F6.29 remains failed and is NOT frozen.**

## Cohorts
- false-positive future winners cut by F6.29: **3** (all discovery)
- parent losers cut by F6.29: **9**
- broader cross-control: **13 future winners vs 9 true-dead**

## Strongest +20m causal separators with external direction agreement
- `pre_taker30`: subset strength **0.889** (lower=winner), med winner/loss **-0.1175/-0.0185**; LOO median/min **0.875/0.875**; external strength **0.658** same direction
- `b4_low_r`: subset strength **0.889** (lower=winner), med winner/loss **-0.4561/-0.2065**; LOO median/min **0.875/0.833**; external strength **0.650** same direction
- `ret30`: subset strength **0.852** (lower=winner), med winner/loss **-0.0032/-0.0011**; LOO median/min **0.833/0.833**; external strength **0.504** same direction
- `seq_progress_r`: subset strength **0.852** (lower=winner), med winner/loss **-0.2908/-0.0756**; LOO median/min **0.833/0.778**; external strength **0.521** same direction
- `b4_ret_r`: subset strength **0.852** (lower=winner), med winner/loss **-0.2908/-0.0756**; LOO median/min **0.833/0.778**; external strength **0.521** same direction
- `post10_taker_change`: subset strength **0.852** (higher=winner), med winner/loss **0.2839/0.0369**; LOO median/min **0.833/0.778**; external strength **0.675** same direction
- `post10_min_low_r`: subset strength **0.852** (lower=winner), med winner/loss **-0.5170/-0.2691**; LOO median/min **0.833/0.778**; external strength **0.692** same direction
- `seq_current_higher_high`: subset strength **0.833** (lower=winner), med winner/loss **0.0000/1.0000**; LOO median/min **0.823/0.812**; external strength **0.564** same direction
- `b4_higher_high`: subset strength **0.833** (lower=winner), med winner/loss **0.0000/1.0000**; LOO median/min **0.823/0.812**; external strength **0.564** same direction
- `b3_taker`: subset strength **0.815** (lower=winner), med winner/loss **-0.3356/-0.1227**; LOO median/min **0.792/0.778**; external strength **0.556** same direction
- `b3_ret_r`: subset strength **0.778** (lower=winner), med winner/loss **-0.2908/-0.1508**; LOO median/min **0.792/0.667**; external strength **0.650** same direction
- `b3_high_r`: subset strength **0.778** (lower=winner), med winner/loss **-0.1450/-0.0096**; LOO median/min **0.750/0.722**; external strength **0.667** same direction

## Natural boolean clues
- `seq_current_higher_high`: false-winner/loss **0.0%/66.7%**; external winner/dead **53.8%/66.7%**; direction agreement **True**
- `b4_higher_high`: false-winner/loss **0.0%/66.7%**; external winner/dead **53.8%/66.7%**; direction agreement **True**
- `b4_red`: false-winner/loss **66.7%/33.3%**; external winner/dead **38.5%/33.3%**; direction agreement **True**
- `seq_current_higher_close`: false-winner/loss **33.3%/66.7%**; external winner/dead **61.5%/66.7%**; direction agreement **True**
- `b4_higher_close`: false-winner/loss **33.3%/66.7%**; external winner/dead **61.5%/66.7%**; direction agreement **True**
- `b3_high_touched_ema7`: false-winner/loss **0.0%/33.3%**; external winner/dead **30.8%/33.3%**; direction agreement **True**
- `pre_last_red`: false-winner/loss **100.0%/100.0%**; external winner/dead **46.2%/100.0%**; direction agreement **True**
- `seq_ema7_reclaim_any`: false-winner/loss **0.0%/0.0%**; external winner/dead **61.5%/22.2%**; direction agreement **True**
- `seq_current_above_ema7`: false-winner/loss **0.0%/0.0%**; external winner/dead **61.5%/22.2%**; direction agreement **True**
- `b4_high_touched_ema7`: false-winner/loss **33.3%/33.3%**; external winner/dead **76.9%/44.4%**; direction agreement **True**

## Guardrail
All 3 false-positive winners are discovery cases. Treat any apparent perfect separator as hypothesis-generation only. The next step may freeze ONE simple natural-state protection only if the signal also agrees with the broader 13-winner vs 9-dead cross-control; otherwise stop rather than overfit.
