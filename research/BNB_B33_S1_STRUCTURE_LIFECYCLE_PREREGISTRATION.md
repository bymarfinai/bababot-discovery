# BNB B33-S1 — Causal Structure Lifecycle Preregistration

## Scientific identity
`BNB_B33_S1_STRUCTURE_LIFECYCLE_V1`

B33 is a new identity after B32 stopped at entry discovery. It does not change B32 thresholds or rescue rejected B32 pairs.

## Question
Does BNB lose actionability because prior entry discovery begins only after a structure is fully mature?

B33 separates each frozen price-action family into an independently causal EARLY phase and a MATURE phase. S1 remains structure-only.

Pipeline:
`B33-S1 lifecycle phase -> B33-S2 entry per phase -> B33-S3 economics -> OOS/shadow`.

## Forbidden in S1
No forward directional outcome, WIN/LOSS, entry selection, TP/SL, MFE/MAE, PnL, PF, fees, leverage, DD, hour/session/day filtering.

## Data / causality
- Same Binance Vision BNBUSDT 5m source and accepted B29-A1 identity guard.
- Same causal 15m reconstruction.
- Same 2-left/2-right confirmed swing semantics.
- Census: 2022-01-01 through 2026-08-26 00:00 UTC.
- Every EARLY detector must be recognizable using only information available at its timestamp. It may later fail to mature and remains a valid historical EARLY occurrence.

## Frozen lifecycle families

### F1 Liquidity sweep reversal
LONG:
- EARLY: current low < latest previously confirmed swing low and current close >= that level.
- MATURE: frozen B32 `LIQUIDITY_SWEEP_DISPLACEMENT_LONG`.
SHORT mirrors at a confirmed swing high.

### F2 Impulse pullback / HL-LH
LONG EARLY `IMPULSE_PULLBACK_REACTION_LONG`:
1. latest confirmed swing high is higher than the previous confirmed swing high;
2. identify the latest confirmed swing low before that latest high;
3. upswing amplitude >= 1.25 * prior-16 median 15m range;
4. current 15m low is a 25%-75% retracement of that upswing;
5. current low remains above that prior swing low;
6. current close is at/above its own candle midpoint.
The native structural level is the current reaction-bar low.

LONG MATURE: frozen B32 `IMPULSE_HL_READY_LONG`.

SHORT EARLY mirrors using a lower confirmed swing low, the latest confirmed swing high before it, a 25%-75% bounce, current high below prior swing high, and close at/below candle midpoint.
SHORT MATURE: frozen B32 `IMPULSE_LH_READY_SHORT`.

### F3 Compression breakout
LONG EARLY:
- frozen B32 compression3 immediately precedes current bar;
- current close newly breaks above latest previously confirmed swing high;
- breakout bar bullish with body_ratio >=0.45.
LONG MATURE: frozen B32 `COMPRESSION_BREAK_RETEST_LONG`.
SHORT mirrors below latest confirmed swing low and `COMPRESSION_BREAK_RETEST_SHORT`.

### F4 Failed break reversal
LONG EARLY:
1. a 15m close newly breaks below latest previously confirmed swing low;
2. within the next 1-3 completed 15m bars, a close returns >= broken level.
Completion is reclaim close.
LONG MATURE: frozen B32 `FAILED_BREAK_DISPLACEMENT_LONG`.

SHORT EARLY mirrors a break above confirmed swing high followed within 1-3 bars by a close <= broken level.
SHORT MATURE: frozen B32 `FAILED_BREAK_DISPLACEMENT_SHORT`.

## Detector IDs
- F1LE / F1LM — sweep LONG EARLY/MATURE
- F2LE / F2LM — impulse-HL LONG EARLY/MATURE
- F3LE / F3LM — compression LONG EARLY/MATURE
- F4LE / F4LM — failed-break LONG EARLY/MATURE
- F1SE / F1SM — sweep SHORT EARLY/MATURE
- F2SE / F2SM — impulse-LH SHORT EARLY/MATURE
- F3SE / F3SM — compression SHORT EARLY/MATURE
- F4SE / F4SM — failed-break SHORT EARLY/MATURE

## De-duplication
Per detector 90-minute cooldown, first causal occurrence retained. Cross-phase and cross-family overlap is measured, not suppressed.

## Mature audit
MATURE event counts must exactly match the frozen B32-S1 parent counts:
- F1LM 1,980
- F2LM 2,021
- F3LM 639
- F4LM 2,702
- F1SM 1,863
- F2SM 1,789
- F3SM 548
- F4SM 2,637.

## S1 viability
Each phase detector is STRUCTURALLY_VIABLE iff:
1. pooled N >=100;
2. at least 4/5 eras have >=12 detections;
3. max era share <=35%;
4. median same-detector gap >=90 minutes;
5. integrity and causality checks pass.

No outcome metric is used.

## Anti-rescue
No threshold edits after counts are seen; no outcome-driven phase definition; no clock/session filters; no entry/economics until S1 is frozen.
