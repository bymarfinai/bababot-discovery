# BNB B41 — IV Expected-Range Level Engine v0

**Status: BNB_B41_IV_LEVEL_ENGINE_V0_BUILT**

Snapshot: 2026-09-24T02:36:56.134Z

Purpose: reproduce the video's information *family* (options IV + expected range + historical range confluence), not claim the video's proprietary formula.

Frozen v0 formulas:
- one-sigma expected move = index_price × ask_IV × sqrt(horizon_days / 365);
- ATM ask IV = mean call/put askIV at nearest paired strike for expiry closest to target horizon;
- weekly surface IV = equal-weight askIV for ±10% moneyness and |delta| 0.15–0.85 at the selected ~7d expiry;
- historical normal range = median high/open and open/low excursion from prior 60 complete days / 26 complete weeks;
- confluence cluster = ≥2 projected levels within 0.75% of spot.

## BNBUSDT

- Index: **769.7683**
- ~1d ATM avg askIV: **39.07%** (DTE 1.22)
- ~7d ATM avg askIV: **40.71%** (DTE 8.22)
- ~7d surface avg askIV: **48.83%**, N=10
- IV daily band: **754.0277 – 785.5089**
- IV weekly band: **726.3715 – 813.1651**
- historical weekly normal: **750.3378 – 799.2677**

### Confluence clusters (0.75%)

- **752.1828** (-2.28%, 2 levels): HIST_WEEKLY_NORMAL_LOWER, IV_DAILY_LOWER

## SOLUSDT

- Index: **114.9294**
- ~1d ATM avg askIV: **67.75%** (DTE 1.22)
- ~7d ATM avg askIV: **67.75%** (DTE 1.22)
- ~7d surface avg askIV: **83.22%**, N=9
- IV daily band: **110.8536 – 119.0051**
- IV weekly band: **104.1460 – 125.7128**
- historical weekly normal: **106.0503 – 117.4139**

### Confluence clusters (0.75%)

- **117.0856** (+1.88%, 2 levels): HIST_DAILY_NORMAL_UPPER, HIST_WEEKLY_NORMAL_UPPER

## Boundary

This is a level-engine prototype, not a trading result. No HOD/LOD capture rate, WR, TP/SL, or economic claim is made yet.

Next valid stage: freeze this map family and evaluate future/unseen touches/reactions using stored IV snapshots. Historical BNB/SOL native option-IV coverage cannot represent the full 2022–2026 B41 window.
