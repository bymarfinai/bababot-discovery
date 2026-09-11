# ETH E15A — Max-6h 24H LONG Rediscovery Scientific Verdict

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen question
Can the ETH 24-hour LONG character map be rediscovered with payoff horizons capped at 6 hours while preserving the exact E12 grammar and formal gates?

## Result-bearing run
- Branch: `eth-e15a-long-max6h-24h`
- Parallel workflow run: `34592612730`
- Aggregate job: `103241514662`
- Trigger/head commit: `2d979da2315027b5e23c0b526ae71514fbcdcba2`
- Final artifact: `10196286805`
- Artifact SHA256: `12e9cd56a58c8d2e2984a8a19eeec42bd34e8ee3d4a465abbf8c8d575f0c020d`

## Search
- ETHUSDT 5m
- LONG only
- Development years 2022/2023/2024
- 24 WIB hours
- four quarter-hour anchors per hour
- 90 frozen E12 rules
- lookbacks 15/30/60/120/240/360m
- holds **60/120/240/360m only**
- 2,160 candidates/hour
- **51,840 total Development candidates**
- exact original E12 anchor/pooled/era gates

## Outcome
Formal PASS hours: **2/24**.
Total full-gate candidates: **3**.

### 01:00–02:00 WIB — PASS
Development-selected representative:
- `RV_HIGH__RANGE_MID / LB240 / H360`
- N 247
- WR 58.70%
- net +$426.27
- expectancy +$1.73/trade
- PF 1.809
- DD $56.41
- max loss streak 8
- supportive/evaluable anchors 4/4
- 2022 WR 62.16%, exp +$3.80
- 2023 WR 57.14%, exp +$0.88
- 2024 WR 57.29%, exp +$0.80
- all three years WR >=55%

This replaces the old E12M representative `EFF_HIGH__RV_LOW / LB240 / H960` when holds above 6h are forbidden. The 01 WIB hour therefore has a genuine shorter-horizon character rather than merely losing its old H960 edge.

### 03:00–04:00 WIB — PASS
- `RV_HIGH__RANGE_MID / LB360 / H240`
- N 250
- WR 60.40%
- net +$433.55
- expectancy +$1.73/trade
- PF 1.937
- DD $116.44
- max loss streak 5
- supportive/evaluable anchors 4/4
- 2022 WR 59.49%, exp +$2.19
- 2023 WR 61.29%, exp +$2.06
- 2024 WR 60.55%, exp +$1.22
- all three years WR >=55%

This is unchanged from the original E12O winner.

## 24h representative map

| WIB | Status | Representative | LB | Hold | N | WR | Net | Exp | PF | DD | LS |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00 | FAIL | RV_MID__RANGE_HIGH | 240 | 240 | 213 | 57.28% | +$159.86 | +$0.75 | 1.408 | $98.78 | 8 |
| 01 | PASS | RV_HIGH__RANGE_MID | 240 | 360 | 247 | 58.70% | +$426.27 | +$1.73 | 1.809 | $56.41 | 8 |
| 02 | FAIL | DRIVE_DOWN__STR_B60_80 | 120 | 360 | 311 | 60.13% | +$258.70 | +$0.83 | 1.313 | $111.90 | 8 |
| 03 | PASS | RV_HIGH__RANGE_MID | 360 | 240 | 250 | 60.40% | +$433.55 | +$1.73 | 1.937 | $116.44 | 5 |
| 04 | FAIL | RV_HIGH__RANGE_MID | 360 | 120 | 220 | 56.82% | +$150.59 | +$0.68 | 1.543 | $66.68 | 8 |
| 05 | FAIL | DRIVE_DOWN__STR_B80_100 | 240 | 120 | 342 | 53.80% | +$280.41 | +$0.82 | 1.499 | $116.79 | 10 |
| 06 | FAIL | EFF_MID__RANGE_HIGH | 240 | 120 | 280 | 54.64% | +$358.68 | +$1.28 | 1.908 | $70.33 | 9 |
| 07 | FAIL | RV_LOW__RANGE_HIGH | 120 | 360 | 10 | 60.00% | +$8.25 | +$0.82 | 2.585 | $4.25 | 3 |
| 08 | FAIL | RV_HIGH__RANGE_MID | 360 | 360 | 222 | 48.65% | +$187.58 | +$0.84 | 1.397 | $89.09 | 13 |
| 09 | FAIL | DRIVE_DOWN__STR_B80_100 | 240 | 360 | 317 | 54.26% | +$218.61 | +$0.69 | 1.187 | $394.50 | 22 |
| 10 | FAIL | DRIVE_UP__STR_B80_100 | 120 | 360 | 316 | 55.38% | +$316.26 | +$1.00 | 1.447 | $174.30 | 11 |
| 11 | FAIL | RV_HIGH__RANGE_MID | 120 | 360 | 212 | 56.60% | +$229.21 | +$1.08 | 1.495 | $81.05 | 10 |
| 12 | FAIL | DRIVE_UP__STR_B80_100 | 240 | 360 | 351 | 55.84% | +$519.34 | +$1.48 | 1.797 | $73.72 | 15 |
| 13 | FAIL | EFF_LOW__EXT_HIGH | 360 | 360 | 196 | 55.10% | +$143.42 | +$0.73 | 1.266 | $88.06 | 6 |
| 14 | FAIL | DRIVE_UP__STR_B80_100 | 360 | 240 | 354 | 55.93% | +$348.96 | +$0.99 | 1.584 | $106.73 | 10 |
| 15 | FAIL | RV_MID__RANGE_HIGH | 60 | 360 | 178 | 53.37% | +$220.02 | +$1.24 | 1.412 | $127.27 | 5 |
| 16 | FAIL | RV_MID__RANGE_LOW | 60 | 240 | 237 | 51.05% | +$34.12 | +$0.14 | 1.088 | $115.01 | 16 |
| 17 | FAIL | EFF_MID__RV_HIGH | 240 | 120 | 318 | 52.20% | +$91.51 | +$0.29 | 1.206 | $64.08 | 9 |
| 18 | FAIL | RV_HIGH__RANGE_MID | 120 | 360 | 216 | 52.31% | +$198.39 | +$0.92 | 1.244 | $147.70 | 12 |
| 19 | FAIL | RV_HIGH__RANGE_LOW | 240 | 360 | 25 | 76.00% | +$155.63 | +$6.23 | 11.247 | $9.20 | 3 |
| 20 | FAIL | RV_HIGH__RANGE_LOW | 240 | 240 | 17 | 58.82% | +$18.19 | +$1.07 | 1.699 | $19.85 | 6 |
| 21 | FAIL | EFF_MID__RANGE_LOW | 360 | 360 | 382 | 49.21% | +$431.23 | +$1.13 | 1.350 | $156.45 | 12 |
| 22 | FAIL | RV_MID__RANGE_HIGH | 240 | 360 | 253 | 57.31% | +$231.68 | +$0.92 | 1.254 | $249.34 | 11 |
| 23 | FAIL | RV_MID__RANGE_HIGH | 120 | 360 | 186 | 56.45% | +$155.86 | +$0.84 | 1.377 | $102.82 | 8 |

## Comparison with original E12 formal-pass map
Original E12 formal PASS hours: 23, 00, 01, 03 WIB.
Max-6h E15A formal PASS hours: **01, 03 WIB only**.

- 23 WIB lost its H720-dependent formal edge.
- 00 WIB lost its H720-dependent formal edge.
- 01 WIB remains formally valid by rotating to a **6h** character.
- 03 WIB remains formally valid with its original **4h** character.
- No previously formal-FAIL hour became a new formal PASS under the frozen max-6h family.

## Scientific interpretation
The experiment supports a shorter-horizon ETH LONG habitat concentrated at **01:00–04:00 WIB**, with two formal components:
1. 01 WIB: 6h character.
2. 03 WIB: 4h character.

The max-6h restriction materially reduces the number of formal hours, but the surviving two have strong pooled and cross-era quality. This is potentially useful for reducing capital occupancy and overlap, but portfolio/sequential behavior has not yet been tested.

**ETH_E15A_MAX6H_CHARACTER_MAP_FOUND**

Research/shadow only. No OOS exposure and no live authorization.