# SOL R4c Final Re-score

All 77,760 authoritative Development candidates were re-scored. `anchor_gate` and `era_gate` were preserved exactly. Only pooled WR is strict `>55%` and pooled DD is `max_dd <= 15% of net_pnl`; every other pooled threshold is unchanged.

- PASS hours: **7/24** — [0, 1, 3, 4, 5, 6, 22]
- Final passers: **9**
- Rescued: **5**
- Dropped old passers: **4**

| WIB | Verdict | Old | Final | Rescued | Dropped | Selected / near-miss | LB | Hold | N | WR | Net | PF | DD/Net | LS | Anchors | Fail |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 00:00-01:00 | PASS | 0 | 2 | 2 | 0 | `EFF_LOW__RANGE_HIGH` | 30 | 720 | 214 | 60.28% | $+1,090.72 | 1.963 | 12.56% | 7 | 3/4 | PASS |
| 01:00-02:00 | PASS | 0 | 1 | 1 | 0 | `RV_HIGH__RANGE_MID` | 120 | 720 | 231 | 63.64% | $+1,320.37 | 2.267 | 11.66% | 6 | 4/4 | PASS |
| 02:00-03:00 | FAIL | 0 | 0 | 0 | 0 | `DRIVE_UP__STR_B80_100` | 360 | 960 | 314 | 60.51% | $+1,900.55 | 2.367 | 16.51% | 10 | 4/4 | DD/net>15%;LS>8 |
| 03:00-04:00 | PASS | 0 | 1 | 1 | 0 | `DRIVE_UP__STR_B80_100` | 360 | 960 | 308 | 64.29% | $+1,917.72 | 2.434 | 10.27% | 8 | 4/4 | PASS |
| 04:00-05:00 | PASS | 0 | 1 | 1 | 0 | `DRIVE_UP__RV_HIGH` | 360 | 960 | 454 | 60.57% | $+2,708.49 | 2.164 | 10.34% | 8 | 3/4 | PASS |
| 05:00-06:00 | PASS | 2 | 2 | 0 | 0 | `EFF_LOW__EXT_MID` | 240 | 360 | 285 | 59.30% | $+717.18 | 1.940 | 13.09% | 5 | 4/4 | PASS |
| 06:00-07:00 | PASS | 3 | 1 | 0 | 2 | `DRIVE_DOWN__STR_B80_100` | 15 | 120 | 306 | 60.13% | $+640.67 | 1.911 | 14.08% | 6 | 4/4 | PASS |
| 07:00-08:00 | FAIL | 0 | 0 | 0 | 0 | `RV_MID__RANGE_LOW` | 240 | 720 | 219 | 66.67% | $+834.30 | 1.901 | 17.50% | 7 | 4/4 | DD/net>15% |
| 08:00-09:00 | FAIL | 0 | 0 | 0 | 0 | `RV_MID__RANGE_LOW` | 240 | 720 | 209 | 60.77% | $+877.56 | 1.921 | 27.92% | 12 | 3/4 | DD/net>15%;LS>8 |
| 09:00-10:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_LOW__RANGE_HIGH` | 30 | 720 | 220 | 55.91% | $+1,225.23 | 1.845 | 20.56% | 6 | 3/4 | era_gate;DD/net>15% |
| 10:00-11:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_LOW__EXT_HIGH` | 120 | 720 | 183 | 48.09% | $+507.65 | 1.487 | 20.91% | 7 | 1/4 | anchor_gate;era_gate;WR<=55%;DD/net>15% |
| 11:00-12:00 | FAIL | 2 | 0 | 0 | 2 | `EFF_LOW__RANGE_HIGH` | 360 | 240 | 201 | 62.19% | $+580.75 | 1.861 | 20.38% | 7 | 4/4 | DD/net>15% |
| 12:00-13:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_MID__RV_HIGH` | 360 | 360 | 310 | 57.10% | $+561.10 | 1.438 | 32.77% | 13 | 3/4 | DD/net>15%;LS>8 |
| 13:00-14:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_LOW__RANGE_HIGH` | 30 | 960 | 222 | 57.66% | $+1,092.18 | 1.642 | 21.16% | 5 | 3/4 | DD/net>15% |
| 14:00-15:00 | FAIL | 0 | 0 | 0 | 0 | `RV_HIGH__RANGE_MID` | 360 | 960 | 180 | 58.89% | $+643.41 | 1.527 | 38.89% | 9 | 3/4 | DD/net>15%;LS>8 |
| 15:00-16:00 | FAIL | 0 | 0 | 0 | 0 | `RV_LOW__RANGE_HIGH` | 240 | 960 | 25 | 56.00% | $+144.26 | 2.876 | 23.05% | 5 | 0/0 | anchor_gate;era_gate;trades<160;DD/net>15% |
| 16:00-17:00 | FAIL | 0 | 0 | 0 | 0 | `RV_LOW__RANGE_HIGH` | 240 | 960 | 24 | 70.83% | $+315.28 | 7.833 | 7.98% | 3 | 0/0 | anchor_gate;era_gate;trades<160 |
| 17:00-18:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_HIGH__EXT_LOW` | 30 | 960 | 80 | 52.50% | $+338.21 | 1.706 | 25.82% | 7 | 0/0 | anchor_gate;era_gate;trades<160;WR<=55%;DD/net>15% |
| 18:00-19:00 | FAIL | 0 | 0 | 0 | 0 | `RV_HIGH__RANGE_LOW` | 240 | 960 | 15 | 53.33% | $+139.19 | 2.851 | 24.64% | 3 | 0/0 | anchor_gate;era_gate;trades<160;WR<=55%;DD/net>15% |
| 19:00-20:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_LOW__RANGE_HIGH` | 360 | 960 | 156 | 55.13% | $+1,123.60 | 1.960 | 22.72% | 9 | 1/2 | anchor_gate;era_gate;trades<160;DD/net>15%;LS>8 |
| 20:00-21:00 | FAIL | 0 | 0 | 0 | 0 | `EFF_MID__RV_HIGH` | 120 | 720 | 322 | 51.55% | $+871.62 | 1.354 | 39.60% | 13 | 2/4 | anchor_gate;era_gate;WR<=55%;DD/net>15%;LS>8 |
| 21:00-22:00 | FAIL | 0 | 0 | 0 | 0 | `DRIVE_UP__RV_HIGH` | 240 | 960 | 510 | 53.33% | $+2,346.01 | 1.591 | 16.56% | 11 | 1/4 | anchor_gate;era_gate;WR<=55%;DD/net>15%;LS>8 |
| 22:00-23:00 | PASS | 1 | 1 | 0 | 0 | `EFF_HIGH__RANGE_LOW` | 240 | 960 | 171 | 60.82% | $+1,002.93 | 2.403 | 11.87% | 7 | 3/3 | PASS |
| 23:00-00:00 | FAIL | 0 | 0 | 0 | 0 | `DRIVE_UP__STR_B60_80` | 30 | 960 | 252 | 58.73% | $+903.66 | 1.606 | 19.68% | 6 | 4/4 | DD/net>15% |

## All final passers

### H00
- RESCUED `EFF_LOW__RANGE_HIGH` LB30 H720: N 214, WR 60.28%, net $+1,090.72, exp $+5.10, PF 1.963, DD/net 12.56%, LS 7, anchors 3/4, min-era exp $+4.06
- RESCUED `EFF_LOW__RV_HIGH` LB30 H720: N 378, WR 58.99%, net $+1,674.78, exp $+4.43, PF 1.916, DD/net 10.82%, LS 8, anchors 3/4, min-era exp $+2.94
### H01
- RESCUED `RV_HIGH__RANGE_MID` LB120 H720: N 231, WR 63.64%, net $+1,320.37, exp $+5.72, PF 2.267, DD/net 11.66%, LS 6, anchors 4/4, min-era exp $+5.31
### H03
- RESCUED `DRIVE_UP__STR_B80_100` LB360 H960: N 308, WR 64.29%, net $+1,917.72, exp $+6.23, PF 2.434, DD/net 10.27%, LS 8, anchors 4/4, min-era exp $+1.67
### H04
- RESCUED `DRIVE_UP__RV_HIGH` LB360 H960: N 454, WR 60.57%, net $+2,708.49, exp $+5.97, PF 2.164, DD/net 10.34%, LS 8, anchors 3/4, min-era exp $+1.76
### H05
- RETAINED `EFF_LOW__EXT_MID` LB240 H360: N 285, WR 59.30%, net $+717.18, exp $+2.52, PF 1.940, DD/net 13.09%, LS 5, anchors 4/4, min-era exp $+1.78
- RETAINED `EFF_HIGH__RV_HIGH` LB30 H120: N 295, WR 56.27%, net $+659.62, exp $+2.24, PF 1.774, DD/net 14.21%, LS 5, anchors 4/4, min-era exp $+1.16
### H06
- RETAINED `DRIVE_DOWN__STR_B80_100` LB15 H120: N 306, WR 60.13%, net $+640.67, exp $+2.09, PF 1.911, DD/net 14.08%, LS 6, anchors 4/4, min-era exp $+0.79
### H22
- RETAINED `EFF_HIGH__RANGE_LOW` LB240 H960: N 171, WR 60.82%, net $+1,002.93, exp $+5.87, PF 2.403, DD/net 11.87%, LS 7, anchors 3/3, min-era exp $+4.14