# BNB B29 A4 — Selective Character Evidence Gate

## Status
PREREGISTERED BEFORE A4 OUTCOME READOUT.

A4 is a new scientific identity after valid rejection of A3. It must not select historically winning regime labels. The hypothesis is narrower: A3 may contain useful information only when its **causally available evidence is unusually coherent**. Most timestamps are expected to become `NO_MEMORY`.

## Frozen parent identities
- A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`.
- A3 slow-regime model, local features, K=64 analogs, chronological folds, query schedule, fixed horizons and analog selection are unchanged.
- A3 accepted baseline: mean pooled sign agreement 50.61%; median pooled Spearman rho 0.0198.
- Frozen raw cutoff remains 2026-08-26 00:00 UTC. No later data may be read.

## Frozen folds and diagnostic horizons
Walk-forward folds: 2022, 2023, 2024, 2025, 2026-precutoff.

Fixed horizons: +15m, +30m, +60m, +120m, +360m.

No horizon is selected after seeing A4 outcomes.

## A4 evidence gate — outcome blind
For each A3 query, compute only from information already available at that query:

1. **Directional consensus:** all five A3 predicted forward returns must have the same non-zero sign (`5/5`).
2. **Prediction strength:** median absolute predicted return across the five horizons must be >= 0.00050 (5 bps), and maximum absolute predicted return >= 0.00100 (10 bps).
3. **Local similarity:** `median_similarity >= 0.35`.
4. **Structural coherence:** `same_structure_rate >= 0.50` and `same_path_rate >= 0.50`.
5. **Analog density:** `regime_memory_n >= 1000` and `analog_n == 64`.
6. A3 chronology and exact-regime identity remain mandatory.

If every clause passes, label the timestamp `EVIDENCE_READY`; otherwise label it `NO_MEMORY`.

The diagnostic direction is the common sign of the five A3 predictions. This is **not yet a trade entry** and no order, entry price, TP, SL, leverage, fee or PnL is defined in A4.

## Frozen acceptance gates
Integrity must PASS before behavioural interpretation:
- exact A1 fingerprint identity;
- frozen raw boundary;
- finite numeric outputs;
- A3 chronology preserved;
- no post-cutoff data;
- all selected rows satisfy every evidence clause.

Selectivity gates:
- each fold has at least 50 `EVIDENCE_READY` rows;
- each fold coverage is >=1% and <=35% of A3 evaluable queries;
- pooled coverage is <=25%.

Behavioural gates on `EVIDENCE_READY` only:
- mean directional hit across five fixed horizons >=52.50%;
- at least 4/5 pooled horizons have directional hit >=52.00%;
- median pooled Spearman rho >=0.0400;
- at least 4/5 chronological folds have positive median rho;
- no fold mean directional hit <50.00%;
- 2025 mean directional hit >=51.50%;
- 2026 mean directional hit >=51.50%;
- versus accepted A3 baseline, mean sign lift >=+1.50 percentage points and median-rho lift >=+0.0150.

PASS requires all integrity, selectivity and behavioural gates.

## Stop rule
If A4 rejects, do not alter these thresholds, cherry-pick regime labels, reduce K, choose only a winning horizon, or inspect later data to rescue this identity. Any materially different selective-memory hypothesis receives a new identity.

## Interpretation
A4 asks only whether BNB contains a sparse, causally identifiable subset where character-memory evidence is materially stronger than the all-condition A3 parent. PASS promotes that subset toward execution discovery. REJECT means this evidence definition is not strong enough and entry/TP/SL discovery remains blocked.
