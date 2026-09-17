# BNB B30-S2 — Per-Structure Entry Archetype Discovery Preregistration

## Scientific identity
`BNB_B30_S2_ENTRY_ARCHETYPE_V1`

Parent: `BNB_B30_S1_STRUCTURE_LIBRARY_V1`.

S1 froze eight independent market-structure detectors. S2 asks a separate question for each detector: **after that structure has causally completed, which preregistered entry archetype gives the cleanest subsequent directional behavior?**

S2 MUST NOT alter an S1 structure definition. S2 also MUST NOT evaluate TP/SL, MFE/MAE, RR, fees, leverage, PnL, expectancy, PF or DD. Those remain illegal until S3 economics.

## Immutable source and parent identity
Use accepted B29-A1 artifact only:
- artifact id `10336102957`
- SHA256 `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- 229267 rows; cutoff `2026-08-26T00:00:00Z`.

Reconstruct the S1 detector events exactly. Parent event-count identity must equal:
- S01 8092
- S02 797
- S03 1577
- S04 5109
- S05 8542
- S06 637
- S07 1207
- S08 5553

Any mismatch is `DATA_TOOLING_FAILURE`, not a scientific result.

## Development / reference split
- Development: 2022, 2023, 2024.
- One-shot reference: 2025 and 2026 through the immutable cutoff.

For each structure, entry policies are ranked using development only. Exactly one development winner per structure may be opened on reference. Reference results may not be used to choose another policy.

## Direction
Frozen by S1:
- LONG: S01, S02, S03, S04.
- SHORT: S05, S06, S07, S08.

A directional signed return is `raw_return * +1` for LONG and `raw_return * -1` for SHORT.

Numerical flat guard: `abs(signed_return) <= 1e-12` is FLAT and is NOT a directional hit. A directional hit requires `signed_return > 1e-12`.

## Frozen entry archetypes
Every policy uses only information fully closed by its own entry timestamp.

### E0 `STRUCTURE_CLOSE`
Entry timestamp = structure completion timestamp `t`.

### E1 `DELAY_15`
Entry timestamp = exact `t+15m`, unconditional, if the timestamp exists.

### E2 `ONE_BAR_DIRECTION_CONFIRM`
Entry timestamp = exact `t+15m` only when that newly closed 15m bar has directional `ret_15` aligned with the structure side:
- LONG: `ret_15(t+15) > 0`;
- SHORT: `ret_15(t+15) < 0`.
Otherwise the structure occurrence has no E2 entry.

### E3 `FIRST_PATH_CONTINUATION_30`
Inspect exact `t+15m`, then `t+30m`. Entry at the first timestamp where:
- LONG: `path_state == CONT_UP`;
- SHORT: `path_state == CONT_DOWN`.
If neither qualifies, no E3 entry.

### E4 `FIRST_LIQUIDITY_BREAK_30`
Inspect exact `t+15m`, then `t+30m`. Entry at the first timestamp where:
- LONG: `break_high_60 == 1`;
- SHORT: `break_low_60 == 1`.
If neither qualifies, no E4 entry.

These five archetypes are applied independently inside every S1 structure. Their meaning is contextual: e.g. E4 after a sweep is a post-reclaim breakout entry, while E4 after a continuation structure is a fresh liquidity-break entry.

## Directional evaluation after entry
No economic exits are simulated.

Primary horizon: exact +60m close-to-close from the selected entry timestamp.
Auxiliary horizons: exact +30m and +120m.
A horizon is valid only if every required 15m return step exists; known A1 gaps may not be crossed.

For each structure × policy report:
- parent structure count;
- valid entry count and participation;
- N by era;
- primary +60m directional hit rate and Wilson 95% lower bound;
- median signed +60m close-to-close return;
- +30m and +120m directional hit rates;
- per-era +60m hit rates.

## Development eligibility gate
A structure × policy is development-eligible iff all are true:
1. development valid-entry N >=120;
2. each development year N >=25;
3. participation among valid-horizon parent events >=35%;
4. pooled +60m directional hit >=55%;
5. Wilson 95% lower bound >50%;
6. each 2022/2023/2024 +60m directional hit >=52%;
7. median signed +60m return >0;
8. at least one of +30m or +120m directional hit >=53%.

## Winner selection within each structure
Among development-eligible policies for the same structure, select exactly one using frozen ranking:
1. highest worst development-era +60m hit;
2. highest +60m Wilson lower bound;
3. highest pooled +60m hit;
4. higher participation;
5. lexical policy id tie-break.

If no policy is eligible, the structure gets status `NO_ENTRY_ARCHETYPE_FOUND` and reference remains unopened for that structure.

## One-shot reference gate
The single selected policy for a structure passes S2 iff all are true:
1. 2025 N >=20 and 2026 N >=15;
2. reference participation >=35%;
3. combined 2025+2026 +60m directional hit >=53%;
4. 2025 +60m directional hit >50%;
5. 2026 +60m directional hit >50%;
6. combined median signed +60m return >0;
7. at least one reference auxiliary horizon (+30/+120) directional hit >=52%.

A PASS freezes only an **entry archetype for that structure**. It is not a profitable strategy and does not authorize trading.

## S3 handoff
Each S2-passing `(structure, entry archetype)` pair advances independently to S3 economic discovery. Only S3 may inspect intratrade excursion, TP, SL, RR, fees, PnL, PF, DD and loss streak.

## Anti-rescue rules
- Do not change S1 structure definitions.
- Do not add time/session filters.
- Do not change +60m primary horizon after seeing results.
- Do not move entry confirmation thresholds after seeing outcomes.
- Do not promote a second policy after the one-shot reference winner fails.
- Do not call directional hit rate a trading win rate.
