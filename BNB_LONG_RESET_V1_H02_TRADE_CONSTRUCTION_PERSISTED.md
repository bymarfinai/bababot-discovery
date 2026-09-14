# BNB LONG Reset V1 — H02 Trade Construction PERSISTED

## Verdict

**CONSTRUCTION_FAIL**

Frozen structural character:
- BNBUSDT perpetual
- LONG only
- 02:00–03:00 WIB
- all four quarter-hour anchors retained
- primary `rv_ratio_60_240__HIGH`
- secondary `efficiency_60m__HIGH`

Construction selection was performed on **Development 2022–2024 only**. Known OOS 2025-01-01 through 2026-07-30 was not read or used by the construction runner for selection or ranking.

Frozen construction prereg commit: `066bae7fb1af733b4c431a0b8495e404f1e306a0`

Workflow provenance:
- GitHub Actions run: **34806719308**
- Trigger/head SHA: `aa0fd8451c65fd039fac12c2dd2c977f382097f8`
- Artifact ID: **10332499383**
- Artifact SHA256: **b8d752c173c774698797d01e23f9dfec6ed396bf5b1cd158ba00f373f900ab82**
- Data coverage: **100.0000%**

## Frozen construction conditions

- Structural Development signals: **483**
- Candidate constructions: **29**
- Overlap: **ONE_POSITION / NO STACKING**
- Entry: anchor 5m open
- Same-bar TP+SL: **SL adverse-first**
- Modeled round-trip cost: **0.12%**
- Reference notional: **$500/trade**
- Full-gate passers: **0**

Therefore no executable construction may be promoted from this stage.

## Strongest candidate — TIME_360m

`TIME_360m` was the strongest candidate and is useful diagnostically, but it **does not pass the frozen construction gate**.

| Metric | TIME_360m |
|---|---:|
| Structural signals | 483 |
| Executed trades | **270** |
| Skipped overlap | **213** |
| Trades/week | **1.72** |
| Net WR | **53.70%** |
| Net mean/trade | **+0.2506%** |
| Net PF | **1.553** |
| Net total @ $500 | **+$338.32** |
| Net max DD @ $500 | **-$60.11** |
| Max loss streak | **5** |
| Positive quarters | **9/12** |
| Pooled gate | **PASS** |
| Year gate | **PASS** |
| Quarter gate | **FAIL** |

Annual economics all pass:

| Year | N | Net WR | Net mean | Net PF | Annual gate |
|---:|---:|---:|---:|---:|---|
| 2022 | 88 | 55.68% | **+0.1083%** | **1.191** | PASS |
| 2023 | 87 | 51.72% | **+0.2786%** | **1.840** | PASS |
| 2024 | 95 | 53.68% | **+0.3568%** | **1.775** | PASS |

The failure is specifically the preregistered per-year quarter-consistency rule requiring every calendar year to have at least **2/4 positive-net quarters**.

TIME_360m quarter means:
- 2022Q1: **-0.2139%**
- 2022Q2: **+0.6795%**
- 2022Q3: **-0.0190%**
- 2022Q4: **-0.0592%**
- 2023Q1: **+0.5114%**
- 2023Q2: **+0.0688%**
- 2023Q3: **+0.2667%**
- 2023Q4: **+0.1942%**
- 2024Q1: **+0.2545%**
- 2024Q2: **+0.0663%**
- 2024Q3: **+0.4806%**
- 2024Q4: **+0.5752%**

Thus:
- 2022 positive quarters: **1/4 → FAIL**
- 2023 positive quarters: **4/4**
- 2024 positive quarters: **4/4**

It would be post-hoc rule relaxation to promote TIME_360m now merely because pooled and annual economics look attractive.

## TIME_240m diagnostic

`TIME_240m` also fails more fundamentally:
- N 270
- 1.72 trades/week
- net WR 52.22%
- net mean +0.0958%
- net PF 1.247
- net total +$129.36
- 9/12 positive quarters
- pooled gate PASS
- **year gate FAIL** because 2022 mean **-0.0694%**, PF **0.874**
- quarter gate FAIL because 2022 again has only 1/4 positive quarters.

This confirms that the longer-hold family is directionally best, but under the frozen standard no candidate is sufficiently consistent to promote.

## Locked consequence

**STOP_NO_RETUNE**

Do not:
- loosen the quarter gate after seeing this result;
- delete 2022 or selected 2022 quarters;
- remove the 02:30 anchor because known OOS disliked it;
- add a new feature/filter to rescue TIME_360m;
- optimize the cost assumption;
- select a construction from known OOS;
- run executable OOS construction validation, because no Development construction was promoted.

H02 remains a valid **structural OOS-passing character**, but under Reset V1 it has **not converted into a frozen executable trade construction**. It is therefore **not READY TO TRADE**.

Research/shadow only.
