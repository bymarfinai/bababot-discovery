# SOL Score-4 SHORT Character Rediscovery V1 — Preregistration

## Objective

Perform exactly one structural-character rediscovery for:

**Anatomy Score 4 + BUY_SIDE liquidity -> SHORT**

The purpose is not to optimize a numeric threshold. The purpose is to determine whether Score-4 SHORT has a discrete, causal structural topology that separates true continuation from reclaim failure.

If no robust structural character is found in this V1, Score-4 SHORT is removed from the tradable universe. No V2/V3 threshold rescue is permitted.

## Frozen upstream stack

Unchanged:
- actionable structural-liquidity detector;
- anatomy score = 4;
- BUY_SIDE only;
- GAP_25 entry;
- RECLAIM_EXTREME initial SL;
- structural-completion exit for economic diagnostics.

Same-reclaim-bar outcome resolution remains excluded by the actionable detector.

## Evidence boundary

All data after **2026-08-26 00:00 UTC** are CLOSED for this rediscovery.

- 2020-2024 = construction.
- 2025 = retrospective consistency check.
- 2026 pre-cutoff = secondary retrospective consistency only.
- post-cutoff data are not used.

2025/2026 are not independent validation because they have been observed in prior work.

## Candidate character family

Only the following binary structural motifs may be tested.

All are known by the reclaim close or, where explicitly stated, by the actual entry time.

### Reclaim displacement motifs

1. `RECLAIM_BREAKS_SWEEP_LOW`
   - reclaim H1 close < sweep H1 low.

2. `RECLAIM_BREAKS_PRE_SWEEP_LOW`
   - reclaim H1 close < low of the H1 bar immediately before the sweep.

3. `RECLAIM_BREAKS_LOCAL_3BAR_LOW`
   - reclaim H1 close < minimum low of the 3 completed H1 bars immediately before the sweep.

4. `RECLAIM_CLOSE_BELOW_APPROACH_START`
   - reclaim H1 close < close of the third completed H1 bar before the sweep.

5. `RECLAIM_BODY_ENGULFS_SWEEP_BODY`
   - reclaim is bearish and its real body fully engulfs the sweep candle real body:
     reclaim open >= max(sweep open, sweep close)
     AND reclaim close <= min(sweep open, sweep close).

### Relative range / rejection motifs

6. `RECLAIM_RANGE_EXPANDS_VS_SWEEP`
   - reclaim H1 range > sweep H1 range.

7. `RECLAIM_RANGE_EXPANDS_VS_PRE_SWEEP`
   - reclaim H1 range > immediately-pre-sweep H1 range.

8. `RECLAIM_INSIDE_DEPTH_EXCEEDS_SWEEP_OVERSHOOT`
   - distance from liquidity level down to reclaim close
     > distance from liquidity level up to sweep high.

9. `SWEEP_SAME_BAR_REJECTION`
   - sweep H1 close is already back below the swept liquidity level.

### Approach topology motifs

10. `APPROACH_3BAR_HIGHER_CLOSES`
    - the three completed H1 closes immediately before the sweep are strictly increasing.

11. `APPROACH_3BAR_STAIRCASE`
    - over the three completed H1 bars immediately before the sweep:
      highs strictly increase AND lows strictly increase.

12. `APPROACH_LAST_BAR_COMPRESSES_THEN_RECLAIM_EXPANDS`
    - immediately-pre-sweep H1 range < range of the H1 bar before it
      AND reclaim H1 range > immediately-pre-sweep H1 range.

### Entry-time causal motif

13. `PRE_FILL_5M_BEARISH_BREAK`
    - for a filled GAP25 entry, the last fully completed 5m bar before entry is bearish
      AND closes below the low of the completed 5m bar before it.

No post-entry feature, MFE, MAE, terminal result, fixed TP result, hour/session, indicator, or future price path may be used as a character input.

## Candidate rules

Permitted rules are:

- exactly one motif; or
- conjunction of exactly two motifs.

No negated motif is allowed.
No more than two conditions.
No numeric threshold search.

## 2020-2024 construction gates

Baseline is all filled Score-4 BUY_SIDE trades in 2020-2024.

A candidate rule is eligible only if ALL are true:

1. selected N >= 5;
2. structural-event rate >= 60%;
3. structural-event lift over unfiltered BUY_SIDE baseline >= +20 percentage points;
4. structural-completion mean realized R > 0;
5. PF > 1.0;
6. selected structural events occur in at least 2 distinct calendar years;
7. leave-one-selected-trade-out robustness:
   - mean R remains > 0 in at least 80% of leave-one-out samples;
   - event rate remains >= 50% in at least 80% of leave-one-out samples.

Selection among eligible candidates:

1. highest Wilson 95% lower bound of event rate;
2. then highest leave-one-out mean-R pass rate;
3. then highest event rate;
4. then highest mean R;
5. then larger N;
6. then fewer motifs;
7. then lexicographic rule text.

If no candidate is eligible:

`NO_ROBUST_SCORE4_SHORT_STRUCTURAL_CHARACTER`

and the operational decision is:

`DROP_SCORE4_SHORT_FROM_TRADABLE_UNIVERSE`

No later-period rule search is allowed.

## 2025 retrospective consistency

Only after the winning 2020-2024 rule is frozen.

If selected 2025 N >= 2, support requires:

1. selected event rate >= unfiltered 2025 BUY_SIDE event rate;
2. selected mean R >= unfiltered 2025 BUY_SIDE mean R;
3. selected mean R > 0.

If selected N < 2, label 2025 not evaluable.

## 2026 pre-cutoff retrospective consistency

Apply the same frozen rule unchanged.

If selected N >= 2, support uses the same three criteria as 2025.

If selected N < 2, label not evaluable.

No failure or low sample in 2025/2026 permits rule modification.

## Robustness interpretation

Possible final statuses:

### SCORE4_SHORT_STRUCTURAL_CHARACTER_FROZEN_RETROSPECTIVE_SUPPORT
- construction candidate passes all gates;
- every evaluable later retrospective period supports it.

### SCORE4_SHORT_STRUCTURAL_CHARACTER_FROZEN_RETROSPECTIVE_MIXED
- construction candidate passes;
- at least one evaluable later period fails support.

### DROP_SCORE4_SHORT_FROM_TRADABLE_UNIVERSE
- no construction candidate passes the frozen robustness gates.

None of these is fresh independent validation.

## Stop rule

This is the one permitted Score-4 SHORT rediscovery.

If the result is DROP:
- do not create V2;
- do not tune a numeric boundary;
- do not search sessions/hours/indicators;
- continue the SOL stack without Score-4 SHORT.

POST_CUTOFF_DATA=CLOSED
