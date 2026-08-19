# Tuesday — Anchored Walk-Forward TRADE/WAIT Engine

**Status: COMPLETE — research only; live BBC untouched.**

## Locked methodology
- Warmup: **52 Tuesdays**.
- Walk-forward predictions: **87 Tuesdays**; each prediction trains only on prior Tuesdays.
- Frozen outcome/execution: Tuesday A5.11 unchanged.
- Model: median imputation + standardization + L2 logistic regression, C=1.
- No feature selection; all predeclared causal pre-entry features are used.
- Primary rule fixed before result: **p(win) >= 0.50 => TRADE; otherwise WAIT**.
- 0.55/0.60 are sensitivity diagnostics only, never candidate selectors.

## Historical expanding walk-forward

| Policy | Opps | Trades | Coverage | Trade WR | PnL | PF | Exp/opportunity | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Always trade | 87 | 87 | 100.0% | 70.1% | $+109.59 | 2.08 | $+1.260 | $14.25 |
| Primary p>=0.50 | 87 | 63 | 72.4% | 71.4% | $+77.38 | 2.05 | $+0.889 | $14.25 |
| Sensitivity p>=0.55 | 87 | 53 | 60.9% | 69.8% | $+53.30 | 1.73 | $+0.613 | $19.00 |
| Sensitivity p>=0.60 | 87 | 38 | 43.7% | 71.1% | $+44.03 | 1.90 | $+0.506 | $14.25 |

Primary minimal robustness gate: **PASS**.

### Chronological blocks — primary only

| Block | Dates | Trades/Opps | WR | PnL | PF |
|---|---|---:|---:|---:|---:|
| B1 | 2024-12-03 → 2025-04-29 | 12/22 | 58.3% | $+6.73 | 1.28 |
| B2 | 2025-05-06 → 2025-09-30 | 12/22 | 66.7% | $+13.49 | 2.19 |
| B3 | 2025-10-07 → 2026-03-03 | 19/22 | 78.9% | $+39.05 | 3.66 |
| B4 | 2026-03-10 → 2026-07-28 | 20/21 | 75.0% | $+18.12 | 1.76 |

## August batch holdout
One model is trained through the Jul-30 cutoff and then frozen across all three August Tuesdays.

| Date | p(win) | Decision | A5.11 PnL | MFE |
|---|---:|---|---:|---:|
| 2026-08-04 | 71.0% | TRADE | $-4.75 | 0.468% |
| 2026-08-11 | 54.3% | TRADE | $-0.82 | 0.193% |
| 2026-08-18 | 66.6% | TRADE | $-0.10 | 0.416% |

- August always-trade frozen A5.11: **$-5.68**.
- August walk-forward model decisions: **3 trades / 0 waits, PnL $-5.68**.

## Guardrail
Causal expanding walk-forward removes future leakage from each historical prediction, but the broader Tuesday dataset and feature vocabulary have prior research exposure. Therefore this is stronger pseudo-OOS evidence, not pristine untouched OOS. August is batch-scored with one Jul30-frozen model and is not used for model selection or refitting.
