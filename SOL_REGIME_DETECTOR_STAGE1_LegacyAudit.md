# SOL Regime Detector — Legacy V2 / V2.5 Audit

**Purpose:** verify whether the old regime implementation is safe to reuse as the foundation of the new SOL Bull/Bear/Sideways detector.

## Files audited

- `continuation_detector_endpoint.py`
- `v25_detector_endpoint.py`
- `BabaBot_V2_Checkpoint.md`
- `BabaBot_V2_V2.5_Final_Checkpoint.md`

## Findings

| Component | Finding | Decision |
|---|---|---|
| V2 swing confirmation | `cand = i - lookback`; with lookback=10 the candidate is checked only after 10 right-side 1H bars have closed. This is causal, but adds ~10h confirmation latency. | KEEP concept; latency must be explicit |
| V2 swing dedup | A confirmed swing is skipped when the latest stored swing has the same **price**, even if it is a different bar. Equal-high / equal-low retests can disappear. | FIX |
| V2 structure counts | High sequence (HH/LH) and low sequence (HL/LL) are counted independently. The code does not enforce a coherent alternating market-structure sequence. | REBUILD |
| V2 protected swing | `protected_low/high` is simply the most recently confirmed low/high. It is not necessarily the structural pivot that defines trend invalidation. | REBUILD |
| V2 SIDEWAYS | SIDEWAYS is assigned when strict 2HH+2HL or 2LH+2LL + EMA conditions are absent. It is therefore a residual class, not positively detected balance. | REJECT definition |
| V2 EMA slope | Slow slope uses `(EMA_t - EMA_t-3)/EMA_t`. This is causal, but the normalization differs from later V2.5 logic. | STANDARDIZE |
| V2 EMA alignment | Bull requires fast EMA > slow EMA; Bear is symmetric. Valid as a feature, not sufficient regime truth. | KEEP as feature |
| V2.5 swing timing | Tier B/C swing logic uses a midpoint of a trailing 11-bar window (for lb=10), so confirmation is causal with ~5h right-side latency. | KEEP concept |
| V2.5 swing significance | Candidate significance is compared with ATR at the **current confirmation bar**, not clearly frozen at the candidate event. | STANDARDIZE |
| V2.5 structure counters | HH/HL/LH/LL counters can retain stale evidence; opposite events decrement rather than reconstructing a fresh chronological swing sequence. | REBUILD |
| V2.5 Tier B persistence | When a developing Bull/Bear condition is true while current tier is not already B, `tier_bars` is reset to 0 and then incremented to 1 on every bar. With `min_regime_bars=3`, Tier B cannot normally accumulate to 3 from SIDEWAYS. | BUG — DO NOT REUSE |
| V2.5 Tier C | C is impulse + EMA alignment + recent EMA touch. This is an early-transition feature, not a full regime definition. | KEEP as candidate feature |
| V2/V2.5 SIDEWAYS share | Historical ~85% SIDEWAYS partly reflects strict directional gates / fallback design and cannot be interpreted as “SOL is genuinely sideways 85% of the time.” | DO NOT USE as truth |
| 4H context | Old strict V2 classification is primarily 1H and does not make fully closed 4H context a required independent family. | ADD in new detector |

## Key conclusion

The old V2 detector contains useful concepts:
- causal delayed swing confirmation,
- ATR-scaled structural significance,
- EMA alignment / slope,
- protected-structure invalidation.

But it should **not** be used as the new ground-truth classifier.

The most important redesigns are:

1. SIDEWAYS must be detected positively.
2. Structure must be built from a chronological causal swing sequence.
3. Protected swing must have structural meaning.
4. EMA / drift units must be standardized.
5. Transition uncertainty must be explicit.
6. 4H context must use only fully completed bars.
7. V2.5 Tier-B persistence bug must not propagate.

## Stage-1 audit verdict

**LEGACY_V2_V25_NOT_SAFE_AS_FINAL_REGIME_ENGINE**

Use the old implementation only as a feature donor.
