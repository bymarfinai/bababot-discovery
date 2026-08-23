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

# REGIME DETECTOR FOUNDATION

# B27BN — 24H Swing-Boundary Invalidation Audit

**Source:** `BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BN_SWING_BOUNDARY_INVALIDATION_SUPPORTED`.**

**Purpose:** test whether the prior causally confirmed swing boundary from the last directional 4H state carries regime-invalidation information during the subsequent SIDEWAYS episode. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

**Frozen boundaries:** BULL uses the last directional state's latest confirmed swing low (`lsl`); BEAR uses the latest confirmed swing high (`lsh`). Boundary is frozen before SIDEWAYS begins. No ATR/percentage buffer or threshold fitting.

### Pooled-OOS first SIDEWAYS bar

- BULL: boundary break N **87**, eventual transition **49.4%**; boundary hold N **226**, transition **41.6%**; lift **+7.8pp**.
- BEAR: boundary break N **71**, eventual transition **59.2%**; boundary hold N **171**, transition **52.0%**; lift **+7.1pp**.

### Cumulative wick break by age 3 / 12h

- BULL: RESUME **33.0%** vs TRANSITION **47.4%** = **+14.5pp** transition separation.
- BEAR: RESUME **27.0%** vs TRANSITION **42.0%** = **+15.0pp** transition separation.

**OOS stability:** first-bar break lift and age-3 break separation were positive in external and reference_validation for both origins: external BULL +5.1pp/+15.5pp; external BEAR +9.6pp/+21.2pp; validation BULL +16.4pp/+18.8pp; validation BEAR +4.3pp/+10.1pp.

**Critical caveat:** swing-boundary break is informative but not a necessary or sufficient regime-change condition. In pooled OOS, **49.6%** of genuine BULL-origin transitions and **56.5%** of genuine BEAR-origin transitions reached the opposite detector state without ever wick-breaking the frozen boundary during SIDEWAYS. Conversely, **35.2%** of BULL resumes and **27.0%** of BEAR resumes did wick-break the boundary before returning to the origin regime. Therefore do not use swing break as a hard binary regime switch by itself.

Observable CI: run `32621440428`, job `97150076162`, success. Exact episode-level cohort is preserved in artifact `9488479830`, ZIP SHA256 `dd6bd11ab8be6e20c61c2516b51f2b1f8b9c4ec449879bdaccde4c29f7a97b95`.

Research only. Live BBC unchanged.

---


# B27BM — 24H SIDEWAYS Age-Hazard Audit

**Source:** `BTC_24H_SIDEWAYS_AGE_HAZARD_B27BM_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BM_PHASED_SIDEWAYS_HAZARD_SUPPORTED`.**

**Purpose:** test whether SIDEWAYS has a reproducible age-dependent cause-specific exit structure, conditional on the episode still being SIDEWAYS. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

### Pooled-OOS primary hazard readout

- BULL age1 / 4h: RESUME **28.8%**, TRANSITION **13.7%**, survive **57.5%**; T-R **-15.0pp**.
- BULL age2 / 8h: RESUME **20.0%**, TRANSITION **25.0%**, survive **55.0%**; T-R **+5.0pp**.
- BULL age3 / 12h: RESUME **13.1%**, TRANSITION **22.2%**, survive **64.6%**; T-R **+9.1pp**.
- BEAR age1 / 4h: RESUME **25.2%**, TRANSITION **20.7%**, survive **54.1%**; T-R **-4.5pp**.
- BEAR age2 / 8h: RESUME **19.1%**, TRANSITION **40.5%**, survive **40.5%**; T-R **+21.4pp**.
- BEAR age3 / 12h: RESUME **20.8%**, TRANSITION **30.2%**, survive **49.1%**; T-R **+9.4pp**.

**OOS stability:** age1->age2 transition-minus-resume margin shifted upward in every preregistered cell: external BULL -17.8pp->-0.9pp; external BEAR -7.4pp->+10.6pp; validation BULL -12.0pp->+13.5pp; validation BEAR -2.2pp->+32.3pp. All frozen gates passed.

**Interpretation:** SIDEWAYS is not temporally homogeneous. The first 4h bar is continuation-heavy; the 8h-12h phase becomes transition-heavy. Ages 4-6 are descriptive only and do not justify a monotonic older-SIDEWAYS=more-reversal rule. This supports an age-dependent regime-state concept only; it does not define a production state machine or trading rule.

Observable CI: run `32619094283`, job `97144386776`, success; exact hazard CSV artifact `9487827397`.

Research only. Live BBC unchanged.

---


# B27BL — 24H Temporal Transition Resolution Audit

**Source:** `BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BL_TEMPORAL_PENDING_STATE_NOT_SUPPORTED`.**

**Purpose:** test whether SIDEWAYS ambiguity is better modeled temporally as an unresolved `PENDING` state rather than forcing a final regime decision on the first completed 4H SIDEWAYS bar. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH directionally bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

### Pooled OOS temporal resolution

- +4h: **44.0%** resolved; 56.0% still pending; pending eventual transition rate **56.3%**.
- +8h: **72.6%** resolved.
- +12h: **83.8%** resolved.
- +24h: **91.7%** resolved.

### One-bar SIDEWAYS survival effect

Remaining SIDEWAYS beyond the first 4H bar increased eventual transition probability in every OOS origin/partition cell, but the pooled lift was below the frozen +10pp promotion gate:

- BULL pooled OOS: baseline **43.8%** -> pending **52.2%** = **+8.5pp**.
- BEAR pooled OOS: baseline **54.1%** -> pending **61.8%** = **+7.7pp**.
- External: BULL +6.3pp; BEAR +4.9pp.
- Reference validation: BULL +14.2pp; BEAR +11.8pp.

**Frozen gate outcome:** identity PASS; +8h resolution PASS; positive OOS sign PASS; sample-size PASS; +12h resolution PASS; pooled one-bar transition lift >=10pp for both origins FAIL.

**Interpretation:** temporal age is informative and most SIDEWAYS episodes resolve naturally within 8-12 hours, but the exact preregistered evidence was not strong enough to promote `PENDING` as the new detector state. Do not relax the +10pp gate post hoc. A new experiment is required for any alternative temporal state-machine design.

Observable CI: run `32618502009`, job `97142952212`, success. Exact CSV outputs are preserved in artifact `9487667797`.

Research only. Live BBC unchanged.

---


## B27BJ — 24H Magnitude-Aware SIDEWAYS Redesign Audit

**Source:** `BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BJ_MAGNITUDE_AWARE_REDESIGN_NOT_SUPPORTED`.**

**Purpose:** test a minimal magnitude-aware redesign of first-SIDEWAYS handling without hand-picking ATR thresholds. Separate BULL-origin and BEAR-origin logistic regressions were trained on `development` only using six preregistered causal B27BI features; external and reference_validation were strictly out-of-sample. The state-machine candidate inherited the prior directional state for exactly one 4H interval only when `P(RESUME)>=0.50`.

### Out-of-sample classifier performance

| Origin | Partition | N | AUC | Balanced accuracy | RESUME recall | TRANSITION recall |
|---|---|---:|---:|---:|---:|---:|
| BULL | external | 163 | 0.652 | 0.612 | 59.6% | 62.7% |
| BULL | reference_validation | 150 | 0.763 | 0.685 | 80.6% | 56.4% |
| BULL | pooled OOS | 313 | 0.690 | 0.637 | 68.2% | 59.1% |
| BEAR | external | 108 | 0.664 | 0.587 | 75.0% | 42.3% |
| BEAR | reference_validation | 134 | 0.637 | 0.558 | 67.3% | 44.3% |
| BEAR | pooled OOS | 242 | 0.654 | 0.573 | 71.2% | **43.5%** |

### Detector effect

- Raw pooled-major one-interval flip-back: **459/2,202 = 20.8%**.
- B27BJ one-interval flip-back: **177/1,640 = 10.8%**.
- `INHERITED_PAUSE` first-SIDEWAYS intervals: **604**.
- Pooled BULL persistence: **90.9% -> 93.2%**.
- Pooled BEAR persistence: **89.3% -> 91.9%**.
- Maximum major-partition occupancy drift: **20.5pp -> 21.2pp** (worse).
- Direct BULL<->BEAR change share: **7.0% -> 13.5%**.

**Why promotion failed:** the candidate dramatically reduced SIDEWAYS flip-back noise and improved directional persistence, but the BEAR-origin model hid too many genuine transitions: pooled-OOS TRANSITION recall was only **43.5%**, below the frozen 55% gate. It also worsened occupancy drift from 20.5pp to 21.2pp. Therefore the exact B27BJ threshold/model/state semantics are not promoted and must not be post-hoc tuned.

**Key interpretation:** magnitude-aware first-SIDEWAYS information is real out of sample (all origin/partition AUCs exceed 0.60), especially for BULL-origin, but a symmetric one-bar inherited-pause rule is too aggressive for BEAR-origin. Any next redesign must use a new preregistered experiment ID; no trading direction or entry research is authorized from B27BJ.

---

## B27BI — 24H SIDEWAYS Continuation-vs-Transition Feature Audit

**Source:** `BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BI_FIRST_SIDEWAYS_FEATURES_INSUFFICIENT_OR_UNSTABLE`.**

**Purpose:** test whether information already available on the **first completed 4H bar labeled SIDEWAYS** can distinguish a continuation-like pause (`BULL->SIDEWAYS->BULL` / `BEAR->SIDEWAYS->BEAR`) from a genuine transition to the opposite directional state. No trading economics were used.

**B27BH identity reproduced exactly:** 1,023 bracketed SIDEWAYS episodes = 527 same-state resumes + 496 opposite-state transitions; BULL-origin 532, BEAR-origin 491.

### Frozen four-clause evidence score

The first SIDEWAYS bar almost always retained **3 of 4** origin-direction regime clauses, regardless of eventual outcome:

| Origin | RESUME mean / median | TRANSITION mean / median |
|---|---:|---:|
| BULL | 2.986 / 3 | 2.988 / 3 |
| BEAR | 2.996 / 3 | 2.996 / 3 |

Thus the preregistered clause-count hypothesis failed: the simple count of surviving BULL/BEAR conditions does not distinguish continuation from transition.

### Pooled-major causal first-bar clues — descriptive only

Higher origin-normalized values favor RESUME in the AUC convention used below:

| Feature | BULL AUC | BEAR AUC | Interpretation |
|---|---:|---:|---|
| close vs EMA20, origin-normalized / ATR | **0.697** | **0.685** | shallower move through EMA20 is more continuation-like |
| EMA20 slope, origin-normalized / ATR | **0.697** | **0.685** | less deterioration of slow trend is more continuation-like |
| EMA7 slope, origin-normalized / ATR | 0.644 | 0.606 | less fast-trend deterioration favors resume |
| directional candle body / ATR | 0.632 | 0.610 | less violent counter-direction body favors resume |
| bar range / ATR | 0.394 | 0.405 | larger transition bar tends to favor genuine regime change |
| EMA7-EMA20 directional spread / ATR | 0.564 | 0.613 | wider surviving trend spread mildly favors resume |

**Critical interpretation:** the detector's discrete first-SIDEWAYS label loses useful magnitude information. In almost every case the state flips to SIDEWAYS because a binary clause fails, but **how far** price/EMA momentum deteriorated carries substantially more information than the clause count itself. These pooled AUCs are descriptive clues only; B27BI's preregistered primary gate still fails and no new SIDEWAYS rule is promoted.

**Research boundary:** do not call these paths accumulation/distribution from price alone. A separate preregistered detector-redesign audit is required before adding pause/transition states, hysteresis, inherited directional state, or confirmation logic.

---

## B27BH — 24H SIDEWAYS Transition Anatomy Audit

**Source:** `BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_Result.md`

**Audit:** PASS. **Frozen primary readout: `SIDEWAYS_MIDDLE_DOMINATES_ONE_BAR_FLIPBACKS`.**

**Purpose:** isolate the source of B27BG's 20.8% one-interval `A->B->A` detector flip-back rate before changing any regime definition. No future return, trade direction, entry, stop, target, fee, WR, PF, or PnL was used.

**Exact B27BG reproduction:** **459 / 2,202 = 20.8%** pooled-major one-interval flip-backs.

### One-interval flip-back anatomy

| Pattern | N | Share of all flip-backs |
|---|---:|---:|
| BULL -> SIDEWAYS -> BULL | 161 | 35.1% |
| BEAR -> SIDEWAYS -> BEAR | 145 | 31.6% |
| BULL -> BEAR -> BULL | 7 | 1.5% |
| BEAR -> BULL -> BEAR | 9 | 2.0% |
| SIDEWAYS -> BULL -> SIDEWAYS | 76 | 16.6% |
| SIDEWAYS -> BEAR -> SIDEWAYS | 61 | 13.3% |

**Key finding:** SIDEWAYS as the middle state accounts for **306/459 = 66.7%** of all one-bar flip-backs. Direct directional one-bar false flips (`BULL->BEAR->BULL` plus `BEAR->BULL->BEAR`) are only **16/459 = 3.5%**.

### Complete directionally bracketed SIDEWAYS episodes

There are **1,023** complete SIDEWAYS episodes with a directional state immediately before and after the SIDEWAYS episode:

| SIDEWAYS path | N | Share | Median SIDEWAYS duration |
|---|---:|---:|---:|
| BULL -> SIDEWAYS -> BULL | 281 | 27.5% | 1 bar / 4h |
| BEAR -> SIDEWAYS -> BEAR | 246 | 24.0% | 1 bar / 4h |
| BULL -> SIDEWAYS -> BEAR | 251 | 24.5% | 2 bars / 8h |
| BEAR -> SIDEWAYS -> BULL | 245 | 23.9% | 2 bars / 8h |

- Resume original directional state: **527/1,023 = 51.5%**.
- Transition to opposite directional state: **496/1,023 = 48.5%**.
- From BULL: resume **52.8%**, transition to BEAR **47.2%**.
- From BEAR: resume **50.1%**, transition to BULL **49.9%**.

**Important interpretation:** the current SIDEWAYS label is doing two materially different jobs almost equally often: (1) a short pause inside the existing directional regime, and (2) a genuine bridge into the opposite directional regime. The duration split is a strong descriptive clue: same-direction resumes have a **4h median**, while genuine directional transitions have an **8h median**. B27BH does not change the detector; any persistence/hysteresis/confirmation redesign must be preregistered separately.

---

## B27BG — 24H Causal Regime Detector Audit

**Source:** `BTC_24H_REGIME_DETECTOR_AUDIT_B27BG_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BG_REGIME_DETECTOR_NEEDS_REDESIGN`.**

**Purpose:** audit the regime detector itself before any directional, entry, stop, target, runner, or PnL research. Exact B27AG/B27BE `SwingRegime(5, 0.5)` semantics were reused on completed 4H bars only; the state becomes effective only after the source 4H bar closes. All seven calendar days were included. B27BE/B27BF remain frozen historical diagnostics.

### Pooled-major detector identity

| State | Intervals | Occupancy | Episodes | Median episode | Next-state persistence |
|---|---:|---:|---:|---:|---:|
| BULL | 6,690 | 46.4% | 607 | 6 bars / 24h | 90.9% |
| BEAR | 5,314 | 36.9% | 572 | 5 bars / 20h | 89.3% |
| SIDEWAYS | 2,407 | 16.7% | 1,024 | 2 bars / 8h | 57.5% |

### Pooled-major transition matrix

| From -> To | BULL | BEAR | SIDEWAYS |
|---|---:|---:|---:|
| BULL | 90.9% | 1.1% | 8.0% |
| BEAR | 1.5% | 89.3% | 9.2% |
| SIDEWAYS | 21.9% | 20.6% | 57.5% |

### Detector-quality gate

- Every state >=100 intervals in every major partition: **PASS**.
- BULL and BEAR next-state persistence >=60% in every major partition: **PASS**.
- Pooled median BULL episode >=2 completed 4H bars: **PASS** (6 bars).
- Pooled median BEAR episode >=2 completed 4H bars: **PASS** (5 bars).
- Pooled one-interval flip-back `A->B->A` <=20%: **FAIL**, actual **20.8%** (459/2,202 state-change-centered triples).
- Maximum state-occupancy drift across major partitions <=20 percentage points: **FAIL**, actual **20.5pp**.

**Important interpretation:** the existing detector is highly persistent for BULL and BEAR and direct BULL<->BEAR flips are rare (155 changes, 7.0% of pooled state changes), but under the frozen quality gate it narrowly fails noise/stability requirements. Therefore the next research step is **detector redesign/stabilization only**. Do not proceed to regime directional behavior, LONG/SHORT mapping, or entry-location discovery until a new detector audit passes or the user explicitly accepts this detector despite the frozen failure.

B27BG used no future return, liquidity direction, LONG/SHORT label, entry fraction, stop, target, fee, WR, PF, or PnL. Live BBC unchanged.

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

1. **Regime research is now explicitly stepwise.** B27BG audits the detector before any directional or entry research, and its frozen verdict is `NEEDS_REDESIGN` because flip-back noise (20.8%) and occupancy drift (20.5pp) narrowly exceeded preregistered limits.
2. **B27BH localizes the main detector-noise problem to SIDEWAYS.** SIDEWAYS in the middle accounts for 66.7% of one-bar flip-backs, while direct BULL<->BEAR one-bar false flips are only 3.5%. Across full SIDEWAYS episodes, however, pause/resume (51.5%) and true directional transition (48.5%) are almost evenly split, so simply deleting or inheriting SIDEWAYS would be incorrect.
3. SHORT entry timing improved materially by waiting for Low retest #2 before the F15 pullback entry.
4. Independent full-range discovery did **not** support entries near the London High after retest #2.
5. F05 has higher raw downside-resolution rate but its economics remain negative even after fairer equal-distance stops.
6. Current pooled-best SHORT diagnostic remains **F15/D30 after retest #2 in London->NY**, total +$6.492, but it fails robustness because external remains slightly negative.
7. Historical 4H regime work showed **SHORT+SIDEWAYS**, not SHORT+BEAR, as the strongest side-specific SHORT economic pocket.
8. B27BE confirms that across a 24H rolling 4H-range structural atlas, K1/OPP0 Low pressure is strong in all regimes (~69.5%-72.3% Low-break probability); BEAR is only modestly highest, while SIDEWAYS has the strongest pooled Low-break-after-second-visit probability at 77.7%.
9. B27BF tested the first adaptive router mapping `BULL->LONG / BEAR->SHORT / SIDEWAYS->FLAT` across the rolling 24H geometry and it failed: N580, PF0.926, expectancy -$0.097/trade, total -$56.249. This remains historical diagnostic context and should not bypass the new stepwise detector-first workflow.
10. B27BF counterfactual attribution found **SHORT/SIDEWAYS N57, PF1.349, expectancy +$0.421, total +$24.010**, while SHORT/BEAR remained negative. This is a diagnostic clue only; SIDEWAYS SHORT was not part of the frozen router and needs a new preregistered audit before use.
11. Moving the exact current candidate to the weekday **NY->20:00-24:00 post-NY off-session** did not improve it: N16, PF0.862, total -$3.546. Raw off-session direction was mildly bullish rather than bearish.
12. No result in this registry changes live BBC automatically.

---

## Maintenance rule

Whenever a later experiment supersedes a diagnostic candidate, **do not delete the old row**. Add a new dated/experiment entry and explicitly state what changed in semantics. This registry is intended to preserve the research trail and prevent numerical results from being remembered under the wrong cohort.