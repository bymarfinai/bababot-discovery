# BNB R4e — H22 H720 Frozen 2026 Confirmation

**Confirmation only. No 2026 value is used to alter the frozen policy.**

Raw 5m coverage: **100.0000%**.
Latest available 5m bar: **2026-08-25T23:55:00+00:00**.
R4e freeze timestamp: **2026-09-13T05:36:03+00:00**.
Frozen policy: **BNBUSDT LONG / H22 WIB / RV_HIGH__RANGE_MID / 2-of-3 LB180-LB240-LB360 / earliest qualifying anchor / H720 / one position per day / no pyramiding**.

## Segment metrics

| Segment | Slip/side | N | WR | Net | Exp | PF | DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026_PRE_FREEZE_OOS | 0 bps | 20 | 45.00% | $+19.56 | $+0.98 | 1.340 | $+38.86 | 6 |
| 2026_PRE_FREEZE_OOS | 2 bps | 20 | 45.00% | $+15.56 | $+0.78 | 1.261 | $+40.06 | 6 |
| 2026_PRE_FREEZE_OOS | 5 bps | 20 | 45.00% | $+9.56 | $+0.48 | 1.152 | $+41.86 | 6 |
| 2026_PRE_FREEZE_OOS | 10 bps | 20 | 40.00% | $-0.44 | $-0.02 | 0.994 | $+45.61 | 7 |
| POST_FREEZE_PROSPECTIVE | 0 bps | 0 | nan | $+0.00 | nan | nan | nan | 0 |
| POST_FREEZE_PROSPECTIVE | 2 bps | 0 | nan | $+0.00 | nan | nan | nan | 0 |
| POST_FREEZE_PROSPECTIVE | 5 bps | 0 | nan | $+0.00 | nan | nan | nan | 0 |
| POST_FREEZE_PROSPECTIVE | 10 bps | 0 | nan | $+0.00 | nan | nan | nan | 0 |

## Frozen 2026 pre-freeze gate audit

- Sample maturity: **20/24 trades** — NOT MATURE.
- 0-bps non-N economic thresholds: **FAIL**.
- 2-bps/side stress thresholds: **PASS**.
- Formal status: **BNB_R4E_2026_SAMPLE_NOT_MATURE**.

Pre-freeze 2026 is historical OOS, not prospective. Post-freeze entries are the prospective shadow segment.
If the prospective segment has zero trades on this first run, that is expected and must not be treated as a failure.
No rescue filters, anchor cherry-picking, or threshold changes are permitted after this output.
Research/shadow only.
