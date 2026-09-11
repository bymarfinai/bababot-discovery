# SOL Economic-First — 24-Hour LONG Character Map

## Scope

This checkpoint consolidates the frozen hourly SOLUSDT LONG discovery from H00 through H23.

- Development only: 2022–2024.
- 5m SOLUSDT Binance Futures raw bars.
- 90 causal character rules.
- 6 lookbacks × 6 holds = 3,240 candidates per hour.
- 24 independent hours = 77,760 candidate evaluations before hourly ranking.
- Fixed $500 notional and $0.75 round-trip fee.
- Exact 5m-open entry and exact 5m-open time exit.
- Frozen anchor, pooled-economic, and all-era gates.
- No gate relaxation, no inherited candidate privilege, no OOS exposure.
- Research/shadow only.

## 24-hour map

| H | UTC | WIB | Full-gate passers | Hour status | Selected character |
|---:|---|---|---:|---|---|
| H00 | 00:00–01:00 | 07:00–08:00 | 0 | NO CHARACTER | — |
| H01 | 01:00–02:00 | 08:00–09:00 | 0 | NO CHARACTER | — |
| H02 | 02:00–03:00 | 09:00–10:00 | 0 | NO CHARACTER | — |
| H03 | 03:00–04:00 | 10:00–11:00 | 0 | NO CHARACTER | — |
| H04 | 04:00–05:00 | 11:00–12:00 | 2 | CHARACTER FOUND | EFF_LOW__RANGE_HIGH / LB360 / Hold240 |
| H05 | 05:00–06:00 | 12:00–13:00 | 0 | NO CHARACTER | — |
| H06 | 06:00–07:00 | 13:00–14:00 | 0 | NO CHARACTER | — |
| H07 | 07:00–08:00 | 14:00–15:00 | 0 | NO CHARACTER | — |
| H08 | 08:00–09:00 | 15:00–16:00 | 0 | NO CHARACTER | — |
| H09 | 09:00–10:00 | 16:00–17:00 | 0 | NO CHARACTER | — |
| H10 | 10:00–11:00 | 17:00–18:00 | 0 | NO CHARACTER | — |
| H11 | 11:00–12:00 | 18:00–19:00 | 0 | NO CHARACTER | — |
| H12 | 12:00–13:00 | 19:00–20:00 | 0 | NO CHARACTER | — |
| H13 | 13:00–14:00 | 20:00–21:00 | 0 | NO CHARACTER | — |
| H14 | 14:00–15:00 | 21:00–22:00 | 0 | NO CHARACTER | — |
| H15 | 15:00–16:00 | 22:00–23:00 | 1 | CHARACTER FOUND | EFF_HIGH__RANGE_LOW / LB240 / Hold960 |
| H16 | 16:00–17:00 | 23:00–00:00 | 0 | NO CHARACTER | — |
| H17 | 17:00–18:00 | 00:00–01:00 | 0 | NO CHARACTER | — |
| H18 | 18:00–19:00 | 01:00–02:00 | 0 | NO CHARACTER | — |
| H19 | 19:00–20:00 | 02:00–03:00 | 0 | NO CHARACTER | — |
| H20 | 20:00–21:00 | 03:00–04:00 | 0 | NO CHARACTER | — |
| H21 | 21:00–22:00 | 04:00–05:00 | 0 | NO CHARACTER | — |
| H22 | 22:00–23:00 | 05:00–06:00 | 2 | CHARACTER FOUND | EFF_LOW__EXT_MID / LB240 / Hold360 |
| H23 | 23:00–00:00 | 06:00–07:00 | 3 | CHARACTER FOUND | DRIVE_DOWN__STR_B80_100 / LB15 / Hold120 |

## Selected hourly winners

### H04 — 11:00–12:00 WIB

**EFF_LOW__RANGE_HIGH / LB360 / Hold240m**

- N 201
- WR 62.19%
- Net +$580.75
- Expectancy +$2.89/trade
- PF 1.861
- Max DD $118.37
- Max loss streak 7
- Supportive anchors 4/4
- 2022 WR 53.45%, Exp +$1.71
- 2023 WR 64.47%, Exp +$3.76
- 2024 WR 67.16%, Exp +$2.92

A second full-gate passer also existed: **EFF_HIGH__RV_MID / LB120 / Hold360m**.

### H15 — 22:00–23:00 WIB

**EFF_HIGH__RANGE_LOW / LB240 / Hold960m**

- N 171
- WR 60.82%
- Net +$1,002.93
- Expectancy +$5.87/trade
- PF 2.403
- Max DD $119.05
- Max loss streak 7
- Supportive/evaluable anchors 3/3; the fourth anchor had N=39 and was not evaluable
- 2022 WR 60.81%, Exp +$4.86
- 2023 WR 63.04%, Exp +$9.40
- 2024 WR 58.82%, Exp +$4.14

### H22 — 05:00–06:00 WIB

**EFF_LOW__EXT_MID / LB240 / Hold360m**

- N 285
- WR 59.30%
- Net +$717.18
- Expectancy +$2.52/trade
- PF 1.940
- Max DD $93.85
- Max loss streak 5
- Supportive anchors 4/4
- 2022 WR 55.95%, Exp +$1.78
- 2023 WR 60.87%, Exp +$3.55
- 2024 WR 60.55%, Exp +$2.21

A second full-gate passer also existed: **EFF_HIGH__RV_HIGH / LB30 / Hold120m**.

### H23 — 06:00–07:00 WIB

**DRIVE_DOWN__STR_B80_100 / LB15 / Hold120m**

- N 306
- WR 60.13%
- Net +$640.67
- Expectancy +$2.09/trade
- PF 1.911
- Max DD $90.21
- Max loss streak 6
- Supportive anchors 4/4
- 2022 WR 58.33%, Exp +$1.29
- 2023 WR 63.96%, Exp +$3.95
- 2024 WR 57.58%, Exp +$0.79

Two additional full-gate passers existed in the same family:

- DRIVE_DOWN__STR_B80_100 / LB15 / Hold60m
- DRIVE_DOWN__STR_B80_100 / LB240 / Hold60m

## Aggregate verdict

- Hours with at least one full-gate LONG character: **4 / 24 = 16.67%**.
- Hours with no full-gate LONG character: **20 / 24 = 83.33%**.
- Total full-gate candidate variants across all hours: **8**.
- The four selected hourly winners occur at **11:00–12:00, 22:00–23:00, 05:00–06:00, and 06:00–07:00 WIB**.
- H22–H23 form the only adjacent two-hour cluster with full-gate passers.

## Structural interpretation

The completed scan rejects the idea that SOL has one transferable all-day LONG structure. The winning state changes materially by clock:

1. **11:00–12:00 WIB:** low efficiency + high realized range over 360m, with a 240m hold.
2. **22:00–23:00 WIB:** high efficiency + low realized range over 240m, with a much longer 960m hold.
3. **05:00–06:00 WIB:** low efficiency + mid extension over 240m, with a 360m hold.
4. **06:00–07:00 WIB:** strong pre-entry downward drive over a short 15m lookback, with a short 120m hold.

This supports a clock-local, state-dependent SOL model rather than a BTC-style universal template.

The rejected hours are still informative. Several show high WR and positive expectancy but fail frozen drawdown, anchor, or cross-era gates. Examples include H00 RV_MID__RANGE_LOW with 66.67% WR and 4/4 anchors but DD $145.99, H16 DRIVE_UP__STR_B60_80 with 58.73% WR and 4/4 anchors but DD $177.80, H18 RV_HIGH__RANGE_MID with 63.64% WR and 4/4 anchors but DD $153.90, and H21 RV_HIGH__RANGE_MID with 68.98% WR and 4/4 anchors but DD $149.46. The risk ceiling is therefore doing real selection work rather than merely filtering weak signals.

## Next research step

Do not reopen a duplicated H24. The 24-hour clock scan is complete. The next logical stage is **validation architecture for the four selected hourly winners**, keeping External and Reference Validation closed until explicitly preregistered. A clean next phase would test the four frozen winners out-of-sample without changing their rule, lookback, hold, or gate definitions.

Research/shadow only. No live promotion or profit guarantee.
