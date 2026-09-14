# BNB LONG Reset V1 — H02 Untouched OOS Validation PREREG

Status: **FROZEN BEFORE OOS DATA IS DOWNLOADED OR EVALUATED**

## Frozen character

- Symbol: **BNBUSDT perpetual futures**
- Side: **LONG only**
- Habitat: **02:00–03:00 WIB only**
- Quarter-hour anchors: **02:00 / 02:15 / 02:30 / 02:45 WIB**
- Primary: **`rv_ratio_60_240__HIGH`**
- Secondary: **`efficiency_60m__HIGH`**
- Both HIGH states use causal percentile **>= 2/3**.
- Percentiles use the **previous 60 observations of the same quarter-hour anchor**, minimum history 40, with no future information.
- Features use only completed 5-minute bars strictly before each anchor.
- Reference entry is the 5-minute open at the anchor.
- Diagnostic horizons remain **+60m / +120m / +240m** and consensus return is their simple mean.
- No threshold, feature, anchor, hour, or secondary may be changed after OOS exposure.

## Untouched OOS period

Evaluation interval in local WIB time:
- Start: **2025-01-01 00:00 WIB**
- End: **2026-07-30 23:59:59 WIB**

Development 2022–2024 may be used only as historical state needed by the frozen causal rolling percentile. OOS observations may enter the rolling history after they occur, exactly as they would in live walk-forward use. No future OOS observation may affect an earlier signal.

## OOS PASS gates

### A. Pooled OOS gate — mandatory

Frozen primary + secondary cohort must satisfy all:
- N >= **120** signals;
- consensus WR > **55%**;
- mean consensus return > **0**;
- consensus PF >= **1.20**.

### B. OOS calendar-block robustness — mandatory

Evaluate separately:
1. calendar year **2025**;
2. **2026-01-01 through 2026-07-30**.

Each block must satisfy:
- N >= **40**;
- WR >= **52%**;
- mean consensus return > **0**;
- PF >= **1.05**.

Both blocks must pass.

### C. Diagnostic-horizon robustness — mandatory

For each frozen diagnostic horizon (+60m / +120m / +240m), a horizon is supportive if:
- N >= **120**;
- WR >= **53%**;
- mean return > **0**;
- PF >= **1.10**.

At least **2/3** horizons must be supportive.

### D. Quarter-hour anchor robustness — mandatory

For each 02:00 / 02:15 / 02:30 / 02:45 WIB anchor, an anchor is supportive if:
- N >= **20**;
- WR >= **52%**;
- mean consensus return > **0**;
- PF >= **1.05**.

At least **3/4** anchors must be supportive.

### E. OOS quarter consistency — diagnostic guardrail

Report every OOS calendar quarter separately, including partial **2026Q3 through July 30**. This section is diagnostic and cannot be used to exclude bad quarters. At least **4/7** evaluated quarters should have positive mean return for a clean robustness read; failure is flagged as `QUARTER_WARNING` but does not override A–D by itself.

## Verdicts

- **OOS_PASS**: mandatory gates A, B, C, and D all pass.
- **OOS_FAIL**: any mandatory gate A, B, C, or D fails. The frozen H02 primary+secondary character is rejected for promotion; no OOS retuning or rescue filter is allowed.
- **INSUFFICIENT_DATA**: coverage/integrity prevents valid evaluation.

If OOS passes, the next stage is **trade construction** on the frozen structural cohort: executable entry/hold/TP/SL, overlap handling, fees, slippage, leverage mechanics, and final READY-TO-TRADE validation.

No trade-construction optimization is permitted inside this OOS validation.
