# BNB LONG Reset V1 — H02 Structural Stress / Secondary Confirmation PREREG

Status: **FROZEN BEFORE STRESS-TEST RESULTS**

Primary character is immutable for this stage:
- Habitat: **02:00–03:00 WIB**
- Side: **LONG only**
- Primary: **`rv_ratio_60_240__HIGH`**
- Frozen HIGH boundary: causal percentile **>= 2/3** using the previous 60 same-anchor observations with minimum history 40.
- Development only: **2022–2024 WIB**
- OOS 2025-01-01 through 2026-07-30 remains **SEALED / not downloaded / not evaluated**.
- H03+ scanning remains blocked while H02 is in promoted structural validation.

This stage may validate or reject the already-selected H02 primary. It may not replace it, rescue it with a new primary, change the habitat, optimize hold/TP/SL/leverage, or expose OOS.

## A. Overlap / pseudo-sample stress

Because H02 contains four quarter-hour anchors and forward-return diagnostics overlap, the primary must survive day-clustered checks.

Two deterministic reductions are evaluated:
1. **FIRST_PER_DAY** — earliest qualifying primary signal in each WIB calendar day.
2. **DAILY_MEAN** — one observation per WIB day equal to the mean consensus return of all qualifying primary signals that day.

Each reduction passes if:
- N >= 300 WIB days;
- pooled WR >= 53%;
- pooled mean return > 0;
- pooled PF >= 1.10;
- each 2022/2023/2024 has N >= 90, mean > 0, PF >= 1.05, WR >= 51%.

Both reductions must pass.

A deterministic day-cluster bootstrap (seed 20260913, 10,000 resamples of WIB days) is also run on DAILY_MEAN. Bootstrap passes if the 95% percentile CI lower bound for mean return is > 0.

## B. HIGH-boundary sensitivity

This is a sensitivity test only; it does **not** redefine the frozen primary boundary.

Evaluate `rv_ratio_60_240_pct >= cutoff` at:
- 0.600
- 0.625
- 0.6666667 (frozen center)
- 0.700
- 0.750

A cutoff is supportive if pooled N >= 300, WR >= 53%, mean > 0, PF >= 1.10.

Sensitivity gate passes if:
- at least 4/5 cutoffs are supportive;
- the frozen center plus both immediate neighbors (0.625 and 0.700) are supportive;
- no cutoff has a negative pooled mean.

## C. Causal percentile-window sensitivity

Recompute `rv_ratio_60_240` causal percentiles independently for each quarter-hour anchor using previous observations only, with windows:
- 40
- 60 (frozen center)
- 90
- 120

Minimum history is min(40, window). Apply the same frozen HIGH boundary >= 2/3.

A window is supportive if:
- pooled N >= 300;
- WR >= 53%;
- mean > 0;
- PF >= 1.10;
- at least 2/3 years have N >= 80, WR >= 51%, mean > 0, PF >= 1.02.

Window-sensitivity gate passes if at least 3/4 windows are supportive and the frozen 60-observation window is supportive.

## D. Quarter consistency

Evaluate the frozen primary separately for the 12 calendar quarters from 2022Q1 through 2024Q4.

Quarter-consistency gate passes if:
- at least 9/12 quarters have positive mean return;
- at least 9/12 quarters have PF > 1.00;
- every calendar year has at least 2/4 positive-mean quarters.

Quarter results are diagnostics; no quarter may be excluded from the primary after seeing results.

## E. Secondary confirmation search

Secondary confirmation is **optional**. Failure to find a secondary does not fail a primary that passes A–D.

Candidate secondaries are exactly one additional preregistered Stage-2 feature/state, conditioned on the frozen primary. The selected primary feature `rv_ratio_60_240` itself is excluded, so this stage cannot merely tighten the same variable. No pairwise secondary combinations are allowed.

Eligible secondary candidates:
- LOW/MID/HIGH state of every other numeric Stage-2 feature;
- TRUE/FALSE state of each Stage-2 binary feature.

A secondary can be promoted only if all are true:
- N >= 400 total;
- N >= 100 in each 2022/2023/2024;
- pooled WR improves by >= 1.00 percentage point versus frozen primary;
- pooled mean return improves by >= 10% versus frozen primary;
- pooled PF improves by >= 0.05 versus frozen primary and is >= 1.30;
- raw max drawdown is no worse than the frozen primary;
- every year: WR >= 53%, mean > 0, PF >= 1.10;
- at least 3/4 quarter-hour anchors are supportive with N >= 50, WR >= 53%, mean > 0, PF >= 1.10.

If multiple secondaries pass, deterministic ranking is:
1. highest minimum yearly mean return;
2. highest pooled PF;
3. highest pooled mean return;
4. highest pooled WR;
5. highest N;
6. lexical rule tie-break.

No secondary may be added later merely because OOS or trade construction underperforms.

## F. Structural-stage verdict

- **STRUCTURAL_PASS_WITH_SECONDARY**: A–D all pass and a secondary passes E. Freeze primary + selected secondary; next stage is untouched OOS.
- **STRUCTURAL_PASS_PRIMARY_ONLY**: A–D all pass and no secondary passes E. Freeze primary alone; next stage is untouched OOS.
- **STRUCTURAL_FAIL**: any mandatory gate A–D fails. Reject H02 promoted character and only then may next-hour discovery be reopened under the frozen reset methodology.
- **INSUFFICIENT_DATA**: data integrity/coverage prevents a valid stress verdict.

No TP/SL, fees, slippage, leverage, position sizing, final hold, or execution optimization belongs to this stage.
