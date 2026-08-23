# B27CY — BTC 24H F05 SHORT Late-Only BAD Refinement — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** B27CV/B27CX identities reproduced: 652 trades / 78 BAD / 348 GOOD / 226 OTHER; PLUS15_ONLY development 6 BAD/6 GOOD, external 2/3, validation 4/6.

Primary development-only delta threshold: **0.4681**. Anatomy only: trading WR/PF/expectancy/PnL are **N/A**.

## Six clocks independently — refined +15m state machine

| WIB | BAD caught | GOOD cut | Precision | Late-only BAD / GOOD flagged |
|---|---:|---:|---:|---:|
| 07-11 | 5/13 (38.5%) | 6/76 (7.9%) | 45.5% | 0/3 / 0/3 |
| 11-15 | 1/5 (20.0%) | 0/36 (0.0%) | 100.0% | 0/0 / 0/3 |
| 15-19 | 10/17 (58.8%) | 8/55 (14.5%) | 55.6% | 2/3 / 0/3 |
| 19-23 | 15/25 (60.0%) | 8/95 (8.4%) | 65.2% | 1/4 / 0/3 |
| 23-03 | 1/8 (12.5%) | 0/50 (0.0%) | 100.0% | 0/0 / 0/1 |
| 03-07 | 5/10 (50.0%) | 1/36 (2.8%) | 83.3% | 1/2 / 0/2 |

## Pooled comparison

| Scope | +15 SAFE BAD / GOOD | Persistence BOTH BAD / GOOD | Refined state BAD / GOOD | Precision refined |
|---|---:|---:|---:|---:|
| development | 28/38 (73.7%) / 9/159 (5.7%) | 22/38 (57.9%) / 3/159 (1.9%) | **23/38 (60.5%) / 3/159 (1.9%)** | 88.5% |
| external | 9/23 (39.1%) / 14/98 (14.3%) | 7/23 (30.4%) / 11/98 (11.2%) | **9/23 (39.1%) / 11/98 (11.2%)** | 45.0% |
| reference_validation | 8/17 (47.1%) / 15/91 (16.5%) | 4/17 (23.5%) / 9/91 (9.9%) | **5/17 (29.4%) / 9/91 (9.9%)** | 35.7% |
| POOLED_REUSED_EXTVAL | 17/40 (42.5%) / 29/189 (15.3%) | 11/40 (27.5%) / 20/189 (10.6%) | **14/40 (35.0%) / 20/189 (10.6%)** | 41.2% |
| POOLED_MAJOR | 45/78 (57.7%) / 38/348 (10.9%) | 33/78 (42.3%) / 23/348 (6.6%) | **37/78 (47.4%) / 23/348 (6.6%)** | 61.7% |

## PLUS15_ONLY primary delta gate

| Partition | BAD caught | GOOD cut | Delta BAD median | Delta GOOD median |
|---|---:|---:|---:|---:|
| development | 1/6 (16.7%) | 0/6 (0.0%) | 0.2559 | 0.2853 |
| external | 2/2 (100.0%) | 0/3 (0.0%) | 0.5675 | 0.2870 |
| reference_validation | 1/4 (25.0%) | 0/6 (0.0%) | 0.4004 | 0.2622 |
| POOLED_REUSED_EXTVAL | 3/6 (50.0%) | 0/9 (0.0%) | 0.4892 | 0.2723 |
| POOLED_MAJOR | 4/12 (33.3%) | 0/15 (0.0%) | 0.3498 | 0.2723 |

## Secondary diagnostics — directional AUC

| Feature | Development | External | Validation |
|---|---:|---:|---:|
| `max_bull_body_r4` | 52.8% | 100.0% | 79.2% |
| `higher_close_streak` | 54.2% | 66.7% | 62.5% |
| `net_close_from_entry_r4` | 55.6% | 0.0% | 41.7% |

## Regime splits — pooled major refined state

| Regime | BAD caught | GOOD cut | Precision |
|---|---:|---:|---:|
| BULL | 21/35 (60.0%) | 13/146 (8.9%) | 61.8% |
| BEAR | 8/31 (25.8%) | 6/154 (3.9%) | 57.1% |
| SIDEWAYS | 8/12 (66.7%) | 4/48 (8.3%) | 66.7% |

**Frozen verdict: `B27CY_LATE_ONLY_REFINEMENT_NOT_SUPPORTED`.**

External/reference_validation are reused-data confirmation, not untouched OOS. No economic abort simulation or live BBC change is authorized.
