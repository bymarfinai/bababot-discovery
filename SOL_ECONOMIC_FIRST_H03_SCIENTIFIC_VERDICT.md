# SOL Economic-First H03 — Scientific Verdict

## Status

**SOL_ECONOMIC_FIRST_H03_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run

- Workflow run ID: **34564411585**.
- Job ID: **103153466409**.
- Head SHA: **dfc5053f99ffd5e700cfca7ad425e15ca28fb4e2**.
- Artifact ID: **10185489966**.
- Artifact digest: **sha256:4580c22af29f18c3a4840a1b812ff96eb7887125788229ad1498a8e5be13d0ab**.
- Targeted workflow conclusion: **success**.
- Raw SOLUSDT 5m coverage: **99.7698%**.

## Frozen discovery scope

- SOLUSDT, LONG only.
- One time habitat: **03:00–04:00 UTC / 10:00–11:00 WIB**.
- Four quarter-hour anchors.
- Development 2022–2024 only.
- 90 causal character rules.
- Lookbacks 15/30/60/120/240/360m.
- Holds 60/120/240/360/720/960m.
- Exactly 3,240 unique candidates were present in the Development grid.
- Exact-open entry and exact-open time exit.
- $500 fixed notional and $0.75 round-trip fee.
- No inherited H00–H02 clue, SOL parent, Fibonacci, reference range, visit, breakout, TP, or SL.
- External and Reference Validation unopened.

## Formal result

**0 / 3,240 candidates passed the preregistered anchor-stability + pooled-economics + all-era gate.**

No H03 candidate passed more than one of the three major gates. H03 is materially weaker than the H02 near-pass.

## Strongest broad clue

### RV_MID__RANGE_LOW / LB360 / hold360m

- N **250**.
- WR **56.80%**.
- Net PnL **+$423.96**.
- Expectancy **+$1.70/trade**.
- PF **1.559**.
- Max DD **$110.61**.
- Max loss streak **9**.
- Supportive anchors **4/4**.
- Anchor gate: **PASS**.
- Pooled gate: **FAIL**, solely because loss streak 9 exceeds the frozen limit of 8.
- Cross-era gate: **FAIL** because 2024 economics are negative.

### Quarter-hour behavior

| UTC | WIB | N | WR | Exp | PF | DD | Supportive |
|---:|---:|---:|---:|---:|---:|---:|---|
| 03:00 | 10:00 | 69 | 56.52% | +$1.02 | 1.327 | $39.89 | YES |
| 03:15 | 10:15 | 62 | 59.68% | +$1.99 | 1.654 | $46.07 | YES |
| 03:30 | 10:30 | 58 | 56.90% | +$2.31 | 1.829 | $36.71 | YES |
| 03:45 | 10:45 | 61 | 54.10% | +$1.59 | 1.498 | $40.20 | YES |

### Cross-era Development

| Year | N | WR | Net | Exp | PF |
|---:|---:|---:|---:|---:|---:|
| 2022 | 75 | 61.33% | +$252.00 | +$3.36 | 2.099 |
| 2023 | 98 | 52.04% | +$205.82 | +$2.10 | 1.837 |
| 2024 | 77 | 58.44% | **-$33.85** | **-$0.44** | **0.881** |

The broad anchor consistency is real, but the negative 2024 economics prevent promotion.

## High-WR sparse clue — invalid for promotion

### RV_HIGH__RANGE_LOW / LB360 / hold360m

- N **43**, WR **86.05%**, net **+$199.33**, expectancy **+$4.64**, PF **10.479**, DD **$13.71**.
- Yearly WR: **80.00% / 76.92% / 100.00%**.
- Each quarter-hour contains only **10–12 trades**.
- Evaluable anchors: **0/4**; pooled N is far below the required 160; every yearly N is far below 40.

This is an interesting sparse hypothesis, but it is statistically ineligible under the frozen experiment. The 100% 2024 figure represents only 15 observations and must not be described as a discovered 100%-WR setup.

## Highest frozen-ranking descriptive row

`EFF_LOW__EXT_HIGH / LB120 / hold720m` produced N 183, WR 48.09%, net +$507.65, expectancy +$2.77, PF 1.487, and DD $106.13. Its positive expectancy comes from payoff skew rather than high win rate; it passes none of the three major gates and is not relevant to the high-WR objective.

## Scientific interpretation

H03 contains one broad and anchor-stable character, but its performance is not durable across Development eras. It also contains a very high-WR sparse pocket, but the sample is too small for any formal inference. Neither finding justifies a gate change or OOS exposure.

The correct next experiment is a fresh **04:00–05:00 UTC / 11:00–12:00 WIB** LONG scan with all 3,240 candidates reopened.

## Integrity

- Preregistration commit preceded engine, workflow, trigger, and data inspection.
- Grid audit confirmed 3,240 rows and 3,240 unique candidate keys.
- No gate relaxation or small-sample rescue.
- No second-best promotion.
- No OOS exposure.
- No inherited setup transfer.
- Overlapping-hold economics remain discovery diagnostics, not executable portfolio returns.
