# Baba Bot Research Results Registry

**Purpose:** durable human-readable registry for important research findings so numerical results, lineage, and caveats are not lost or conflated across experiments.

**Status:** research record only. This file does **not** authorize live deployment or changes to live BBC rules.

**Last seeded:** 2026-08-23 (UTC+7 discussion context).

---

## Persistence protocol — REQUIRED FOR FUTURE RESEARCH

For every material research experiment:

1. Preregister semantics and success/promotion gates **before** seeing new results.
2. Commit preregistration.
3. Implement and run through GitHub CI.
4. Do not call an experiment PASS until the persisted result exists.
5. Persist the experiment-specific result file(s) to `main`.
6. Update this registry with:
   - experiment ID;
   - exact cohort/lineage;
   - key numerical result(s);
   - PASS/FAIL/diagnostic/promoted status;
   - important caveats;
   - source result filename.
7. Never silently replace a historical result when semantics change; add a new lineage entry instead.
8. Keep side-specific results separate from combined LONG+SHORT results.
9. Keep structural evidence separate from economic evidence.
10. Research-only changes must not modify live BBC unless explicitly authorized.

---

# CURRENT SHORT LINEAGE

## B27BF — 24H Adaptive Regime Router Audit

**Source:** `BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BF_ADAPTIVE_ROUTER_NOT_SUPPORTED`.**

**Question tested:** whether the existing causal 4H state can operate as an adaptive 24/7 playbook router without Asia/London/New-York entry windows.

**Frozen router v1:**
- BULL -> rolling-range LONG playbook translated from B27W/B27AA/B27AC.
- BEAR -> rolling-range SHORT playbook translated from B27AY/B27BC.
- SIDEWAYS -> FLAT.
- UTC 4H boundaries refresh the causal regime state and previous-4H frozen H/L; they are not preferred trading hours.
- All seven calendar days included.

### Router economics

| Partition | N | WR | PF | Exp/trade | Total | E20 activation | Trades/week |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 197 | 49.7% | 0.853 | -$0.247 | -$48.616 | 43.7% | 1.89 |
| development | 269 | 50.2% | 0.969 | -$0.038 | -$10.169 | 47.6% | 1.72 |
| reference_validation | 114 | 51.8% | 1.025 | +$0.022 | +$2.535 | 52.6% | 1.39 |
| **POOLED_MAJOR** | **580** | **50.3%** | **0.926** | **-$0.097** | **-$56.249** | **47.2%** | **1.69** |

### Frozen router components — pooled major

| Component | Regime | N | WR | PF | Exp/trade | Total |
|---|---|---:|---:|---:|---:|---:|
| LONG | BULL | 488 | 52.3% | 0.960 | -$0.052 | -$25.359 |
| SHORT | BEAR | 92 | 40.2% | 0.750 | -$0.336 | -$30.890 |

### Counterfactual playbook attribution — pooled major

These rows were simulated only for attribution. They did **not** change router eligibility.

| Side / actual regime | N | WR | PF | Exp/trade | Total |
|---|---:|---:|---:|---:|---:|
| LONG / BULL | 488 | 52.3% | 0.960 | -$0.052 | -$25.359 |
| LONG / BEAR | 350 | 48.6% | 0.719 | -$0.369 | -$129.094 |
| LONG / SIDEWAYS | 169 | 48.5% | 0.813 | -$0.253 | -$42.693 |
| SHORT / BULL | 105 | 37.1% | 0.391 | -$0.789 | -$82.864 |
| SHORT / BEAR | 92 | 40.2% | 0.750 | -$0.336 | -$30.890 |
| **SHORT / SIDEWAYS** | **57** | **47.4%** | **1.349** | **+$0.421** | **+$24.010** |

**Critical guardrail:** `SHORT / SIDEWAYS +$24.010` is a **post-run counterfactual diagnostic**, not a promoted router rule. SIDEWAYS was preregistered FLAT in B27BF. Activating SHORT in SIDEWAYS requires a separate preregistered experiment; it cannot be adopted from B27BF after seeing the result.

**Key lesson:** the naive trend-aligned mapping `BULL->LONG / BEAR->SHORT` failed across the rolling 24H geometry. The strongest new economic clue is again SHORT during SIDEWAYS, consistent in direction with older B27AG, but the exact B27BF SIDEWAYS row is not yet a validated adaptive rule.

---

## B27BE — 24H Causal 4H Regime SHORT Compatibility Atlas

**Source:** `BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Result.md`

**Audit:** PASS. **Frozen status: `B27BE_SHORT_STRUCTURALLY_FAVORED_NONE__CLOCK_NONE`.**

**Question tested:** whether the existing causal 4H BULL/BEAR/SIDEWAYS detector identifies recurring SHORT-compatible states across the entire BTC day without Asia/London/New-York session filters.

**Frozen geometry:** all seven calendar days; six sequential 4H observation blocks cover 00:00-24:00 UTC. Each block uses the immediately previous completed 4H H/L as its frozen liquidity reference. The 4H regime is available only after its bar completes. A pandas datetime-unit compatibility bug in the original lookup was fixed without changing detector parameters or regime semantics.

### Pooled-major structural atlas

| Regime | Blocks | K1 OPP0 | Low break | High break | No break | 2nd Low | Low break after 2nd |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 6,690 | 1,146 | 70.3% | 7.5% | 22.2% | 23.9% | 71.9% |
| BEAR | 5,312 | 1,122 | **72.3%** | 6.7% | 21.0% | 24.4% | 71.5% |
| SIDEWAYS | 2,407 | 499 | 69.5% | 6.4% | 24.0% | **26.1%** | **77.7%** |

### Major-partition regime stability

| Regime | External low break / 2nd Low | Development | Validation |
|---|---|---|---|
| BULL | 64.8% / 21.0% | 70.0% / 29.4% | 80.1% / 17.5% |
| BEAR | 66.0% / 26.1% | 71.1% / 24.6% | 79.2% / 22.8% |
| SIDEWAYS | 67.6% / 24.7% | 70.9% / 28.4% | 72.6% / 26.4% |

**Frozen gate:** NONE passes because the preregistered regime gate required second-Low-visit probability >=50% in every major partition. Actual second-Low probability is only ~17.5%-29.4% depending state/partition.

**Important interpretation:** the first Low K1/OPP0 event is directionally strong across **all** 4H regimes (~69.5%-72.3% pooled Low break), so BEAR is only modestly better on first-break probability. However, repeated-Low pressure does not occur often enough inside a single 4H observation block for any regime to satisfy the frozen `2nd Low >=50%` gate. SIDEWAYS has the strongest pooled Low-break-after-second-visit probability (77.7%), which echoes earlier regime findings, but B27BE is structural only and does not establish profitable entry economics.

### Pooled clock diagnostics

- 00-04: Low break 72.1%, 2nd Low 22.3%, break-after-2nd 80.8%.
- 04-08: 72.3%, 25.3%, 75.7%.
- 08-12: 68.1%, 22.9%, 67.9%.
- 12-16: 72.4%, 27.5%, 72.5%.
- 16-20: 72.5%, 24.1%, 74.8%.
- 20-00: 67.9%, 24.3%, 64.8%.

No clock block passes the same frozen three-partition gate. No session/time block is promoted.

**Next evidence needed:** economic attribution of a genuinely continuous 24H SHORT execution rule by causal regime. Do not infer that the current London->NY Retest#2/F15/D30 economics automatically transfer to the 4H rolling-range cohort.

---

## B27BD — NY -> Post-NY Off-Session SHORT Audit

**Source:** `BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Result.md`

**Audit:** PASS. **Frozen verdict: B27BD_NOT_ROBUST.**

**Question tested:** whether the current leading SHORT architecture improves when moved out of the three active session blocks into the previously unassigned post-New-York block.

**Frozen time/source geometry:** New York 13:30-20:00 UTC H/L frozen after 20:00; observation/trading 20:00-24:00 UTC on complete weekdays. BTC is 24/7, so `market closed` here means post-NY/off-session, not exchange closure.

**Frozen setup:** `NY Low Touch #1 -> Low Touch #2 -> causal leave -> F15 SHORT -> D30 hard stop -> E20_DOWN -> 100% full-position hybrid`.

### Raw post-NY direction census — pooled major

- Complete weekdays: **1,716**.
- Down days: **46.3%**.
- Mean 20:00->23:55 return: **+7.89 bp**.
- Median return: **+6.41 bp**.
- Completed-close break above frozen NY High: **24.9%**.
- Completed-close break below frozen NY Low: **20.3%**.
- High breaks first: **24.7%**; Low breaks first: **19.8%**; no strict boundary close-break: **55.5%**.

**Interpretation:** the post-NY weekday block is not intrinsically more bearish in this sample; pooled raw direction is mildly positive/bullish.

### Current candidate shifted to off-session

| Partition | N | E20 act | Act rate | WR | PF | Exp/trade | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 4 | 2 | 50.0% | 50.0% | 0.592 | -$1.253 | -$5.012 |
| development | 7 | 1 | 14.3% | 28.6% | 0.884 | -$0.131 | -$0.919 |
| reference_validation | 5 | 1 | 20.0% | 40.0% | 1.431 | +$0.477 | +$2.386 |
| **POOLED_MAJOR** | **16** | **4** | **25.0%** | **37.5%** | **0.862** | **-$0.222** | **-$3.546** |

**Key lesson:** simply moving the current Retest#2/F15/D30 SHORT architecture into the weekday 20:00-24:00 post-NY block does **not** rescue it; opportunity count collapses and pooled economics remain negative. This does not test weekends, which require a separate preregistered experiment.

---

## B27BC — Post-Retest#2 Equal-Distance Hard-Stop Economics

**Source:** `BTC_LONDON_NY_SHORT_POST_H2_EQUAL_DISTANCE_STOP_B27BC_Result.md`

**Audit:** PASS.

**Frozen setup:**
`Low Touch #1 -> Low Touch #2 -> causal leave -> SHORT retrace entry -> hard resting stop measured from entry -> E20_DOWN activation -> 100% full-position hybrid runner`.

Only entry zone and preregistered stop distance grid were compared. Same-bar stop-vs-E20 ambiguity was resolved **stop-first** conservatively.

### Pooled-major headline

| Candidate | N | WR | PF | Exp/trade | Total | Formal status |
|---|---:|---:|---:|---:|---:|---|
| F05 / D30 | 28 | 53.6% | 0.811 | -$0.243 | -$6.814 | FAIL |
| F05 / D40 | 28 | 53.6% | 0.816 | -$0.234 | -$6.565 | FAIL |
| F05 / D50 | 28 | 53.6% | 0.709 | -$0.428 | -$11.985 | FAIL |
| F10 / D30 | 37 | 51.4% | 1.033 | +$0.036 | +$1.350 | NOT ROBUST |
| F10 / D40 | 37 | 56.8% | 1.004 | +$0.005 | +$0.178 | NOT ROBUST |
| F10 / D50 | 37 | 56.8% | 0.925 | -$0.098 | -$3.612 | FAIL |
| **F15 / D30** | **42** | **52.4%** | **1.152** | **+$0.155** | **+$6.492** | **BEST DIAGNOSTIC; NOT ROBUST** |
| F15 / D40 | 42 | 57.1% | 1.032 | +$0.038 | +$1.584 | NOT ROBUST |
| F15 / D50 | 42 | 59.5% | 1.110 | +$0.122 | +$5.129 | NOT ROBUST |

**Formal B27BC selection:** `NONE`.

**Current leading SHORT diagnostic candidate:** `Retest #2 -> F15 -> D30 hard stop -> E20 full hybrid`.

### F15 / D30 partition detail

| Partition | N | WR | PF | Exp/trade | Total |
|---|---:|---:|---:|---:|---:|
| external | 10 | 40.0% | 0.893 | -$0.118 | -$1.183 |
| development | 26 | 53.8% | 1.118 | +$0.127 | +$3.291 |
| reference_validation | 6 | 66.7% | 2.206 | +$0.731 | +$4.383 |

**Interpretation:** tightening risk from the old absolute F65 geometry materially improved SHORT economics, but external remains slightly negative. Do **not** call F15/D30 promoted or validated.

---

## B27BB — Post-Retest#2 F05/F10/F15 Winner MAE / Natural Stop-Distance Audit

**Source:** `BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Result.md`

**Audit:** PASS. Diagnostic only; no stop selected.

Old F65 invalidation was removed from the path audit. Winner = raw chronology reaches E20. Distance `D` is measured upward from each entry in London-range units.

### Pooled-major raw E20 and winner MAE

| Entry | N | Raw E20 | Rate | Winner MAE P50 | P75 | P90 | P95 | Non-E20 median adverse D |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F05 | 28 | 17 | 60.7% | 0.146R | 0.232R | 0.312R | 0.418R | 0.505R |
| F10 | 37 | 22 | 59.5% | 0.173R | 0.281R | 0.326R | 0.602R | 0.529R |
| F15 | 42 | 24 | 57.1% | 0.203R | 0.273R | 0.399R | 0.544R | 0.442R |

**Important:** B27BB showed that F05 itself was not fairly judged by the old F65 stop. However, B27BC later showed that equal-distance hard stops still did not make F05 profitable.

---

## B27BA — Post-Retest#2 F05/F10/F15 Economics with Old F65

**Source:** `BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_ECON_B27BA_Result.md`

**Audit:** PASS.

| Entry | N | WR | PF | Exp/trade | Total |
|---|---:|---:|---:|---:|---:|
| F05 | 28 | 57.1% | 0.834 | -$0.215 | -$6.034 |
| F10 | 37 | 59.5% | 0.943 | -$0.075 | -$2.776 |
| F15 | 42 | 61.9% | 1.114 | +$0.130 | +$5.450 |

**Formal selection:** `NONE` because no entry zone had expectancy >= 0 and PF >= 1 in external, development, and validation simultaneously.

**Key lesson:** F05 had the highest structural E20 rate but inferior price geometry under the old absolute F65 stop.

---

## B27AZ — Full-Range Entry-Zone Discovery After Retest #2

**Source:** `BTC_LONDON_NY_SHORT_POST_H2_RETRACE_ZONE_B27AZ_Result.md` (or corresponding persisted B27AZ result file in repo).

**Audit:** PASS.

Independent full-range sweep after valid Low retest #2 tested `F05 ... F95` without assuming entry should remain near Low.

Key pooled structural observations:

- F05: 28 fills, 22 downside resolutions = 78.6%.
- F10: 37 fills, 27 downside resolutions = 73.0%.
- **F15: 42 fills, 31 downside resolutions = 73.8%; highest opportunity count.**
- F40: 20 fills, 7 resolutions = 35.0%.
- F50: 15 fills, 3 resolutions = 20.0%.
- F75-F95: fills occurred but **0 downside resolutions** in the observed cohort.

**Key lesson:** after Low retest #2, a deep upward retracement toward the London High is not a better SHORT entry in this sample; it increasingly behaves like SHORT setup failure. F15 re-emerged independently as the highest-opportunity useful zone.

---

## B27AY — F15 Entry Between Low Retest #2 and #3

**Source:** `BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Result.md` / persisted summary.

**Audit:** PASS.

Setup changed only entry timing: wait for a valid second Low retest, then causal leave, then F15 entry before a third Low revisit/direct breakdown.

### Economics

| Partition | N | WR | PF | Exp/trade | Total |
|---|---:|---:|---:|---:|---:|
| external | 10 | 40.0% | 0.579 | -$0.716 | -$7.157 |
| development | 26 | 65.4% | 1.223 | +$0.242 | +$6.289 |
| reference_validation | 6 | 83.3% | 3.283 | +$1.053 | +$6.318 |
| **POOLED_MAJOR** | **42** | **61.9%** | **1.114** | **+$0.130** | **+$5.450** |

**Status:** pooled improvement but not robust. The major conceptual improvement was requiring Low Touch #2 before taking the pullback SHORT.

---

# 4H REGIME RESULTS — DO NOT CONFLATE SIDE-SPECIFIC AND COMBINED RESULTS

## B27AG — 4H HH/HL Regime Alignment Audit

**Source:** `BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Result.md`

**Audit:** PASS.

### Side-specific confirmed-entry economics

| Side | Rule | 4H state | N | Fixed WR | Fixed PF | Fixed total | Hybrid WR | Hybrid PF | Hybrid total |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| LONG | EARLY_RECLAIM | BULL | 55 | 70.9% | 1.66 | +$46.12 | 69.1% | 1.98 | +$68.55 |
| LONG | EARLY_RECLAIM | BEAR | 41 | 63.4% | 1.04 | +$2.63 | 51.2% | 0.99 | -$0.67 |
| LONG | EARLY_RECLAIM | SIDEWAYS | 22 | 86.4% | 2.33 | +$27.77 | 86.4% | 2.70 | +$35.42 |
| SHORT | EARLY_REJECT | BULL | 52 | 51.9% | 0.56 | -$38.75 | 46.2% | 0.78 | -$19.76 |
| **SHORT** | **EARLY_REJECT** | **BEAR** | **41** | **58.5%** | **0.90** | **-$6.99** | **51.2%** | **0.66** | **-$25.69** |
| **SHORT** | **EARLY_REJECT** | **SIDEWAYS** | **27** | **74.1%** | **2.16** | **+$38.06** | **66.7%** | **2.25** | **+$42.64** |

### Combined LONG+SHORT alignment buckets

| Alignment bucket | N | Fixed WR | Fixed PF | Fixed total | Hybrid WR | Hybrid PF | Hybrid total |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALIGNED | 96 | 65.6% | 1.28 | +$39.12 | 61.5% | 1.29 | +$42.86 |
| COUNTER | 93 | 57.0% | 0.77 | -$36.12 | 48.4% | 0.87 | -$20.43 |
| **SIDEWAYS** | **49** | **79.6%** | **2.23** | **+$65.82** | **75.5%** | **2.42** | **+$78.06** |

### Critical memory guardrail

- **+$65.82 is NOT SHORT+BEAR.** It is the **combined LONG+SHORT SIDEWAYS bucket** with fixed exit.
- **+$78.06** is the corresponding combined SIDEWAYS hybrid result.
- SHORT+BEAR is **-$6.99 fixed / -$25.69 hybrid**.
- The strongest side-specific SHORT regime pocket in B27AG is **SHORT+SIDEWAYS: +$38.06 fixed / +$42.64 hybrid**.
- B27AG used the older confirmed-entry lineage. It has **not yet been applied to the current Retest#2 -> F15 -> D30 SHORT candidate**.

---

# HISTORICAL LONG REFERENCE

## B27AC — E20-Triggered Profit-Lock Runner

Historical LONG SAME_BAR diagnostic pooled-major result:

- Fixed E20: N68, WR 73.5%, PF ~1.70, total **+$61.80**.
- E20-triggered full-position hybrid: N68, WR 69.1%, PF ~2.03, total **+$91.31**.

Important lineage note: later B27AJ confirmed that this +$91.31 cohort was **all-regime liquidity cohort**, not a hard 4H-BULL-gated cohort.

This remains historical/diagnostic context, not automatic live authorization.

---

# CURRENT INTERPRETATION SNAPSHOT

1. **SHORT entry timing improved materially by waiting for Low retest #2 before the F15 pullback entry.**
2. Independent full-range discovery did **not** support entries near the London High after retest #2.
3. F05 has higher raw downside-resolution rate but its economics remain negative even after fairer equal-distance stops.
4. Current pooled-best SHORT diagnostic remains **F15/D30 after retest #2 in London->NY**, total +$6.492, but it fails robustness because external remains slightly negative.
5. Historical 4H regime work showed **SHORT+SIDEWAYS**, not SHORT+BEAR, as the strongest side-specific SHORT economic pocket.
6. B27BE confirms that across a 24H rolling 4H-range structural atlas, K1/OPP0 Low pressure is strong in all regimes (~69.5%-72.3% Low-break probability); BEAR is only modestly highest, while SIDEWAYS has the strongest pooled Low-break-after-second-visit probability at 77.7%.
7. B27BF tested the first true adaptive router mapping `BULL->LONG / BEAR->SHORT / SIDEWAYS->FLAT` across the rolling 24H geometry and it failed: N580, PF0.926, expectancy -$0.097/trade, total -$56.249.
8. B27BF counterfactual attribution found **SHORT/SIDEWAYS N57, PF1.349, expectancy +$0.421, total +$24.010**, while SHORT/BEAR remained negative. This is a diagnostic clue only; SIDEWAYS SHORT was not part of the frozen router and needs a new preregistered audit before use.
9. Moving the exact current candidate to the weekday **NY->20:00-24:00 post-NY off-session** did not improve it: N16, PF0.862, total -$3.546. Raw off-session direction was mildly bullish rather than bearish.
10. No result in this registry changes live BBC automatically.

---

## Maintenance rule

Whenever a later experiment supersedes a diagnostic candidate, **do not delete the old row**. Add a new dated/experiment entry and explicitly state what changed in semantics. This registry is intended to preserve the research trail and prevent numerical results from being remembered under the wrong cohort.