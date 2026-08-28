# BNB Session-Native LONG M9 MICRO_HL Shallow Guardrail — B27EU Result

Raw BNB 5m coverage: **100.0000%**.

Frozen rule: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**, with one guardrail `entry_depth_R <= 0.324528R`.

Holdout: **external 2020-01-01 → 2022-01-01 only**.

## External economics

| Cohort | N | Retention | Net WR | Avg net/trade | Total PnL @ $500 | PF | Max DD | Median RR | SL-before-H share of losses | Med entry depth |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RAW_MICRO_HL_EXTERNAL | 38 | 100.0% | 31.6% | -0.343% | $-65.13 | 0.53 | $82.80 | 1.41 | 61.5% | 0.123R |
| SHALLOW_MICRO_HL_EXTERNAL | 33 | 86.8% | 30.3% | -0.444% | $-73.30 | 0.39 | $94.37 | 1.39 | 56.5% | 0.117R |

## Preregistered support contract

- Shallow N >= 10: **33** → PASS
- Retention >= 50%: **86.8%** → PASS
- Shallow avg net > 0: **-0.444%** → FAIL
- Shallow PF > 1.0: **0.39** → FAIL
- Avg-net improvement >= +0.050pp vs raw: **-0.101pp** → FAIL
- Strong-support PF >= 1.20: **0.39**

**Verdict: NOT_SUPPORTED**

This is a frozen external replication of one development-derived guardrail; no alternate threshold is selected here.

**Status: B27EU_BNB_MICROHL_SHALLOW_EXTERNAL_NOT_SUPPORTED**

STOP: no second feature, no threshold retuning, no reference-validation, no August, no SHORT/live integration.
