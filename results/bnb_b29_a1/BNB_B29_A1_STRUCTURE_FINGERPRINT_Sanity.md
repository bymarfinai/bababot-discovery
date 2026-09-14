# BNB B29 A1 — Structure Fingerprint Sanity Result

**Status: BNB_B29_A1_STRUCTURE_FINGERPRINT_PASS**

A1 validates representation and causality only. It does **not** evaluate trading edge, entry, TP, SL, WR, PnL, or RTD.

## Frozen data

- Symbol: `BNBUSDT`
- Raw 5m open-time span: `2020-02-10 08:00:00+00:00` to `2026-08-25 23:55:00+00:00`
- Last fully closed bar represented: `2026-08-26 00:00:00+00:00`
- Loader frozen END: `2026-08-26 00:00:00+00:00`
- Raw rows: 687,936
- Raw coverage: 100.000000%
- Post-2026-08-26 data touched: **NO**

## Fingerprint

- 15m decision rows after warm-up: 229,267
- First usable decision: `2020-02-10 14:15:00+00:00`
- Last usable decision: `2026-08-26 00:00:00+00:00`
- Numeric features: 49
- Categorical/context features: 10
- Character tokens observed: 12,556
- Deterministic fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`

## Anti-leak prefix invariant

- Prefix raw cutoff: `2025-01-01 00:00:00+00:00`
- Prefix fingerprint hash: `e87b9455f1abf971e79ad35d6778be8e611123a9f38f01837d6c5b94add3a34d`
- Overlapping decision rows checked: 171,477
- Index identical: True
- Numeric identical within 1e-12: True
- Categorical exactly identical: True
- Maximum absolute numeric difference: 0.000e+00
- Causal invariant: **PASS**

## Acceptance gates

- `coverage`: **PASS**
- `raw_integrity`: **PASS**
- `decision_integrity`: **PASS**
- `causal_invariant`: **PASS**
- `numeric_finite`: **PASS**
- `categorical_populated`: **PASS**
- `state_variance`: **PASS**
- `schema_guard`: **PASS**
- `frozen_boundary`: **PASS**

## Core state cardinality

| State family | Observed states |
|---|---:|
| `structure_state` | 5 |
| `trend_state` | 5 |
| `efficiency_state` | 3 |
| `vol_state` | 3 |
| `range_state` | 3 |
| `liquidity_state` | 6 |
| `path_state` | 7 |
| `wib_bucket` | 4 |

## Ten most common diagnostic character tokens

| Token | N | Share |
|---|---:|---:|
| `HH_HL|STRONG_UP|MID|NORMAL|HIGH|NONE|CONT_UP|WIB_12_17` | 1899 | 0.83% |
| `HH_HL|STRONG_UP|MID|NORMAL|HIGH|NONE|CONT_UP|WIB_06_11` | 1714 | 0.75% |
| `HH_HL|STRONG_UP|MID|NORMAL|HIGH|NONE|CONT_UP|WIB_00_05` | 1556 | 0.68% |
| `HH_HL|STRONG_UP|MID|NORMAL|HIGH|NONE|CONT_UP|WIB_18_23` | 1553 | 0.68% |
| `LH_LL|STRONG_DOWN|MID|EXPAND|LOW|NONE|CONT_DOWN|WIB_18_23` | 1552 | 0.68% |
| `LH_LL|STRONG_DOWN|MID|NORMAL|LOW|NONE|CONT_DOWN|WIB_12_17` | 1473 | 0.64% |
| `LH_LL|STRONG_DOWN|MID|NORMAL|LOW|NONE|CONT_DOWN|WIB_06_11` | 1303 | 0.57% |
| `HH_HL|STRONG_UP|MID|EXPAND|HIGH|NONE|CONT_UP|WIB_18_23` | 1263 | 0.55% |
| `LH_LL|STRONG_DOWN|MID|NORMAL|LOW|NONE|CONT_DOWN|WIB_00_05` | 1248 | 0.54% |
| `HH_HL|STRONG_UP|LOW|NORMAL|HIGH|NONE|CONT_UP|WIB_18_23` | 1197 | 0.52% |

## Decision

**BNB_B29_A1_STRUCTURE_FINGERPRINT_PASS**

If PASS, the only permitted next phase is B29 A2 Character Memory / similarity construction using this frozen A1 representation. Entry and TP/SL work remain blocked.

No live orders were placed.
