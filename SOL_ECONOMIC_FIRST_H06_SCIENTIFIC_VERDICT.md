# SOL Economic-First H06 — Scientific Verdict

## Status

**SOL_ECONOMIC_FIRST_H06_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run

- Workflow run ID: **34573716020**.
- Job ID: **103181325169**.
- Head SHA: **e95a68fdabfec48b7912f41f48415d2d7a8fc860**.
- Artifact ID: **10188788617**.
- Artifact digest: **sha256:aae5afccb4ddb1a9b13641f72f1e8507ef8ffe34b9ebba2df4a0f1cabf2e308e**.
- Targeted workflow conclusion: **success**; raw SOLUSDT 5m coverage **99.7698%**.

## Frozen scope and formal result

- One habitat: **06:00–07:00 UTC / 13:00–14:00 WIB**, LONG only.
- Development 2022–2024; four quarter-hour anchors.
- 90 rules x six lookbacks x six holds = **3,240 unique candidates**.
- External and Reference Validation unopened.

**0 / 3,240 candidates passed the complete anchor + pooled + cross-era gate.**

## Highest frozen-ranking two-gate clue

### EFF_LOW__RANGE_HIGH / LB30 / hold960m

- N **222**, WR **57.66%**, net **+$1,092.18**.
- Expectancy **+$4.92**, PF **1.642**, DD **$231.09**, loss streak **5**.
- Supportive anchors **3/4**.
- Annual WR **57.14% / 59.46% / 56.34%**, positive economics in all years.
- Anchor gate **PASS**; cross-era gate **PASS**; pooled gate **FAIL only on DD**.

This is the strongest frozen-ranked descriptive clue, but its pooled DD is almost twice the $125 ceiling and it is not promoted.

## Closest risk-boundary clue

### EFF_LOW__RANGE_MID / LB360 / hold360m

- N **274**, WR **58.03%**, net **+$390.53**.
- Expectancy **+$1.43**, PF **1.441**.
- DD **$114.72**; max loss streak **12**.
- Supportive anchors **3/4**.
- Annual WR **62.96% / 52.88% / 59.55%**, with positive economics in every year.
- Anchor and cross-era gates **PASS**.
- Pooled gate **FAIL only because loss streak 12 exceeds 8**.

### Quarter-hour behavior

| UTC | WIB | N | WR | Exp | PF | DD | Supportive |
|---:|---:|---:|---:|---:|---:|---:|---|
| 06:00 | 13:00 | 61 | 55.74% | +$1.17 | 1.365 | $43.01 | YES |
| 06:15 | 13:15 | 62 | 56.45% | -$0.08 | 0.978 | $97.17 | NO |
| 06:30 | 13:30 | 76 | 59.21% | +$1.95 | 1.637 | $51.64 | YES |
| 06:45 | 13:45 | 75 | 60.00% | +$2.34 | 1.785 | $53.39 | YES |

## H04 winner cross-hour comparison

The H04 winner `EFF_LOW__RANGE_HIGH / LB360 / hold240m` appears naturally in H06 but produces only WR **53.92%**, DD **$262.18**, loss streak **11**, and negative economics in both 2023 and 2024. It passes only the anchor gate and again confirms that the H04 character should not be transferred across hours.

## Scientific interpretation

H06 has several broad positive characters, but risk sequence remains the binding constraint. One clue has excellent cross-era expectancy but excessive DD; another stays inside the DD ceiling but exceeds the loss-streak ceiling. Neither warrants gate relaxation or OOS exposure.

The correct next experiment is an independent **07:00–08:00 UTC / 14:00–15:00 WIB** LONG scan with all 3,240 candidates reopened.

## Integrity

- Preregistration preceded implementation and data inspection.
- Grid audit confirmed 3,240 unique candidate keys.
- No inherited-winner privilege, gate relaxation, rounding rescue, or OOS exposure.
- Overlapping-hold results are discovery diagnostics, not executable portfolio returns.
