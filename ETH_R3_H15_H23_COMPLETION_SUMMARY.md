# ETH R3 H15-H23 Completion Scan

**Sequential per-hour protocol: 2022 Development freeze first, then 2023 frozen-rule local stability test. 2024 is NOT opened by this batch. 2025-2026 remain CLOSED.**

| WIB hour | 2022 frozen character | Dev timing | Dev N | Dev WR | Dev Exp | Dev PF | 2023 exact WR | Exact Exp | Exact PF | Viable | Stable | Stage B verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 15:00-16:00 | DRIVE_UP__STR_B40_60 | LB180/H480 | 62 | 59.68% | $2.77 | 2.014 | 48.61% | $2.01 | 1.878 | 1 | 0 | TEST_DEGRADATION_FAIL |
| 16:00-17:00 | EFF_LOW__RV_MID | LB120/H360 | 76 | 63.16% | $3.94 | 2.254 | 39.19% | $-1.36 | 0.604 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 17:00-18:00 | EFF_LOW__RANGE_HIGH | LB120/H240 | 60 | 60.00% | $5.49 | 3.019 | 28.85% | $-2.08 | 0.200 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 18:00-19:00 | DRIVE_DOWN__STR_B80_100 | LB120/H240 | 80 | 57.50% | $2.88 | 1.958 | 36.28% | $-1.60 | 0.446 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 19:00-20:00 | RV_LOW__RANGE_MID | LB60/H240 | 76 | 59.21% | $3.68 | 2.413 | 50.85% | $0.97 | 1.523 | 1 | 0 | TEST_DEGRADATION_FAIL |
| 20:00-21:00 | DRIVE_DOWN__STR_B80_100 | LB120/H120 | 69 | 65.22% | $4.53 | 3.295 | 35.16% | $-1.33 | 0.388 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 21:00-22:00 | DRIVE_UP__STR_B60_80 | LB60/H480 | 72 | 55.56% | $3.47 | 1.948 | 39.71% | $-0.95 | 0.755 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 22:00-23:00 | DRIVE_UP__EFF_HIGH | LB360/H480 | 153 | 58.82% | $5.07 | 2.527 | 43.75% | $-1.13 | 0.721 | 0 | 0 | TEST_DEGRADATION_FAIL |
| 23:00-00:00 | DRIVE_UP__RV_MID | LB120/H240 | 101 | 66.34% | $2.58 | 2.490 | 41.41% | $-0.49 | 0.751 | 0 | 0 | TEST_DEGRADATION_FAIL |

Any hour with STABLE_EDGE_FROZEN must be handled in a separate, frozen 2024 confirmation step before interpretation. No 2024 winner reselection is allowed.
