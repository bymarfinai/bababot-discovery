# SOL Regime + Phase Detector V2 — Stage 6A Legacy Concept Audit

**Purpose:** identify which older BabaBot concepts may be reused as ideas and which must not be inherited as the new phase engine.

## Sources reviewed

- `continuation_detector_endpoint.py`
- `BTC_Temporal_Saturday_A724_A727_Preentry_Exhaustion_Checkpoint.md`
- `research/registry_entries/B27BM.md`
- `BTC_Temporal_Friday_A617_A620_ParityCorrect_Checkpoint.md`
- Stage 5 / 5F SOL regime results already preserved in this branch history

## Findings

| Legacy concept | Audit finding | Stage 6 decision |
|---|---|---|
| V2 `TREND` | Means directional regime is active; does not distinguish fresh vs mature vs exhausted trend. | TOO COARSE |
| V2 `PULLBACK` | Useful lifecycle concept, but one EMA touch cannot define continuation quality. | KEEP AS FEATURE/EVENT |
| V2 `INVALIDATED` | Useful for transition evidence; old timeout logic is not phase ground truth. | KEEP CONCEPT, REBUILD |
| V2 continuation reclaim | Encodes renewal after pullback, relevant to Healthy Continuation. | KEEP AS CANDIDATE FEATURE |
| Old swing confirmation | Can arrive many hours after actual directional move. Stage 5F showed the largest observed edge drop at structure break -> structure confirm. | DO NOT USE AS PHASE ANCHOR ALONE |
| Saturday `PUMP_TREND_NEAR_PH` | Historical BTC research found a locally bullish, above-EMA, rising context near prior high could be a lower-quality BUY / exhaustion-like state. | SUPPORTS ORTHOGONAL EXHAUSTION CONCEPT |
| Friday stretched decline lesson | Failed BUY / bearish direction did not imply unlimited downside continuation; chasing deep downside stretch could chase exhaustion. | EXHAUSTION MUST BE SYMMETRIC |
| BTC SIDEWAYS age-hazard | SIDEWAYS behavior changed with episode age; first 4H bar was more continuation-like, later 8-12H became more transition-heavy in that study. | SIDEWAYS MUST HAVE PHASE/AGE FEATURES |
| Stage 5 SOL | V1 BULL aligned ±1% first-hit 48.3%; BEAR aligned 49.5%; SIDEWAYS approximately balanced. | V1 DIRECTION IS NOT PHASE GROUND TRUTH |
| Stage 5F SOL | M0/M1 only ~51-52% aligned; M4 46.4%; all milestones had negative median aligned future 24H return. | DIRECTIONAL HISTORY != REMAINING ENERGY |

## Critical design correction

The old architecture was effectively:

`REGIME -> TREND/PULLBACK -> EVENT`

The revised architecture must represent:

`REGIME CONTEXT -> LIFECYCLE PHASE -> QUALITY / EVENT`

where the directional lifecycle explicitly distinguishes:

- fresh expansion,
- renewed continuation,
- mature extension,
- exhaustion,
- transition.

## Key lesson from Stage 5F

The redesign must not assume that simply removing hysteresis or speeding up swing confirmation is enough.

Observed 24H aligned ±1% first-hit in Stage 5F:

- impulse start: ~51.4%
- structure break: ~51.7%
- structure confirm: ~47.4%
- raw score switch: ~50.1%
- final switch: ~46.4%

Therefore:

> the missing information is not only **direction** or **latency**; it is likely **remaining directional quality / lifecycle state**.

This is why Stage 6 focuses on phase and remaining-energy features.

## What must not be copied into Stage 6C

- old V2 TREND = Healthy Continuation
- old BULL/BEAR = directional truth
- old SIDEWAYS = balance truth
- simple age bucket = phase
- EMA distance alone = exhaustion
- RSI/CCI overbought/oversold alone = exhaustion
- swing confirmation alone = Early Expansion
- future MFE/MAE to label present phase

## What may be reused as causal inputs

- completed-candle impulse
- causal structure break
- causal swing sequence
- protected structure
- EMA alignment/slope
- pullback start/depth/duration
- reclaim/rejection
- range/ATR expansion
- balance age
- stretch / distance from equilibrium
- failed continuation events

## Stage 6A audit verdict

**LEGACY_PHASE_CONCEPTS_USEFUL_AS_FEATURE_DONORS_ONLY**

No legacy phase classifier is accepted as V2 phase ground truth.
