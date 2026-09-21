# BNB B40-S4 — Frozen Demand Survival Detector Validation Preregistration

## Objective
Validate a simple frozen survival detector derived from B40-S3 without searching any new feature, threshold, level, or combination.

S4 asks:
"Among B40 demand zones still unresolved at +15m after first retest, can a simple sustained-response state identify zones that will SURVIVE before being structurally CONSUMED?"

## Frozen parent
Use only the persisted B40-S3 decision ledger.

Parent labels remain unchanged:
- SURVIVE = +0.50 event-R before a completed 15m close below protected_low
- CONSUMED = completed 15m close below protected_low before +0.50 event-R

No B39 D1 logic is imported.

## Frozen decision point
PLUS15_CLOSE only:
- exactly three raw 5m bars strictly after the completed first-retouch 15m bar;
- events already resolved before/on this checkpoint remain excluded exactly as in B40-S3.

Expected unresolved parity:
- DEV eligible = 532: 391 SURVIVE / 141 CONSUMED
- REF eligible = 307: 228 SURVIVE / 79 CONSUMED

## Frozen primary detector
### SD1_CLOSE15_ABOVE_ANCHOR
PASS when:
`CLOSE15_ABOVE_ANCHOR == True`

Interpretation:
after 15 minutes of post-touch interaction, the completed reaction window closes above the original first-retouch anchor.

No numeric threshold is searched.

## Frozen strict benchmarks
Report for comparison only; neither can replace SD1 in S4:
1. `B1_ALL3_ABOVE_ANCHOR`
   - all three post-touch 5m closes are above anchor.
2. `B2_BREAK_TOUCH_HIGH`
   - the +15m completed close is above the first-retouch 15m high.

These are latency/strictness benchmarks, not competing rules eligible for promotion.

## Required metrics
For DEV, REF, and every year:
- eligible unresolved zones
- detector PASS count / rate
- SURVIVE precision among PASS
- CONSUMED false-pass count / rate
- SURVIVE retention = PASS survivors / all eligible survivors
- CONSUMED rejection = rejected consumed / all eligible consumed
- Wilson 95% interval of PASS survival precision
- base survival rate and uplift
- whole-parent survivor capture, explicitly including too-fast survivors as outside the detector cohort

## Stability
Report:
- unchanged rule DEV -> REF
- each year 2022–2026
- no year-level tuning
- no threshold perturbation / selection

## Advance rule
SD1 may advance as the frozen B40 Demand Survival Detector only if:
1. PASS survival precision is materially above eligible base rate in both DEV and REF;
2. survivor retention remains operationally useful;
3. consumed rejection is meaningful;
4. REF does not collapse relative to DEV;
5. year results are not driven by one isolated year.

S4 validates survival only.
Expansion probability, entry, SL, and TP remain separate downstream problems.
