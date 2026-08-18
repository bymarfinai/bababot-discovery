# Sunday Friday-Method SF5 — Failure-to-Develop Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE PROMOTED.**

- Failure-to-develop cohort **51** = D 30 / V 21, aggregate PnL **$-338.11**.
- SL/TIMEOUT **40/11**; median MFE **0.205R**, MAE **1.081R**.

## Top separators vs HARD slow-start winners
### +2h — target/slow winner 50/59
- `cp120_mfe_r` strength full/D/V **0.707/0.699/0.718**, lower=loss; med loss/control 0.0980/0.2053
- `cp120_progress_r` strength full/D/V **0.676/0.696/0.640**, lower=loss; med loss/control -0.0254/0.0940
- `cp120_close_vs_ema20_r` strength full/D/V **0.646/0.682/0.571**, higher=loss; med loss/control 0.0014/-0.0199
- `cp120_above20` strength full/D/V **0.557/0.564/0.546**, higher=loss; med loss/control 1.0000/0.0000
### +4h — target/slow winner 47/47
- `cp240_mfe_r` strength full/D/V **0.672/0.691/0.635**, lower=loss; med loss/control 0.1434/0.2389
- `cp240_above20` strength full/D/V **0.606/0.615/0.596**, higher=loss; med loss/control 1.0000/0.0000
- `cp240_progress_r` strength full/D/V **0.660/0.713/0.585**, lower=loss; med loss/control -0.1199/0.0178
- `cp240_mae_r` strength full/D/V **0.632/0.683/0.550**, higher=loss; med loss/control 0.3011/0.1864
- `cp240_close_vs_ema20_r` strength full/D/V **0.579/0.606/0.532**, higher=loss; med loss/control 0.0153/-0.0174
- `cp240_green_frac` strength full/D/V **0.574/0.613/0.519**, higher=loss; med loss/control 0.5208/0.4792
### +6h — target/slow winner 42/32
- `cp360_progress_r` strength full/D/V **0.757/0.829/0.705**, lower=loss; med loss/control -0.2398/0.0311
- `cp360_green_frac` strength full/D/V **0.700/0.662/0.752**, higher=loss; med loss/control 0.5208/0.4861
- `cp360_mfe_r` strength full/D/V **0.684/0.658/0.705**, lower=loss; med loss/control 0.1677/0.2811
- `cp360_close_vs_ema7_r` strength full/D/V **0.651/0.630/0.710**, higher=loss; med loss/control 0.0221/-0.0061
- `cp360_close_vs_ema20_r` strength full/D/V **0.668/0.615/0.754**, higher=loss; med loss/control 0.0559/-0.0235
- `cp360_above7` strength full/D/V **0.622/0.603/0.661**, higher=loss; med loss/control 1.0000/0.0000

## Guardrail
Forensic only. Hard slow-start winner control prevents trivial no-movement rules. No action timing or threshold optimized.
