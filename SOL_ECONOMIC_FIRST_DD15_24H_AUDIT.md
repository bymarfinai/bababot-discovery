# SOL Economic-First — DD15 Full-Gate 24-Hour Audit

## Frozen interpretation

This is a re-score of the same 77,760 Development candidates, not a new discovery search.
The only pooled-gate change is `max DD / net profit <= 15%`; the former pooled `max DD <= $125` test is removed.
Anchor support remains under its original gate, including anchor DD <= $125. All sample, expectancy, PF, loss-streak, and 2022/2023/2024 gates remain unchanged. Pooled WR is evaluated strictly as >55%.

## Hour audit

| H | UTC | WIB | Old | New | Rescued | Lost | Status / exact leading fail |
|---:|---|---|---:|---:|---:|---:|---|
| H00 | 00:00-01:00 | 07:00-08:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;DD/net>15%;all_era_gate |
| H01 | 01:00-02:00 | 08:00-09:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;DD/net>15%;loss_streak>8 |
| H02 | 02:00-03:00 | 09:00-10:00 | 0 | 0 | 0 | 0 | FAIL — DD/net>15%;all_era_gate |
| H03 | 03:00-04:00 | 10:00-11:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;WR<=55%;DD/net>15%;all_era_gate |
| H04 | 04:00-05:00 | 11:00-12:00 | 2 | 0 | 0 | 2 | FAIL — DD/net>15%;loss_streak>8;all_era_gate |
| H05 | 05:00-06:00 | 12:00-13:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;WR<=55%;DD/net>15%;loss_streak>8;all_era_gate |
| H06 | 06:00-07:00 | 13:00-14:00 | 0 | 0 | 0 | 0 | FAIL — DD/net>15% |
| H07 | 07:00-08:00 | 14:00-15:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;WR<=55%;DD/net>15%;loss_streak>8;all_era_gate |
| H08 | 08:00-09:00 | 15:00-16:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;DD/net>15%;all_era_gate |
| H09 | 09:00-10:00 | 16:00-17:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;all_era_gate |
| H10 | 10:00-11:00 | 17:00-18:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;WR<=55%;DD/net>15%;all_era_gate |
| H11 | 11:00-12:00 | 18:00-19:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;WR<=55%;DD/net>15%;all_era_gate |
| H12 | 12:00-13:00 | 19:00-20:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;N<160;DD/net>15%;loss_streak>8;all_era_gate |
| H13 | 13:00-14:00 | 20:00-21:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;WR<=55%;DD/net>15%;loss_streak>8;all_era_gate |
| H14 | 14:00-15:00 | 21:00-22:00 | 0 | 0 | 0 | 0 | FAIL — anchor_gate;WR<=55%;DD/net>15%;loss_streak>8;all_era_gate |
| H15 | 15:00-16:00 | 22:00-23:00 | 1 | 1 | 0 | 0 | PASS |
| H16 | 16:00-17:00 | 23:00-00:00 | 0 | 0 | 0 | 0 | FAIL — DD/net>15% |
| H17 | 17:00-18:00 | 00:00-01:00 | 0 | 2 | 2 | 0 | PASS |
| H18 | 18:00-19:00 | 01:00-02:00 | 0 | 1 | 1 | 0 | PASS |
| H19 | 19:00-20:00 | 02:00-03:00 | 0 | 0 | 0 | 0 | FAIL — DD/net>15%;loss_streak>8 |
| H20 | 20:00-21:00 | 03:00-04:00 | 0 | 1 | 1 | 0 | PASS |
| H21 | 21:00-22:00 | 04:00-05:00 | 0 | 1 | 1 | 0 | PASS |
| H22 | 22:00-23:00 | 05:00-06:00 | 2 | 2 | 0 | 0 | PASS |
| H23 | 23:00-00:00 | 06:00-07:00 | 3 | 1 | 0 | 2 | PASS |

## Final full-pass shortlist

| H | Character | LB | Hold | N | WR | Net | Exp | PF | DD | DD/Net | L-streak | Anchors | Origin |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H15 | EFF_HIGH__RANGE_LOW | 240m | 960m | 171 | 60.82% | $+1,002.93 | $+5.87 | 2.403 | $+119.05 | 11.87% | 7 | 3/3 | ORIGINAL |
| H17 | EFF_LOW__RANGE_HIGH | 30m | 720m | 214 | 60.28% | $+1,090.72 | $+5.10 | 1.963 | $+137.00 | 12.56% | 7 | 3/4 | RESCUED |
| H17 | EFF_LOW__RV_HIGH | 30m | 720m | 378 | 58.99% | $+1,674.78 | $+4.43 | 1.916 | $+181.16 | 10.82% | 8 | 3/4 | RESCUED |
| H18 | RV_HIGH__RANGE_MID | 120m | 720m | 231 | 63.64% | $+1,320.37 | $+5.72 | 2.267 | $+153.90 | 11.66% | 6 | 4/4 | RESCUED |
| H20 | DRIVE_UP__STR_B80_100 | 360m | 960m | 308 | 64.29% | $+1,917.72 | $+6.23 | 2.434 | $+196.88 | 10.27% | 8 | 4/4 | RESCUED |
| H21 | DRIVE_UP__RV_HIGH | 360m | 960m | 454 | 60.57% | $+2,708.49 | $+5.97 | 2.164 | $+280.18 | 10.34% | 8 | 3/4 | RESCUED |
| H22 | EFF_LOW__EXT_MID | 240m | 360m | 285 | 59.30% | $+717.18 | $+2.52 | 1.940 | $+93.85 | 13.09% | 5 | 4/4 | ORIGINAL |
| H22 | EFF_HIGH__RV_HIGH | 30m | 120m | 295 | 56.27% | $+659.62 | $+2.24 | 1.774 | $+93.70 | 14.21% | 5 | 4/4 | ORIGINAL |
| H23 | DRIVE_DOWN__STR_B80_100 | 15m | 120m | 306 | 60.13% | $+640.67 | $+2.09 | 1.911 | $+90.21 | 14.08% | 6 | 4/4 | ORIGINAL |

## Status changes

- Original passers retained: **4** candidate variants.
- NO PASS -> PASS rescued variants: **5**.
- PASS -> FAIL under proportional DD: **4**.
- Full-pass hours after re-score: **7/24**.

No OOS, exact-anchor/local-ridge, TP/SL fitting, or live promotion was opened by this audit.
