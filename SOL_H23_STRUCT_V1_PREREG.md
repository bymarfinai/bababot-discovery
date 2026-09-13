# SOL-H23-STRUCT-V1 — Winner-First Structural Discovery Preregistration

## Purpose
Discover whether the existing SOL H23 LONG Development winner has an early, repeatable price-action sequence analogous to a 15-minute opening-range breakout/retest. ORB is a candidate structural language, not a presumed answer.

## Frozen parent cohort
- Pair: SOLUSDT, 5m completed bars.
- Parent habitat: 23:00–00:00 UTC / 06:00–07:00 WIB.
- Parent rule: `DRIVE_DOWN__STR_B80_100`.
- Parent lookback: 15m.
- Parent payoff horizon: 120m.
- Four anchors: 23:00, 23:15, 23:30, 23:45 UTC.
- Development partition only: 2022-01-01 through 2024-12-31 under the existing engine semantics.
- Parent economics remain frozen: $500 notional and $0.75 fee; WIN means parent 120m net PnL > 0, LOSS otherwise.

## Data firewall
Only Development is eligible for discovery. The already-observed 2025–Jul-2026 reference period is not used in V1. August 2026 remains unopened. No OOS/reference result may influence thresholds, feature definitions, ranking, or verdict.

## Structural clock
For every frozen parent occurrence:
1. Candidate activation remains at the original anchor.
2. Build a 15m **response range** from the first three completed 5m bars after activation: `[t, t+15m)`.
3. Observe structural events only from `t+15m` through `t+45m` (six completed 5m bars).
4. Parent WIN/LOSS remains defined only at the frozen `t+120m` payoff horizon.

This makes the structural observation temporally earlier than the parent payoff. V1 is a structural map, not yet a live entry rule, because it intentionally waits up to 45m after parent activation.

## Frozen event grammar
No numerical threshold is optimized in V1.

- `break_high`: first completed 5m close strictly above response-range high during +15..+45m.
- `break_low`: first completed 5m close strictly below response-range low during +15..+45m.
- `high_break_first`: high break occurs before any low break; ties/none are false.
- `low_break_first`: low break occurs before any high break; ties/none are false.
- `sweep_low_before_high_break`: a 5m low trades strictly below response-range low before the first high-break close, while no low-break close has occurred first.
- `reclaim_low_then_high_break`: after such a low sweep, a completed close returns at/above response-range low before the later high-break close.
- `retest_after_high_break`: after a high-break close, a later observed bar has low <= response-range high and close >= response-range high.
- `hold_after_retest`: the next completed 5m bar after the first valid retest closes >= response-range high and remains inside the +45m observation window.
- `break_retest_hold`: `break_high -> retest_after_high_break -> hold_after_retest` in that order.
- `failed_high_break`: after a high-break close, any later completed bar inside the observation window closes below response-range high before a valid hold-after-retest completes.
- `higher_low_after_high_break`: after high break, the minimum subsequent observed low stays strictly above response-range low.

Descriptive continuous fields are also persisted, but they are not threshold-searched in V1: response-range width %, minutes to first high break, breakout displacement / response-range width, and retest depth / response-range width.

VWAP is deliberately excluded from V1 so the core price structure is tested first.

## Frozen sequences to compare
1. `break_high`
2. `high_break_first`
3. `break_retest_hold`
4. `sweep_low_before_high_break`
5. `reclaim_low_then_high_break`
6. `failed_high_break`
7. `higher_low_after_high_break`

## Reporting
For every binary event/sequence report:
- eligible N;
- WIN prevalence;
- LOSS prevalence;
- prevalence delta in percentage points;
- Haldane-corrected odds ratio;
- pooled counts;
- same-direction consistency across the four quarter-hour anchors;
- same-direction consistency across Development years 2022/2023/2024.

## Structural-candidate gate
An event/sequence is a V1 **structural discriminator** only if all are true:
- total parent cohort N >= 160;
- both WIN and LOSS classes >= 40;
- absolute pooled prevalence delta >= 15 percentage points;
- odds ratio >= 1.50 for positive discrimination or <= 0.67 for negative discrimination;
- pooled delta direction is reproduced in at least 3 of 4 anchors where both classes are present;
- pooled delta direction is reproduced in all three Development years where both classes are present.

Passing this gate does **not** authorize live trading. It only promotes the structure to a separately preregistered causal execution experiment.

## Stop rules
- Exactly this fixed grammar is evaluated once.
- No tolerance, window, range length, breakout definition, retest rule, or threshold may be altered after seeing V1 results.
- No feature may be added to rescue a failed result.
- No reference/OOS/August data may be opened in V1.
- If no sequence passes, verdict is `NO_REPEATABLE_EARLY_ORB_LIKE_DISCRIMINATOR_V1`.
- Any follow-up requires a new preregistration and experiment ID.

Research/shadow only.