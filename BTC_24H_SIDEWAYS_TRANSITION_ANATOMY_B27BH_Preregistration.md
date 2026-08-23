# B27BH — BTC 24H SIDEWAYS Transition Anatomy Audit — Preregistration

## Purpose
Determine exactly where the B27BG pooled one-interval flip-back rate comes from, with special focus on whether `SIDEWAYS` is acting as a noisy bridge between the persistent BULL and BEAR states.

This is still **regime-detector research only**. B27BH does not study future returns, liquidity direction, LONG/SHORT mapping, entries, stops, targets, fees, WR, PF, or PnL.

B27BG/B27BE/B27BF remain frozen historical records and are not modified.

## Frozen source and detector
Reuse B27BG exactly:
- BTCUSDT repository 5m source, expected 698,112 rows / 100% coverage;
- complete UTC 4H bars only, exactly 48 constituent 5m bars;
- exact existing B27AG/B27BE `SwingRegime(lookback=5, swing_atr=0.5)` state semantics;
- BULL: `hh>=2`, `hl>=2`, EMA7>EMA20, completed close>EMA20;
- BEAR: `lh>=2`, `ll>=2`, EMA7<EMA20, completed close<EMA20;
- otherwise SIDEWAYS;
- state becomes effective only at completed 4H availability time and remains active until the next completed 4H state;
- global chronological state/episode segmentation; reporting partitions do not reset state.

## B27BG flip-back denominator — frozen reproduction
For every center interval `t`, let:
- `A = state[t-1]`
- `B = state[t]`
- `C = state[t+1]`

Require all three effective intervals to be consecutive exactly 4h apart and `A != B`. Such centers form the B27BG denominator.

A one-interval flip-back is `A != B` and `C == A` (therefore `A -> B -> A`).

B27BH must reproduce the persisted B27BG pooled-major count exactly: **459 flip-backs / 2,202 eligible state-change-centered triples = 20.8%** (allowing only display-rounding differences in the percentage).

## Primary anatomy question
Break all pooled-major one-interval flip-backs into the six possible ordered patterns:
- `BULL -> SIDEWAYS -> BULL`
- `BEAR -> SIDEWAYS -> BEAR`
- `BULL -> BEAR -> BULL`
- `BEAR -> BULL -> BEAR`
- `SIDEWAYS -> BULL -> SIDEWAYS`
- `SIDEWAYS -> BEAR -> SIDEWAYS`

Report count and share of all 459 flip-backs for each pattern, plus external / development / reference_validation counts.

### Frozen primary readout
Tag `SIDEWAYS_MIDDLE_DOMINATES_ONE_BAR_FLIPBACKS` only if:

`count(BULL->SIDEWAYS->BULL) + count(BEAR->SIDEWAYS->BEAR) > 50% of all pooled-major one-interval flip-backs`.

Otherwise tag `SIDEWAYS_MIDDLE_DOES_NOT_DOMINATE_ONE_BAR_FLIPBACKS`.

This is a descriptive detector-anatomy tag, not a redesigned detector and not permission to alter SIDEWAYS semantics post hoc.

## SIDEWAYS episode bridge anatomy
The one-bar statistic can miss multi-bar SIDEWAYS episodes, so independently audit every complete SIDEWAYS episode that is bracketed by a directional state immediately before the episode and a directional state immediately after it, with no chronology gap.

Classify each bracketed SIDEWAYS episode as:
- `BULL -> SIDEWAYS -> BULL` = BULL pause / resume;
- `BEAR -> SIDEWAYS -> BEAR` = BEAR pause / resume;
- `BULL -> SIDEWAYS -> BEAR` = BULL-to-BEAR genuine transition;
- `BEAR -> SIDEWAYS -> BULL` = BEAR-to-BULL genuine transition.

For each class report:
- episode count;
- share of bracketed SIDEWAYS episodes;
- SIDEWAYS duration median / P75 / P90 in 4H intervals and hours;
- duration buckets: exactly 1 bar, exactly 2 bars, 3+ bars;
- same-direction resume versus opposite-direction transition rate overall and separately by originating BULL/BEAR;
- external / development / reference_validation stability.

Episodes touching a data gap or lacking a directional state on either side are reported separately and excluded from the bracketed denominator.

## Additional diagnostic — where SIDEWAYS comes from and where it goes
For every transition into SIDEWAYS from BULL or BEAR, follow only the contiguous SIDEWAYS episode and report its first directional exit:
- returns to origin state;
- exits to opposite directional state;
- remains/censors at data boundary/gap.

No future price information is used; only later detector state labels are examined to characterize state-machine behavior.

## Mandatory assertions
1. Reproduce 698,112 source rows / 100% coverage.
2. Reproduce B27BG effective state sequence and exact 459/2,202 pooled-major flip-back count.
3. Every effective state uses only completed 4H information.
4. Pattern counts sum exactly to total one-interval flip-backs.
5. Bracketed SIDEWAYS episode classes are mutually exclusive and exhaustive among eligible episodes.
6. Partition boundaries are reporting boundaries only and never reset detector chronology.
7. No directional trading inference, entry, stop, target, or economics are introduced.
8. Live BBC unchanged.

## Interpretation boundary
B27BH answers only **whether SIDEWAYS is primarily a transient pause/noise state or a genuine directional bridge, and where the B27BG flip-backs originate**.

Any redesign of SIDEWAYS must be a later separately preregistered experiment. No threshold or state rule is changed in B27BH after observing results.

Research only. Live BBC unchanged.
