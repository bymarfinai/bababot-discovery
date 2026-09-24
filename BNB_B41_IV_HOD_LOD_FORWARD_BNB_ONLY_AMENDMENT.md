# BNB IV-HOD/LOD Forward Reaction Validation v0 — BNB-Only Amendment

## Effective scope change

Effective immediately for all forward observations not yet scored:

- Active research asset: **BNBUSDT only**
- SOLUSDT is **FROZEN / ARCHIVE ONLY**
- Existing SOL forecast files remain immutable historical artifacts.
- SOL observations do not enter any headline statistic, gate, nomination, or promotion decision after this amendment.

Reason: research scope intentionally narrowed to one pair before outcome accumulation.

This amendment changes asset scope only. It does **not** change:
- IV_LEVEL_ENGINE_V0 formula;
- level families;
- 0.75% confluence rule;
- hourly forecast horizon;
- touch definition;
- 15m / 30m / 60m reaction metrics;
- CLEAN_REACTION_30;
- STRONG_REACTION_30;
- BREAK_THROUGH_30;
- capture-error thresholds.

## Active BNB sample gate

No mechanism verdict until both are available:

- >=30 de-duplicated touched **primary BNB confluence** forecasts;
- >=30 de-duplicated touched **primary BNB singleton** forecasts.

## Active BNB quality gate

The BNB-only IV-HOD/LOD mechanism is supported only if:

- BNB primary confluence median capture_error_bps <=100 bps;
- BNB primary confluence CLEAN_REACTION_30 >=60%;
- BNB primary confluence BREAK_THROUGH_30 <=25%;
- BNB primary confluence CLEAN_REACTION_30 exceeds BNB primary singleton CLEAN_REACTION_30 by >=10 percentage points.

Until sample gate:
`BNB_IV_HOD_LOD_V0_FORWARD_VALIDATION_ACCUMULATING`

Sample reached but quality fails:
`BNB_IV_HOD_LOD_V0_NOT_SUPPORTED`

Both pass:
`BNB_IV_HOD_LOD_V0_MECHANISM_SUPPORTED`

Still no trading strategy or WR claim.
