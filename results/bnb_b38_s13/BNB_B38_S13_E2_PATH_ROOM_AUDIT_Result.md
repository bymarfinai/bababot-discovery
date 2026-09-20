# BNB B38-S13 — E2 Path & Real-Room Audit

**Step 1 freeze:** exact S10/S11 E2 detector, entry, touch-low SL, and TP1 baseline are unchanged.
Frozen plan signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

## Baseline parity

| Period | Plans | WIN | LOSS | WR |
|---|---:|---:|---:|---:|
| DEV | 440 | 325 | 115 | 73.9% |
| REF | 272 | 201 | 71 | 73.9% |

## Step 2 — path anatomy

MFE/MAE horizons are capped at the first structural SL touch; the SL bar itself is excluded because intrabar ordering is unknown.

| Period | Outcome | N | TP1 med | MFE 4h | MFE 12h | MFE 24h | MFE pre-SL | MAE 24h | Missed room 24h | Capture 24h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | ALL | 440 | 0.294R | 0.458R | 0.698R | 0.755R | 0.801R | -0.799R | 0.409R | 35.0% |
| DEV | WIN | 325 | 0.224R | 0.654R | 1.000R | 1.131R | 1.316R | -0.764R | 0.800R | 19.0% |
| DEV | LOSS | 115 | 0.561R | 0.138R | 0.148R | 0.148R | 0.148R | -0.870R | 0.000R | 253.4% |
| REF | ALL | 272 | 0.319R | 0.542R | 0.774R | 0.848R | 0.907R | -0.803R | 0.482R | 25.9% |
| REF | WIN | 201 | 0.183R | 0.769R | 1.087R | 1.323R | 1.627R | -0.711R | 0.968R | 15.6% |
| REF | LOSS | 71 | 0.641R | 0.132R | 0.132R | 0.132R | 0.132R | -0.904R | 0.000R | 341.1% |

### Excursion thresholds

| Period | Outcome | Threshold | Reach 24h | Reach pre-SL |
|---|---|---:|---:|---:|
| DEV | WIN | 0.25R | 301/325 (92.6%) | 305/325 (93.8%) |
| DEV | WIN | 0.50R | 255/325 (78.5%) | 264/325 (81.2%) |
| DEV | WIN | 1.00R | 178/325 (54.8%) | 192/325 (59.1%) |
| DEV | WIN | 1.50R | 133/325 (40.9%) | 155/325 (47.7%) |
| DEV | WIN | 2.00R | 107/325 (32.9%) | 138/325 (42.5%) |
| DEV | LOSS | 0.25R | 46/115 (40.0%) | 46/115 (40.0%) |
| DEV | LOSS | 0.50R | 15/115 (13.0%) | 15/115 (13.0%) |
| DEV | LOSS | 1.00R | 1/115 (0.9%) | 1/115 (0.9%) |
| DEV | LOSS | 1.50R | 0/115 (0.0%) | 0/115 (0.0%) |
| DEV | LOSS | 2.00R | 0/115 (0.0%) | 0/115 (0.0%) |
| REF | WIN | 0.25R | 175/201 (87.1%) | 187/201 (93.0%) |
| REF | WIN | 0.50R | 156/201 (77.6%) | 169/201 (84.1%) |
| REF | WIN | 1.00R | 117/201 (58.2%) | 125/201 (62.2%) |
| REF | WIN | 1.50R | 94/201 (46.8%) | 106/201 (52.7%) |
| REF | WIN | 2.00R | 71/201 (35.3%) | 94/201 (46.8%) |
| REF | LOSS | 0.25R | 26/71 (36.6%) | 26/71 (36.6%) |
| REF | LOSS | 0.50R | 15/71 (21.1%) | 16/71 (22.5%) |
| REF | LOSS | 1.00R | 3/71 (4.2%) | 3/71 (4.2%) |
| REF | LOSS | 1.50R | 1/71 (1.4%) | 1/71 (1.4%) |
| REF | LOSS | 2.00R | 0/71 (0.0%) | 0/71 (0.0%) |

## Step 3 — known structural/liquidity room

Every level below was already known at entry; no future pivots are used.

| Period | Outcome | Target | Available | Med distance | Hit before SL | Hit <=24h | Med hours if hit |
|---|---|---|---:|---:|---:|---:|---:|
| DEV | ALL | TP1 | 440 | 0.294R | 325 (73.9%) | 321 (73.0%) | 0.67h |
| DEV | ALL | TP2 | 382 | 0.533R | 241 (63.1%) | 236 (61.8%) | 1.17h |
| DEV | ALL | TP3 | 319 | 0.670R | 180 (56.4%) | 176 (55.2%) | 1.71h |
| DEV | ALL | EXPANSION | 423 | 0.885R | 223 (52.7%) | 210 (49.6%) | 2.58h |
| DEV | ALL | H1_NEAREST | 404 | 0.782R | 214 (53.0%) | 210 (52.0%) | 2.21h |
| DEV | ALL | MAJOR_NEAREST | 439 | 0.679R | 258 (58.8%) | 254 (57.9%) | 1.71h |
| DEV | WIN | TP1 | 325 | 0.224R | 325 (100.0%) | 321 (98.8%) | 0.67h |
| DEV | WIN | TP2 | 288 | 0.447R | 241 (83.7%) | 236 (81.9%) | 1.17h |
| DEV | WIN | TP3 | 243 | 0.535R | 180 (74.1%) | 176 (72.4%) | 1.71h |
| DEV | WIN | EXPANSION | 314 | 0.824R | 223 (71.0%) | 210 (66.9%) | 2.58h |
| DEV | WIN | H1_NEAREST | 303 | 0.726R | 214 (70.6%) | 210 (69.3%) | 2.21h |
| DEV | WIN | MAJOR_NEAREST | 325 | 0.540R | 258 (79.4%) | 254 (78.2%) | 1.71h |
| DEV | LOSS | TP1 | 115 | 0.561R | 0 (0.0%) | 0 (0.0%) | —h |
| DEV | LOSS | TP2 | 94 | 0.803R | 0 (0.0%) | 0 (0.0%) | —h |
| DEV | LOSS | TP3 | 76 | 0.961R | 0 (0.0%) | 0 (0.0%) | —h |
| DEV | LOSS | EXPANSION | 109 | 1.042R | 0 (0.0%) | 0 (0.0%) | —h |
| DEV | LOSS | H1_NEAREST | 101 | 1.105R | 0 (0.0%) | 0 (0.0%) | —h |
| DEV | LOSS | MAJOR_NEAREST | 114 | 0.955R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | ALL | TP1 | 272 | 0.319R | 201 (73.9%) | 200 (73.5%) | 0.50h |
| REF | ALL | TP2 | 241 | 0.511R | 162 (67.2%) | 161 (66.8%) | 0.92h |
| REF | ALL | TP3 | 211 | 0.689R | 125 (59.2%) | 124 (58.8%) | 2.00h |
| REF | ALL | EXPANSION | 267 | 0.891R | 149 (55.8%) | 134 (50.2%) | 2.42h |
| REF | ALL | H1_NEAREST | 252 | 0.841R | 145 (57.5%) | 142 (56.3%) | 2.00h |
| REF | ALL | MAJOR_NEAREST | 272 | 0.663R | 167 (61.4%) | 164 (60.3%) | 1.75h |
| REF | WIN | TP1 | 201 | 0.183R | 201 (100.0%) | 200 (99.5%) | 0.50h |
| REF | WIN | TP2 | 178 | 0.350R | 162 (91.0%) | 161 (90.4%) | 0.92h |
| REF | WIN | TP3 | 157 | 0.542R | 125 (79.6%) | 124 (79.0%) | 2.00h |
| REF | WIN | EXPANSION | 197 | 0.726R | 149 (75.6%) | 134 (68.0%) | 2.42h |
| REF | WIN | H1_NEAREST | 185 | 0.603R | 145 (78.4%) | 142 (76.8%) | 2.00h |
| REF | WIN | MAJOR_NEAREST | 201 | 0.531R | 167 (83.1%) | 164 (81.6%) | 1.75h |
| REF | LOSS | TP1 | 71 | 0.641R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | LOSS | TP2 | 63 | 1.013R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | LOSS | TP3 | 54 | 1.234R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | LOSS | EXPANSION | 70 | 1.282R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | LOSS | H1_NEAREST | 67 | 1.410R | 0 (0.0%) | 0 (0.0%) | —h |
| REF | LOSS | MAJOR_NEAREST | 71 | 1.174R | 0 (0.0%) | 0 (0.0%) | —h |

### TP2 extension anatomy (diagnostic only)

| Period | Outcome | TP2 available | TP2 hit before SL | TP2 hit <=24h | Med TP2 distance |
|---|---|---:|---:|---:|---:|
| DEV | WIN | 288 | 241 (83.7%) | 236 (81.9%) | 0.447R |
| DEV | LOSS | 94 | 0 (0.0%) | 0 (0.0%) | 0.803R |
| REF | WIN | 178 | 162 (91.0%) | 161 (90.4%) | 0.350R |
| REF | LOSS | 63 | 0 (0.0%) | 0 (0.0%) | 1.013R |

## Interpretation boundary
This audit does not choose a new TP, SL, or entry rule.
It measures how much room the frozen E2 setup actually had and which causal structural objectives were reachable before invalidation.
Any adaptive TP rule must be derived only after this audit and then validated separately on DEV/REF without changing the frozen detector.
