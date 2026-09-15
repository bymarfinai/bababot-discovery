# BNB B29-B1J — Journey Character Promotion Verdict

**Final character-level status: `BNB_B29_B1J_JOURNEY_CHARACTER_PASS`**

B1J-v1 is frozen after a valid preregistered run. Exactly one development-selected character survived unchanged through 2025 and 2026 reference validation.

## Reproducibility identity
- Branch: `bnb-b29-walkforward-reset`
- Preregistration commit: `2aa5a70908b24f73da9e0cb6f5180ad5806cab2e`
- Valid dedicated run: `34927125571`
- Valid run head: `710ea24c75d415d1d7b43ed57bb77698509c4ed7`
- Persisted evidence commit: `b4b6455d4cf42893dd75da25be16f68215bea1e3`
- Reproducibility artifact: `10379488957`
- Artifact digest: `sha256:e5d5c252399d3cddb92df345ea059f156a498a562d3b617b109b380067a51201`
- Accepted A1 source artifact: `10336102957`
- Accepted A1 fingerprint SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`

## Frozen winning character
Direction: **LONG**

Base event:
- current completed 15-minute decision bar has `sweep_low_60 == 1`;
- therefore the bar trades below the prior 60-minute low and closes back at/above that prior low.

Journey clause at `t-15m`:
- `pre_path_state == CONT_DOWN`.
- Under frozen A1 semantics this means the longer path is down (`disp_atr_360 < -0.75`) and the recent 60-minute path is also down (`disp_atr_60 < -0.25`).

Reclaim anatomy on the sweep bar:
- `reclaim_strength == HIGH` => A1 `close_location >= 0.50`, equivalent to the close finishing in the upper quarter of the completed candle range.
- `reclaim_body == LOW` => absolute candle body is <33% of the full completed candle range.

Compact interpretation:

`CONTINUATION DOWN JOURNEY -> SWEEP PRIOR 60M LOW -> SMALL-BODY STRONG UPPER-CLOSE RECLAIM -> LONG CHARACTER`

This is an interpretable structural rejection pattern after a sustained downward path, not a nearest-neighbor similarity rule and not an hour/session rule.

## Frozen evidence
Development discovery (2022-2024):
- N = 293
- +60m directional hit = 61.09%
- Wilson 95% lower bound = 55.40%
- worst development-era hit = 58.54%
- all 4 auxiliary horizons were >=54%
- BH-FDR q = 0.000883949

Era detail:
- 2022: N=97, +60m hit 60.82%
- 2023: N=82, +60m hit 58.54%
- 2024: N=114, +60m hit 63.16%
- 2025 reference: N=93, +60m hit 55.91%
- 2026 reference through frozen cutoff: N=65, +60m hit 58.46%

Reference validation:
- 2025+2026 N = 158
- +60m hit = 56.96%
- median signed +60m return > 0
- 3/4 auxiliary reference horizons >=54%

Pooled 2022-2026:
- N = 451
- +60m hit = 59.65%
- Wilson 95% lower bound = 55.05%
- every era >50%
- max five-era sample share <=35%

All preregistered B1J development and reference gates passed.

## What is frozen
The following character definition must not change in the next phase:
1. LONG direction;
2. `pre_path_state == CONT_DOWN`;
3. base `sweep_low_60 == 1` event;
4. `reclaim_strength == HIGH` cut at `close_location >= 0.50`;
5. `reclaim_body == LOW` cut at `body_range < 0.33`;
6. accepted A1 immutable history and gap-safe causal semantics.

Do not add hour/session/day filters, regime filters, extra character clauses, or loosen/tighten the character thresholds while calling it the same B1J winner.

## Promotion boundary
B1J proves a **character**, not an executable strategy.

The only allowed next scientific phase is execution discovery on this frozen character. That phase may compare preregistered entry mechanisms (for example event-close market, fixed ATR pullback, structural retest, reclaim confirmation, breakout/retest) and later TP/SL surfaces, but it must not alter the character itself.

No claim of READY TO TRADE is authorized yet. Final ready-to-trade status requires execution/risk rules to be frozen and then tested on genuinely new future shadow data not used by B29 discovery.

No live orders were placed.