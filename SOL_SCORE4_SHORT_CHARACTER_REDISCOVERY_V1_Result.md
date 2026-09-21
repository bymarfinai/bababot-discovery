# SOL Score-4 SHORT Character Rediscovery V1 — Result

- 5m coverage: **99.769767%**
- Scope: Score-4 BUY_SIDE liquidity -> SHORT only.
- One-shot structural rediscovery; post-cutoff data CLOSED.
- No numeric threshold search, session/hour filter, indicator, MFE/MAE or future-path feature.

## Historical baseline 2020-2024

- N: **16**
- Structural-event rate: **37.50%**
- Structural-completion mean R: **-0.436R**
- PF: **0.419**

## Frozen structural character

**RECLAIM_INSIDE_DEPTH_EXCEEDS_SWEEP_OVERSHOOT AND APPROACH_3BAR_STAIRCASE**

- Selected N: **5**
- Event rate: **80.00%**
- Lift vs baseline: **42.50 pp**
- Mean R: **0.342R**
- PF: **1.856**
- Event years represented: **3**
- LOO mean>0 survival: **100.00%**
- LOO event-rate>=50% survival: **100.00%**
- Wilson 95% lower bound: **37.55%**

## Retrospective consistency

| Period | Baseline N | Baseline event | Baseline mean R | Selected N | Selected event | Selected mean R | PF | Evaluable | Support |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| RETRO_2025 | 5 | 40.00% | 0.215 | 0 | n/a | n/a | n/a | NO | N/A |
| RETRO_2026_PRE | 8 | 12.50% | -0.493 | 0 | n/a | n/a | n/a | NO | N/A |

**STATUS: SCORE4_SHORT_STRUCTURAL_CHARACTER_FROZEN_RETROSPECTIVE_MIXED**

**OPERATIONAL DECISION: DROP_SCORE4_SHORT_FROM_TRADABLE_UNIVERSE**

No threshold rescue or second rediscovery is permitted.

POST_CUTOFF_DATA=CLOSED
