# BNB B41-S4 — Frozen Direction Detector Validation Preregistration

## Objective

Validate whether the robust B41-S3 Q80 interaction characters can be converted into a causal LONG / SHORT / NO-TRADE direction detector.

S4 validates **direction only**. It does not choose an entry geometry, stop loss, take profit, leverage, position sizing, or trade PnL.

## Frozen parents

- B41-S1 wall signature:
  `4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6`
- B41-S2 signature:
  `53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2`
- B41-S3 signature:
  `dfcfe845a7547c649defe7f47eeafb356bc2c307c00361b0794a131780e32492`
- Wall: Q80 only.
- Character window: first-touch bar plus the next two completed 5m bars.
- Signal time: close of the third character bar.
- DEV: 2022-2024.
- REF: 2025-2026.

## Frozen direction map

Only S3 states labeled stable are allowed to emit a direction:

- UPPER + C1_CLEAN_REJECTION -> **SHORT**
- UPPER + C3_ACCEPTANCE_HOLD -> **LONG**
- LOWER + C1_CLEAN_REJECTION -> **LONG**
- LOWER + C2_RECLAIM_AFTER_CLOSE -> **LONG**
- every other eligible character -> **NO_TRADE**

No new character, threshold, side symmetry assumption, or fallback direction may be introduced in S4.

## Critical causal origin

All directional outcomes are measured from the **detector close price**, i.e. the close of the third 5m character bar.

The Q80 wall price is only used as a normalization distance:

wall_distance = abs(Q80 wall - UTC session open)

This prevents a signal from receiving credit for price movement that happened before the detector was known.

## Frozen directional outcomes

For a LONG signal:
- aligned return = (future close - detector close) / wall_distance

For a SHORT signal:
- aligned return = (detector close - future close) / wall_distance

Metrics:

1. **60m aligned close displacement**
2. **180m aligned close displacement**
3. **60m directional hit** = aligned 60m > 0
4. **180m directional hit** = aligned 180m > 0
5. **Post-signal maximum favorable excursion (MFE)** to session end, normalized by wall distance
6. **Post-signal maximum adverse excursion (MAE)** to session end, normalized by wall distance
7. **Favorable dominance** = MFE > MAE
8. **Signal coverage** = directional signals / eligible Q80 character events

If the exact +60m or +180m bar is outside the same UTC session, that horizon is unavailable and excluded from that horizon's statistics.

## Frozen support rule

Each of the four directional character classes is **DIRECTION_SUPPORTED** only if, in both DEV and REF:

- valid 180m sample >= 20;
- median aligned 180m displacement > 0;
- 180m directional hit rate > 50%;
- favorable-dominance rate > 50%.

The full frozen direction map is **READY_FOR_ENTRY_DISCOVERY** only if:

1. all four directional character classes are DIRECTION_SUPPORTED;
2. pooled DEV and pooled REF each have positive median aligned 180m displacement and >50% hit rate;
3. pooled annual median aligned 180m displacement is positive in at least 4 of 5 research years.

Failure of any condition means S4 remains descriptive and no entry discovery is promoted.

## Explicit exclusions

S4 does not optimize:
- observation window;
- wall quantile;
- direction mapping;
- entry price;
- stop;
- target;
- holding period;
- MFE/MAE threshold;
- WR/PF/PnL/expectancy.

Those remain later-stage questions.
