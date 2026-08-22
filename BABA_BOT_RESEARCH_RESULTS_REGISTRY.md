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
4. Current pooled-best SHORT diagnostic is **F15/D30 after retest #2**, total +$6.492, but it fails robustness because external remains slightly negative.
5. Historical 4H regime work showed **SHORT+SIDEWAYS**, not SHORT+BEAR, as the strongest side-specific SHORT pocket.
6. The current F15/D30 lineage has not yet been crossed with 4H BULL/BEAR/SIDEWAYS; that must be a separate preregistered audit.
7. No result in this registry changes live BBC automatically.

---

## Maintenance rule

Whenever a later experiment supersedes a diagnostic candidate, **do not delete the old row**. Add a new dated/experiment entry and explicitly state what changed in semantics. This registry is intended to preserve the research trail and prevent numerical results from being remembered under the wrong cohort.